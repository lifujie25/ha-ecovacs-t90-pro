"""Install the T90 Pro hardware-class compatibility profile."""

from __future__ import annotations

import importlib
from dataclasses import replace

from deebot_client.capabilities import (
    CapabilityEvent,
    CapabilityExecute,
    CapabilityMap,
)
from deebot_client.commands.json.clean import CleanAreaV2, CleanV2
from deebot_client.commands.json.map import (
    GetMapInfoV2,
    GetMapTrace,
    GetMinorMap,
)
from deebot_client.events import (
    CachedMapInfoEvent,
    MajorMapEvent,
    MapChangedEvent,
    MapTraceEvent,
    PositionsEvent,
    RoomsEvent,
)
from deebot_client.models import StaticDeviceInfo

from .const import SOURCE_HARDWARE_MODULE, TARGET_DEVICE_CLASS
from .map import GetMapBootstrap, GetMapSetV2T90, add_room_metadata_to_svg


def _install_svg_room_labels() -> None:
    """Decorate T90 maps with room labels and selection metadata."""
    from deebot_client.map import Map

    if hasattr(Map, "_t90_original_get_svg_map"):
        return

    original = Map.get_svg_map
    Map._t90_original_get_svg_map = original

    def get_svg_map_with_rooms(self: Map) -> str | None:
        svg = original(self)
        if svg is None:
            return None
        return add_room_metadata_to_svg(
            svg,
            self._event_bus,
            self._map_data._rotation,
        )

    Map.get_svg_map = get_svg_map_with_rooms


def _build_device_info() -> StaticDeviceInfo:
    """Extend the conservative T90 profile with its current V2 protocols."""
    source_module = importlib.import_module(SOURCE_HARDWARE_MODULE)
    source_device_info = source_module.get_device_info()

    map_capabilities = CapabilityMap(
        cached_info=CapabilityEvent(CachedMapInfoEvent, [GetMapBootstrap()]),
        changed=CapabilityEvent(MapChangedEvent, []),
        info=CapabilityExecute(GetMapInfoV2),
        # T90 does not support getMajorMap. MapInfo V2 supplies the geometry.
        major=CapabilityEvent(MajorMapEvent, []),
        minor=CapabilityExecute(GetMinorMap),
        # Bootstrap refreshes both of these after discovering the active map ID.
        position=CapabilityEvent(PositionsEvent, []),
        rooms=CapabilityEvent(RoomsEvent, []),
        set=CapabilityExecute(GetMapSetV2T90),
        trace=CapabilityEvent(MapTraceEvent, [GetMapTrace()]),
    )
    clean_capabilities = replace(
        source_device_info.capabilities.clean,
        action=replace(
            source_device_info.capabilities.clean.action,
            command=CleanV2,
            area=CleanAreaV2,
        ),
    )
    capabilities = replace(
        source_device_info.capabilities,
        clean=clean_capabilities,
        map=map_capabilities,
    )
    return replace(source_device_info, capabilities=capabilities)


def install_hardware_alias() -> StaticDeviceInfo:
    """Register the Chinese T90 Pro class with its augmented profile."""
    hardware_package = importlib.import_module("deebot_client.hardware")
    devices = getattr(hardware_package, "_DEVICES", None)
    if isinstance(devices, dict):
        official = devices.get(TARGET_DEVICE_CLASS)
        if official is not None and getattr(official.capabilities, "map", None):
            # A future official profile wins and the helper becomes a no-op.
            return official

    device_info = _build_device_info()
    _install_svg_room_labels()

    # The library caches missing class lookups, so a previous failed discovery
    # must be cleared before the official integration is reloaded.
    not_found = getattr(hardware_package, "_NOT_FOUND", None)
    if isinstance(not_found, set):
        not_found.discard(TARGET_DEVICE_CLASS)

    if isinstance(devices, dict):
        devices[TARGET_DEVICE_CLASS] = device_info

    return device_info
