import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mathen.config import (
    ConfigError,
    config_to_dict,
    initialize_config,
    load_config,
    platform_paths,
    set_config_value,
)


class ConfigurationTests(unittest.TestCase):
    def test_toml_config_overrides_paths_and_llm(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                '[paths]\ndata_dir = "~/mathen-data"\n'
                '[llm]\nbase_url = "https://llm.example/v1"\n'
                'model = "local-model"\ntimeout = 45\n',
                encoding="utf-8",
            )
            config = load_config(path)

        self.assertTrue(config.loaded)
        self.assertEqual(config.llm.base_url, "https://llm.example/v1")
        self.assertEqual(config.llm.model, "local-model")
        self.assertEqual(config.llm.timeout, 45.0)
        self.assertEqual(config.paths.data_dir, Path.home() / "mathen-data")

    def test_initialize_config_is_private_and_valid_toml(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = initialize_config(Path(directory) / "config.toml")
            config = load_config(path)

            self.assertTrue(config.loaded)
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_set_config_value_creates_a_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            set_config_value("llm.model", "test-model", path)
            set_config_value("llm.timeout", "30", path)
            config = load_config(path)

        self.assertEqual(config.llm.model, "test-model")
        self.assertEqual(config.llm.timeout, 30.0)

    def test_invalid_config_key_and_timeout_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text("[llm]\ntimeout = 0\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)
            with self.assertRaises(ConfigError):
                set_config_value("unknown.value", "x", path)

    def test_platform_defaults_use_standard_directories(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APPDATA": "/windows/roaming",
                "LOCALAPPDATA": "/windows/local",
                "XDG_CONFIG_HOME": "/xdg/config",
                "XDG_DATA_HOME": "/xdg/data",
                "XDG_CACHE_HOME": "/xdg/cache",
            },
            clear=False,
        ):
            with patch("mathen.config.platform.system", return_value="Windows"):
                windows = platform_paths()
            with patch("mathen.config.platform.system", return_value="Darwin"):
                macos = platform_paths()
            with patch("mathen.config.platform.system", return_value="Linux"):
                linux = platform_paths()

        self.assertEqual(windows.config_dir, Path("/windows/roaming/mathen"))
        self.assertEqual(windows.data_dir, Path("/windows/local/mathen"))
        self.assertEqual(
            macos.config_dir, Path.home() / "Library/Application Support/Mathen"
        )
        self.assertEqual(linux.config_dir, Path("/xdg/config/mathen"))
        self.assertEqual(linux.data_dir, Path("/xdg/data/mathen"))

    def test_config_view_can_be_serialized_and_redacts_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                '[llm]\nmodel = "model"\napi_key = "secret"\n', encoding="utf-8"
            )
            config = load_config(path)

        view = config_to_dict(config, redact_secrets=True)
        self.assertEqual(view["llm"]["api_key"], "***")
        json.dumps(view)

    def test_provider_and_mcp_settings_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                '[llm]\nprovider = "local"\n'
                '[llm.providers.local]\nbase_url = "http://localhost:11434/v1"\n'
                'model = "qwen"\napi_key = "local"\n'
                '[mcp]\nurl = "https://example.com/mcp"\n'
                '[sync]\nref = "v0.0.1"\n',
                encoding="utf-8",
            )
            config = load_config(path)

        self.assertEqual(config.llm.provider, "local")
        self.assertEqual(config.llm.providers["local"]["model"], "qwen")
        self.assertEqual(config.mcp.url, "https://example.com/mcp")
        self.assertEqual(config.sync.ref, "v0.0.1")

    def test_starter_config_contains_mcp_and_sync_sections(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = initialize_config(Path(directory) / "config.toml")
            text = path.read_text(encoding="utf-8")

        self.assertIn("[mcp]", text)
        self.assertIn("[sync]", text)


if __name__ == "__main__":
    unittest.main()
