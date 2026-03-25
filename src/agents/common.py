from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from dotenv import load_dotenv


load_dotenv()


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json_file(path: str | Path, default: Any) -> Any:
    file_path = Path(path)
    if not file_path.exists():
        return default

    with file_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json_file(path: str | Path, payload: Any) -> None:
    file_path = Path(path)
    ensure_parent_dir(file_path)
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def append_jsonl(path: str | Path, payload: dict[str, Any]) -> None:
    file_path = Path(path)
    ensure_parent_dir(file_path)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def call_json_api(url: str, api_key: str = "", method: str = "GET", timeout: int = 180) -> dict[str, Any]:
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    opener = build_opener(ProxyHandler({}))
    request = Request(url, headers=headers, method=method)

    try:
        with opener.open(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API request failed with status {exc.code}: {payload}") from exc
    except URLError as exc:
        raise RuntimeError(f"API request failed: {exc.reason}") from exc
