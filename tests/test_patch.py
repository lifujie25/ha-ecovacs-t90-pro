"""Tests for the T90 Pro compatibility profile."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

from deebot_client.event_bus import EventBus
from deebot_client.events import MapSetType
from deebot_client.message import HandlingState
from deebot_client.models import CleanAction, CleanMode

ROOT = Path(__file__).parents[1] / "custom_components" / "ecovacs_t90_patch"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


package = types.ModuleType("ecovacs_t90_patch")
package.__path__ = [str(ROOT)]
sys.modules["ecovacs_t90_patch"] = package
_load_module("ecovacs_t90_patch.const", ROOT / "const.py")
map_module = _load_module("ecovacs_t90_patch.map", ROOT / "map.py")
patch_module = _load_module("ecovacs_t90_patch.patch", ROOT / "patch.py")


def test_install_hardware_profile_adds_map_without_legacy_major_command() -> None:
    from deebot_client import hardware

    old_device = hardware._DEVICES.get("guaexd")
    old_not_found = hardware._NOT_FOUND.copy()
    try:
        hardware._NOT_FOUND.add("guaexd")
        profile = patch_module.install_hardware_alias()

        assert hardware._DEVICES["guaexd"] is profile
        assert "guaexd" not in hardware._NOT_FOUND
        assert profile.capabilities.map is not None
        assert profile.capabilities.map.major.get == []
        assert [
            command.NAME for command in profile.capabilities.map.cached_info.get
        ] == ["getInfo"]
    finally:
        hardware._NOT_FOUND.clear()
        hardware._NOT_FOUND.update(old_not_found)
        if old_device is None:
            hardware._DEVICES.pop("guaexd", None)
        else:
            hardware._DEVICES["guaexd"] = old_device


def test_map_bootstrap_requests_v2_map_layers_and_position() -> None:
    profile = patch_module._build_device_info()

    async def execute_command(_):
        raise AssertionError("No command should execute while parsing a response")

    event_bus = EventBus(execute_command, profile.capabilities)
    command = map_module.GetMapBootstrap()
    response = {
        "ret": "ok",
        "resp": {
            "body": {
                "code": 0,
                "data": {
                    "getCachedMapInfo": {
                        "code": 0,
                        "data": {
                            "info": [
                                {
                                    "mid": "test-map",
                                    "using": 1,
                                    "built": 1,
                                    "angle": 270,
                                }
                            ]
                        },
                    }
                },
            }
        },
    }

    result = command._handle_response(event_bus, response)

    assert result.state == HandlingState.SUCCESS
    assert [entry.NAME for entry in result.requested_commands] == [
        "getMapSet_V2",
        "getMapSet_V2",
        "getMapSet_V2",
        "getMapInfo_V2",
        "getPos_V2",
    ]
    assert [entry._args["type"] for entry in result.requested_commands[:3]] == [
        entry.value for entry in MapSetType
    ]
    assert result.requested_commands[-2]._args == {
        "mid": "test-map",
        "type": "0",
    }
    assert result.requested_commands[-1]._args == {
        "type": ["chargePos", "deebotPos"],
        "mid": "test-map",
    }


def test_hardware_profile_uses_v2_clean_commands() -> None:
    profile = patch_module._build_device_info()
    clean_action = profile.capabilities.clean.action

    auto_command = clean_action.command(CleanAction.START)
    room_command = clean_action.area(CleanMode.SPOT_AREA, [5, 8], 1)

    assert auto_command.NAME == "clean_V2"
    assert auto_command._args == {
        "act": "start",
        "content": {"type": "auto"},
    }
    assert room_command.NAME == "clean_V2"
    assert room_command._args == {
        "act": "start",
        "content": {
            "type": "spotArea",
            "value": "5,8",
        },
    }
