#!/usr/bin/env python3
"""Install the Goose modpack into a Steam Deck / Linux Valheim install.

Reads manifest.json, downloads every Thunderstore dependency (recursively),
installs BepInEx into the game folder, puts each mod in BepInEx/plugins/<pkg>/,
removes mods that are no longer in the manifest, and copies the pack's config/
files over BepInEx/config/.

Run it again any time the manifest or configs change. Nothing else to manage.

Usage (on the Deck, or over SSH from another machine):
    python3 deck/install.py              # from a checkout of the repo
    python3 deck/install.py --game-dir /run/media/mmcblk0p1/steamapps/common/Valheim

One-liner with no checkout (fetches the repo tarball first):
    curl -fsSL https://raw.githubusercontent.com/anguspiv/valheim-goose-modpack/main/deck/install.py | python3 - --remote
"""
import argparse
import glob
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

REPO = "anguspiv/valheim-goose-modpack"
REPO_TARBALL = f"https://github.com/{REPO}/archive/refs/heads/{{branch}}.tar.gz"
TS_DOWNLOAD = "https://thunderstore.io/package/download/{ns}/{name}/{ver}/"
STATE_FILE = ".goose-modpack.json"
LAUNCH_OPTIONS = "./start_game_bepinex.sh %command%"
SKIP_ROOT_FILES = {"icon.png", "manifest.json", "readme.md", "changelog.md", "license", "license.md", "license.txt"}

GAME_DIR_CANDIDATES = [
    "~/.local/share/Steam/steamapps/common/Valheim",
    "~/.steam/steam/steamapps/common/Valheim",
    "/run/media/*/steamapps/common/Valheim",
    "/run/media/*/SteamLibrary/steamapps/common/Valheim",
    "/run/media/deck/*/steamapps/common/Valheim",
    "/run/media/deck/*/SteamLibrary/steamapps/common/Valheim",
]


def log(msg):
    print(f"[goose] {msg}", flush=True)


def die(msg):
    print(f"[goose] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def find_game_dir(explicit):
    if explicit:
        d = os.path.expanduser(explicit)
        if not os.path.isfile(os.path.join(d, "valheim.x86_64")):
            die(f"{d} does not look like a Linux Valheim install (no valheim.x86_64)")
        return d
    for pattern in GAME_DIR_CANDIDATES:
        for d in glob.glob(os.path.expanduser(pattern)):
            if os.path.isfile(os.path.join(d, "valheim.x86_64")):
                return d
    die("Could not find Valheim. Install it from Steam first, or pass --game-dir.")


def valheim_running():
    try:
        out = subprocess.run(["pgrep", "-f", "valheim.x86_64"], capture_output=True, text=True)
        return out.returncode == 0
    except FileNotFoundError:
        return False


def parse_dep(dep):
    # Thunderstore dependency string: Namespace-Name-Major.Minor.Patch
    m = re.fullmatch(r"(.+?)-(.+)-(\d+\.\d+\.\d+)", dep)
    if not m:
        die(f"Bad dependency string: {dep}")
    return m.group(1), m.group(2), m.group(3)


def ver_tuple(v):
    return tuple(int(x) for x in v.split("."))


def urlopen(url):
    # GitHub and Thunderstore both reject urllib's default User-Agent
    req = urllib.request.Request(url, headers={"User-Agent": f"goose-modpack-installer ({REPO})"})
    return urllib.request.urlopen(req, timeout=120)


def fetch(url, dest):
    tmp = dest + ".part"
    with urlopen(url) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    os.replace(tmp, dest)


def download_package(cache, ns, name, ver):
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, f"{ns}-{name}-{ver}.zip")
    if not os.path.isfile(path):
        log(f"  downloading {ns}-{name} {ver}")
        fetch(TS_DOWNLOAD.format(ns=ns, name=name, ver=ver), path)
    return path


def resolve(deps, cache):
    """Resolve the full dependency closure. Returns {(ns,name): (ver, zip_path)}."""
    resolved = {}
    queue = list(deps)
    while queue:
        ns, name, ver = parse_dep(queue.pop(0))
        key = (ns, name)
        if key in resolved and ver_tuple(resolved[key][0]) >= ver_tuple(ver):
            continue
        zpath = download_package(cache, ns, name, ver)
        resolved[key] = (ver, zpath)
        with zipfile.ZipFile(zpath) as z:
            if "manifest.json" in z.namelist():
                sub = json.loads(z.read("manifest.json").decode("utf-8-sig"))
                queue.extend(sub.get("dependencies", []))
    return resolved


def is_bepinex_pack(ns, name):
    return name == "BepInExPack_Valheim"


def check_archive_parts(parts, archive_name):
    """Refuse zip entries that could escape the install dir (.., absolute, backslashes)."""
    for part in parts:
        if part in ("", ".", "..") or "\\" in part:
            die(f"refusing unsafe path in {archive_name}: {'/'.join(parts)!r}")


def safe_dest(root, rel):
    """Join rel onto root and prove the result stays inside root."""
    dest = os.path.join(root, rel)
    root_real = os.path.realpath(root)
    if os.path.commonpath([root_real, os.path.realpath(dest)]) != root_real:
        die(f"refusing to write outside {root}: {rel!r}")
    return dest


def install_bepinex(zpath, game_dir):
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            parts = info.filename.split("/")
            check_archive_parts(parts, os.path.basename(zpath))
            if parts[0] != "BepInExPack_Valheim" or len(parts) < 2:
                continue
            rel = os.path.join(*parts[1:])
            # Never clobber the pack's config dir; the modpack ships its own BepInEx.cfg
            if rel == os.path.join("BepInEx", "config", "BepInEx.cfg") and os.path.exists(os.path.join(game_dir, rel)):
                continue
            dest = safe_dest(game_dir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
    for script in ("start_game_bepinex.sh", "start_server_bepinex.sh"):
        p = os.path.join(game_dir, script)
        if os.path.exists(p):
            os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def plan_mod_file(parts, pkg_folder):
    """Map a path inside a mod zip to a path relative to the game dir, r2modman-style."""
    lower = [p.lower() for p in parts]
    if len(parts) == 1 and lower[0] in SKIP_ROOT_FILES:
        return None
    # Strip a leading BepInEx/ if present
    if lower[0] == "bepinex" and len(parts) > 1:
        parts, lower = parts[1:], lower[1:]
    if lower[0] == "plugins" and len(parts) > 1:
        return os.path.join("BepInEx", "plugins", pkg_folder, *parts[1:])
    if lower[0] == "patchers" and len(parts) > 1:
        return os.path.join("BepInEx", "patchers", pkg_folder, *parts[1:])
    if lower[0] == "config" and len(parts) > 1:
        return os.path.join("BepInEx", "config", *parts[1:])
    return os.path.join("BepInEx", "plugins", pkg_folder, *parts)


def install_mod(zpath, game_dir, pkg_folder):
    for sub in ("plugins", "patchers"):
        shutil.rmtree(os.path.join(game_dir, "BepInEx", sub, pkg_folder), ignore_errors=True)
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            parts = info.filename.split("/")
            check_archive_parts(parts, os.path.basename(zpath))
            rel = plan_mod_file(parts, pkg_folder)
            if rel is None:
                continue
            dest = safe_dest(game_dir, rel)
            # Don't overwrite a config the user/pack already has; mods regenerate missing ones
            if rel.startswith(os.path.join("BepInEx", "config")) and os.path.exists(dest):
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)


CONFIG_SUFFIXES = (".cfg", ".yml", ".yaml")
STALE_CONFIGS = ("valheim_plus.cfg", "valheim_plus.cfg.migrated")


def copy_pack_configs(pack_dir, game_dir, target_mode):
    """Copy the pack's config/*.cfg|yml|yaml into BepInEx/config. Server images
    keep the image's own BepInEx.cfg, so target mode skips the core loader config."""
    cfg_src = os.path.join(pack_dir, "config")
    cfg_dst = os.path.join(game_dir, "BepInEx", "config")
    os.makedirs(cfg_dst, exist_ok=True)
    copied = []
    if os.path.isdir(cfg_src):
        for name in sorted(os.listdir(cfg_src)):
            if not name.endswith(CONFIG_SUFFIXES):
                continue
            if target_mode and name == "BepInEx.cfg":
                continue
            shutil.copy2(os.path.join(cfg_src, name), os.path.join(cfg_dst, name))
            copied.append(name)
    return copied


def remove_stale_configs(game_dir):
    """ValheimPlus 10.x reads an old-format valheim_plus.cfg in preference to its
    BepInEx config when both exist. The pack ships only the new file, so drop the
    old one and the .migrated copy V+ leaves behind."""
    cfg_dst = os.path.join(game_dir, "BepInEx", "config")
    removed = []
    for name in STALE_CONFIGS:
        p = os.path.join(cfg_dst, name)
        if os.path.exists(p):
            os.remove(p)
            removed.append(name)
    return removed


def load_client_only(pack_dir):
    """server.json lists packages that must not go on a dedicated server."""
    p = os.path.join(pack_dir, "server.json")
    if not os.path.isfile(p):
        return []
    with open(p) as f:
        return list(json.load(f).get("client_only", []))


def filter_client_only(resolved, client_only):
    skip = set(client_only)
    return {k: v for k, v in resolved.items() if f"{k[0]}-{k[1]}" not in skip}


def check_expected_version(manifest, expected):
    """Unattended builds pass the git tag; refuse a manifest that disagrees."""
    if expected is None:
        return
    if not re.match(r"^\d+\.\d+\.\d+$", expected or ""):
        die(f"--expect-version must look like X.Y.Z, got {expected!r}")
    if str(manifest.get("version_number")) != expected:
        die(f"manifest version_number {manifest.get('version_number')} does not match expected {expected}")


def load_state(game_dir):
    p = os.path.join(game_dir, STATE_FILE)
    if os.path.isfile(p):
        with open(p) as f:
            return json.load(f)
    return {"packages": []}


def save_state(game_dir, packages):
    with open(os.path.join(game_dir, STATE_FILE), "w") as f:
        json.dump({"packages": sorted(packages)}, f, indent=2)


def fetch_repo(branch):
    tmp = tempfile.mkdtemp(prefix="goose-modpack-")
    url = REPO_TARBALL.format(branch=branch)
    log(f"fetching modpack from {url}")
    with urlopen(url) as r:
        data = r.read()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
        try:
            t.extractall(tmp, filter="data")
        except TypeError:  # Python < 3.12 has no filter argument
            t.extractall(tmp)
    roots = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
    if len(roots) != 1:
        die("unexpected tarball layout")
    return os.path.join(tmp, roots[0])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game-dir", help="Valheim install folder (auto-detected if omitted)")
    ap.add_argument("--remote", action="store_true", help="fetch the modpack repo from GitHub instead of using a local checkout")
    ap.add_argument("--branch", default="main", help="branch to fetch with --remote (default: main)")
    ap.add_argument("--cache", default=os.path.expanduser("~/.cache/goose-modpack"), help="where downloaded zips are kept")
    ap.add_argument("--force", action="store_true", help="install even if Valheim appears to be running")
    ap.add_argument("--target", help="server images: write BepInEx/plugins and BepInEx/config under this directory "
                                     "instead of a game install; skips the BepInEx core pack, Steam discovery "
                                     "and the running-game check")
    ap.add_argument("--expect-version", help="fail unless manifest version_number equals this (pass the git tag without its v)")
    args = ap.parse_args()
    target_mode = args.target is not None
    if target_mode and not args.target.strip():
        die("--target must not be empty")
    if target_mode and args.game_dir:
        die("--target and --game-dir are mutually exclusive")

    if args.remote:
        pack_dir = fetch_repo(args.branch)
    else:
        pack_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest_path = os.path.join(pack_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        die(f"no manifest.json at {pack_dir} (use --remote if you piped this script in)")
    with open(manifest_path) as f:
        manifest = json.load(f)
    check_expected_version(manifest, args.expect_version)

    if target_mode:
        game_dir = os.path.abspath(args.target)
        os.makedirs(game_dir, exist_ok=True)
        log(f"target: {game_dir}")
    else:
        game_dir = find_game_dir(args.game_dir)
        log(f"Valheim: {game_dir}")
    log(f"modpack: {manifest['name']} {manifest['version_number']}")

    if not target_mode and valheim_running() and not args.force:
        die("Valheim is running. Quit it first (or pass --force).")

    log("resolving mods")
    resolved = resolve(manifest["dependencies"], args.cache)
    if target_mode:
        client_only = load_client_only(pack_dir)
        for pkg in sorted(client_only):
            log(f"skipping {pkg} (client-side only, not for the server)")
        resolved = filter_client_only(resolved, client_only)

    bepinex = [k for k in resolved if is_bepinex_pack(*k)]
    if not bepinex:
        die("manifest has no BepInExPack_Valheim dependency")
    ver, zpath = resolved[bepinex[0]]
    if target_mode:
        log(f"skipping BepInEx pack {ver} (the server image provides BepInEx)")
    else:
        log(f"installing BepInEx pack {ver}")
        install_bepinex(zpath, game_dir)

    installed = []
    for (ns, name), (ver, zpath) in sorted(resolved.items()):
        if is_bepinex_pack(ns, name):
            continue
        folder = f"{ns}-{name}"
        log(f"installing {folder} {ver}")
        install_mod(zpath, game_dir, folder)
        installed.append(folder)

    # Remove mods that were installed by a previous run but are no longer in the pack
    previous = set(load_state(game_dir)["packages"])
    for folder in sorted(previous - set(installed)):
        log(f"removing {folder} (no longer in modpack)")
        for sub in ("plugins", "patchers"):
            shutil.rmtree(os.path.join(game_dir, "BepInEx", sub, folder), ignore_errors=True)
    save_state(game_dir, installed)

    for name in remove_stale_configs(game_dir):
        log(f"removed stale {name}")
    for name in copy_pack_configs(pack_dir, game_dir, target_mode):
        log(f"config {name}")

    log("done")
    if target_mode:
        return
    print()
    print("Steam launch options for Valheim (set once; works in Game Mode and Desktop Mode):")
    print(f"    {LAUNCH_OPTIONS}")
    print("If modded launch flashes and dies, append:  -compat-force-slr off")
    print("Mods installed:")
    for folder in installed:
        print(f"    {folder}")


if __name__ == "__main__":
    main()
