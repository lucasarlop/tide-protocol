from __future__ import annotations

import json

from tide import mcp


def test_mcp_initialize_serves_tide_1_1_policy(capsys) -> None:
    mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})

    payload = json.loads(capsys.readouterr().out)
    result = payload["result"]

    assert result["serverInfo"]["version"] == "1.1.1"
    assert "model_policy" in result["instructions"]
    assert "two bounded failed attempts" in result["instructions"]
