import asyncio
import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

APP_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
VERSION_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
BUCKET_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]+$')
URL_PATTERN = re.compile(r'^https?://[^\s]+$')
SEARCH_QUERY_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.\s]+$')

DATA_DIR = Path(__file__).parent.parent / ".data"
CONFIG_FILE = DATA_DIR / "config.json"
LOG_DB_FILE = DATA_DIR / "logs.db"
STATIC_DIR = Path(__file__).parent.parent / "frontend" / "dist"


def get_scoop_dir() -> Path:
    """Get scoop installation directory from config or environment."""
    scoop_config = Path.home() / ".config" / "scoop" / "config.json"
    if scoop_config.exists():
        try:
            config = json.loads(scoop_config.read_text(encoding="utf-8"))
            if "root_path" in config:
                return Path(config["root_path"])
        except (json.JSONDecodeError, OSError):
            pass

    scoop_env = os.environ.get("SCOOP")
    if scoop_env:
        return Path(scoop_env)
    return Path.home() / "scoop"


SCOOP_DIR = get_scoop_dir()
SCOOP_APPS_DIR = SCOOP_DIR / "apps"


def read_manifest_file(app_name: str) -> Optional[dict]:
    """Read manifest.json directly from app directory."""
    manifest_path = SCOOP_APPS_DIR / app_name / "current" / "manifest.json"
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def read_install_info(app_name: str) -> Optional[dict]:
    """Read install.json to get bucket info."""
    install_path = SCOOP_APPS_DIR / app_name / "current" / "install.json"
    if install_path.exists():
        try:
            return json.loads(install_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def get_installed_apps_from_dir() -> list[dict]:
    """Get installed apps by scanning apps directory."""
    apps = []
    if not SCOOP_APPS_DIR.exists():
        return apps

    for app_dir in SCOOP_APPS_DIR.iterdir():
        if not app_dir.is_dir():
            continue
        current_link = app_dir / "current"
        if not current_link.exists():
            continue

        app_name = app_dir.name
        manifest = read_manifest_file(app_name)
        install_info = read_install_info(app_name)

        if manifest:
            apps.append({
                "name": app_name,
                "version": manifest.get("version", "unknown"),
                "bucket": install_info.get("bucket", "unknown") if install_info else "unknown",
                "manifest": manifest,
            })
    return apps


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {"search_command": "scoop"}


def save_config(config: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def init_log_db():
    """Initialize SQLite database for operation logs."""
    LOG_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(LOG_DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            operation TEXT NOT NULL,
            command TEXT NOT NULL,
            success INTEGER NOT NULL,
            message TEXT DEFAULT ''
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_time ON logs(time DESC)")
    conn.commit()
    conn.close()


def append_log(operation: str, command: str, success: bool, message: str = ""):
    """Append operation log entry to SQLite."""
    conn = sqlite3.connect(LOG_DB_FILE)
    conn.execute(
        "INSERT INTO logs (time, operation, command, success, message) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), operation, command, 1 if success else 0, message or "")
    )
    conn.commit()
    conn.close()


def read_logs(limit: int = 100) -> list[dict]:
    """Read operation logs from SQLite, newest first."""
    if not LOG_DB_FILE.exists():
        return []
    conn = sqlite3.connect(LOG_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT time, operation, command, success, message FROM logs ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    logs = [
        {"time": row["time"], "operation": row["operation"], "command": row["command"],
         "success": bool(row["success"]), "message": row["message"]}
        for row in cursor
    ]
    conn.close()
    return logs


def clear_logs():
    """Clear all operation logs."""
    if LOG_DB_FILE.exists():
        conn = sqlite3.connect(LOG_DB_FILE)
        conn.execute("DELETE FROM logs")
        conn.commit()
        conn.close()


init_log_db()


OPERATION_MAP = {
    ("GET", "/api/apps"): ("查询已安装应用", "scoop list"),
    ("GET", "/api/buckets"): ("查询软件桶", "scoop bucket list"),
    ("GET", "/api/logs"): None,
    ("DELETE", "/api/logs"): None,
    ("GET", "/api/settings"): None,
    ("POST", "/api/settings"): None,
}


async def get_operation_info(method: str, path: str, query_params: dict, body: dict) -> Optional[tuple[str, str]]:
    """Get operation name and command from request info."""
    if (method, path) in OPERATION_MAP:
        return OPERATION_MAP[(method, path)]

    # GET requests
    if method == "GET":
        if path.startswith("/api/apps/") and path.endswith("/versions"):
            app_name = path.split("/")[3]
            return ("查询版本", f"scoop search {app_name}")

        if path.startswith("/api/apps/") and path.endswith("/related"):
            app_name = path.split("/")[3]
            return ("查询关联应用", f"读取 {app_name} 的 manifest.json")

        if path.startswith("/api/apps/") and path.endswith("/info"):
            app_name = path.split("/")[3]
            return ("查看信息", f"读取 {app_name} 的 manifest.json")

        if path == "/api/search" and "q" in query_params:
            return ("搜索软件", f"scoop search {query_params['q']}")

    # POST requests
    if method == "POST":
        if path == "/api/apps/update":
            apps = body.get("apps", [])
            return ("更新应用", f"scoop update {' '.join(apps)}")

        if path == "/api/apps/uninstall":
            apps = body.get("apps", [])
            return ("卸载应用", f"scoop uninstall {' '.join(apps)}")

        if path == "/api/apps/install":
            name = query_params.get("name", "")
            bucket = body.get("bucket", "")
            cmd = f"scoop install {bucket}/{name}" if bucket else f"scoop install {name}"
            return ("安装应用", cmd)

        if path == "/api/buckets":
            name = body.get("name", "")
            url = body.get("url", "")
            cmd = f"scoop bucket add {name} {url}".strip() if url else f"scoop bucket add {name}"
            return ("添加软件桶", cmd)

        if path == "/api/apps/hold":
            apps = body.get("apps", [])
            return ("锁定应用", f"scoop hold {' '.join(apps)}")

        if path.startswith("/api/apps/") and path.endswith("/hold"):
            app_name = path.split("/")[3]
            return ("锁定应用", f"scoop hold {app_name}")

        if path.startswith("/api/apps/") and path.endswith("/reset"):
            app_name = path.split("/")[3]
            version = body.get("version")
            target_app = body.get("target_app")
            if target_app:
                return ("切换版本", f"scoop reset {target_app}")
            elif version:
                return ("切换版本", f"scoop reset {app_name}@{version}")

    # DELETE requests
    if method == "DELETE":
        if path == "/api/apps/hold":
            apps = body.get("apps", [])
            return ("解锁应用", f"scoop unhold {' '.join(apps)}")

        if path.startswith("/api/apps/") and path.endswith("/hold"):
            app_name = path.split("/")[3]
            return ("解锁应用", f"scoop unhold {app_name}")

        if path.startswith("/api/buckets/"):
            bucket_name = path.split("/")[3]
            return ("移除软件桶", f"scoop bucket rm {bucket_name}")

    return None


def validate_app_name(name: str) -> str:
    if not APP_NAME_PATTERN.match(name):
        raise ValueError(f"Invalid app name: {name}")
    return name


def validate_version(version: str) -> str:
    if not VERSION_PATTERN.match(version):
        raise ValueError(f"Invalid version: {version}")
    return version


def validate_bucket_name(name: str) -> str:
    if not BUCKET_NAME_PATTERN.match(name):
        raise ValueError(f"Invalid bucket name: {name}")
    return name

app = FastAPI(title="Scoop Easy API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_scoop_output(response_body: bytes) -> str:
    """Extract scoop raw output from response JSON."""
    if not response_body:
        return ""
    try:
        data = json.loads(response_body)
    except (json.JSONDecodeError, TypeError):
        return response_body.decode("utf-8", errors="replace")

    if "message" in data:
        return data["message"]
    if "detail" in data:
        return data["detail"]
    if "results" in data and isinstance(data["results"], list) and data["results"]:
        return data["results"][0].get("message", "")
    return ""


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """AOP-style middleware to log all API operations."""
    method = request.method
    path = request.url.path
    query_params = dict(request.query_params)

    body = {}
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        try:
            body_bytes = await request.body()
            if body_bytes:
                body = json.loads(body_bytes)

            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request = Request(request.scope, receive)
        except Exception:
            pass

    info = await get_operation_info(method, path, query_params, body)
    if info is None:
        return await call_next(request)

    operation, cmd = info

    try:
        response = await call_next(request)
        success = response.status_code < 400

        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        message = extract_scoop_output(response_body)
        append_log(operation, cmd, success, message)

        from starlette.responses import Response
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
    except Exception as e:
        append_log(operation, cmd, False, str(e))
        raise


class AppInfo(BaseModel):
    name: str
    version: str
    bucket: str
    updated: Optional[str] = None
    held: bool = False
    has_update: bool = False
    latest_version: Optional[str] = None


class UpdateRequest(BaseModel):
    apps: list[str]

    @field_validator('apps')
    @classmethod
    def validate_apps(cls, v: list[str]) -> list[str]:
        return [validate_app_name(name) for name in v]


class ResetRequest(BaseModel):
    version: Optional[str] = None
    target_app: Optional[str] = None

    @field_validator('version')
    @classmethod
    def validate_ver(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return validate_version(v)
        return v

    @field_validator('target_app')
    @classmethod
    def validate_target(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return validate_app_name(v)
        return v


class VersionInfo(BaseModel):
    name: str
    version: str
    bucket: str


class BucketInfo(BaseModel):
    name: str
    source: str
    updated: Optional[str] = None
    manifests: Optional[int] = None


class AddBucketRequest(BaseModel):
    name: str
    url: Optional[str] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return validate_bucket_name(v)

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not URL_PATTERN.match(v):
            raise ValueError(f"Invalid URL: {v}")
        return v


class SearchResult(BaseModel):
    name: str
    version: str
    bucket: str
    description: Optional[str] = None


class AppManifest(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    homepage: Optional[str] = None
    license: Optional[str] = None
    bin: Optional[list[str]] = None
    shortcuts: Optional[list] = None


class RelatedApp(BaseModel):
    name: str
    version: str
    bucket: str
    shared_bins: list[str]


class SettingsRequest(BaseModel):
    search_command: str
    turbo_mode: bool = False


class OperationLog(BaseModel):
    time: str
    operation: str
    command: str
    success: bool
    message: str = ""


async def run_scoop_command(args: list[str], timeout: int = 120) -> tuple[str, str, int]:
    """Execute scoop command asynchronously."""
    cmd = ["powershell", "-NoProfile", "-Command", f"scoop {' '.join(args)}"]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode("utf-8", errors="ignore"), stderr.decode("utf-8", errors="ignore"), proc.returncode or 0
    except asyncio.TimeoutError:
        proc.kill()
        raise HTTPException(status_code=504, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def parse_list_output(output: str) -> list[dict]:
    """Parse 'scoop list' output."""
    apps = []
    lines = output.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("Installed") or line.startswith("Name") or line.startswith("-"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            name = parts[0]
            version = parts[1]
            bucket = parts[2] if len(parts) > 2 else "main"
            updated = None
            held = False
            if len(parts) > 3:
                updated = parts[3]
                if len(parts) > 4:
                    updated = f"{parts[3]} {parts[4]}"
            if "Held" in line:
                held = True
            apps.append({"name": name, "version": version, "bucket": bucket, "updated": updated, "held": held})
    return apps


def parse_status_output(output: str) -> dict[str, str]:
    """Parse 'scoop status' output to get available updates."""
    updates = {}
    lines = output.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line or "WARN" in line or "Name" in line or line.startswith("-") or "held" in line.lower():
            continue
        parts = line.split()
        if len(parts) >= 3:
            name = parts[0]
            latest = parts[2]
            updates[name] = latest
    return updates


async def get_held_apps() -> set[str]:
    """Get list of held apps."""
    stdout, _, _ = await run_scoop_command(["hold"])
    held = set()
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if line and "held" not in line.lower() and "no apps" not in line.lower():
            held.add(line.split()[0] if line.split() else "")
    held.discard("")
    return held


@app.get("/api/apps", response_model=list[AppInfo])
async def get_installed_apps():
    """Get all installed applications."""
    list_task = run_scoop_command(["list"])
    status_task = run_scoop_command(["status"])

    (list_stdout, _, _), (status_stdout, _, _) = await asyncio.gather(
        list_task, status_task
    )

    apps = parse_list_output(list_stdout)
    updates = parse_status_output(status_stdout)

    result = []
    for app in apps:
        name = app["name"]
        result.append(AppInfo(
            name=name,
            version=app["version"],
            bucket=app["bucket"],
            updated=app.get("updated"),
            held=app.get("held", False),
            has_update=name in updates,
            latest_version=updates.get(name),
        ))
    return result


@app.post("/api/apps/update")
async def update_apps(request: UpdateRequest):
    """Update specified applications."""
    if not request.apps:
        raise HTTPException(status_code=400, detail="No apps specified")

    stdout, stderr, code = await run_scoop_command(["update"] + request.apps, timeout=600)
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr or "Update failed")
    return {"success": True, "message": stdout}


@app.post("/api/apps/uninstall")
async def uninstall_apps(request: UpdateRequest):
    """Uninstall specified applications."""
    if not request.apps:
        raise HTTPException(status_code=400, detail="No apps specified")

    stdout, stderr, code = await run_scoop_command(["uninstall"] + request.apps, timeout=600)
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr or "Uninstall failed")
    return {"success": True, "message": stdout}


@app.post("/api/apps/hold")
async def hold_apps(request: UpdateRequest):
    """Hold multiple apps to prevent updates."""
    if not request.apps:
        raise HTTPException(status_code=400, detail="No apps specified")

    stdout, stderr, code = await run_scoop_command(["hold"] + request.apps, timeout=120)
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr or "Hold failed")
    return {"success": True, "message": stdout}


@app.delete("/api/apps/hold")
async def unhold_apps(request: UpdateRequest):
    """Unhold multiple apps to allow updates."""
    if not request.apps:
        raise HTTPException(status_code=400, detail="No apps specified")

    stdout, stderr, code = await run_scoop_command(["unhold"] + request.apps, timeout=120)
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr or "Unhold failed")
    return {"success": True, "message": stdout}


@app.post("/api/apps/{name}/hold")
async def hold_app(name: str):
    """Hold an app to prevent updates."""
    validate_app_name(name)
    stdout, stderr, code = await run_scoop_command(["hold", name])
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr or "Failed to hold app")
    return {"success": True, "message": stdout}


@app.delete("/api/apps/{name}/hold")
async def unhold_app(name: str):
    """Unhold an app to allow updates."""
    validate_app_name(name)
    stdout, stderr, code = await run_scoop_command(["unhold", name])
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr or "Failed to unhold app")
    return {"success": True, "message": stdout}


@app.get("/api/apps/{name}/versions", response_model=list[VersionInfo])
async def get_available_versions(name: str):
    """Get available versions for an app from all buckets."""
    validate_app_name(name)

    config = load_config()
    use_scoop_search = config.get("search_command", "scoop") == "scoop-search"

    if use_scoop_search:
        cmd = ["powershell", "-NoProfile", "-Command", f"scoop-search {name}"]
    else:
        cmd = ["powershell", "-NoProfile", "-Command", f"scoop search {name}"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    versions = []
    lines = output.strip().split("\n")

    if use_scoop_search:
        current_bucket = "unknown"
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("'") and "bucket" in line.lower():
                current_bucket = line.split("'")[1] if "'" in line else "unknown"
                continue
            if line.startswith("Results"):
                continue
            match = re.match(r'^(\S+)\s+\(([^)]+)\)', line)
            if match:
                app_name = match.group(1)
                version = match.group(2)
                if app_name.lower() == name.lower() or app_name.lower().startswith(f"{name.lower()}-"):
                    versions.append(VersionInfo(
                        name=app_name,
                        version=version,
                        bucket=current_bucket,
                    ))
    else:
        for line in lines:
            line = line.strip()
            if not line or "Results" in line or line.startswith("-") or line.startswith("Name"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                app_name = parts[0]
                version = parts[1]
                source = parts[2]
                if app_name.lower() == name.lower() or app_name.lower().startswith(f"{name.lower()}-"):
                    versions.append(VersionInfo(
                        name=app_name,
                        version=version,
                        bucket=source,
                    ))

    return versions


@app.post("/api/apps/{name}/reset")
async def reset_app(name: str, request: ResetRequest):
    """Reset an app to a specific version or switch to a related app."""
    validate_app_name(name)

    if request.target_app:
        stdout, stderr, code = await run_scoop_command(["reset", request.target_app], timeout=300)
    elif request.version:
        stdout, stderr, code = await run_scoop_command(["reset", f"{name}@{request.version}"], timeout=300)
    else:
        raise HTTPException(status_code=400, detail="Either version or target_app is required")

    if code != 0:
        raise HTTPException(status_code=400, detail=stderr or "Failed to reset app")
    return {"success": True, "message": stdout}


@app.get("/api/buckets", response_model=list[BucketInfo])
async def get_buckets():
    """Get all configured buckets."""
    stdout, _, _ = await run_scoop_command(["bucket", "list"])
    buckets = []
    lines = stdout.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("Name") or line.startswith("-"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            name = parts[0]
            source = parts[1]
            updated = None
            manifests = None
            if len(parts) >= 4:
                updated = f"{parts[2]} {parts[3]}"
                if len(parts) >= 5 and parts[4].isdigit():
                    manifests = int(parts[4])
            buckets.append(BucketInfo(name=name, source=source, updated=updated, manifests=manifests))
    return buckets


@app.post("/api/buckets")
async def add_bucket(request: AddBucketRequest):
    """Add a new bucket."""
    cmd_args = ["bucket", "add", request.name]
    if request.url:
        cmd_args.append(request.url)
    stdout, stderr, code = await run_scoop_command(cmd_args, timeout=300)
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr or "Failed to add bucket")
    return {"success": True, "message": stdout}


@app.delete("/api/buckets/{name}")
async def remove_bucket(name: str):
    """Remove a bucket."""
    validate_bucket_name(name)
    stdout, stderr, code = await run_scoop_command(["bucket", "rm", name])
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr or "Failed to remove bucket")
    return {"success": True, "message": stdout}


@app.get("/api/settings")
async def get_settings():
    """Get application settings."""
    return load_config()


@app.post("/api/settings")
async def update_settings(request: SettingsRequest):
    """Update application settings."""
    config = load_config()
    config["search_command"] = request.search_command
    config["turbo_mode"] = request.turbo_mode
    save_config(config)
    return {"success": True}


@app.get("/api/logs", response_model=list[OperationLog])
async def get_logs(limit: int = 100):
    """Get operation logs."""
    return read_logs(limit)


@app.delete("/api/logs")
async def delete_logs():
    """Clear all operation logs."""
    clear_logs()
    return {"success": True}


@app.get("/api/search", response_model=list[SearchResult])
async def search_apps(q: str):
    """Search for apps using configured search command."""
    if not q or not SEARCH_QUERY_PATTERN.match(q):
        raise HTTPException(status_code=400, detail="Invalid search query")

    config = load_config()
    use_scoop_search = config.get("search_command", "scoop") == "scoop-search"

    if use_scoop_search:
        cmd = ["powershell", "-NoProfile", "-Command", f"scoop-search {q}"]
    else:
        cmd = ["powershell", "-NoProfile", "-Command", f"scoop search {q}"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    results = []
    lines = output.strip().split("\n")

    if use_scoop_search:
        current_bucket = "unknown"
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("'") and "bucket" in line.lower():
                current_bucket = line.split("'")[1] if "'" in line else "unknown"
                continue
            if line.startswith("Results"):
                continue
            match = re.match(r'^(\S+)\s+\(([^)]+)\)', line)
            if match:
                name = match.group(1)
                version = match.group(2)
                results.append(SearchResult(name=name, version=version, bucket=current_bucket))
    else:
        for line in lines:
            line = line.strip()
            if not line or line.startswith("Results") or line.startswith("-") or line.startswith("Name"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                name = parts[0]
                version = parts[1]
                source = parts[2]
                results.append(SearchResult(name=name, version=version, bucket=source))

    return results


@app.post("/api/apps/install")
async def install_app(request: ResetRequest, name: str):
    """Install an app."""
    validate_app_name(name)
    install_target = f"{name}@{request.version}" if request.version else name
    stdout, stderr, code = await run_scoop_command(["install", install_target], timeout=300)
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr or "Failed to install app")
    return {"success": True, "message": stdout}


@app.get("/api/apps/{name}/info")
async def get_app_info(name: str):
    """Get app manifest by reading manifest.json directly."""
    validate_app_name(name)

    manifest = read_manifest_file(name)
    if manifest:
        return manifest

    stdout, stderr, code = await run_scoop_command(["cat", name])
    if code != 0:
        raise HTTPException(status_code=400, detail=stderr or "App not found")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"raw": stdout}


def extract_bin_names(bin_field) -> set[str]:
    """Extract executable names from manifest bin field."""
    bins = set()
    if not bin_field:
        return bins
    if isinstance(bin_field, str):
        bins.add(Path(bin_field).stem.lower())
    elif isinstance(bin_field, list):
        for item in bin_field:
            if isinstance(item, str):
                bins.add(Path(item).stem.lower())
            elif isinstance(item, list) and len(item) >= 2:
                bins.add(Path(item[1]).stem.lower())
    return bins


def get_app_executables(app_name: str, manifest: dict) -> set[str]:
    """Get all executable names for an app from bin field or env_add_path."""
    bins = extract_bin_names(manifest.get("bin"))

    if not bins:
        env_add_path = manifest.get("env_add_path")
        if env_add_path:
            app_dir = SCOOP_APPS_DIR / app_name / "current"
            if isinstance(env_add_path, str):
                bin_dir = app_dir / env_add_path
                if bin_dir.exists():
                    for exe in bin_dir.glob("*.exe"):
                        bins.add(exe.stem.lower())
            elif isinstance(env_add_path, list):
                for path in env_add_path:
                    bin_dir = app_dir / path
                    if bin_dir.exists():
                        for exe in bin_dir.glob("*.exe"):
                            bins.add(exe.stem.lower())

    return bins


@app.get("/api/apps/{name}/related", response_model=list[RelatedApp])
async def get_related_apps(name: str):
    """Get installed apps that share bin executables with the specified app."""
    validate_app_name(name)

    target_manifest = read_manifest_file(name)
    if not target_manifest:
        return []

    target_bins = get_app_executables(name, target_manifest)
    if not target_bins:
        return []

    installed_apps = get_installed_apps_from_dir()

    related = []
    for app in installed_apps:
        app_name = app["name"]
        if app_name.lower() == name.lower():
            continue

        app_manifest = app.get("manifest")
        if not app_manifest:
            continue

        app_bins = get_app_executables(app_name, app_manifest)
        shared = target_bins & app_bins
        if shared:
            related.append(RelatedApp(
                name=app_name,
                version=app["version"],
                bucket=app["bucket"],
                shared_bins=list(shared),
            ))

    return related


# Mount static files for desktop mode (must be after all API routes)
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = STATIC_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
