import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "deck"))
import install  # noqa: E402


def make_zip(entries):
    """entries: {name_in_zip: bytes}. Returns path to a temp zip."""
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return path


def tree(root):
    out = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            out.append(os.path.relpath(os.path.join(dirpath, f), root))
    return sorted(out)


class PlanModFileTests(unittest.TestCase):
    def test_r2modman_style_mapping(self):
        self.assertEqual(install.plan_mod_file(["plugins", "Mod.dll"], "ns-Mod"), os.path.join("BepInEx", "plugins", "ns-Mod", "Mod.dll"))
        self.assertEqual(install.plan_mod_file(["BepInEx", "plugins", "Mod.dll"], "ns-Mod"), os.path.join("BepInEx", "plugins", "ns-Mod", "Mod.dll"))
        self.assertEqual(install.plan_mod_file(["config", "x.cfg"], "ns-Mod"), os.path.join("BepInEx", "config", "x.cfg"))
        self.assertEqual(install.plan_mod_file(["patchers", "P.dll"], "ns-Mod"), os.path.join("BepInEx", "patchers", "ns-Mod", "P.dll"))
        self.assertEqual(install.plan_mod_file(["Mod.dll"], "ns-Mod"), os.path.join("BepInEx", "plugins", "ns-Mod", "Mod.dll"))
        self.assertIsNone(install.plan_mod_file(["manifest.json"], "ns-Mod"))


class TraversalTests(unittest.TestCase):
    def setUp(self):
        self.outer = tempfile.mkdtemp()
        self.game = os.path.join(self.outer, "game")
        os.makedirs(self.game)

    def test_install_mod_refuses_parent_traversal(self):
        z = make_zip({"plugins/../../../escaped.txt": b"x", "plugins/ok.dll": b"y"})
        with self.assertRaises(SystemExit):
            install.install_mod(z, self.game, "ns-Mod")
        self.assertFalse(os.path.exists(os.path.join(self.outer, "escaped.txt")))
        self.assertEqual([p for p in tree(self.outer) if "escaped" in p], [])

    def test_install_mod_refuses_absolute_and_backslash(self):
        for name in ("/etc/passwd", "plugins\\..\\..\\x.dll"):
            z = make_zip({name: b"x"})
            with self.assertRaises(SystemExit, msg=name):
                install.install_mod(z, self.game, "ns-Mod")

    def test_install_bepinex_refuses_traversal(self):
        z = make_zip({"BepInExPack_Valheim/../../escaped.txt": b"x"})
        with self.assertRaises(SystemExit):
            install.install_bepinex(z, self.game)
        self.assertFalse(os.path.exists(os.path.join(self.outer, "escaped.txt")))

    def test_install_mod_writes_only_inside_game_dir(self):
        z = make_zip({"plugins/Mod.dll": b"dll", "config/mod.cfg": b"cfg", "README.md": b"r", "icon.png": b"i"})
        install.install_mod(z, self.game, "ns-Mod")
        self.assertEqual(tree(self.game), [os.path.join("BepInEx", "config", "mod.cfg"), os.path.join("BepInEx", "plugins", "ns-Mod", "Mod.dll")])


class ConfigCopyTests(unittest.TestCase):
    def test_target_mode_skips_bepinex_core_config(self):
        with tempfile.TemporaryDirectory() as pack, tempfile.TemporaryDirectory() as game:
            os.makedirs(os.path.join(pack, "config"))
            for n in ("BepInEx.cfg", "valheim_plus.cfg", "notes.txt"):
                with open(os.path.join(pack, "config", n), "w") as f:
                    f.write(n)
            copied = install.copy_pack_configs(pack, game, target_mode=True)
            self.assertEqual(copied, ["valheim_plus.cfg"])
            self.assertEqual(tree(game), [os.path.join("BepInEx", "config", "valheim_plus.cfg")])

    def test_deck_mode_copies_bepinex_config_too(self):
        with tempfile.TemporaryDirectory() as pack, tempfile.TemporaryDirectory() as game:
            os.makedirs(os.path.join(pack, "config"))
            for n in ("BepInEx.cfg", "valheim_plus.cfg"):
                with open(os.path.join(pack, "config", n), "w") as f:
                    f.write(n)
            self.assertEqual(install.copy_pack_configs(pack, game, target_mode=False), ["BepInEx.cfg", "valheim_plus.cfg"])


class ExpectVersionTests(unittest.TestCase):
    def test_mismatch_dies_and_match_passes(self):
        m = {"version_number": "2.0.0"}
        install.check_expected_version(m, None)
        install.check_expected_version(m, "2.0.0")
        with self.assertRaises(SystemExit):
            install.check_expected_version(m, "2.0.1")
        with self.assertRaises(SystemExit):
            install.check_expected_version(m, "")


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, os.path.join(REPO, "deck", "install.py"), *args], capture_output=True, text=True)

    def test_empty_target_is_rejected_before_any_network(self):
        r = self.run_cli("--target", "")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--target", r.stderr + r.stdout)
        self.assertNotIn("Could not find Valheim", r.stderr + r.stdout)

    def test_target_and_game_dir_are_exclusive(self):
        r = self.run_cli("--target", "/tmp/x", "--game-dir", "/tmp/y")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("mutually exclusive", r.stderr + r.stdout)


if __name__ == "__main__":
    unittest.main()
