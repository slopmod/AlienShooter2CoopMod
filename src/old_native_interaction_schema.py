"""Immutable interaction schema and strict original-map evidence guards.

No campaign geometry or map catalog lives here. Consumers select explicitly
reviewed definitions; these classes do not infer or mutate game behavior.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
import re
import struct
from typing import Literal


XYZ = tuple[float, float, float]
Triple = tuple[int, int, int]
Bounds = tuple[int, int]


def _integer(value: object, minimum: int, maximum: int, label: str) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'Invalid {label}: {value!r}')


def _tuple(value: object, length: int, label: str) -> None:
    if type(value) is not tuple or len(value) != length:
        raise ValueError(f'{label} must be an immutable {length}-tuple')


def _name(value: object, label: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', value):
        raise ValueError(f'Invalid {label}: {value!r}')


def _triple(value: Triple, label: str) -> None:
    _tuple(value, 3, label)
    for number in value:
        _integer(number, -(2 ** 31), 2 ** 31 - 1, label)


def _bounds(value: Bounds, label: str) -> None:
    _tuple(value, 2, label)
    for number in value:
        _integer(number, -(2 ** 31), 2 ** 31 - 1, label)
    if value[0] > value[1]:
        raise ValueError(f'Reversed {label}')


@dataclass(frozen=True, slots=True)
class MapIdentity:
    key: str
    path: str
    sha256: str

    def __post_init__(self) -> None:
        _name(self.key, 'map key')
        if not re.fullmatch(r'Maps/Level_(?:[0-9]{2}|07_[23])\.map', self.path):
            raise ValueError('Expected an audited campaign map path')
        if not re.fullmatch(r'[0-9a-f]{64}', self.sha256):
            raise ValueError('Expected a lowercase SHA256 map identity')


@dataclass(frozen=True, slots=True)
class SpriteIdentity:
    offset: int
    saved_id: int
    vid: int
    xyz: XYZ

    def __post_init__(self) -> None:
        for label, value in (('sprite offset', self.offset), ('saved ID', self.saved_id), ('VID', self.vid)):
            _integer(value, 0, 2 ** 32 - 1, label)
        _tuple(self.xyz, 3, 'source XYZ')
        for coordinate in self.xyz:
            if type(coordinate) not in (int, float) or not math.isfinite(coordinate):
                raise ValueError('Source coordinates must be finite original float32 values')
            try:
                exact = struct.unpack('<f', struct.pack('<f', coordinate))[0]
            except (OverflowError, struct.error) as error:
                raise ValueError('Source coordinate exceeds float32 range') from error
            if exact != coordinate:
                raise ValueError('Source coordinate is not an exact original float32 value')

    def packed(self) -> bytes:
        return struct.pack('<IIfff', self.saved_id, self.vid, *self.xyz)


@dataclass(frozen=True, slots=True)
class MapCommand:
    offset: int
    values: tuple[int, int, int, int]

    def __post_init__(self) -> None:
        _integer(self.offset, 0, 2 ** 32 - 1, 'command offset')
        _tuple(self.values, 4, 'command')
        for value in self.values:
            _integer(value, -(2 ** 31), 2 ** 31 - 1, 'command field')

    def packed(self) -> bytes:
        return struct.pack('<4i', *self.values)


@dataclass(frozen=True, slots=True)
class PartyTrigger:
    name: str
    map_key: str
    sprite: SpriteIdentity
    trigger: Triple
    records: tuple[int, ...]
    extra_commands: tuple[MapCommand, ...] = ()
    source_guard: Literal['exact_xyz', 'map_vid_act43'] = 'exact_xyz'
    runtime_vid: int | None = None

    def __post_init__(self) -> None:
        _name(self.name, 'trigger name')
        _name(self.map_key, 'map key')
        if not isinstance(self.sprite, SpriteIdentity):
            raise ValueError('Trigger requires an immutable sprite identity')
        if self.source_guard not in ('exact_xyz', 'map_vid_act43'):
            raise ValueError('Unsupported native trigger source guard')
        if self.runtime_vid is not None:
            _integer(self.runtime_vid, 1, 2 ** 31 - 1, 'Runtime source VID')
            if self.source_guard != 'map_vid_act43':
                raise ValueError('Runtime VID requires the map/VID source guard')
        _triple(self.trigger, 'ACT43 tuple')
        if self.trigger[2] <= 0:
            raise ValueError('ACT43 radius must be positive')
        if type(self.records) is not tuple or not self.records or len(set(self.records)) != len(self.records):
            raise ValueError('ACT43 records must be a nonempty unique immutable tuple')
        for offset in self.records:
            _integer(offset, 0, 2 ** 32 - 1, 'ACT43 offset')
        if type(self.extra_commands) is not tuple or not all(isinstance(command, MapCommand) for command in self.extra_commands):
            raise ValueError('Extra commands must be an immutable MapCommand tuple')
        offsets = tuple(command.offset for command in self.commands())
        if len(set(offsets)) != len(offsets):
            raise ValueError('Duplicate trigger command offset')

    @property
    def source(self) -> XYZ:
        return self.sprite.xyz

    @property
    def guard_vid(self) -> int:
        return self.sprite.vid if self.runtime_vid is None else self.runtime_vid

    def commands(self) -> tuple[MapCommand, ...]:
        return tuple(MapCommand(offset, (43, *self.trigger)) for offset in self.records) + self.extra_commands

    def legacy_dict(self) -> dict:
        """Fresh metadata view; mutating it cannot modify the registry."""
        source = tuple(int(value) if value == int(value) else value for value in self.source)
        return {'name': self.name, 'source': source, 'trigger': self.trigger, 'records': self.records}


@dataclass(frozen=True, slots=True)
class PortalPolicy:
    activation_group: str
    event_actor_policy: Literal['leader_pending', 'eligible_order']
    reusable: bool
    rearm_margin: int
    strict_radius: bool
    source_z_bounds: Bounds | None
    arrival_z_bounds: Bounds
    create_missing_peer_goal: bool
    consume_invalid_event: bool = False
    closed_by_quest: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        _name(self.activation_group, 'activation group')
        if self.event_actor_policy not in ('leader_pending', 'eligible_order'):
            raise ValueError('Unsupported portal event actor policy')
        for value in (self.reusable, self.strict_radius, self.create_missing_peer_goal, self.consume_invalid_event):
            if type(value) is not bool:
                raise ValueError('Portal policy flags must be booleans')
        _integer(self.rearm_margin, 0, 2 ** 31 - 1, 'rearm margin')
        if self.source_z_bounds is not None:
            _bounds(self.source_z_bounds, 'source Z bounds')
        _bounds(self.arrival_z_bounds, 'arrival Z bounds')
        if self.closed_by_quest is not None:
            if type(self.closed_by_quest) is not tuple or len(self.closed_by_quest) != 2:
                raise ValueError('Portal closing quest must be a source group/ID pair')
            for value in self.closed_by_quest:
                _integer(value, 1, 2 ** 31 - 1, 'portal closing quest')
        if not self.reusable and (self.rearm_margin or self.create_missing_peer_goal):
            raise ValueError('Once-per-hero portals cannot rearm or prepare a reverse goal')


@dataclass(frozen=True, slots=True)
class LogicalPortal:
    name: str
    map_key: str
    sprite: SpriteIdentity
    trigger: Triple
    trigger_offset: int
    goal: Triple
    goal_offset: int
    event_offset: int
    policy: PortalPolicy
    event_id: int = 13

    def __post_init__(self) -> None:
        _name(self.name, 'portal name')
        _name(self.map_key, 'map key')
        if not isinstance(self.sprite, SpriteIdentity) or not isinstance(self.policy, PortalPolicy):
            raise ValueError('Portal requires immutable sprite identity and policy')
        if type(self.event_id) is not int or self.event_id not in (11, 12, 13):
            raise ValueError('Unsupported native portal script event')
        _triple(self.trigger, 'portal trigger')
        _triple(self.goal, 'portal goal')
        if self.trigger[2] <= 0:
            raise ValueError('Portal radius must be positive')
        offsets = (self.trigger_offset, self.goal_offset, self.event_offset)
        for offset in offsets:
            _integer(offset, 0, 2 ** 32 - 1, 'portal command offset')
        if len(set(offsets)) != 3:
            raise ValueError('Duplicate portal command offset')
        if not self.policy.arrival_z_bounds[0] <= self.goal[2] <= self.policy.arrival_z_bounds[1]:
            raise ValueError('Portal goal Z is outside arrival bounds')

    @property
    def source(self) -> XYZ:
        return self.sprite.xyz

    def commands(self) -> tuple[MapCommand, ...]:
        return (MapCommand(self.trigger_offset, (43, *self.trigger)),
                MapCommand(self.goal_offset, (91, *self.goal)),
                MapCommand(self.event_offset, (136, self.event_id, 0, 0)))

    def legacy_dict(self) -> dict:
        return {'name': self.name, 'sprite_offset': self.sprite.offset,
                'saved_id': self.sprite.saved_id, 'sprite': (self.sprite.vid, *self.source),
                'trigger_offset': self.trigger_offset, 'trigger': self.trigger,
                'goal_offset': self.goal_offset, 'goal': self.goal, 'event_offset': self.event_offset}


@dataclass(frozen=True, slots=True)
class InteractionRegistry:
    maps: tuple[MapIdentity, ...]
    triggers: tuple[PartyTrigger, ...]
    portals: tuple[LogicalPortal, ...]

    def __post_init__(self) -> None:
        for values, kind in ((self.maps, MapIdentity), (self.triggers, PartyTrigger), (self.portals, LogicalPortal)):
            if type(values) is not tuple or not all(isinstance(value, kind) for value in values):
                raise ValueError(f'Registry expects immutable {kind.__name__} tuples')
        for attribute in ('key', 'path', 'sha256'):
            values = tuple(getattr(identity, attribute) for identity in self.maps)
            if len(set(values)) != len(values):
                raise ValueError('Duplicate map ' + attribute)
        map_keys = {identity.key for identity in self.maps}
        sprites, saved_ids, commands = {}, {}, {}
        for entries in (self.triggers, self.portals):
            names, geometries = set(), set()
            for entry in entries:
                if entry.map_key not in map_keys:
                    raise ValueError('Unknown map for ' + entry.name)
                name = (entry.map_key, entry.name)
                geometry = (entry.map_key, entry.sprite.offset, entry.trigger)
                if name in names or geometry in geometries:
                    raise ValueError('Duplicate interaction: ' + entry.name)
                names.add(name)
                geometries.add(geometry)
                sprite_key = (entry.map_key, entry.sprite.offset)
                if sprite_key in sprites and sprites[sprite_key] != entry.sprite:
                    raise ValueError('Conflicting sprite identity: ' + entry.name)
                sprites[sprite_key] = entry.sprite
                saved_key = (entry.map_key, entry.sprite.saved_id)
                if saved_key in saved_ids and saved_ids[saved_key] != entry.sprite.offset:
                    raise ValueError('Duplicate saved sprite ID: ' + entry.name)
                saved_ids[saved_key] = entry.sprite.offset
                for command in entry.commands():
                    key = (entry.map_key, command.offset)
                    expected = (entry.sprite, command)
                    if key in commands and commands[key] != expected:
                        raise ValueError('Conflicting command ownership or value: ' + entry.name)
                    commands[key] = expected
        groups = {}
        for portal in self.portals:
            groups.setdefault(portal.policy.activation_group, []).append(portal)
        for group in groups.values():
            first = group[0]
            # Only the two implemented lifecycles are supported. Arrival Z
            # differs between the two bunker directions; the other rules agree.
            for portal in group[1:]:
                for field in ('event_actor_policy', 'reusable', 'rearm_margin', 'strict_radius', 'source_z_bounds', 'create_missing_peer_goal', 'consume_invalid_event', 'closed_by_quest'):
                    if getattr(portal.policy, field) != getattr(first.policy, field):
                        raise ValueError('Inconsistent activation group policy')
                if portal.map_key != first.map_key:
                    raise ValueError('Activation group cannot span maps')
            if first.policy.reusable:
                pair = len(group) == 2 and first.policy.create_missing_peer_goal and first.policy.event_actor_policy == 'leader_pending'
                event_route = len(group) == 1 and not first.policy.create_missing_peer_goal and first.policy.event_actor_policy == 'eligible_order'
                if not (pair or event_route):
                    raise ValueError('Reusable portal group must be a leader-activated pair')
            elif len(group) != 1 or first.policy.event_actor_policy != 'eligible_order':
                raise ValueError('Once-per-hero portal group must be a single eligible-order entrance')

    def map_identity(self, map_key: str) -> MapIdentity:
        for identity in self.maps:
            if identity.key == map_key:
                return identity
        raise ValueError('Unknown campaign map: ' + str(map_key))

    def triggers_for(self, map_key: str) -> tuple[PartyTrigger, ...]:
        self.map_identity(map_key)
        return tuple(trigger for trigger in self.triggers if trigger.map_key == map_key)

    def portals_for(self, map_key: str) -> tuple[LogicalPortal, ...]:
        self.map_identity(map_key)
        return tuple(portal for portal in self.portals if portal.map_key == map_key)

    def manifest(self) -> dict:
        """Detached JSON-serializable evidence in stable declaration order."""
        return {'schema': 2, **asdict(self)}

    def validate_original_map(self, image: bytes, map_key: str) -> None:
        """Reject unsupported maps before any consumer emits patch bytes.

        Sprite comparisons use packed bytes, preserving signed zero and the
        exact float32 representation. Specific record guards remain explicit
        even though the full original map hash also pins these bytes.
        """
        if not isinstance(image, bytes):
            raise TypeError('Expected immutable original map bytes')
        identity = self.map_identity(map_key)
        if hashlib.sha256(image).hexdigest() != identity.sha256:
            raise ValueError('Unsupported original map: ' + identity.path)
        for entry in self.triggers_for(map_key) + self.portals_for(map_key):
            expected = entry.sprite.packed()
            offset = entry.sprite.offset
            if image[offset:offset + len(expected)] != expected:
                raise ValueError(f'Original sprite differs: {entry.name} at {offset:#x}')
            for command in entry.commands():
                expected = command.packed()
                if image[command.offset:command.offset + len(expected)] != expected:
                    raise ValueError(f'Original command differs: {entry.name} at {command.offset:#x}')
