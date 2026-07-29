"""T90 Pro map protocol compatibility commands."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

from deebot_client.commands.json.common import JsonCommandWithMessageHandling
from deebot_client.commands.json.map import GetMapSetV2
from deebot_client.commands.json.pos import GetPos
from deebot_client.events import MapSetType, RoomsEvent
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict
from deebot_client.messages.json.map.cached_map_info import OnCachedMapInfo
from deebot_client.models import Room
from deebot_client.rs.map import RotationAngle

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


@dataclass(frozen=True)
class T90Room:
    """Room metadata needed for labels and interactive map selection."""

    id: int
    name: str
    x: float
    y: float


_ROOMS: WeakKeyDictionary[EventBus, tuple[T90Room, ...]] = WeakKeyDictionary()
_ROOM_PATH_RE = re.compile(r"(?:^|\s)r\d+(?:\s|$)")


def _rotate_point(x: float, y: float, rotation: RotationAngle) -> tuple[float, float]:
    """Apply the same coordinate transform as deebot-client's SVG renderer."""
    if rotation == RotationAngle.DEG_90:
        return y / 50, x / 50
    if rotation == RotationAngle.DEG_180:
        return -x / 50, y / 50
    if rotation == RotationAngle.DEG_270:
        return -y / 50, -x / 50
    return x / 50, -y / 50


def add_room_metadata_to_svg(
    svg: str, event_bus: EventBus, rotation: RotationAngle
) -> str:
    """Add room names and selection metadata to a generated SVG map."""
    rooms = _ROOMS.get(event_bus)
    if not rooms or 'id="t90-room-labels"' in svg:
        return svg

    room_paths = []
    for match in re.finditer(r"<path\b[^>]*>", svg):
        tag = match.group(0)
        class_match = re.search(r'class="([^"]*)"', tag)
        if class_match and _ROOM_PATH_RE.search(class_match.group(1)):
            room_paths.append(match)

    # MapInfo V2 emits room paths in room-ID order. Extra colored paths can be
    # present for newer layers, so only annotate the first path for each room.
    annotated = svg
    offset = 0
    for path_match, room in zip(room_paths, sorted(rooms, key=lambda entry: entry.id)):
        metadata = (
            f' data-room-id="{room.id}" data-room-name="{escape(room.name)}"'
            ' class="t90-room '
        )
        original = path_match.group(0)
        replacement = original.replace('class="', metadata, 1)
        start = path_match.start() + offset
        end = path_match.end() + offset
        annotated = annotated[:start] + replacement + annotated[end:]
        offset += len(replacement) - len(original)

    labels = []
    for room in rooms:
        x, y = _rotate_point(room.x, room.y, rotation)
        label = escape(room.name)
        width = max(16, len(room.name) * 5 + 7)
        labels.append(
            f'<g class="t90-room-label" data-room-id="{room.id}" '
            f'data-room-name="{escape(room.name)}" '
            f'transform="translate({x:.2f} {y:.2f})">'
            f'<rect x="{-width / 2:.2f}" y="-4.5" width="{width}" height="9" '
            'rx="2.5"/>'
            f'<text y="1.8">{label}</text></g>'
        )

    overlay = (
        '<g id="t90-room-labels">' + "".join(labels) + '</g><style id="t90-room-style">'
        ".t90-room{cursor:pointer;transition:filter .15s,stroke .15s}"
        ".t90-room:hover{filter:brightness(.92)}"
        ".t90-room.t90-selected{stroke:#1677ff;stroke-width:3}"
        ".t90-room-label{cursor:pointer;pointer-events:auto}"
        ".t90-room-label.t90-selected rect{fill:#dbeafe;stroke:#1677ff;stroke-width:1}"
        ".t90-room-label rect{fill:#fff;fill-opacity:.88;stroke:#64748b;stroke-width:.35}"
        ".t90-room-label text{fill:#1f2937;font-family:sans-serif;font-size:5px;"
        "font-weight:600;text-anchor:middle}"
        "</style>"
    )
    return annotated.replace("</svg>", f"{overlay}</svg>")


class GetMapSetV2T90(GetMapSetV2):
    """Parse the 12-field room format used by Chinese T90 firmware."""

    @classmethod
    def _handle_rooms_subsets(
        cls,
        event_bus: EventBus,
        data: dict[str, Any],
        subsets: list[list[str]],
        map_id: str,
    ) -> HandlingResult:
        if subsets and all(len(subset) >= 7 for subset in subsets):
            rooms = tuple(
                T90Room(
                    id=int(subset[0]),
                    name=subset[1].strip() or f"区域 {subset[0]}",
                    x=float(subset[5]),
                    y=float(subset[6]),
                )
                for subset in subsets
            )
            _ROOMS[event_bus] = rooms
            event_bus.notify(
                RoomsEvent(
                    map_id,
                    [Room(room.name, room.id, f"{room.x},{room.y}") for room in rooms],
                )
            )
            return HandlingResult.success()

        return super()._handle_rooms_subsets(event_bus, data, subsets, map_id)


class GetPosV2(GetPos):
    """Get robot and charging-station positions for a T90 map."""

    NAME = "getPos_V2"

    def __init__(self, map_id: str) -> None:
        JsonCommandWithMessageHandling.__init__(
            self,
            {
                "type": ["chargePos", "deebotPos"],
                "mid": map_id,
            },
        )


class GetMapBootstrap(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Discover the active T90 map through the combined getInfo command."""

    NAME = "getInfo"

    def __init__(self) -> None:
        # This is the request shape used by the Ecovacs app for current T90 firmware.
        super().__init__(["getCachedMapInfo", "getRobotState", "getWorkState"])

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        cached_map_info = data.get("getCachedMapInfo")
        if (
            not isinstance(cached_map_info, dict)
            or cached_map_info.get("code") != 0
            or not isinstance(cached_map_info.get("data"), dict)
        ):
            return HandlingResult.analyse()

        result = OnCachedMapInfo._handle_body_data_dict(
            event_bus, cached_map_info["data"]
        )
        if (
            result.state != HandlingState.SUCCESS
            or not result.args
            or not (map_capability := event_bus.capabilities.map)
        ):
            return result

        map_id = result.args["map_id"]
        commands = [
            map_capability.set.execute(map_id, map_set_type)
            for map_set_type in MapSetType
        ]
        if map_capability.info:
            commands.append(map_capability.info.execute(map_id))
        commands.append(GetPosV2(map_id))

        return HandlingResult(
            HandlingState.SUCCESS,
            result.args,
            requested_commands=commands,
        )

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        # CommandWithMessageHandling drops follow-up commands returned by a message
        # handler, so preserve them for this compound response explicitly.
        if response.get("ret") == "ok":
            return self.handle(event_bus, response.get("resp", response))

        return super()._handle_response(event_bus, response)


__all__ = [
    "GetMapBootstrap",
    "GetMapSetV2T90",
    "GetPosV2",
    "add_room_metadata_to_svg",
]
