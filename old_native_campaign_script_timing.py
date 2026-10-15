"""Pinned data overlays for campaign markers with local random story timers.

Only explicitly reviewed map commands are admitted. Ordinary NPC timers,
decorative effects and important generators keep their original behavior.
The executable, action order, quest predicates and script-variable writes
are unchanged. Each replacement keeps the midpoint of the original delay.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct

from old_native_interaction_schema import MapCommand, MapIdentity, SpriteIdentity


FEATURE = 'old-campaign-script-timing-v1'


@dataclass(frozen=True)
class MarkerTiming:
    key: str
    map: MapIdentity
    sprite: SpriteIdentity
    detail_offset: int
    detail_header: tuple[int, ...]
    stack_sha256: str
    commands: tuple[MapCommand, ...]  # Complete stack0, native stored order.
    pause_offset: int


CATALOG = (
    MarkerTiming(
        'level02_trap_phase',
        MapIdentity('level02', 'Maps/Level_02.map',
                    'e52d86951d508743ed625ef0b4910e7ba2c4ce633e3e94029c179a466186ff79'),
        SpriteIdentity(0x92150, 0x1870C588, 922, (3591, 3500, 1)),
        0xE3F31, (104, 0x1870C588, 0, 4, 4),
        'd15f09bae0b38a011beadc96f56ead78f77dc188dc85adbe8ac96a7438dccbe0',
        (
            MapCommand(0xE3F45, (131, 10, 3, 0)),
            MapCommand(0xE3F55, (40, 5000, 2000, 0)),
            MapCommand(0xE3F65, (43, 3231, 3422, 620)),
            MapCommand(0xE3F75, (77, 1, 22, 0)),
        ),
        0xE3F55,
    ),
)


def patch_map(data, path):
    """Return a same-size overlay; reject unknown, modified or patched input."""
    if not isinstance(data, bytes):
        raise TypeError('Expected immutable original map bytes')
    rules = tuple(rule for rule in CATALOG if rule.map.path == path)
    if not rules:
        raise ValueError('No admitted campaign timing map: ' + str(path))
    source_sha = hashlib.sha256(data).hexdigest()
    output = bytearray(data)
    changes = []
    touched = set()
    for rule in rules:
        if source_sha != rule.map.sha256:
            raise ValueError('Unsupported campaign timing map source: ' + path)
        identity = rule.sprite.packed()
        if data[rule.sprite.offset:rule.sprite.offset + len(identity)] != identity:
            raise ValueError('Campaign timing sprite identity changed')
        header = struct.pack('<' + 'I' * len(rule.detail_header), *rule.detail_header)
        if data[rule.detail_offset:rule.detail_offset + len(header)] != header:
            raise ValueError('Campaign timing stack ownership/header changed')
        stack = b''.join(command.packed() for command in rule.commands)
        begin = rule.detail_offset + len(header)
        if (hashlib.sha256(stack).hexdigest() != rule.stack_sha256
                or data[begin:begin + len(stack)] != stack
                or any(command.offset != begin + index * 16
                       for index, command in enumerate(rule.commands))):
            raise ValueError('Campaign timing complete source stack changed')
        pause = next((command for command in rule.commands
                      if command.offset == rule.pause_offset), None)
        if (pause is None or pause.values[0] != 40 or pause.values[1] < 0
                or pause.values[2] <= 0 or pause.values[3] != 0
                or rule.pause_offset in touched):
            raise ValueError('Unsupported campaign timing pause rule')
        # ACT_PAUSE(base, spread, 0) uses an inclusive [0, spread] local RNG
        # for this unmarked VID922. Its countdown uses simulation time.
        replacement = (40, pause.values[1] + pause.values[2] // 2, 0, 0)
        output[pause.offset:pause.offset + 16] = struct.pack('<4i', *replacement)
        touched.add(pause.offset)
        changes.append(dict(key=rule.key, offset=pause.offset,
                            before=list(pause.values), after=list(replacement),
                            sprite_offset=rule.sprite.offset,
                            source_stack_sha256=rule.stack_sha256))
    output = bytes(output)
    if len(output) != len(data):
        raise ValueError('Campaign timing overlay changed map size')
    return output, dict(source_sha256=source_sha,
                       output_sha256=hashlib.sha256(output).hexdigest(),
                       source_size=len(data), output_size=len(output), changes=changes)


def prepare(root):
    files, maps = {}, {}
    for path in dict.fromkeys(rule.map.path for rule in CATALOG):
        files[path], maps[path] = patch_map((Path(root) / path).read_bytes(), path)
    return files, dict(feature=FEATURE, maps=maps,
                       policy='Pinned story marker random pauses use original midpoint',
                       npc_and_decorative_timers_changed=False,
                       executable_changed=False, runtime_tested=False)
