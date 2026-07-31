from __future__ import annotations

import ast

from kaggriculture_lab.research.extract_public_agents import _literal, _strip_magic


def test_strip_magic() -> None:
    assert _strip_magic("%%writefile main.py\n\ndef agent(obs):\n    return {}\n").startswith(
        "def agent"
    )


def test_literal_extracts_exact_string() -> None:
    source = "AGENT_SOURCE = 'def agent(obs):\\n    return {}\\n'\n"
    extracted = _literal(source, "AGENT_SOURCE")
    ast.parse(extracted)
    assert extracted == "def agent(obs):\n    return {}\n"
