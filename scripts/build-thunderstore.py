#!/usr/bin/env python3
"""Build the Thunderstore upload zip for this modpack.

    python3 scripts/build-thunderstore.py [--out dist] [--src .] [--expect-version X.Y.Z]

The zip holds manifest.json, README.md, icon.png, CHANGELOG.md if present, and
config/*.cfg. r2modman and Thunderstore Mod Manager copy a package's config/
folder into BepInEx/config, so friends get the pack's settings on install.
Fails loudly on a bad manifest or icon so a broken upload never reaches the
site. Standard library only.
"""
import argparse
import json
import os
import re
import struct
import sys
import zipfile

REQUIRED_MANIFEST_KEYS = ("name", "version_number", "website_url", "description", "dependencies")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def fail(msg):
    print(f"build-thunderstore: {msg}", file=sys.stderr)
    sys.exit(1)


def load_manifest(src):
    path = os.path.join(src, "manifest.json")
    if not os.path.isfile(path):
        fail(f"missing {path}")
    with open(path, encoding="utf-8") as f:
        manifest = json.load(f)
    for key in REQUIRED_MANIFEST_KEYS:
        if key not in manifest:
            fail(f"manifest.json lacks '{key}'")
    if not VERSION_RE.match(str(manifest["version_number"])):
        fail(f"version_number '{manifest['version_number']}' is not X.Y.Z")
    if not isinstance(manifest["dependencies"], list) or not manifest["dependencies"]:
        fail("manifest.json dependencies must be a non-empty list")
    return manifest


def check_icon(src):
    path = os.path.join(src, "icon.png")
    if not os.path.isfile(path):
        fail("missing icon.png (Thunderstore needs a 256x256 PNG)")
    with open(path, "rb") as f:
        head = f.read(24)
    if len(head) < 24 or head[:8] != PNG_SIGNATURE or head[12:16] != b"IHDR":
        fail("icon.png is not a PNG")
    width, height = struct.unpack(">II", head[16:24])
    if (width, height) != (256, 256):
        fail(f"icon.png must be 256x256, got {width}x{height}")


def build(src, out, expect_version=None):
    manifest = load_manifest(src)
    if expect_version and str(manifest["version_number"]) != expect_version:
        fail(f"manifest version_number {manifest['version_number']} does not match expected {expect_version}")
    check_icon(src)
    if not os.path.isfile(os.path.join(src, "README.md")):
        fail("missing README.md")

    os.makedirs(out, exist_ok=True)
    zip_path = os.path.join(out, f"{manifest['name']}-{manifest['version_number']}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("manifest.json", "README.md", "icon.png", "CHANGELOG.md"):
            path = os.path.join(src, name)
            if os.path.isfile(path):
                z.write(path, name)
        cfg_dir = os.path.join(src, "config")
        if os.path.isdir(cfg_dir):
            for name in sorted(os.listdir(cfg_dir)):
                if name.endswith(".cfg"):
                    z.write(os.path.join(cfg_dir, name), f"config/{name}")
    print(zip_path)
    return zip_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="dist", help="output directory (default: dist)")
    ap.add_argument("--src", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    help="modpack root containing manifest.json (default: this repo)")
    ap.add_argument("--expect-version", help="fail unless manifest version_number equals this (CI passes the git tag)")
    args = ap.parse_args()
    build(os.path.abspath(args.src), os.path.abspath(args.out), args.expect_version)


if __name__ == "__main__":
    main()
