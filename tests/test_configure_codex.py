import importlib.util
from pathlib import Path
import tempfile
import unittest
import tomllib

spec = importlib.util.spec_from_file_location('configure', Path(__file__).parents[1]/'scripts'/'configure_codex.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.exe = self.root/'folder with spaces'/'capcut-mcp'
        self.exe.parent.mkdir()
        self.exe.write_bytes(b'test fixture only')
        self.config = self.root/'config.toml'

    def test_missing_file_and_idempotence(self):
        result = module.configure(self.config, self.exe)
        self.assertTrue(result['changed'])
        payload = self.config.read_bytes()
        self.assertFalse(module.configure(self.config, self.exe)['changed'])
        self.assertEqual(payload, self.config.read_bytes())

    def test_other_mcp_preserved_and_backup_exact(self):
        original = b'# keep\r\nmodel="example"\r\n[mcp_servers.other]\r\ncommand="other"\r\n'
        self.config.write_bytes(original)
        result = module.configure(self.config, self.exe)
        self.assertEqual(Path(result['backup']).read_bytes(), original)
        self.assertTrue(self.config.read_bytes().startswith(original))
        self.assertEqual(tomllib.loads(self.config.read_text())['mcp_servers']['other'], {'command':'other'})

    def test_existing_section_preserves_env_and_following(self):
        self.config.write_text('[mcp_servers.capcut]\ncommand="old"\nstartup_timeout_sec=30\n[mcp_servers.capcut.env]\nA="B"\n[mcp_servers.other]\ncommand="other"\n')
        module.configure(self.config, self.exe)
        parsed = tomllib.loads(self.config.read_text())
        self.assertEqual(parsed['mcp_servers']['capcut']['env'], {'A':'B'})
        self.assertEqual(parsed['mcp_servers']['capcut']['startup_timeout_sec'],30)
        self.assertEqual(parsed['mcp_servers']['other'],{'command':'other'})

    def test_invalid_toml_untouched(self):
        original = b'[invalid'
        self.config.write_bytes(original)
        with self.assertRaises(tomllib.TOMLDecodeError): module.configure(self.config,self.exe)
        self.assertEqual(self.config.read_bytes(),original)
        self.assertEqual(list(self.root.glob('*.bak-*')),[])

    def test_bom_preserved(self):
        self.config.write_bytes(b'\xef\xbb\xbf# header\r\n')
        module.configure(self.config,self.exe)
        self.assertTrue(self.config.read_bytes().startswith(b'\xef\xbb\xbf'))

    def test_quoted_header_refused_safely(self):
        original=b'[mcp_servers."capcut"]\ncommand="old"\n'
        self.config.write_bytes(original)
        with self.assertRaises(ValueError):module.configure(self.config,self.exe)
        self.assertEqual(self.config.read_bytes(),original)

    def test_existing_args_cleared_for_native_entry_point(self):
        self.config.write_text('[mcp_servers.capcut]\ncommand="old"\nargs=["-m","old_module"]\n')
        module.configure(self.config,self.exe)
        parsed=tomllib.loads(self.config.read_text())
        self.assertEqual(parsed['mcp_servers']['capcut']['args'],[])

    def test_remote_transport_refused_without_changes(self):
        original=b'[mcp_servers.capcut]\nurl="https://example.invalid/mcp"\n'
        self.config.write_bytes(original)
        with self.assertRaises(ValueError):module.configure(self.config,self.exe)
        self.assertEqual(self.config.read_bytes(),original)

if __name__ == '__main__':unittest.main()
