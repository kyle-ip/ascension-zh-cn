"""Install BepInEx 6 (IL2CPP) and build the CJK TMP fallback plugin."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

from common import REPO_ROOT, STATE_DIR, detect_game_root

PACK_ZIP = STATE_DIR / "BepInExPack_IL2CPP-6.0.755.zip"
PACK_URL = "https://gcdn.thunderstore.io/live/repository/packages/BepInEx-BepInExPack_IL2CPP-6.0.755.zip"
SDK_ZIP = STATE_DIR / "dotnet-sdk-8.0.424-win-x64.zip"
SDK_DIR = STATE_DIR / "dotnet-sdk"
PLUGIN_PROJ = REPO_ROOT / "plugin" / "AscensionZhCn" / "AscensionZhCn.csproj"
RUNTIME_CSV = REPO_ROOT / "loc" / "zh-Hans" / "ui_runtime.csv"
OVERLAY_TSV = REPO_ROOT / "loc" / "zh-Hans" / "overlay.tsv"

MARKER_FILES = (
    "winhttp.dll",
    "doorstop_config.ini",
    ".doorstop_version",
)


def _game() -> Path:
    return detect_game_root()


def installed(game: Path | None = None) -> bool:
    game = game or _game()
    return (game / "BepInEx" / "core" / "BepInEx.Unity.IL2CPP.dll").is_file() and (
        game / "winhttp.dll"
    ).is_file()


def plugin_built(game: Path | None = None) -> bool:
    game = game or _game()
    return (game / "BepInEx" / "plugins" / "AscensionZhCn.dll").is_file()


def interop_ready(game: Path | None = None) -> bool:
    game = game or _game()
    interop = game / "BepInEx" / "interop"
    needed = (
        interop / "UnityEngine.CoreModule.dll",
        interop / "Unity.TextMeshPro.dll",
    )
    return all(path.is_file() and path.stat().st_size > 50_000 for path in needed)


def _download(url: str, dest: Path) -> None:
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        return
    print(f"downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        dest.write_bytes(resp.read())
    print(f"wrote {dest} ({dest.stat().st_size} bytes)")


def install_bepinex(game: Path | None = None) -> None:
    game = game or _game()
    if installed(game):
        print(f"BepInEx already present in {game}")
        _quiet_console(game)
        return
    _download(PACK_URL, PACK_ZIP)
    print(f"extracting BepInEx into {game}")
    with zipfile.ZipFile(PACK_ZIP) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if not name.startswith("BepInExPack/") or name.endswith("/"):
                continue
            rel = name[len("BepInExPack/") :]
            if not rel:
                continue
            dest = game / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if info.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                continue
            with zf.open(info) as src, dest.open("wb") as out:
                shutil.copyfileobj(src, out)
    _quiet_console(game)
    print("installed BepInEx IL2CPP (first launch generates interop, can take a few minutes)")


def _quiet_console(game: Path) -> None:
    """Hide the BepInEx console, keep disk logs, and ignore Steam's DOORSTOP_DISABLE."""
    cfg = game / "BepInEx" / "config" / "BepInEx.cfg"
    if cfg.is_file():
        text = cfg.read_text(encoding="utf-8", errors="replace")
        updated = _set_ini_flag(text, "[Logging.Console]", "Enabled", "false")
        updated = _set_ini_flag(updated, "[Logging.Disk]", "Enabled", "true")
        if updated != text:
            cfg.write_text(updated, encoding="utf-8")
            print("BepInEx: console off, disk log on")
    door = game / "doorstop_config.ini"
    if door.is_file():
        text = door.read_text(encoding="utf-8", errors="replace")
        updated = text.replace("ignore_disable_switch = false", "ignore_disable_switch = true")
        if updated != text:
            door.write_text(updated, encoding="utf-8")
            print("Doorstop: ignore_disable_switch = true (Steam often sets DOORSTOP_DISABLE)")


def _set_ini_flag(text: str, section: str, key: str, value: str) -> str:
    if section not in text:
        return text
    parts = text.split(section, 1)
    head, rest = parts[0], parts[1]
    nxt = rest.find("\n[")
    body, tail = (rest, "") if nxt < 0 else (rest[:nxt], rest[nxt:])
    lines = []
    replaced = False
    for line in body.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(f"{key} =") or stripped.startswith(f"{key}="):
            nl = "\n" if line.endswith("\n") else ""
            lines.append(f"{key} = {value}{nl}")
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.append(f"{key} = {value}\n")
    return head + section + "".join(lines) + tail


def uninstall_bepinex(game: Path | None = None) -> None:
    game = game or _game()
    removed = 0
    for name in MARKER_FILES:
        path = game / name
        if path.is_file():
            path.unlink()
            removed += 1
    for folder in ("BepInEx", "dotnet"):
        path = game / folder
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=False)
            removed += 1
    changelog = game / "changelog.txt"
    if changelog.is_file() and "BepInEx" in changelog.read_text(encoding="utf-8", errors="replace")[:200]:
        changelog.unlink()
        removed += 1
    print(f"removed BepInEx files from {game} ({removed} entries)")


def find_dotnet() -> Path:
    candidates = [
        SDK_DIR / "dotnet.exe",
        Path(r"C:\Program Files\dotnet\dotnet.exe"),
        Path(os.environ.get("DOTNET_ROOT", "")) / "dotnet.exe",
    ]
    for path in candidates:
        if path.is_file():
            return path
    which = shutil.which("dotnet")
    if which:
        return Path(which)
    raise FileNotFoundError(
        "No .NET SDK. Extract state/dotnet-sdk-8.0.424-win-x64.zip to state/dotnet-sdk/"
    )


def extract_portable_sdk() -> Path | None:
    if (SDK_DIR / "dotnet.exe").is_file():
        return SDK_DIR / "dotnet.exe"
    if not SDK_ZIP.is_file():
        return None
    print(f"extracting portable SDK -> {SDK_DIR}")
    SDK_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SDK_ZIP) as zf:
        zf.extractall(SDK_DIR)
    exe = SDK_DIR / "dotnet.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"dotnet.exe missing after extracting {SDK_ZIP}")
    return exe


def generate_interop(game: Path | None = None, timeout_s: int = 480) -> None:
    game = game or _game()
    if interop_ready(game):
        print("IL2CPP interop already generated")
        return
    install_bepinex(game)
    exe = game / "AscensionGame.exe"
    log = game / "BepInEx" / "LogOutput.txt"
    interop = game / "BepInEx" / "interop"
    print("launching game once so BepInEx can generate IL2CPP interop (a window may appear, then it will be closed)")
    proc = subprocess.Popen([str(exe)], cwd=str(game))
    deadline = time.time() + timeout_s
    last_report = 0.0
    try:
        while time.time() < deadline:
            if interop_ready(game):
                print("interop ready")
                return
            now = time.time()
            if now - last_report > 10:
                sizes = []
                for name in ("UnityEngine.CoreModule.dll", "Unity.TextMeshPro.dll", "UnityEngine.dll"):
                    path = interop / name
                    sizes.append(f"{name}={path.stat().st_size if path.is_file() else 0}")
                print("waiting for interop:", ", ".join(sizes))
                last_report = now
            if proc.poll() is not None:
                break
            time.sleep(2)
        extra = ""
        if log.is_file():
            extra = "\n" + log.read_text(encoding="utf-8", errors="replace")[-2000:]
        raise RuntimeError("BepInEx interop was not generated in time." + extra)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
            print("closed the interop bootstrap launch")


def build_plugin(game: Path | None = None) -> None:
    game = game or _game()
    if not interop_ready(game):
        generate_interop(game)
    extract_portable_sdk()
    dotnet = find_dotnet()
    out_dir = PLUGIN_PROJ.parent / "bin" / "Release"
    env = os.environ.copy()
    env["DOTNET_ROOT"] = str(dotnet.parent)
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    cmd = [
        str(dotnet),
        "build",
        str(PLUGIN_PROJ),
        "-c",
        "Release",
        "--verbosity",
        "minimal",
    ]
    subprocess.check_call([str(dotnet), "restore", str(PLUGIN_PROJ), "--verbosity", "quiet"], env=env)
    print("building plugin")
    subprocess.check_call(cmd, env=env, cwd=str(PLUGIN_PROJ.parent))
    built = out_dir / "AscensionZhCn.dll"
    if not built.is_file():
        matches = list(PLUGIN_PROJ.parent.rglob("AscensionZhCn.dll"))
        if not matches:
            raise FileNotFoundError("plugin build did not produce AscensionZhCn.dll")
        built = matches[0]
    plugins = game / "BepInEx" / "plugins"
    plugins.mkdir(parents=True, exist_ok=True)
    dest = plugins / "AscensionZhCn.dll"
    shutil.copy2(built, dest)
    if RUNTIME_CSV.is_file():
        shutil.copy2(RUNTIME_CSV, plugins / "ui_runtime.csv")
    if OVERLAY_TSV.is_file():
        shutil.copy2(OVERLAY_TSV, plugins / "overlay.tsv")
        from common import streaming_zh_overlay

        overlay_dest = streaming_zh_overlay(game)
        overlay_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OVERLAY_TSV, overlay_dest)
    print(f"plugin -> {dest}")


def enable_runtime(game: Path | None = None) -> None:
    game = game or _game()
    install_bepinex(game)
    build_plugin(game)


def disable_runtime(game: Path | None = None) -> None:
    uninstall_bepinex(game or _game())
