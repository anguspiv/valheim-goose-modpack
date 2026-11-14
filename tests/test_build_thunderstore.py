import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "build-thunderstore.py")


def run(*args, cwd=REPO):
    return subprocess.run([sys.executable, SCRIPT, *args], cwd=cwd, capture_output=True, text=True)


class BuildThunderstoreTests(unittest.TestCase):
    def test_builds_zip_named_after_manifest_with_required_files(self):
        with tempfile.TemporaryDirectory() as out:
            r = run("--out", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(os.path.join(REPO, "manifest.json")) as f:
                m = json.load(f)
            path = os.path.join(out, f"{m['name']}-{m['version_number']}.zip")
            self.assertTrue(os.path.isfile(path), os.listdir(out))
            with zipfile.ZipFile(path) as z:
                names = set(z.namelist())
            self.assertIn("manifest.json", names)
            self.assertIn("README.md", names)
            self.assertIn("icon.png", names)
            self.assertIn("config/org.bepinex.plugins.valheim_plus.cfg", names)
            self.assertFalse(any(n.startswith("deck/") or n.startswith(".git") for n in names), names)

    def test_rejects_manifest_version_that_does_not_match_tag(self):
        with tempfile.TemporaryDirectory() as out:
            r = run("--out", out, "--expect-version", "9.9.9")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("9.9.9", r.stderr)

    def test_rejects_bad_icon(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            for name in ("manifest.json", "README.md"):
                with open(os.path.join(REPO, name)) as f, open(os.path.join(src, name), "w") as g:
                    g.write(f.read())
            with open(os.path.join(src, "icon.png"), "wb") as g:
                g.write(b"not a png")
            r = run("--out", out, "--src", src)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("icon", r.stderr.lower())


if __name__ == "__main__":
    unittest.main()


class BuildThunderstoreHardeningTests(unittest.TestCase):
    def test_empty_expect_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as out:
            r = run("--out", out, "--expect-version", "")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("expect-version", r.stderr)

    def test_wrong_size_png_icon_is_rejected(self):
        import struct
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            for name in ("manifest.json", "README.md"):
                with open(os.path.join(REPO, name)) as f, open(os.path.join(src, name), "w") as g:
                    g.write(f.read())
            header = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 128, 128) + b"\x08\x06\x00\x00\x00"
            with open(os.path.join(src, "icon.png"), "wb") as g:
                g.write(header)
            r = run("--out", out, "--src", src)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("256x256", r.stderr)

    def test_manifest_name_description_and_dependencies_are_validated(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            for name in ("README.md", "icon.png"):
                with open(os.path.join(REPO, name), "rb") as f, open(os.path.join(src, name), "wb") as g:
                    g.write(f.read())
            bad = {"name": "goose modpack", "version_number": "2.0.0", "website_url": "", "description": "x" * 251, "dependencies": ["not-a-dep"]}
            with open(os.path.join(src, "manifest.json"), "w") as g:
                json.dump(bad, g)
            r = run("--out", out, "--src", src)
            self.assertNotEqual(r.returncode, 0)
            self.assertRegex(r.stderr, r"name|description|dependenc")


class BuildThunderstoreYamlTests(unittest.TestCase):
    def test_zip_includes_yml_and_yaml_configs(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            for name in ("manifest.json", "README.md", "icon.png"):
                with open(os.path.join(REPO, name), "rb") as f, open(os.path.join(src, name), "wb") as g:
                    g.write(f.read())
            os.makedirs(os.path.join(src, "config"))
            for n in ("a.cfg", "b.server.yml", "c.yaml", "ignore.txt"):
                with open(os.path.join(src, "config", n), "w") as g:
                    g.write(n)
            r = run("--out", out, "--src", src)
            self.assertEqual(r.returncode, 0, r.stderr)
            with zipfile.ZipFile(r.stdout.strip()) as z:
                names = set(z.namelist())
            self.assertTrue({"config/a.cfg", "config/b.server.yml", "config/c.yaml"} <= names, names)
            self.assertNotIn("config/ignore.txt", names)
