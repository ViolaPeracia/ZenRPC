import sys
from unittest.mock import MagicMock, patch
import pytest

from main import parse_args, run_app


def test_parse_args_defaults():
    args = parse_args([])
    assert args.gui is False
    assert args.tray is False
    assert args.headless is False
    assert args.config is None


def test_parse_args_modes():
    args_gui = parse_args(["--gui"])
    assert args_gui.gui is True

    args_tray = parse_args(["--tray"])
    assert args_tray.tray is True

    args_headless = parse_args(["--headless"])
    assert args_headless.headless is True


def test_parse_args_custom_config():
    args = parse_args(["--config", "/custom/zenrpc.json"])
    assert args.config == "/custom/zenrpc.json"


def test_parse_args_mutually_exclusive_modes():
    with pytest.raises(SystemExit):
        parse_args(["--tray", "--headless"])


@patch("main.run_headless")
def test_run_app_dispatches_headless(mock_run_headless):
    with patch("main.parse_args", return_value=parse_args(["--headless", "--config", "my_cfg.json"])):
        run_app()
    mock_run_headless.assert_called_once_with(config_path="my_cfg.json")


@patch("main.run_tray")
def test_run_app_dispatches_tray(mock_run_tray):
    with patch("main.parse_args", return_value=parse_args(["--tray"])):
        run_app()
    mock_run_tray.assert_called_once_with(config_path=None)


@patch("main.run_gui")
def test_run_app_dispatches_gui_default(mock_run_gui):
    with patch("main.parse_args", return_value=parse_args([])):
        run_app()
    mock_run_gui.assert_called_once_with(config_path=None)


@patch("main.run_headless")
@patch("main.run_tray")
@patch("main.run_gui", side_effect=RuntimeError("No X display"))
def test_run_app_gui_fallback_to_tray(mock_run_gui, mock_run_tray, mock_run_headless):
    with patch("main.parse_args", return_value=parse_args([])):
        run_app()
    mock_run_gui.assert_called_once()
    mock_run_tray.assert_called_once()
    mock_run_headless.assert_not_called()


@patch("main.run_headless")
@patch("main.run_tray", side_effect=RuntimeError("Tray failed"))
@patch("main.run_gui", side_effect=RuntimeError("No X display"))
def test_run_app_gui_fallback_to_headless(mock_run_gui, mock_run_tray, mock_run_headless):
    with patch("main.parse_args", return_value=parse_args([])):
        run_app()
    mock_run_gui.assert_called_once()
    mock_run_tray.assert_called_once()
    mock_run_headless.assert_called_once()
