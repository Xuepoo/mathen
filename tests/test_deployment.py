"""Offline checks for deployment variable overrides; never invoke Wrangler."""

import os
import shutil
import subprocess
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "deploy.yml"
PUBLIC_VARIABLES = (
    "TURNSTILE_SITE_KEY",
    "TURNSTILE_HOSTNAME",
    "TURNSTILE_SESSION_TTL_SECONDS",
)


class DeploymentConfigurationTests(unittest.TestCase):
    def test_public_settings_use_environment_variables_not_secrets(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for name in PUBLIC_VARIABLES:
            self.assertIn("${{ vars." + name + " }}", workflow)
            self.assertNotIn("${{ secrets." + name + " }}", workflow)
        for name in ("TURNSTILE_SECRET_KEY", "API_ACCESS_TOKEN"):
            self.assertIn("${{ secrets." + name + " }}", workflow)
            self.assertNotIn("${{ vars." + name + " }}", workflow)

    @unittest.skipUnless(shutil.which("bash"), "requires Bash for workflow checks")
    def test_deploy_overrides_only_nonempty_variables_and_quotes_values(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        step = workflow.split("      - name: Deploy Worker\n", 1)[1]
        step = step.split("\n      - name:", 1)[0]
        script = step.split("        run: |\n", 1)[1]
        script = "\n".join(
            line.removeprefix("          ") for line in script.splitlines()
        )
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in PUBLIC_VARIABLES
        }
        cases = [
            ({}, []),
            ({name: "" for name in PUBLIC_VARIABLES}, []),
            (
                {"TURNSTILE_HOSTNAME": "preview.example.test"},
                ["--var", "TURNSTILE_HOSTNAME:preview.example.test"],
            ),
            (
                {"TURNSTILE_HOSTNAME": "quoted value; $(exit 99)"},
                ["--var", "TURNSTILE_HOSTNAME:quoted value; $(exit 99)"],
            ),
        ]
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                result = subprocess.run(
                    [
                        "bash",
                        "-euo",
                        "pipefail",
                        "-c",
                        'bun() { printf "%s\\n" "$@"; return 0; }\n' + script,
                    ],
                    env=environment | overrides,
                    text=True,
                    capture_output=True,
                    check=True,
                    timeout=10,
                )
                self.assertEqual(
                    result.stdout.splitlines(), ["run", "wrangler", "deploy", *expected]
                )


if __name__ == "__main__":
    unittest.main()
