import argparse
import io
import json
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from unittest.mock import patch

from mathen.cli import build_parser, mcp_command
from mathen.config import MCPSettings, default_config


class _Response:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit: int) -> bytes:
        return self.body


class CliTests(unittest.TestCase):
    def test_mathview_validation_command_is_in_help(self) -> None:
        help_text = build_parser(default_config()).format_help()

        self.assertIn("validate-mathviews", help_text)
        self.assertIn("validate mathematical-view contracts", help_text)

    def test_mcp_check_sends_protocol_metadata_and_validates_response(self) -> None:
        config = replace(
            default_config(),
            mcp=MCPSettings(url="https://example.test/mcp", token_env="TEST_TOKEN"),
        )
        args = argparse.Namespace(mcp_command="check")
        response = _Response(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "test-mcp"},
                    },
                }
            ).encode()
        )
        output = io.StringIO()
        with patch.dict("os.environ", {"TEST_TOKEN": "secret"}, clear=False):
            with patch("mathen.cli.urlopen", return_value=response) as open_url:
                with redirect_stdout(output):
                    result = mcp_command(args, config)

        self.assertEqual(result, 0)
        self.assertIn("connected  test-mcp", output.getvalue())
        request = open_url.call_args.args[0]
        self.assertEqual(request.headers["Authorization"], "Bearer secret")
        self.assertEqual(request.headers["Mcp-protocol-version"], "2025-06-18")
        payload = json.loads(request.data)
        self.assertEqual(payload["params"]["clientInfo"]["name"], "mathen-cli")


if __name__ == "__main__":
    unittest.main()
