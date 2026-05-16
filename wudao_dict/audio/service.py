import logging
from os import replace

from requests import get
from requests.exceptions import ConnectionError, ReadTimeout, RequestException, Timeout

from ..core import PronounceAccent, load_config
from ..dict import get_youdao_pronunciation_audio_url
from .cache import (
    cleanup_audio_cache,
    ensure_audio_parent_dir,
    get_audio_cache_path,
    get_cached_audio_path,
    update_audio_cache_index,
)

LOGGER = logging.getLogger("wudao-dict")


def ensure_pronunciation_file(word: str, accent: PronounceAccent, provider: str = "youdao") -> str:
    cached_path = get_cached_audio_path(provider, accent, word)
    if cached_path:
        return cached_path

    if provider != "youdao":
        raise ValueError(f"Unsupported audio provider: {provider}")

    download_url = get_youdao_pronunciation_audio_url(word, accent)
    _, target_path = get_audio_cache_path(provider, accent, word)
    temp_path = f"{target_path}.tmp"

    ensure_audio_parent_dir(target_path)
    _download_audio_file(download_url, temp_path)
    replace(temp_path, target_path)
    update_audio_cache_index(provider, accent, word, target_path)

    LOGGER.info(f"Cache pronunciation audio: {target_path}")

    conf = load_config()
    cleanup_audio_cache(conf["audio_cache_max_mb"] * 1024 * 1024)

    return target_path


def _download_audio_file(url: str, file_path: str):
    try:
        response = get(url, stream=True, timeout=(2, 5))
    except (Timeout, ReadTimeout, ConnectionError, RequestException) as error:
        raise RuntimeError(f"Failed to download pronunciation audio: {error}") from error

    if response.status_code != 200:
        raise RuntimeError(f"Failed to download pronunciation audio: {response.status_code}")

    with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


__all__ = ["ensure_pronunciation_file"]
