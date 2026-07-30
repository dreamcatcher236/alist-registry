"""Shared schema constants and helpers for validate.py / build_index.py.

These constants mirror alist-org/alist's Go source, field for field. Where the
comment says "mirrors <path>", that Go file is the source of truth -- if the
backend ever changes, update this file to match it, not the other way around.
"""
import hashlib
import json
import re
import urllib.request
import urllib.error

# --- plugin index entry: mirrors internal/extension/index.go IndexEntry ---
PLUGIN_REQUIRED_FIELDS = [
    "id", "name", "version", "kind", "core_api", "sha256", "url",
    "license", "source_url", "pricing",
]
PLUGIN_OPTIONAL_FIELDS = ["sig"]
PLUGIN_ALL_FIELDS = set(PLUGIN_REQUIRED_FIELDS + PLUGIN_OPTIONAL_FIELDS)

# mirrors internal/extension/manifest.go knownKinds, minus
# unimplementedKindReasons (kinds that are recognized but hard-rejected at
# install time -- listing one here would be a promise the backend refuses to
# keep).
PLUGIN_KNOWN_KINDS = {
    "StorageDriver", "AuthProvider", "AuthNMethod", "OfflineDownloadTool",
    "ArchiveTool", "SearchIndexer", "EventHook", "ScheduledJob",
    "NotificationChannel", "Action", "Previewer", "UIPanel", "APIRoute",
    "AccessProtocol", "Feature", "BackgroundService", "FeatureBundle",
    "FileDecorator",
}
PLUGIN_UNIMPLEMENTED_KINDS = {"FileTransformer", "MetadataProvider", "Thumbnailer"}

# mirrors internal/extension/manifest.go pluginIDRe
ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
# mirrors internal/extension/semver.go parseSemver: plain MAJOR.MINOR.PATCH,
# no pre-release/build suffix (the registry requires strict semver so version
# comparisons are always well-defined; the backend itself is more lenient for
# theme entries, but there is no reason for OUR entries to be).
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
# mirrors internal/extension/sources.go / internal/thememarket/thememarket.go
# sourceNamePattern (not used for entry ids directly, but the same charset
# constraint is reused for consistency).
PRICING_VALUES = {"free", "paid"}

# --- theme catalog entry: mirrors internal/thememarket/thememarket.go CatalogEntry ---
THEME_REQUIRED_FIELDS = ["id", "url", "sha256"]
THEME_OPTIONAL_FIELDS = ["name", "author", "version", "preview", "has_js", "mode", "signature"]
THEME_ALL_FIELDS = set(THEME_REQUIRED_FIELDS + THEME_OPTIONAL_FIELDS)
THEME_MODE_VALUES = {"", "light", "dark"}

MAX_PLUGIN_PACKAGE_BYTES = 256 << 20  # mirrors server/handles/plugins.go downloadPackage's io.LimitReader
MAX_THEME_BYTES = 512 << 10  # mirrors internal/thememarket/thememarket.go MaxThemeDownloadBytes


class ValidationError(Exception):
    """One human-readable validation failure, with the offending path attached."""

    def __init__(self, path, message):
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message


def require_https(url, path):
    if not (url.startswith("https://")):
        raise ValidationError(path, f'url must start with "https://" (got {url!r})')


def sha256_of_url(url, path, max_bytes, timeout=30):
    """Downloads url (bounded by max_bytes+1) and returns its hex sha256.

    Raises ValidationError with a readable message on any network failure --
    callers should not have to guess why a submission's hash could not be
    checked.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "alist-registry-ci"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                raise ValidationError(path, f"fetching {url} returned HTTP {resp.status}")
            h = hashlib.sha256()
            total = 0
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ValidationError(
                        path, f"{url} exceeds the {max_bytes} byte size cap"
                    )
                h.update(chunk)
            return h.hexdigest(), total
    except urllib.error.HTTPError as e:
        raise ValidationError(path, f"could not fetch {url}: HTTP {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise ValidationError(path, f"could not fetch {url}: {e.reason}")


def is_hex_sha256(s):
    return bool(re.fullmatch(r"[0-9a-f]{64}", s or "", re.IGNORECASE))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValidationError(path, f"not valid JSON: {e}")
