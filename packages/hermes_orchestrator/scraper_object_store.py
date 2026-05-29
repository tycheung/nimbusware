"""S3-compatible / file:// object store for scraper artifacts (Lane D / fo204)."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

import httpx

_S3_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _int_env(name: str, default: int, *, minimum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return max(parsed, minimum)


def object_store_url() -> str:
    return os.environ.get("HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_URL", "").strip()


def object_store_bucket() -> str:
    return os.environ.get("HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_BUCKET", "").strip()


def object_store_configured() -> bool:
    return bool(object_store_url())


def object_store_ready() -> bool:
    return object_store_configured() and bool(object_store_bucket())


def object_store_timeout_seconds() -> int:
    return _int_env("HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_TIMEOUT_SECONDS", 30, minimum=1)


def object_store_delete_max_attempts() -> int:
    return _int_env("HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_DELETE_MAX_ATTEMPTS", 1, minimum=1)


def object_store_primary_requested() -> bool:
    return _truthy_env("HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_PRIMARY")


def object_store_local_mirror_enabled(*, primary: bool) -> bool:
    if not primary:
        return True
    return _truthy_env("HERMES_SCRAPER_ARTIFACT_LOCAL_MIRROR")


def object_store_primary_enabled() -> bool:
    if not object_store_primary_requested():
        return False
    if not object_store_ready():
        return False
    try:
        from nimbusware_env.edition import enterprise_feature_enabled

        return enterprise_feature_enabled("object_store_primary")
    except ImportError:
        return False


def _file_backend_root() -> Path | None:
    url = object_store_url()
    if not url.lower().startswith("file://"):
        return None
    parsed = urlparse(url)
    root = Path(unquote(parsed.path)).expanduser()
    bucket = object_store_bucket()
    if bucket:
        return (root / bucket).resolve()
    return root.resolve()


def _http_object_url(relpath: str) -> str | None:
    if not object_store_ready():
        return None
    base = object_store_url().rstrip("/")
    if base.lower().startswith("file://"):
        return None
    bucket = object_store_bucket()
    clean = relpath.lstrip("/").replace("\\", "/")
    return f"{base}/{quote(bucket, safe='')}/{quote(clean, safe='/')}"


def _file_object_path(relpath: str) -> Path | None:
    root = _file_backend_root()
    if root is None:
        return None
    clean = relpath.lstrip("/").replace("\\", "/")
    return (root / clean).resolve()


def object_store_put_artifact(relpath: str, content: bytes) -> dict[str, Any]:
    """Write artifact bytes to object store (file:// or HTTP PUT)."""
    if not object_store_ready():
        return {"attempted": False, "stored": False, "error": "not_ready"}
    file_path = _file_object_path(relpath)
    if file_path is not None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        return {"attempted": True, "stored": True, "error": None, "backend": "file"}
    url = _http_object_url(relpath)
    if url is None:
        return {"attempted": False, "stored": False, "error": "no_url"}
    try:
        with httpx.Client(timeout=float(object_store_timeout_seconds())) as client:
            resp = client.put(url, content=content)
        if resp.status_code in (200, 201, 204):
            return {"attempted": True, "stored": True, "error": None, "backend": "http"}
        return {"attempted": True, "stored": False, "error": f"http_{resp.status_code}"}
    except httpx.HTTPError as exc:
        return {"attempted": True, "stored": False, "error": str(exc)[:200]}


def object_store_delete_artifact(relpath: str) -> dict[str, Any]:
    """Delete one artifact key (file:// or HTTP DELETE)."""
    if not object_store_ready():
        return {"attempted": False, "deleted": False, "error": None}
    file_path = _file_object_path(relpath)
    if file_path is not None:
        existed = file_path.is_file()
        if existed:
            file_path.unlink(missing_ok=True)
        return {"attempted": True, "deleted": True, "error": None, "attempts_made": 1}
    url = _http_object_url(relpath)
    if url is None:
        return {"attempted": False, "deleted": False, "error": None}
    last_error: str | None = None
    attempts_made = 0
    for _ in range(object_store_delete_max_attempts()):
        attempts_made += 1
        try:
            with httpx.Client(timeout=float(object_store_timeout_seconds())) as client:
                resp = client.delete(url)
            if resp.status_code in (200, 204, 404):
                return {
                    "attempted": True,
                    "deleted": True,
                    "error": None,
                    "attempts_made": attempts_made,
                }
            last_error = f"http_{resp.status_code}"
        except httpx.HTTPError as exc:
            last_error = str(exc)[:200]
    return {
        "attempted": True,
        "deleted": False,
        "error": last_error,
        "attempts_made": attempts_made,
    }


def _parse_s3_list_xml(body: bytes, *, cap: int) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return entries
    for contents in root.findall(f"{_S3_NS}Contents"):
        key_el = contents.find(f"{_S3_NS}Key")
        size_el = contents.find(f"{_S3_NS}Size")
        lm_el = contents.find(f"{_S3_NS}LastModified")
        if key_el is None or key_el.text is None:
            continue
        relpath = key_el.text.replace("\\", "/")
        nbytes = int(size_el.text) if size_el is not None and size_el.text else 0
        mtime_iso = None
        if lm_el is not None and lm_el.text:
            try:
                dt = datetime.fromisoformat(lm_el.text.replace("Z", "+00:00"))
                mtime_iso = dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            except ValueError:
                mtime_iso = lm_el.text
        entries.append({"relpath": relpath, "bytes": nbytes, "mtime_iso": mtime_iso})
        if len(entries) >= cap:
            break
    return entries


def object_store_list_artifacts(*, max_entries: int = 1000) -> list[dict[str, Any]]:
    """List artifact keys from object store (file:// walk or S3 ListObjectsV2)."""
    cap = max(1, int(max_entries))
    root = _file_backend_root()
    if root is not None:
        if not root.is_dir():
            return []
        out: list[dict[str, Any]] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            try:
                st = path.stat()
            except OSError:
                continue
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat().replace(
                "+00:00",
                "Z",
            )
            out.append(
                {
                    "relpath": path.relative_to(root).as_posix(),
                    "bytes": st.st_size,
                    "mtime_iso": mtime,
                },
            )
            if len(out) >= cap:
                break
        return out
    if not object_store_ready():
        return []
    base = object_store_url().rstrip("/")
    bucket = object_store_bucket()
    list_url = f"{base}/{quote(bucket, safe='')}?list-type=2&max-keys={cap}"
    try:
        with httpx.Client(timeout=float(object_store_timeout_seconds())) as client:
            resp = client.get(list_url)
        if resp.status_code != 200:
            return []
        return _parse_s3_list_xml(resp.content, cap=cap)
    except httpx.HTTPError:
        return []
