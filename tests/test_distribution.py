from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]


class DistributionFilesTests(unittest.TestCase):
    def test_local_runtime_data_and_secrets_are_ignored(self) -> None:
        gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

        for required_pattern in (
            ".venv/",
            "__pycache__/",
            ".streamlit/secrets.toml",
            ".qa_data/",
            "*.sqlite3",
        ):
            with self.subTest(pattern=required_pattern):
                self.assertIn(required_pattern, gitignore)

    def test_streamlit_configuration_and_secret_template_are_valid_toml(self) -> None:
        config = tomllib.loads(
            (PROJECT_ROOT / ".streamlit/config.toml").read_text(encoding="utf-8")
        )
        secret_template = tomllib.loads(
            (PROJECT_ROOT / ".streamlit/secrets.toml.example").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(config["server"]["maxUploadSize"], 2)
        self.assertFalse(config["client"]["showErrorDetails"])
        self.assertGreaterEqual(len(secret_template["presenter_password"]), 12)


if __name__ == "__main__":
    unittest.main()
