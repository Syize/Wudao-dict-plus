import os
import subprocess
import sys
import threading
from importlib import import_module
from os.path import dirname, exists, join
from shutil import which
from typing import Any, List

from ..core import AudioPlayerBackend, PlaybackResponseMessage, load_config, save_config

_LINUX_AUDIO_BACKENDS = ("mpv", "ffplay", "paplay")
_ACTIVE_VLC_PLAYERS: "list[tuple[Any, Any]]" = []


def play_audio(file_path: str) -> PlaybackResponseMessage:
    if sys.platform == "darwin":
        return _play_audio_macos(file_path)

    if os.name == "nt":
        return _play_audio_windows(file_path)

    return _play_audio_linux(file_path)


def _play_audio_macos(file_path: str) -> PlaybackResponseMessage:
    if which("afplay") is None:
        return _playback_response(
            status="afplay_not_found",
            backend="",
            message="Cannot find `afplay`. Please check your macOS audio environment."
        )

    _save_audio_backend("afplay")
    _spawn_audio_process(["afplay", file_path])
    return _playback_response("ok", "afplay", "Pronunciation playback started.")


def _play_audio_linux(file_path: str) -> PlaybackResponseMessage:
    conf = load_config()
    backend = conf["audio_player_backend"]

    if backend in _LINUX_AUDIO_BACKENDS:
        response = _play_audio_with_linux_backend(backend, file_path)
        if response["status"] == "ok":
            return response
        _save_audio_backend("")

    for candidate in _LINUX_AUDIO_BACKENDS:
        if which(candidate) is None:
            continue

        response = _play_audio_with_linux_backend(candidate, file_path)
        if response["status"] == "ok":
            _save_audio_backend(candidate)
            return response

    return _playback_response(
        status="linux_backend_not_found",
        backend="",
        message="Cannot find an available Linux audio backend. Please install `mpv`, `ffplay`, or `paplay`."
    )


def _play_audio_with_linux_backend(backend: str, file_path: str) -> PlaybackResponseMessage:
    if which(backend) is None:
        return _playback_response(
            status="backend_not_found",
            backend=backend,  # type: ignore[arg-type]
            message=f"Cannot find audio backend `{backend}`."
        )

    try:
        _spawn_audio_process(_build_linux_audio_command(backend, file_path))
    except (FileNotFoundError, OSError) as error:
        return _playback_response(
            status="backend_broken",
            backend=backend,  # type: ignore[arg-type]
            message=f"Failed to start audio backend `{backend}`: {error}"
        )

    return _playback_response("ok", backend, "Pronunciation playback started.")  # type: ignore[arg-type]


def _play_audio_windows(file_path: str) -> PlaybackResponseMessage:
    conf = load_config()
    vlc_path = conf["vlc_path"].strip()

    if not vlc_path or not exists(vlc_path):
        return _playback_response(
            status="vlc_path_invalid",
            backend="",
            message="VLC path is not configured or invalid."
        )

    try:
        vlc_module = _import_vlc_module(vlc_path, conf["vlc_lib_path"].strip())
    except ImportError:
        return _playback_response(
            status="vlc_not_installed",
            backend="",
            message="python-vlc is not installed. Please install `python-vlc` and VLC."
        )
    except (FileNotFoundError, OSError) as error:
        return _playback_response(
            status="vlc_path_invalid",
            backend="",
            message=f"Invalid VLC configuration: {error}"
        )

    try:
        instance = vlc_module.Instance()
        player = instance.media_player_new()
        media = instance.media_new(file_path)
        player.set_media(media)
        player.play()
        _keep_vlc_player_alive(instance, player, vlc_module)
    except Exception as error:
        return _playback_response(
            status="play_failed",
            backend="vlc",
            message=f"Failed to start VLC playback: {error}"
        )

    _save_audio_backend("vlc")
    return _playback_response("ok", "vlc", "Pronunciation playback started.")


def _import_vlc_module(vlc_path: str, vlc_lib_path: str):
    if vlc_lib_path:
        if not exists(vlc_lib_path):
            raise FileNotFoundError(f"Cannot find libvlc path: {vlc_lib_path}")
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(vlc_lib_path)  # type: ignore

    vlc_dir = dirname(vlc_path)
    if not exists(vlc_dir):
        raise FileNotFoundError(f"Cannot find VLC directory: {vlc_dir}")

    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(vlc_dir)   # type: ignore

    plugins_dir = join(vlc_dir, "plugins")
    if exists(plugins_dir):
        os.environ["VLC_PLUGIN_PATH"] = plugins_dir

    path_env = os.environ.get("PATH", "")
    if vlc_dir not in path_env.split(os.pathsep):
        os.environ["PATH"] = f"{vlc_dir}{os.pathsep}{path_env}" if path_env else vlc_dir

    return import_module("vlc")


def _keep_vlc_player_alive(instance: Any, player: Any, vlc_module: Any):
    _ACTIVE_VLC_PLAYERS.append((instance, player))

    def _cleanup():
        try:
            end_states = {
                vlc_module.State.Ended,
                vlc_module.State.Error,
                vlc_module.State.Stopped
            }
            while True:
                state = player.get_state()
                if state in end_states:
                    break
                if state == vlc_module.State.NothingSpecial:
                    pass
                threading.Event().wait(0.2)
        finally:
            try:
                player.stop()
            except Exception:
                pass
            try:
                player.release()
            except Exception:
                pass
            try:
                instance.release()
            except Exception:
                pass
            try:
                _ACTIVE_VLC_PLAYERS.remove((instance, player))
            except ValueError:
                pass

    threading.Thread(target=_cleanup, daemon=True).start()


def _build_linux_audio_command(backend: str, file_path: str) -> List[str]:
    if backend == "mpv":
        return ["mpv", "--no-video", "--really-quiet", file_path]
    if backend == "ffplay":
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", file_path]
    return ["paplay", file_path]


def _spawn_audio_process(cmd: List[str]):
    popen_kwargs = {
        "args": cmd,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True
    }

    if os.name != "nt":
        popen_kwargs["start_new_session"] = True

    subprocess.Popen(**popen_kwargs)  # type: ignore[arg-type]


def _save_audio_backend(backend: AudioPlayerBackend):
    conf = load_config()
    if conf["audio_player_backend"] == backend:
        return

    conf["audio_player_backend"] = backend
    save_config(conf)


def _playback_response(status: str, backend: AudioPlayerBackend, message: str) -> PlaybackResponseMessage:
    return {
        "cmd": "playback_response",
        "status": status,  # type: ignore[typeddict-item]
        "backend": backend,
        "message": message
    }


__all__ = ["play_audio"]
