"""Admit either campaign hero at three pinned Level_01 story triggers.

The original ACT43 handler still performs its distance test and executes the
original map stack. Only its two hero lookup calls are wrapped. For the exact
planting, lift-inspection and lift-unlock sprites, prefer army0 when it is in
range, otherwise army3 when it is in range. All other lookups stay army0.

The optional admin extension admits either hero at three additional exact
Level02 door/entry/arrival records. Historical Level01 bytes stay reproducible.
Pure bytes transformation, composed after party-items and before diagnostics.
"""
from __future__ import annotations

import hashlib
import json
import struct
from types import MappingProxyType

from old_native_campaign_patch import BASELINE_SHA256, ISOLATION_PATCHES, STORY_PATCHES
from old_native_spawn_rng_patch import SPAWN_PATCHES
from old_native_crush_sync_patch import normalize_optional as normalize_crush
from old_native_party_items_patch import normalize_optional as normalize_items
from old_native_interaction_registry import LEVEL01, LEVEL02, REGISTRY, validate_original_map


IMAGE_BASE = 0x400000
FEATURE = 'old-campaign-party-triggers-v1'
MAP_SHA256 = LEVEL01.sha256
CAVE_VA = 0x59A900
CAVE_SIZE = 0x500
TEXT_VIRTUAL_SIZE_FIELD = 0x230
ITEMS_TEXT_VIRTUAL_SIZE = 0x199900
TRIGGERS_TEXT_VIRTUAL_SIZE = 0x199E00
FLAGMAN_VA = 0x420990
HOOK_VAS = (0x44D29E, 0x44D2C8)

# Freeze profile membership and order, while geometry stays in the registry.
# A future event on either map must not silently change historical v1/v2 bytes.
LEVEL01_PROFILE = (
    ('level01', 'dynamite_plant'),
    ('level01', 'elevator_inspect'),
    ('level01', 'elevator_unlock'),
)
ADMIN_PROFILE = (
    ('level02', 'admin_door'),
    ('level02', 'admin_entry'),
    ('level02', 'admin_arrival'),
)


def _legacy_profile(registry, members):
    entries = {(entry.map_key, entry.name): entry for entry in registry.triggers}
    result = []
    for key in members:
        if key not in entries:
            raise ValueError('Historical trigger profile missing: ' + '/'.join(key))
        result.append(MappingProxyType(entries[key].legacy_dict()))
    return tuple(result)


# Read-only mapping views retain the existing emitter/test interface.
TRIGGERS = _legacy_profile(REGISTRY, LEVEL01_PROFILE)

# Optional Level02 extension. Keep the historical Level01 bytes reproducible.
ADMIN_FEATURE = 'old-campaign-party-triggers-admin-v2'
REGISTERED_FEATURE = 'old-campaign-party-triggers-registered-v3'
SECTION_NAME = b'.oparty\0'
ADMIN_MAP_SHA256 = LEVEL02.sha256
ADMIN_TRIGGERS = _legacy_profile(REGISTRY, ADMIN_PROFILE)

# Preserve the exact registered profile used by the first lower-floor proofs.
# Policy changes or future catalog additions must not redefine trusted old EXEs.
REGISTERED_V1_PROFILE = (LEVEL01_PROFILE + ADMIN_PROFILE
    + tuple(('level02', f'interior_stair_monster_{i:02}') for i in range(1, 4))
    + (('level02', 'interior_corridor_generator_01'),)
    + tuple(('level02', f'interior_lower_monster_{i:02}') for i in range(1, 28))
    + tuple(('level02', f'personal_key_door_{i:02}') for i in range(1, 5))
    + (('level02', 'personal_key_room_roof'),))
_V1_LOOKUP = {(entry.map_key, entry.name): entry for entry in REGISTRY.triggers}
REGISTERED_V1_TRIGGERS = tuple(_V1_LOOKUP[key] for key in REGISTERED_V1_PROFILE)


def _relative(opcode: int, source: int, destination: int) -> bytes:
    return bytes([opcode]) + struct.pack('<i', destination - source - 5)


class _Code:
    def __init__(self):
        self.code = bytearray()
        self.labels = {}
        self.fixups = []

    def raw(self, value):
        self.code.extend(bytes.fromhex(value) if isinstance(value, str) else value)

    def label(self, name):
        self.labels[name] = len(self.code)

    def branch(self, opcode, label):
        self.raw(opcode)
        self.fixups.append((len(self.code), label))
        self.raw(b'\0' * 4)

    def finish(self):
        for at, label in self.fixups:
            struct.pack_into('<i', self.code, at, self.labels[label] - at - 4)
        return bytes(self.code)


def _stub(entries=TRIGGERS) -> bytes:
    c = _Code()
    # CALL's return and one pushed army argument put the original ACT43
    # frame 8 bytes above entry ESP. These five pushes add another 20 bytes.
    # Thus its pinned x/y/r locals +44/+48/+4C appear here at +60/+64/+68.
    # EBP is the live source sprite; ECX is the game's unchanged this pointer.
    c.raw('9c535256578bf1')  # pushfd; push ebx/edx/esi/edi; mov esi,ecx
    for index, entry in enumerate(entries):
        c.label('match_' + str(index))
        fail = 'match_' + str(index + 1) if index + 1 < len(entries) else 'fallback'
        for offset, value in zip((0x60, 0x64, 0x68), entry['trigger']):
            c.raw(bytes((0x81, 0x7C, 0x24, offset)) + struct.pack('<i', value))
            c.branch('0f85', fail)
        for offset, value in zip((4, 8, 12), entry['source']):
            c.raw(bytes((0x81, 0x7D, offset)) + struct.pack('<f', value))
            c.branch('0f85', fail)
        c.branch('e9', 'choose')
    _emit_selection(c)
    return c.finish()


def _emit_selection(c, base_va=CAVE_VA):
    """Unchanged native actor selection and x87 distance ABI for both layouts."""
    c.label('choose')
    c.raw('8b7c24608b5c2464')  # edi=x; ebx=y
    for army, player_offset in ((0, 0x9C0), (3, 0x9CC)):
        c.raw('8b8e' + struct.pack('<I', player_offset).hex())
        c.raw('85c9')
        c.branch('0f84', 'next_' + str(army))
        c.raw('8b810001000085c0')  # eax=player.hero; test eax,eax
        c.branch('0f84', 'next_' + str(army))
        c.raw('8b542468')  # edx=radius
        c.branch('e8', 'near')
        c.raw('85d2')
        c.branch('0f85', 'selected')
        c.label('next_' + str(army))

    c.label('fallback')
    c.raw('8bce5f5e5a5b9d')  # restore original game ECX and preserved state
    c.raw(_relative(0xE9, base_va + len(c.code), FLAGMAN_VA))
    c.label('selected')
    # Return the selected live sprite in EAX and player in ECX, exactly the
    # native getter's output contract. No global state or input is changed.
    c.raw('5f5e5a5b9dc20400')

    c.label('near')
    # EAX=hero, ECX=player, EDI=x, EBX=y, EDX=radius. Preserve EAX and ECX;
    # return EDX=boolean. The exact original x87 sequence uses a float scratch
    # for abs(dx), float32(0.398) and strict '< radius'. All x87 pushes pop.
    # Stack after prologue: +0 scratch,+4 constant,+8 x,+C y,+10 r,+14 hero.
    c.raw('5052535768')
    c.raw(struct.pack('<f', 0.398))
    c.raw('83ec04')
    c.raw('db44240cd86008db442408d86004d9e1d91c24d9e1d90424d8d9dfe0f6c441')
    c.branch('0f85', 'near_y_max')
    c.raw('d84c2404d80424')
    c.branch('e9', 'near_compare')
    c.label('near_y_max')
    c.raw('d90424d84c2404dec1')
    c.label('near_compare')
    c.raw('db442410d9c9ded9dfe0f6c4010f95c20fb6d283c41458c3')


STUB = _stub()
ADMIN_STUB = _stub(TRIGGERS + ADMIN_TRIGGERS)
if max(len(STUB), len(ADMIN_STUB)) > CAVE_SIZE:
    raise AssertionError('Party trigger wrapper exceeds reserved cave')
TRIGGER_PATCHES = (
    (IMAGE_BASE + TEXT_VIRTUAL_SIZE_FIELD,
     struct.pack('<I', ITEMS_TEXT_VIRTUAL_SIZE),
     struct.pack('<I', TRIGGERS_TEXT_VIRTUAL_SIZE)),
    (CAVE_VA, b'\0' * CAVE_SIZE, STUB.ljust(CAVE_SIZE, b'\0')),
    *tuple((va, _relative(0xE8, va, FLAGMAN_VA), _relative(0xE8, va, CAVE_VA))
           for va in HOOK_VAS),
)
ADMIN_PATCHES = tuple((va, before, ADMIN_STUB.ljust(CAVE_SIZE, b'\0') if va == CAVE_VA else after)
                      for va, before, after in TRIGGER_PATCHES)
CONTEXT_GUARDS = (
    (0x44D271, bytes.fromhex('8b308b78048b58088b400c83fe2b897c2444895c24488944244c')),
    (0x44D2CD, bytes.fromhex('d9442424d86008d9442420d86004d9e1d95c2410')),
    (0x59B3AC, struct.pack('<f', 0.398)),
    (0x420990, bytes.fromhex('8b44240483e0078b8c81c00900008b8100010000c20400')),
    (0x4BD000, bytes.fromhex('8b40448bce8b4004')),  # GetVid83 descriptor+44 -> VID+4
    (0x427D22, bytes.fromhex('8b714c')),  # GetMapName126's physical map string
)


def normalize_optional(image: bytes) -> tuple[bytes, bool]:
    """Remove a complete trigger group before normalizing party-items."""
    if not isinstance(image, bytes):
        raise TypeError('Expected executable bytes')
    extended = _normalize_extended(image)
    if extended is not None:
        return extended, True
    states = []
    for va, before, after in TRIGGER_PATCHES[1:]:
        current = image[va - IMAGE_BASE:va - IMAGE_BASE + len(before)]
        if current == before:
            states.append(False)
        elif current == after or (va == CAVE_VA and current == ADMIN_STUB.ljust(CAVE_SIZE, b'\0')):
            states.append(True)
        elif va == CAVE_VA and current == REGISTERED_V1_STUB.ljust(CAVE_SIZE, b'\0'):
            states.append(True)
        elif va == CAVE_VA and current == _registered_stub().ljust(CAVE_SIZE, b'\0'):
            # Only code regenerated from this module's trusted registry is
            # accepted. Never normalize caller-supplied descriptors or hashes.
            states.append(True)
        else:
            raise ValueError(f'Unknown party trigger bytes at {va:#x}')
    if not any(states):
        return image, False
    if not all(states):
        raise ValueError('Incomplete party trigger group')
    va, _, after = TRIGGER_PATCHES[0]
    if image[va - IMAGE_BASE:va - IMAGE_BASE + len(after)] != after:
        raise ValueError('Party trigger section header does not match group')
    output = bytearray(image)
    for va, before, _ in TRIGGER_PATCHES:
        output[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] = before
    return bytes(output), True


def _apply_executable(image: bytes, patches) -> bytes:
    """Shared guarded application; profiles only choose exact replacement bytes."""
    if not isinstance(image, bytes):
        raise TypeError('Expected executable bytes')
    _, already = normalize_optional(image)
    if already:
        raise ValueError('Party trigger patch is already applied')
    for va, expected in CONTEXT_GUARDS:
        if image[va - IMAGE_BASE:va - IMAGE_BASE + len(expected)] != expected:
            raise ValueError(f'Unsupported ACT43 context at {va:#x}')
    normalized, has_items = normalize_items(image)
    if not has_items:
        raise ValueError('Complete party-items patch is required')
    normalized, has_crush = normalize_crush(normalized)
    if not has_crush:
        raise ValueError('Complete crush patch is required')
    normalized = bytearray(normalized)
    for va, before, after in SPAWN_PATCHES:
        at = va - IMAGE_BASE
        if normalized[at:at + len(after)] != after:
            raise ValueError(f'Complete spawn patch is required at {va:#x}')
        normalized[at:at + len(before)] = before
    for va, before, after in ISOLATION_PATCHES + STORY_PATCHES:
        at = va - IMAGE_BASE
        if normalized[at:at + len(before)] not in (before, after):
            raise ValueError(f'Unknown executable modification at {va:#x}')
        # Both ACT43 loads must be canonical: the fallback passes their army
        # argument to the unchanged native getter, so do not accept local -1.
        if va in (0x44D297, 0x44D2BD) and normalized[at:at + len(after)] != after:
            raise ValueError('Canonical ACT43 story patch is required')
        normalized[at:at + len(before)] = before
    if hashlib.sha256(normalized).hexdigest() != BASELINE_SHA256:
        raise ValueError('Unsupported party trigger executable: normalized hash mismatch')
    output = bytearray(image)
    for va, before, after in patches:
        at = va - IMAGE_BASE
        if output[at:at + len(before)] != before or len(before) != len(after):
            raise ValueError(f'Party trigger source bytes mismatch at {va:#x}')
        output[at:at + len(before)] = after
    return bytes(output)


def patch(image: bytes, map_image: bytes, admin_map: bytes | None = None) -> tuple[bytes, dict]:
    """Patch pinned OLD campaign bytes after the complete party-items group."""
    if not isinstance(image, bytes) or not isinstance(map_image, bytes):
        raise TypeError('Expected executable and original Level_01 map bytes')
    if hashlib.sha256(map_image).hexdigest() != MAP_SHA256:
        raise ValueError('Unsupported Level_01 map for party triggers')
    validate_original_map(map_image, 'level01')
    for entry in TRIGGERS:
        for offset in entry['records']:
            if struct.unpack_from('<4i', map_image, offset) != (43, *entry['trigger']):
                raise ValueError(f'Unexpected original ACT43 record at {offset:#x}')
    if admin_map is not None:
        if hashlib.sha256(admin_map).hexdigest() != ADMIN_MAP_SHA256:
            raise ValueError('Unsupported Level_02 map for party triggers')
        validate_original_map(admin_map, 'level02')
        for entry in ADMIN_TRIGGERS:
            for offset in entry['records']:
                if struct.unpack_from('<4i', admin_map, offset) != (43, *entry['trigger']):
                    raise ValueError(f'Unexpected admin ACT43 record at {offset:#x}')
    patches = TRIGGER_PATCHES if admin_map is None else ADMIN_PATCHES
    result = _apply_executable(image, patches)
    return result, {
        'feature': FEATURE if admin_map is None else ADMIN_FEATURE,
        'baseline_sha256': BASELINE_SHA256,
        'input_sha256': hashlib.sha256(image).hexdigest(),
        'output_sha256': hashlib.sha256(result).hexdigest(),
        'source_map_sha256': MAP_SHA256,
        'scope': 'Exact original Level_01 plant/lift records' + (' and Level_02 admin door/entry/arrival' if admin_map is not None else ''),
        'admin_map_sha256': ADMIN_MAP_SHA256 if admin_map is not None else None,
        'actor_policy': 'Army0 if within native radius, else army3 if within native radius, else original army0',
        'distance': 'Original x87 max(abs(dx),abs(dy)) + float32(0.398)*min; strict < radius',
        'source_sprite_guard': 'Exact original float32 XYZ plus complete ACT43 x/y/r tuple',
        'health_policy': 'Original ACT43 has no HP filter; preserved',
        'preserved': ['original quest waits', 'original stack commands and order',
                      'canonical dialogue and reward owner', 'other ACT43 triggers',
                      'original radius', 'native original final proximity test'],
        'stub_va': hex(CAVE_VA), 'stub_size': len(STUB if admin_map is None else ADMIN_STUB), 'cave_size': CAVE_SIZE,
        'triggers': tuple(dict(entry) for entry in
                          (TRIGGERS if admin_map is None else TRIGGERS + ADMIN_TRIGGERS)),
        'patches': [{'va': hex(va), 'before': before.hex(), 'after': after.hex()}
                    for va, before, after in patches],
    }


def _registered_entries():
    # Preserve raw float32 source values, including signed zero. Legacy JSON
    # adapters intentionally use integer-valued coordinates for old profiles.
    return tuple(MappingProxyType({**entry.legacy_dict(), 'source': entry.source})
                 for entry in REGISTRY.triggers)


def _registered_stub():
    # Preserve the v2 bytes already installed in historical diagnostic builds.
    return _registered_program(REGISTERED_V1_TRIGGERS)[0]


def _registered_program_v1(entries=REGISTERED_V1_TRIGGERS, *, base_va=CAVE_VA, capacity=CAVE_SIZE):
    """Historical exact-XYZ emitter. Its 42-source output is permanently pinned."""
    if not entries:
        raise ValueError('Registered native trigger profile cannot be empty')
    # Native behavior is the same for every admitted signature, so sources
    # with an equal ACT43 tuple can share one test. First declaration order is
    # retained for groups and unique sources; exact float32 bits are preserved.
    groups = {}
    for entry in entries:
        sources = groups.setdefault(entry.trigger, {})
        sources.setdefault(entry.sprite.packed()[8:20], entry.source)
    c = _Code()
    c.raw('9c535256578bf1')  # same preserved registers and game ECX as legacy
    c.branch('e8', 'table_origin')
    c.label('table_origin')
    c.raw('5f81c7')  # pop edi; add edi, table-relative-to-return-address
    table_delta = len(c.code)
    c.raw(b'\0' * 4)
    c.raw('8b0f83c704')  # ecx=group_count; edi=first group
    c.label('group')
    c.raw('85c9')
    c.branch('0f84', 'fallback')
    c.raw('8b570c8bdf83c310')  # edx=source_count; ebx=first source
    for local, field in ((0x60, 0), (0x64, 4), (0x68, 8)):
        c.raw(bytes((0x8B, 0x44, 0x24, local)))  # eax=original ACT43 argument
        c.raw('3b07' if field == 0 else bytes((0x3B, 0x47, field)))
        c.branch('0f85', 'next_group')
    c.label('source')
    for source, field in ((4, 0), (8, 4), (12, 8)):
        c.raw(bytes((0x8B, 0x45, source)))  # eax=source sprite coordinate bits
        c.raw('3b03' if field == 0 else bytes((0x3B, 0x43, field)))
        c.branch('0f85', 'next_source')
    c.branch('e9', 'choose')
    c.label('next_source')
    c.raw('83c30c83ea01')  # next source; --source_count
    c.branch('0f85', 'source')
    # Each ACT43 tuple occurs in only one group.
    c.branch('e9', 'fallback')
    c.label('next_group')
    c.raw('8bc203d203d003d203d2')  # edx=source_count*12, using volatile eax
    c.raw('8bfb03fa83e901')  # edi=first source+bytes; --group_count
    c.branch('e9', 'group')
    _emit_selection(c, base_va)
    c.raw(b'\0' * (-len(c.code) % 4))
    code_size = len(c.code)
    struct.pack_into('<i', c.code, table_delta, code_size - c.labels['table_origin'])
    c.raw(struct.pack('<I', len(groups)))
    for trigger, sources in groups.items():
        c.raw(struct.pack('<3iI', *trigger, len(sources)))
        for source in sources:
            c.raw(source)
    stub = c.finish()
    if len(stub) > capacity:
        raise ValueError(f'Registered ACT43 wrapper needs {len(stub)} bytes; capacity is {capacity}')
    return stub, {'layout': 'grouped-act43-tuples-v1', 'code_bytes': code_size,
        'table_bytes': len(stub) - code_size,
        'relative_table_address': True,
        'groups': tuple({'trigger': trigger, 'source_count': len(sources)}
                        for trigger, sources in groups.items()),
        'distinct_source_signatures': sum(map(len, groups.values()))}


REGISTERED_V1_STUB, REGISTERED_V1_TABLE = _registered_program_v1()
if hashlib.sha256(REGISTERED_V1_STUB).hexdigest() != '4381901f20e4cbe306f9a9bf0d153f0dead9b8a9a78342121e8aa6befe4d361e':
    raise AssertionError('Historical registered-v1 source geometry or emitter changed')


def _registered_program(entries=None, *, base_va=CAVE_VA, capacity=CAVE_SIZE):
    """Emit exact sources and explicitly admitted movable map/VID cohorts.

    A positive group count precedes exact XYZ triples. Count zero selects an
    eight-byte payload: VID and the physical map identity. Ordinary profiles
    retain the historical two ASCII digits. Profiles with Reloaded submaps
    use the four bytes at path+11 ("07.m", "07_2", "07_3") and validate the
    complete appropriate suffix, keeping all three physical maps distinct.
    All source identities and command bytes remain pinned at build time.
    """
    entries = REGISTRY.triggers if entries is None else entries
    if not any(entry.source_guard == 'map_vid_act43' for entry in entries):
        return _registered_program_v1(entries, base_va=base_va, capacity=capacity)
    submaps = any(entry.source_guard == 'map_vid_act43' and
                  REGISTRY.map_identity(entry.map_key).path in
                  ('Maps/Level_07_2.map', 'Maps/Level_07_3.map') for entry in entries)
    groups = {}
    for entry in entries:
        if entry.source_guard == 'exact_xyz':
            key = (entry.source_guard, entry.trigger)
        else:
            key = (entry.source_guard, entry.trigger, entry.map_key, entry.guard_vid)
        sources = groups.setdefault(key, {})
        sources.setdefault(entry.sprite.packed()[8:20], entry.source)
    c = _Code()
    c.raw('9c535256578bf1')
    c.branch('e8', 'table_origin')
    c.label('table_origin')
    c.raw('5f81c7')
    table_delta = len(c.code)
    c.raw(b'\0' * 4)
    c.raw('8b0f83c704')
    c.label('group')
    c.raw('85c9')
    c.branch('0f84', 'fallback')
    c.raw('8b570c8bdf83c310')  # edx=count; ebx=payload
    for local, field in ((0x60, 0), (0x64, 4), (0x68, 8)):
        c.raw(bytes((0x8B, 0x44, 0x24, local)))
        c.raw('3b07' if field == 0 else bytes((0x3B, 0x47, field)))
        c.branch('0f85', 'next_group')
    c.raw('85d2')
    c.branch('0f84', 'moving_source')
    c.label('source')
    for source, field in ((4, 0), (8, 4), (12, 8)):
        c.raw(bytes((0x8B, 0x45, source)))
        c.raw('3b03' if field == 0 else bytes((0x3B, 0x43, field)))
        c.branch('0f85', 'next_source')
    c.branch('e9', 'choose')
    c.label('next_source')
    c.raw('83c30c83ea01')
    c.branch('0f85', 'source')
    # Equal tuples may have distinct policies, maps or VIDs. Keep searching.
    c.branch('e9', 'next_group')

    c.label('moving_source')
    # Exact native GetVid83 getter: actor+44 -> descriptor, descriptor+4 -> VID.
    c.raw('8b454485c0')
    c.branch('0f84', 'next_group')
    c.raw('8b40043b03')
    c.branch('0f85', 'next_group')
    # GetMapName126 reads game+4C but allocates a copy; compare its physical
    # path directly like the production reward guard. Bounded to20 bytes,
    # ASCII case-insensitive letters, exact punctuation/digits/NUL terminator.
    c.raw('8b564c85d2')
    c.branch('0f84', 'next_group')
    def check_path(fields):
        for offset, size, value, mask in fields:
            if size == 4:
                c.raw('8b02' if offset == 0 else bytes((0x8B, 0x42, offset)))
            else:
                c.raw(bytes((0x0F, 0xB7 if size == 2 else 0xB6, 0x42, offset)))
            if mask:
                c.raw(b'\x0d' + struct.pack('<I', mask))  # or eax, letter-case bits
            c.raw(b'\x3d' + struct.pack('<I', int.from_bytes(value, 'little')))
            c.branch('0f85', 'next_group')
    check_path(((0, 4, b'maps', 0x20202020), (4, 4, b'\\lev', 0x20202000),
                (8, 2, b'el', 0x2020), (10, 1, b'_', 0)))
    if submaps:
        # Case-fold the fourth token byte (normal '.map' has 'm' there;
        # submap digits2/3 already have that bit set). Punctuation stays exact.
        c.raw('8b420b0d000000203b4304')
        c.branch('0f85', 'next_group')
        c.raw('0fb6420d3d5f000000')
        c.branch('0f84', 'submap_suffix')
        check_path(((13, 4, b'.map', 0x20202000), (17, 1, b'\0', 0)))
        c.branch('e9', 'choose')
        c.label('submap_suffix')
        check_path(((15, 4, b'.map', 0x20202000), (19, 1, b'\0', 0)))
    else:
        check_path(((13, 4, b'.map', 0x20202000), (17, 1, b'\0', 0)))
        c.raw('0fb7420b3b4304')  # historical two-digit identity and emitter bytes
        c.branch('0f85', 'next_group')
    c.branch('e9', 'choose')

    c.label('next_group')
    c.raw('8b570c8bdf83c31085d2')
    c.branch('0f84', 'next_moving_group')
    c.raw('8bc203d203d003d203d2')  # edx=count*12
    c.branch('e9', 'advance_group')
    c.label('next_moving_group')
    c.raw('ba08000000')
    c.label('advance_group')
    c.raw('8bfb03fa83e901')
    c.branch('e9', 'group')
    _emit_selection(c, base_va)
    c.raw(b'\0' * (-len(c.code) % 4))
    code_size = len(c.code)
    struct.pack_into('<i', c.code, table_delta, code_size - c.labels['table_origin'])
    c.raw(struct.pack('<I', len(groups)))
    metadata = []
    for key, sources in groups.items():
        policy, trigger = key[:2]
        moving = policy == 'map_vid_act43'
        c.raw(struct.pack('<3iI', *trigger, 0 if moving else len(sources)))
        group = {'trigger': trigger, 'source_guard': policy, 'source_count': len(sources)}
        if moving:
            map_key, vid = key[2:]
            path = REGISTRY.map_identity(map_key).path.lower().replace('/', '\\')
            token = int.from_bytes(path[11:15 if submaps else 13].encode('ascii'), 'little')
            c.raw(struct.pack('<II', vid, token))
            group.update(map_key=map_key, source_vid=vid, map_path=path)
        else:
            for source in sources:
                c.raw(source)
        metadata.append(group)
    stub = c.finish()
    if len(stub) > capacity:
        raise ValueError(f'Registered ACT43 wrapper needs {len(stub)} bytes; capacity is {capacity}')
    return stub, {'layout': 'grouped-act43-source-policies-v2', 'code_bytes': code_size,
        'table_bytes': len(stub) - code_size, 'relative_table_address': True,
        'groups': tuple(metadata),
        'distinct_source_signatures': sum(1 if key[0] == 'map_vid_act43' else len(sources)
                                          for key, sources in groups.items())}


def _section_headers(image):
    if len(image) < 0x200 or image[:2] != b'MZ':
        raise ValueError('Expected complete x86 PE image')
    pe = struct.unpack_from('<I', image, 0x3C)[0]
    if not 0x40 <= pe <= len(image) - 256 or image[pe:pe + 4] != b'PE\0\0':
        raise ValueError('Invalid PE header')
    optional = pe + 24
    machine, count = struct.unpack_from('<HH', image, pe + 4)
    table = optional + struct.unpack_from('<H', image, pe + 20)[0]
    if (machine != 0x14C or struct.unpack_from('<H', image, optional)[0] != 0x10B
            or struct.unpack_from('<I', image, optional + 28)[0] != IMAGE_BASE
            or table + count * 40 > len(image)):
        raise ValueError('Unsupported PE section layout')
    sections = [struct.unpack_from('<8sIIII', image, table + i * 40) for i in range(count)]
    return pe, optional, table, sections


def _apply_registered_extended(image):
    """Keep the audited selector ABI; give its growing table its own RX section."""
    from old_native_pe_sections import logical_section_count
    pe, optional, headers, sections = _section_headers(image)
    if logical_section_count(sections) != 5 or len(sections) != 5:
        raise ValueError('Party section must follow the five original sections')
    sa, fa = struct.unpack_from('<II', image, optional + 32)
    if (sa, fa) != (0x1000, 0x1000):
        raise ValueError('Unexpected original PE alignment')
    align = lambda value: (value + 0xFFF) & ~0xFFF
    header = headers + len(sections) * 40
    raw = len(image)
    if (header + 40 > min(s[4] for s in sections if s[3])
            or image[header:header + 40] != b'\0' * 40
            or max(s[4] + s[3] for s in sections) != raw or raw != align(raw)):
        raise ValueError('No safe section header or unexpected executable overlay')
    rva = align(max(s[2] + max(s[1], s[3]) for s in sections))
    if struct.unpack_from('<I', image, optional + 56)[0] != rva:
        raise ValueError('Unexpected SizeOfImage')
    stub, table = _registered_program(base_va=IMAGE_BASE + rva, capacity=0x10000)
    trampoline = _relative(0xE9, CAVE_VA, IMAGE_BASE + rva).ljust(CAVE_SIZE, b'\0')
    patches = tuple((va, before, trampoline if va == CAVE_VA else after)
                    for va, before, after in TRIGGER_PATCHES)
    base = _apply_executable(image, patches)
    raw_size = align(len(stub))
    out = bytearray(base + b'\0' * raw_size)
    out[raw:raw + len(stub)] = stub
    struct.pack_into('<8sIIIIIIHHI', out, header, SECTION_NAME, len(stub),
                     rva, raw_size, raw, 0, 0, 0, 0, 0x60000020)
    struct.pack_into('<H', out, pe + 6, len(sections) + 1)
    struct.pack_into('<I', out, optional + 4,
                     struct.unpack_from('<I', image, optional + 4)[0] + raw_size)
    struct.pack_into('<I', out, optional + 56, align(rva + len(stub)))
    return bytes(out), stub, table, dict(name='.oparty', rva=rva, raw=raw,
        raw_size=raw_size, virtual_size=len(stub), writable=False), patches


def _normalize_extended(image):
    pe, optional, headers, sections = _section_headers(image)
    positions = [i for i, s in enumerate(sections) if s[0] == SECTION_NAME]
    if not positions:
        return None
    if positions != [5] or len(sections) != 6:
        raise ValueError('Remove later extensions before normalizing the party section')
    _, _, rva, raw_size, raw = sections[-1]
    if raw + raw_size != len(image) or raw != max(s[4] + s[3] for s in sections[:-1]):
        raise ValueError('Invalid party section extent')
    prior = bytearray(image[:raw])
    for va, before, _ in TRIGGER_PATCHES:
        prior[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] = before
    prior[headers + 5 * 40:headers + 6 * 40] = b'\0' * 40
    struct.pack_into('<H', prior, pe + 6, 5)
    code_size = struct.unpack_from('<I', image, optional + 4)[0]
    if code_size < raw_size:
        raise ValueError('Invalid party code size')
    struct.pack_into('<I', prior, optional + 4, code_size - raw_size)
    struct.pack_into('<I', prior, optional + 56, rva)
    prior = bytes(prior)
    if _apply_registered_extended(prior)[0] != image:
        raise ValueError('Party section differs from the trusted registry output')
    return prior


def patch_registered(image: bytes, map_images) -> tuple[bytes, dict]:
    """Apply all current trusted registry triggers in declaration order.

    Every registered original map is required and audited. Unknown maps are
    rejected rather than silently excluded from the signature collision check.
    This API does not accept custom registry data or caller-provided stub code.
    """
    from old_native_trigger_validation import audit_trigger_signatures
    if not isinstance(image, bytes):
        raise TypeError('Expected executable bytes')
    audit = audit_trigger_signatures(REGISTRY, map_images)
    result, stub, table, section, patches = _apply_registered_extended(image)
    return result, {
        'feature': REGISTERED_FEATURE,
        'baseline_sha256': BASELINE_SHA256,
        'input_sha256': hashlib.sha256(image).hexdigest(),
        'output_sha256': hashlib.sha256(result).hexdigest(),
        'source_maps': {identity.key: {'path': identity.path, 'sha256': identity.sha256}
                        for identity in REGISTRY.maps},
        'catalog_sha256': hashlib.sha256(json.dumps(REGISTRY.manifest(), sort_keys=True).encode('utf-8')).hexdigest(),
        'actor_policy': 'Army0 if within native radius, else army3 if within native radius, else original army0',
        'distance': 'Original x87 max(abs(dx),abs(dy)) + float32(0.398)*min; strict < radius',
        'source_sprite_guard': 'Per-source policy: exact float32 XYZ or physical map path plus source VID; complete ACT43 x/y/r tuple in both',
        'health_policy': 'Original ACT43 has no HP filter; preserved',
        'native_map_guard': any(entry.source_guard == 'map_vid_act43' for entry in REGISTRY.triggers),
        'native_vid_guard': any(entry.source_guard == 'map_vid_act43' for entry in REGISTRY.triggers),
        'native_guard_scope': 'Map and VID guards apply only to map_vid_act43 sources; exact_xyz preserves the historical selector',
        'stub_va': hex(IMAGE_BASE + section['rva']), 'stub_size': len(stub),
        'cave_size': CAVE_SIZE, 'remaining_cave_bytes': CAVE_SIZE - 5,
        'storage': 'Dedicated read/execute PE section; existing cave holds only a jump',
        'section': section,
        'trigger_count': len(REGISTRY.triggers),
        'table': table,
        'triggers': tuple({'map_key': entry.map_key, 'source_guard': entry.source_guard,
                          'source_vid': entry.guard_vid, 'original_source_vid': entry.sprite.vid, **dict(view)}
                          for entry, view in zip(REGISTRY.triggers, _registered_entries())),
        'collision_audit': audit,
        'patches': [{'va': hex(va), 'before': before.hex(), 'after': after.hex()}
                    for va, before, after in patches],
    }
