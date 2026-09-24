"""Smoke tests proving the new package, toolchain and entry point are wired."""

import re

import pytest

import serptank
from serptank.__main__ import main


def test_version_is_semver_like() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+.*", serptank.__version__)


def test_module_entrypoint_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert capsys.readouterr().out == f"serptank {serptank.__version__}\n"
