import hashlib
from json import dump, load
from os import makedirs, remove
from os.path import dirname, exists, getsize
from time import time
from typing import Any, Optional, Tuple

from ..core import AUDIO_CACHE_DIR, AUDIO_CACHE_INDEX_FILE, PronounceAccent


def _ensure_audio_cache_dir():
    if not exists(AUDIO_CACHE_DIR):
        makedirs(AUDIO_CACHE_DIR)


def _load_audio_index() -> "dict[str, dict[str, Any]]":
    _ensure_audio_cache_dir()

    if not exists(AUDIO_CACHE_INDEX_FILE):
        return {}

    with open(AUDIO_CACHE_INDEX_FILE, "r", encoding="utf-8") as f:
        return load(f)


def _save_audio_index(index_data: "dict[str, dict[str, Any]]"):
    _ensure_audio_cache_dir()

    with open(AUDIO_CACHE_INDEX_FILE, "w", encoding="utf-8") as f:
        dump(index_data, f, ensure_ascii=False, indent=2)


def normalize_audio_word(word: str) -> str:
    return word.strip().lower()


def build_audio_cache_key(provider: str, accent: PronounceAccent, word: str) -> str:
    normalized_word = normalize_audio_word(word)
    raw_key = f"{provider}:{accent}:{normalized_word}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_audio_cache_path(provider: str, accent: PronounceAccent, word: str) -> Tuple[str, str]:
    cache_key = build_audio_cache_key(provider, accent, word)
    shard = cache_key[:2]
    file_path = f"{AUDIO_CACHE_DIR}/{provider}/{accent}/{shard}/{cache_key}.mp3"
    return cache_key, file_path


def get_cached_audio_path(provider: str, accent: PronounceAccent, word: str) -> Optional[str]:
    cache_key, cache_path = get_audio_cache_path(provider, accent, word)
    index_data = _load_audio_index()

    if exists(cache_path):
        now = time()
        entry = index_data.get(cache_key, {})
        entry.update({
            "provider": provider,
            "accent": accent,
            "word": normalize_audio_word(word),
            "path": cache_path,
            "last_accessed_at": now,
            "file_size": _get_file_size(cache_path)
        })
        if "created_at" not in entry:
            entry["created_at"] = now
        index_data[cache_key] = entry
        _save_audio_index(index_data)
        return cache_path

    if cache_key in index_data:
        index_data.pop(cache_key)
        _save_audio_index(index_data)

    return None


def update_audio_cache_index(provider: str, accent: PronounceAccent, word: str, file_path: str):
    cache_key, _ = get_audio_cache_path(provider, accent, word)
    index_data = _load_audio_index()
    now = time()
    index_data[cache_key] = {
        "provider": provider,
        "accent": accent,
        "word": normalize_audio_word(word),
        "path": file_path,
        "created_at": now,
        "last_accessed_at": now,
        "file_size": _get_file_size(file_path)
    }
    _save_audio_index(index_data)


def ensure_audio_parent_dir(file_path: str):
    parent_dir = dirname(file_path)
    if not exists(parent_dir):
        makedirs(parent_dir)


def cleanup_audio_cache(max_cache_bytes: int):
    if max_cache_bytes <= 0:
        return

    index_data = _load_audio_index()
    stale_keys = []

    for cache_key, entry in index_data.items():
        path = entry.get("path", "")
        if not path or not exists(path):
            stale_keys.append(cache_key)
            continue
        entry["file_size"] = _get_file_size(path)

    for cache_key in stale_keys:
        index_data.pop(cache_key, None)

    total_size = sum(int(entry.get("file_size", 0)) for entry in index_data.values())

    if total_size <= max_cache_bytes:
        _save_audio_index(index_data)
        return

    sorted_items = sorted(index_data.items(), key=lambda item: float(item[1].get("last_accessed_at", 0)))

    for cache_key, entry in sorted_items:
        if total_size <= max_cache_bytes:
            break

        path = entry.get("path", "")
        file_size = int(entry.get("file_size", 0))

        if path and exists(path):
            remove(path)

        total_size -= file_size
        index_data.pop(cache_key, None)

    _save_audio_index(index_data)


def _get_file_size(file_path: str) -> int:
    if not exists(file_path):
        return 0

    return getsize(file_path)


__all__ = [
    "build_audio_cache_key",
    "cleanup_audio_cache",
    "ensure_audio_parent_dir",
    "get_audio_cache_path",
    "get_cached_audio_path",
    "normalize_audio_word",
    "update_audio_cache_index"
]
