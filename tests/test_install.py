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



class ConfigCopyYamlAndStaleTests(unittest.TestCase):
    def test_copies_yml_and_yaml_files_too(self):
        with tempfile.TemporaryDirectory() as pack, tempfile.TemporaryDirectory() as game:
            os.makedirs(os.path.join(pack, "config"))
            for n in ("a.cfg", "odinplus.TeleportCarts.server.yml", "b.yaml", "notes.txt"):
                with open(os.path.join(pack, "config", n), "w") as f:
                    f.write(n)
            copied = install.copy_pack_configs(pack, game, target_mode=False)
            self.assertEqual(copied, ["a.cfg", "b.yaml", "odinplus.TeleportCarts.server.yml"])

    def test_removes_stale_valheim_plus_files(self):
        with tempfile.TemporaryDirectory() as game:
            cfg = os.path.join(game, "BepInEx", "config")
            os.makedirs(cfg)
            for n in ("valheim_plus.cfg", "valheim_plus.cfg.migrated", "org.bepinex.plugins.valheim_plus.cfg"):
                with open(os.path.join(cfg, n), "w") as f:
                    f.write("x")
            removed = install.remove_stale_configs(game)
            self.assertEqual(removed, ["valheim_plus.cfg"])
            # V+'s own backup of the player's pre-10.x settings stays.
            self.assertEqual(tree(game), [os.path.join("BepInEx", "config", "org.bepinex.plugins.valheim_plus.cfg"), os.path.join("BepInEx", "config", "valheim_plus.cfg.migrated")])


class ClientOnlyTests(unittest.TestCase):
    def test_server_json_lists_client_only_packages_that_exist_in_manifest(self):
        with open(os.path.join(REPO, "server.json")) as f:
            client_only = json.load(f)["client_only"]
        with open(os.path.join(REPO, "manifest.json")) as f:
            deps = json.load(f)["dependencies"]
        names = {"-".join(d.split("-")[:2]) for d in deps}
        for pkg in client_only:
            self.assertIn(pkg, names, pkg)

    def test_filter_for_target_drops_client_only_dependency_strings_before_resolve(self):
        deps = ["Advize-PlantEasily-2.3.1", "RustyMods-PortalStations-1.4.7", "denikson-BepInExPack_Valheim-5.4.2360"]
        kept = install.filter_client_only(deps, ["Advize-PlantEasily"])
        self.assertEqual(kept, ["RustyMods-PortalStations-1.4.7", "denikson-BepInExPack_Valheim-5.4.2360"])

    def test_load_client_only_without_server_json_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(install.load_client_only(d), [])


class MacOSTests(unittest.TestCase):
    def make_mac_game(self, root, app="Valheim.app"):
        d = os.path.join(root, "steamapps", "common", "Valheim")
        os.makedirs(os.path.join(d, app, "Contents", "MacOS"))
        with open(os.path.join(d, app, "Contents", "MacOS", "Valheim"), "w") as f:
            f.write("")
        return d

    def test_explicit_game_dir_with_valheim_app_is_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            d = self.make_mac_game(root)
            self.assertEqual(install.find_game_dir(d, platform="darwin"), d)
            self.assertTrue(install.is_macos_game_dir(d))
            self.assertFalse(install.is_linux_game_dir(d))

    def test_lowercase_app_name_on_case_sensitive_volume(self):
        with tempfile.TemporaryDirectory() as root:
            d = self.make_mac_game(root, app="valheim.app")
            self.assertEqual(install.macos_app_name(d), "valheim.app")

    def test_auto_detect_from_candidate_paths(self):
        with tempfile.TemporaryDirectory() as root:
            d = self.make_mac_game(root)
            pattern = os.path.join(root, "*", "common", "Valheim")
            self.assertEqual(install.find_macos_game_dir(None, candidates=[pattern]), d)

    def test_dir_without_valheim_app_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                install.find_game_dir(d, platform="darwin")
            # A file named Valheim.app is not an app bundle
            open(os.path.join(d, "Valheim.app"), "w").close()
            with self.assertRaises(SystemExit):
                install.find_game_dir(d, platform="darwin")

    def test_linux_detection_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            mac = self.make_mac_game(root)
            with self.assertRaises(SystemExit):
                install.find_game_dir(mac, platform="linux")
        with tempfile.TemporaryDirectory() as lin:
            open(os.path.join(lin, "valheim.x86_64"), "w").close()
            self.assertEqual(install.find_game_dir(lin, platform="linux"), lin)

    def test_prepare_macos_points_script_at_app_and_makes_it_executable(self):
        with tempfile.TemporaryDirectory() as root:
            d = self.make_mac_game(root)
            script = os.path.join(d, "start_game_bepinex.sh")
            with open(script, "w") as f:
                f.write('#!/bin/sh\n# LINUX: name of Unity executable\nexecutable_name="valheim.x86_64"\narchpreference="arm64,x86_64"\n')
            os.chmod(script, 0o644)
            install.prepare_macos(d, apple_silicon=True)
            with open(script) as f:
                text = f.read()
            self.assertIn('executable_name="Valheim.app"\n', text)
            self.assertNotIn("valheim.x86_64", text)
            # Apple Silicon keeps the pack's native-first default
            self.assertIn('archpreference="arm64,x86_64"', text)
            self.assertTrue(os.access(script, os.X_OK))

    def test_intel_mac_gets_x86_64_only_arch_preference(self):
        # arch(1) on Intel exits "Unknown architecture: arm64" with the pack default
        with tempfile.TemporaryDirectory() as root:
            d = self.make_mac_game(root)
            script = os.path.join(d, "start_game_bepinex.sh")
            with open(script, "w") as f:
                f.write('executable_name="valheim.x86_64"\narchpreference="arm64,x86_64"\n')
            install.prepare_macos(d, apple_silicon=False)
            with open(script) as f:
                text = f.read()
            self.assertIn('archpreference="x86_64"\n', text)
            self.assertNotIn("arm64", text)

    def test_macos_launch_options_use_quoted_absolute_script_path(self):
        d = "/Users/x/Library/Application Support/Steam/steamapps/common/Valheim"
        self.assertEqual(install.macos_launch_options(d),
                         '"/Users/x/Library/Application Support/Steam/steamapps/common/Valheim/start_game_bepinex.sh" %command%')

    def test_language_pref_written_only_when_missing(self):
        class Run:
            def __init__(self, read_rc, read_out=""):
                self.calls, self.read_rc, self.read_out = [], read_rc, read_out
            def __call__(self, cmd, **kw):
                self.calls.append(cmd)
                rc = self.read_rc if cmd[1] == "read" else 0
                return subprocess.CompletedProcess(cmd, rc, stdout=self.read_out if cmd[1] == "read" else "", stderr="")
        missing = Run(read_rc=1)
        self.assertTrue(install.ensure_language_pref(run=missing))
        self.assertEqual(missing.calls[-1], ["defaults", "write", "com.coffeestain.valheim-steam", "language", "-string", "English"])
        present = Run(read_rc=0, read_out="German\n")
        self.assertFalse(install.ensure_language_pref(run=present))
        self.assertEqual([c[1] for c in present.calls], ["read"])

    def test_loose_plugin_dlls_are_reported(self):
        with tempfile.TemporaryDirectory() as d:
            plugins = os.path.join(d, "BepInEx", "plugins")
            os.makedirs(os.path.join(plugins, "ns-Mod"))
            open(os.path.join(plugins, "ns-Mod", "Mod.dll"), "w").close()
            open(os.path.join(plugins, "ValheimPlus.dll"), "w").close()
            self.assertEqual(install.loose_plugin_files(d), ["ValheimPlus.dll"])


if __name__ == "__main__":
    unittest.main()
