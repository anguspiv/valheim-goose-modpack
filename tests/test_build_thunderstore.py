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
            self.assertIn("config/valheim_plus.cfg", names)
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
