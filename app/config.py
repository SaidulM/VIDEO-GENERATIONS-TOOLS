from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
SKILLS_DIR = ROOT / "skills"
WORKSPACE = ROOT / "workspace"
OUTPUTS = WORKSPACE / "outputs"
UPLOADS = WORKSPACE / "uploads"
LOCAL_ENV = ROOT / ".env.local"

for directory in (WORKSPACE, OUTPUTS, UPLOADS):
    directory.mkdir(parents=True, exist_ok=True)

load_dotenv(LOCAL_ENV, override=True)
load_dotenv(ROOT / ".env", override=False)


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def put_local_setting(name: str, value: str) -> None:
    from dotenv import set_key
    LOCAL_ENV.touch(exist_ok=True)
    try:
        os.chmod(LOCAL_ENV, 0o600)
    except OSError:
        pass
    set_key(str(LOCAL_ENV), name, value, quote_mode="always")
    os.environ[name] = value
