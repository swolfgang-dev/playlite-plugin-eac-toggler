import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import toggler


class TogglerTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        (self.root/'eldenring.exe').write_bytes(b'MZgame')
        (self.root/'start_protected_game.exe').write_bytes(b'MZeac')

    def test_round_trip_restores_launcher_and_removes_created_appid(self):
        self.assertEqual(toggler.status(self.root),'Enabled')
        toggler.disable(self.root)
        self.assertEqual(toggler.status(self.root),'Disabled')
        self.assertEqual((self.root/'start_protected_game.exe').read_bytes(),b'MZgame')
        toggler.enable(self.root)
        self.assertEqual((self.root/'start_protected_game.exe').read_bytes(),b'MZeac')
        self.assertFalse((self.root/'steam_appid.txt').exists())
        self.assertFalse((self.root/toggler.STATE).exists())

    def test_malformed_backup_records_fail_before_modifying_launchers(self):
        toggler.disable(self.root)
        launcher = (self.root / 'start_protected_game.exe').read_bytes()
        for record in ([], None, {}, {'original': 1, 'patched': [], 'created_appid': 'yes'}):
            (self.root / toggler.STATE / 'state.json').write_text(json.dumps(record))
            with self.subTest(record=record), self.assertRaises(ValueError):
                toggler.enable(self.root)
            self.assertEqual((self.root / 'start_protected_game.exe').read_bytes(), launcher)

    def test_preserves_existing_appid(self):
        (self.root/'steam_appid.txt').write_bytes(b'1245620')
        toggler.disable(self.root);toggler.enable(self.root)
        self.assertEqual((self.root/'steam_appid.txt').read_bytes(),b'1245620')

    def test_updated_launcher_is_preserved(self):
        toggler.disable(self.root)
        (self.root/'start_protected_game.exe').write_bytes(b'MZupdated')
        self.assertEqual(toggler.status(self.root),'Game files changed')
        with self.assertRaises(ValueError):toggler.enable(self.root)
        self.assertEqual((self.root/'start_protected_game.exe').read_bytes(),b'MZupdated')

    def test_modified_backup_is_rejected(self):
        toggler.disable(self.root)
        (self.root/toggler.STATE/'start_protected_game.exe').write_bytes(b'MZmodified')
        with self.assertRaises(ValueError):toggler.enable(self.root)

    def test_symlink_does_not_modify_target(self):
        target=self.root/'original';target.write_bytes(b'MZeac')
        (self.root/'start_protected_game.exe').unlink()
        (self.root/'start_protected_game.exe').symlink_to(target)
        with self.assertRaises(ValueError):toggler.disable(self.root)
        self.assertEqual(target.read_bytes(),b'MZeac')

    def test_double_disable_keeps_original_backup(self):
        toggler.disable(self.root)
        with self.assertRaises(ValueError):toggler.disable(self.root)
        toggler.enable(self.root)
        self.assertEqual((self.root/'start_protected_game.exe').read_bytes(),b'MZeac')

    def test_subfolder_and_unrelated_appid(self):
        with self.assertRaises(ValueError):toggler.folder(self.root/'missing')
        (self.root/'steam_appid.txt').write_bytes(b'999')
        with self.assertRaises(ValueError):toggler.disable(self.root)
        self.assertFalse((self.root/toggler.STATE).exists())

    def test_copy_failure_leaves_original_unchanged(self):
        with patch.object(toggler.shutil,'copy2',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):toggler.disable(self.root)
        self.assertFalse((self.root/toggler.STATE).exists())
        self.assertEqual((self.root/'start_protected_game.exe').read_bytes(),b'MZeac')

    def test_updated_game_executable_is_detected(self):
        toggler.disable(self.root)
        (self.root/'eldenring.exe').write_bytes(b'MZnew game')
        self.assertEqual(toggler.status(self.root),'Game files changed')
        toggler.enable(self.root)
        self.assertEqual((self.root/'eldenring.exe').read_bytes(),b'MZnew game')

    def test_changed_generated_appid_is_preserved(self):
        toggler.disable(self.root)
        (self.root/'steam_appid.txt').write_bytes(b'changed')
        with self.assertRaises(ValueError):toggler.enable(self.root)
        self.assertEqual((self.root/'steam_appid.txt').read_bytes(),b'changed')

    def test_installation_root_resolves_game_subfolder(self):
        game=self.root/'Game';game.mkdir()
        for name in ('eldenring.exe','start_protected_game.exe'):(self.root/name).rename(game/name)
        toggler.disable(self.root);self.assertEqual(toggler.status(self.root),'Disabled')
        toggler.enable(self.root)
