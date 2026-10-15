"""Audit the native ACT43 signature against actual original SPR/SPRD records.

Exact-source policies have no map/VID comparison; movable-source policies use
map identity, VID and the complete ACT43 tuple. Every matching original action
must be explicitly listed. This scans every stack in each registered map; it
does not prove the absence of later script-created copies of those stacks.
"""
import hashlib
import math
import struct

from tools.map_format import chunks, records, u32


def scan_act43(image: bytes) -> tuple[int, tuple[dict, ...]]:
    """Read real sprite ownership and ACT43 record offsets; never byte-search."""
    if not isinstance(image, bytes):
        raise TypeError('Expected immutable original map bytes')
    found = {}
    for tag, offset, payload in chunks(image):
        if tag in (b'SPR ', b'SPRD'):
            if tag in found:
                raise ValueError('Duplicate SPR/SPRD chunk')
            found[tag] = (offset, payload)
    if set(found) != {b'SPR ', b'SPRD'}:
        raise ValueError('Map has no SPR/SPRD pair')
    offset, payload = found[b'SPR ']
    blocks = list(records(payload, offset + 8))
    if len(blocks) != 1:
        raise ValueError('Expected one packed sprite-record block')
    start, block = blocks[0]
    if len(block) < 4 or block[-4:] != b'\xff' * 4 or (len(block) - 4) % 48:
        raise ValueError('Unsupported packed sprite layout')
    sprites = {}
    for at in range(0, len(block) - 4, 48):
        saved_id, vid, x, y, z = struct.unpack_from('<IIfff', block, at)
        if saved_id in sprites or not all(math.isfinite(value) for value in (x, y, z)):
            raise ValueError('Duplicate saved sprite ID or nonfinite coordinate')
        sprites[saved_id] = {'saved_id': saved_id, 'vid': vid,
            'sprite_offset': start + at, 'source': (x, y, z),
            'source_bytes': block[at + 8:at + 20]}
    offset, payload = found[b'SPRD']
    detailed, actions = set(), []
    for start, record in records(payload, offset + 8):
        if record == b'\xff' * 4:
            continue
        saved_id = u32(record, 0)
        if saved_id not in sprites or saved_id in detailed:
            raise ValueError('Unmatched or duplicate sprite detail record')
        detailed.add(saved_id)
        count = u32(record, 8)
        if count > 64:
            raise ValueError('Unreasonable action-stack count')
        cursor = 12
        for stack in range(count):
            command_count = u32(record, cursor)
            cursor += 4
            if command_count > 65536 or cursor + 16 * command_count > len(record):
                raise ValueError('Action stack extends beyond detail record')
            # Native stacks execute in reverse storage order. ACT62 can change
            # a moving NPC's VID before its later proximity conditions.
            runtime_vid = sprites[saved_id]['vid']
            for index in reversed(range(command_count)):
                command_at = cursor + 16 * index
                opcode, *args = struct.unpack_from('<4i', record, command_at)
                if opcode == 62:
                    runtime_vid = args[0]
                if opcode == 43:
                    actions.append({**sprites[saved_id], 'record_offset': start + command_at,
                        'runtime_vid': runtime_vid,
                        'stack': stack, 'trigger': tuple(args)})
            cursor += 16 * command_count
        property_count = u32(record, cursor)
        cursor += 4
        if property_count > 65536 or cursor + 4 * property_count > len(record):
            raise ValueError('Property list extends beyond detail record')
    if detailed != sprites.keys():
        raise ValueError('Some packed sprites have no detail record')
    return len(sprites), tuple(sorted(actions, key=lambda action: action['record_offset']))


def audit_trigger_signatures(registry, map_images) -> dict:
    """Reject any matching action outside the registry's exact record allowlist."""
    expected_keys = {identity.key for identity in registry.maps}
    if set(map_images) != expected_keys:
        raise ValueError('Trigger audit requires exactly the registered map keys')
    expected, signatures, moving_signatures = {}, set(), set()
    for entry in registry.triggers:
        signature = entry.sprite.packed()[8:20] + struct.pack('<3i', *entry.trigger)
        if entry.source_guard == 'exact_xyz':
            signatures.add(signature)
        else:
            moving_signatures.add((entry.map_key, entry.guard_vid, entry.trigger))
        for offset in entry.records:
            key = (entry.map_key, entry.sprite.offset, entry.sprite.saved_id, offset)
            if key in expected:
                raise ValueError('Duplicate registered ACT43 record ownership')
            expected[key] = (entry.name, signature, entry.sprite.vid, entry.source_guard, entry.guard_vid)
    seen, matched, maps = set(), [], {}
    for identity in registry.maps:
        image = map_images[identity.key]
        registry.validate_original_map(image, identity.key)
        sprite_count, actions = scan_act43(image)
        map_matches = 0
        for action in actions:
            signature = action['source_bytes'] + struct.pack('<3i', *action['trigger'])
            key = (identity.key, action['sprite_offset'], action['saved_id'], action['record_offset'])
            moving = (identity.key, action['runtime_vid'], action['trigger']) in moving_signatures
            if signature in signatures or moving:
                if (key not in expected or expected[key][1] != signature
                        or expected[key][2] != action['vid']
                        or (expected[key][3] == 'map_vid_act43'
                            and expected[key][4] != action['runtime_vid'])):
                    raise ValueError('Unregistered native ACT43 signature collision in '
                        f'{identity.path} at SPR {action["sprite_offset"]:#x}, ACT43 {action["record_offset"]:#x}')
                seen.add(key)
                map_matches += 1
                matched.append({'map_key': identity.key, 'trigger': expected[key][0],
                    'saved_id': hex(action['saved_id']), 'vid': action['vid'],
                    'runtime_vid': action['runtime_vid'],
                    'sprite_offset': hex(action['sprite_offset']),
                    'record_offset': hex(action['record_offset']), 'stack': action['stack'],
                    'source_guard': expected[key][3]})
        maps[identity.key] = {'path': identity.path,
            'sha256': hashlib.sha256(image).hexdigest(), 'sprite_count': sprite_count,
            'act43_records': len(actions), 'matching_records': map_matches}
    if seen != set(expected):
        missing = sorted(set(expected) - seen)
        raise ValueError('Registered ACT43 record is not attached to its original sprite: ' + repr(missing))
    return {'signature': 'Per-source exact XYZ bits or map+VID, always full signed ACT43 x/y/r tuple',
        'native_map_guard': bool(moving_signatures), 'native_vid_guard': bool(moving_signatures),
        'native_guard_scope': 'Map and VID apply only to map_vid_act43 sources',
        'runtime_source_movements_audited': False,
        'runtime_stack_creation_audited': False,
        'scope': 'All ACT43 stacks in exactly the supplied registered original maps',
        'maps': maps, 'registered_triggers': len(registry.triggers),
        'distinct_signatures': len(signatures) + len(moving_signatures),
        'moving_signatures': [{'map_key': key, 'source_vid': vid, 'trigger': trigger}
                              for key, vid, trigger in sorted(moving_signatures)],
        'registered_records': len(expected),
        'matching_records': len(matched), 'unregistered_matches': 0, 'matches': matched}
