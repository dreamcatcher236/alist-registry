# alist-registry

<div align="center">

**[AList v4](https://github.com/alist-org/alist) 社区插件与主题索引**

[![Validate](https://github.com/AlistGo/alist-registry/actions/workflows/validate.yml/badge.svg)](https://github.com/AlistGo/alist-registry/actions/workflows/validate.yml)
[![Publish](https://github.com/AlistGo/alist-registry/actions/workflows/publish.yml/badge.svg)](https://github.com/AlistGo/alist-registry/actions/workflows/publish.yml)
[![License](https://img.shields.io/github/license/AlistGo/alist-registry)](LICENSE)

[English](README.md) | [简体中文](README_cn.md)

</div>

一个可添加到 AList v4 的插件源与主题源(管理后台 → 插件 → 源 / 管理后台 →
外观 → 主题市场)。非官方索引——由社区维护的第三方插件与主题列表,所有条目
经 CI 校验,格式对齐 `alist-org/alist` 后端实际解析的 schema。

## 目录

- [添加此源](#添加此源)
- [索引格式](#索引格式)
  - [插件索引条目](#插件索引条目)
  - [主题目录条目](#主题目录条目)
- [仓库结构](#仓库结构)
- [签名与信任](#签名与信任)
- [如何贡献](#如何贡献)
- [校验与-ci](#校验与-ci)
- [许可证](#许可证)

## 添加此源

**插件** —— *管理后台 → 插件 → 源 → 添加源*:

| 字段 | 值 |
|---|---|
| 名称 | `alist-registry`(可自定义) |
| 索引地址 | `https://raw.githubusercontent.com/AlistGo/alist-registry/main/dist/plugins/index.json` |
| 公钥 | 见[签名与信任](#签名与信任) |

**主题** —— *管理后台 → 外观 → 主题市场 → 添加源*:

| 字段 | 值 |
|---|---|
| 名称 | `alist-registry` |
| 索引地址 | `https://raw.githubusercontent.com/AlistGo/alist-registry/main/dist/themes/index.json` |
| 公钥 | 可留空——留空则所有条目按 `untrusted` 安装 |

两份索引文件均由 CI 根据 `plugins/` 与 `themes/` 生成
([`publish.yml`](.github/workflows/publish.yml)),每次合并到 `main` 后提交。

## 索引格式

两份索引文件与 `alist-org/alist` 的 Go 结构体逐字段对齐,CI 在每个 PR 上
强制校验。

### 插件索引条目

对应 `internal/extension/index.go` 的 `IndexEntry`——`GET .../plugins/sources`
抓取、`extension.FetchIndex` 解析的就是这个数组。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 反域名格式,`^[a-zA-Z0-9][a-zA-Z0-9._-]*$`,不含 `..`——须与 `plugin.json` 自身的 `id` 一致 |
| `name` | string | 是 | 展示名称 |
| `version` | string | 是 | 纯 `MAJOR.MINOR.PATCH` |
| `kind` | string | 是 | 单个 `ext.Kind` 值,如 `StorageDriver` |
| `core_api` | string | 是 | semver 约束,如 `^0.1.0` |
| `sha256` | string | 是 | `url` 处 `.tar.gz` 的十六进制 sha256 |
| `url` | string | 是 | 包的 `https://` 下载地址 |
| `sig` | string | 否 | base64 分离签名,仅供展示——后端安装时不会用它比对下载的字节 |
| `license` | string | 是 | 须为开源许可证;`proprietary`(或任何闭源许可证)会被拒绝 |
| `source_url` | string | 是 | 缺失会被视为闭源 |
| `pricing` | string | 是 | `free` 或 `paid`;`paid` 会被拒绝 |

签名校验发生在 `.tar.gz` 内部,而不是这份索引的 `sha256`/`sig` 字段上。每个
包都是一个目录,包含 `plugin.json`、二进制文件、`checksums.txt`(其余所有
文件的 sha256 清单)以及 `signature`(用 `alist plugin sign` 对
`checksums.txt` 做的 ed25519 签名)。`extension.TieredVerifier.DetermineTier`
在安装时读取下载压缩包内部的 `checksums.txt`/`signature`,从不读索引条目
自身的 `sha256`/`sig`。内部没有 `checksums.txt`/`signature` 的包,无论索
引怎么写,都会安装为第三方(🔴)。本仓库的 CI 仍会用真实下载的字节校验
`sha256`,以便发现过期或写错的条目,但这项校验属于本索引,不属于 AList
后端。

### 主题目录条目

对应 `internal/thememarket/thememarket.go` 的 `CatalogEntry`——主题源索引
地址提供的就是这个数组。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 目录条目自身的 id,与下载后描述文件自身的 `"id"` 字段是不同的命名空间 |
| `name` | string | 否 | 展示名称 |
| `author` | string | 否 | |
| `version` | string | 否 | 若填写,使用纯 `MAJOR.MINOR.PATCH`,以便升级/回退比较有明确定义 |
| `url` | string | 是 | 主题 JSON 描述文件的 `https://` 地址 |
| `sha256` | string | 是 | `url` 处描述文件的十六进制 sha256——后端在安装时强制校验(`thememarket.DownloadTheme`) |
| `preview` | string | 否 | 预览图的 `https://` 地址 |
| `has_js` | bool | 否 | 描述文件是否带有非空的 `js` 字段 |
| `mode` | string | 否 | `light`、`dark` 或不填——仅展示用,不会被强制校验 |
| `signature` | string | 否 | 对 `id\|version\|sha256\|url`(`canonicalEntrySigningInput`)的十六进制 ed25519 签名——仅当源配置了公钥时才必填并被校验 |

主题源的公钥是可选的(`thememarket.Source.PubKey`):不配置时,该源的每个
主题都按 `untrusted` 安装。配置了公钥后,该源的每个条目都必须携带可验证的
`signature`,否则拒绝安装。

主题描述文件本身只需是一个合法 JSON 对象,并带有非空字符串的 `"id"` 字段
(`ValidateDescriptor`)。色彩 token、CSS 清理、JS 门控在前端加载时校验。

## 仓库结构

```
plugins/<plugin-id>/entry.json   每个插件一个文件,id = 目录名
themes/<theme-id>/entry.json     每个主题一个文件,id = 目录名
themes/<theme-id>/theme.json     (可选)主题描述文件,如果托管在本仓库
dist/plugins/index.json          自动生成:发布的插件源索引
dist/themes/index.json           自动生成:发布的主题源目录
scripts/                         校验脚本 + 索引生成脚本(纯 Python 标准库)
```

`dist/` 由 CI 生成,每次合并到 `main` 后自动提交——请勿手动编辑。

## 签名与信任

本仓库的 ed25519 公钥,用于维护者亲自审查并签名过的条目:

```
44447605a7bc68e1a4acca29d1d4d3bfb21575fc83d432a18d731de50d5da158
```

对应的私钥不在本仓库中,也不是 CI 密钥;它由维护者离线保管,只用于维护者
真正从源码重新构建并审查过的包。`plugins/` 目录下的大多数条目未用这把密钥
签名,会以第三方(🔴)身份安装,与直接用 URL 安装插件同一信任等级。如果希
望自己的提交被审查,请在 PR 中说明——签名从不自动进行。

[`plugins/com.example.demoplugin`](plugins/com.example.demoplugin) 用这把
密钥签过名,用于验证格式与「已验证」安装路径。

## 如何贡献

参见 [CONTRIBUTING.md](CONTRIBUTING.md)(英文)了解如何提交插件或主题;也
可以先用 [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/) 下的模板开
一个 issue。

## 校验与 CI

[`scripts/validate.py`](scripts/validate.py) 校验每个 `entry.json`:必填字
段、仅允许 `https://` 地址、对下载的包/描述文件做真实 sha256 比对、严格的
`MAJOR.MINOR.PATCH` 版本号、合法的插件 id/kind,以及(给定一个 git 引用作
对比基准时)更新是否让版本号回退。

```bash
python3 scripts/validate.py            # 完整校验,包含下载
python3 scripts/validate.py --no-hash  # 仅格式校验,不联网
```

[`scripts/build_index.py`](scripts/build_index.py) 把所有条目聚合进
`dist/plugins/index.json` / `dist/themes/index.json`。CI 在每次推送到
`main` 且校验通过后运行此脚本。

## 许可证

[MIT](LICENSE)。
