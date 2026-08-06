"""Local filesystem storage adapter.

Exposes an S3-like interface (put_object/get_object/delete_object) on purpose:
swapping this module for a real `boto3` S3 client later only requires
reimplementing these three functions, nothing in the routers/business logic
needs to change. Kept local here so the project runs end-to-end without any
cloud credentials.
"""

from pathlib import Path

from .config import settings


def _resolve(key: str) -> Path:
    path = (settings.storage_dir / key).resolve()
    if not str(path).startswith(str(settings.storage_dir.resolve())):
        raise ValueError("Invalid storage key")
    return path


def put_object(key: str, data: bytes) -> str:
    path = _resolve(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return key


def get_object(key: str) -> bytes:
    return _resolve(key).read_bytes()


def delete_object(key: str) -> None:
    path = _resolve(key)
    if path.exists():
        path.unlink()


def object_path(key: str) -> Path:
    return _resolve(key)
