"""Exact OLD campaign shared-wallet hooks; no polling or balance reconciliation.

After explicit EXT203 activation, army3 MONEY(18) accesses use army0's native
skill interface. The actor's higher-level OnGetMoney callback is unchanged.
Raw guest skill-array cells remain a non-authoritative shadow, not a save format.
Apply after party triggers and before optional shop/input/RNG sections.
"""
from __future__ import annotations

import hashlib
import struct

from old_native_campaign_patch import BASELINE_SHA256, ISOLATION_PATCHES, STORY_PATCHES
from old_native_spawn_rng_patch import SPAWN_PATCHES
from old_native_crush_sync_patch import normalize_optional as normalize_crush
from old_native_party_items_patch import normalize_optional as normalize_items
from old_native_party_triggers_patch import normalize_optional as normalize_triggers
from old_native_pe_sections import logical_section_count

FEATURE = 'old-native-shared-money-v1'
IMAGE_BASE = 0x400000
SECTION_NAME = b'.omoney\0'
EXT_ENABLE, EXT_STATUS = 203, 204
STATE_OFFSET = 0x800
PAYLOAD_SIZE = 0x808
# Entire instructions. Functions take ECX=RPGowner+0C, arg1=skill ID.
HOOKS = (
    (0x471B00, bytes.fromhex('5356578b7c2410'), 'set'),
    (0x471BB0, bytes.fromhex('558b6c2408'), 'add'),
    (0x471C50, bytes.fromhex('56578b7c240c'), 'get'),
    (0x471CA0, bytes.fromhex('56578b7c240c'), 'base_get'),
    (0x49B478, bytes.fromhex('68ec080000'), 'control'),
)


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _align(value, alignment):
    if alignment <= 0 or alignment & (alignment - 1):
        raise ValueError('Invalid PE alignment')
    return (value + alignment - 1) & -alignment


def _headers(image):
    if not isinstance(image, bytes) or len(image) < 0x200 or image[:2] != b'MZ':
        raise ValueError('Expected PE bytes')
    pe = struct.unpack_from('<I', image, 0x3C)[0]
    if not 0x40 <= pe <= len(image) - 256 or image[pe:pe + 4] != b'PE\0\0':
        raise ValueError('Invalid PE header')
    machine, count = struct.unpack_from('<HH', image, pe + 4)
    optional = pe + 24
    size = struct.unpack_from('<H', image, pe + 20)[0]
    if machine != 0x14C or struct.unpack_from('<H', image, optional)[0] != 0x10B:
        raise ValueError('Expected x86 PE32')
    if struct.unpack_from('<I', image, optional + 28)[0] != IMAGE_BASE or not 5 <= count <= 7:
        raise ValueError('Money must precede shop and diagnostic sections')
    table = optional + size
    if table + count * 40 > len(image):
        raise ValueError('Truncated section table')
    sections = [struct.unpack_from('<8sIIII', image, table + i * 40) for i in range(count)]
    if logical_section_count(sections) not in (5, 6):
        raise ValueError('Money must precede shop and diagnostic sections')
    return pe, optional, table, sections


class _Code:
    def __init__(self, va):
        self.va, self.code, self.labels, self.fixups = va, bytearray(), {}, []

    def emit(self, value):
        self.code.extend(bytes.fromhex(value) if isinstance(value, str) else value)

    def label(self, name):
        self.labels[name] = len(self.code)

    def branch(self, opcode, name):
        self.emit(opcode)
        self.fixups.append((len(self.code), name))
        self.emit(b'\0' * 4)

    def base(self):
        self.emit('e8000000005b81eb')
        self.emit(struct.pack('<I', self.va - IMAGE_BASE + len(self.code) - 3))

    def finish(self):
        for at, target in self.fixups:
            destination = self.labels[target] if isinstance(target, str) else target - self.va
            struct.pack_into('<i', self.code, at, destination - at - 4)
        return bytes(self.code)


def _stub(section_rva):
    c = _Code(IMAGE_BASE + section_rva)
    state = section_rva + STATE_OFFSET
    for va, before, name in HOOKS[:4]:
        c.label(name)
        c.emit('9c505253837c241412')  # save flags/eax/edx/ebx, inspect arg1
        c.branch('0f85', name + '_done')
        c.base()
        c.branch('e8', 'active_pair')
        c.emit('85c0')
        c.branch('0f84', name + '_done')
        c.emit('3bca')  # only exact guest skill interface
        c.branch('0f85', name + '_done')
        c.emit('8bc8')
        c.label(name + '_done')
        c.emit('5b5a589d')
        c.emit(before)
        c.branch('e9', va + len(before))

    c.label('control')
    c.emit('9c3dcb000000')
    c.branch('0f84', 'command')
    c.emit('3dcc000000')
    c.branch('0f84', 'command')
    c.emit('9d')
    c.emit(HOOKS[4][1])
    c.branch('e9', 0x49B47D)
    c.label('command')
    c.emit('53515255')  # preserve dispatcher locals; EDI holds result
    c.emit('8be8')      # EBP=command
    c.base()
    c.emit('bfffffffff')
    c.branch('e8', 'pair')
    c.emit('85c0')
    c.branch('0f84', 'command_done')
    # Only an explicit command sent to current army0 may activate/read status.
    c.emit('8b8bdc4d20008b89c009000081c1600100003bce')
    c.branch('0f85', 'wrong_caller')
    c.emit('81fdcb000000')
    c.branch('0f85', 'status')
    c.emit('8983' + struct.pack('<I', state).hex())
    c.emit('8993' + struct.pack('<I', state + 4).hex())
    c.emit('bf01000000')
    c.branch('e9', 'command_done')
    c.label('status')
    c.emit('33ff')
    c.emit('3b83' + struct.pack('<I', state).hex())
    c.branch('0f85', 'command_done')
    c.emit('3b93' + struct.pack('<I', state + 4).hex())
    c.branch('0f85', 'command_done')
    c.emit('bf01000000')
    c.branch('e9', 'command_done')
    c.label('wrong_caller')
    c.emit('bffeffffff')
    c.label('command_done')
    c.emit('5d5a595b9d')
    c.branch('e9', 0x49B491)

    c.label('active_pair')
    c.branch('e8', 'pair')
    c.emit('85c0')
    c.branch('0f84', 'inactive')
    c.emit('3b83' + struct.pack('<I', state).hex())
    c.branch('0f85', 'inactive')
    c.emit('3b93' + struct.pack('<I', state + 4).hex())
    c.branch('0f85', 'inactive')
    c.emit('c3')
    c.label('inactive')
    c.emit('33c0c3')

    # Pair resolution never calls engine code or dereferences saved heap pointers.
    # Saved pointers are compared with freshly resolved owners, never followed.
    c.label('pair')
    c.emit('56578b83dc4d200085c0')
    c.branch('0f84', 'invalid_pair')
    c.emit('8bb0c00900008bb8cc09000085f6')
    c.branch('0f84', 'invalid_pair')
    c.emit('85ff')
    c.branch('0f84', 'invalid_pair')
    c.emit('3bf7')
    c.branch('0f84', 'invalid_pair')
    c.emit('8bb6940100008bbf9401000085f6')
    c.branch('0f84', 'invalid_pair')
    c.emit('85ff')
    c.branch('0f84', 'invalid_pair')
    c.emit('3bf7')
    c.branch('0f84', 'invalid_pair')
    c.emit('8d83b4ce19003906')
    c.branch('0f85', 'invalid_pair')
    c.emit('3907')
    c.branch('0f85', 'invalid_pair')
    c.emit('83c60c83c70c8d8338cd19003906')
    c.branch('0f85', 'invalid_pair')
    c.emit('3907')
    c.branch('0f85', 'invalid_pair')
    for register in ('be', 'bf'):
        c.emit('83' + register + '8800000012')
        c.branch('0f8e', 'invalid_pair')
        for offset in (0xA4, 0xA8):
            c.emit('83' + register + struct.pack('<I', offset).hex() + '00')
            c.branch('0f84', 'invalid_pair')
    c.emit('8bc68bd75f5ec3')
    c.label('invalid_pair')
    c.emit('33c05f5ec3')
    code = c.finish()
    if len(code) > STATE_OFFSET:
        raise AssertionError('Money hooks overlap state')
    return code, {name: c.labels[name] for _, _, name in HOOKS}


def _validate_preimage(image):
    if logical_section_count(_headers(image)[3]) != 5:
        raise ValueError('Expected pre-money executable')
    normalized, triggers = normalize_triggers(image)
    normalized, items = normalize_items(normalized)
    normalized, crush = normalize_crush(normalized)
    if not (triggers and items and crush):
        raise ValueError('Complete campaign party patches are required')
    normalized = bytearray(normalized)
    for va, before, after in SPAWN_PATCHES + ISOLATION_PATCHES + STORY_PATCHES:
        at = va - IMAGE_BASE
        current = normalized[at:at + len(before)]
        if current not in (before, after) or ((va, before, after) in SPAWN_PATCHES and current != after):
            raise ValueError(f'Unknown/incomplete pre-money patch at {va:#x}')
        normalized[at:at + len(before)] = before
    if _sha(normalized) != BASELINE_SHA256:
        raise ValueError('Unsupported money executable: normalized hash mismatch')


def patch(image: bytes) -> tuple[bytes, dict]:
    _validate_preimage(image)
    pe, optional, table, sections = _headers(image)
    sa, fa = struct.unpack_from('<II', image, optional + 32)
    if (sa, fa) != (0x1000, 0x1000):
        raise ValueError('Unexpected original PE alignment')
    header = table + len(sections) * 40
    if header + 40 > min(s[4] for s in sections if s[3]) or image[header:header + 40] != b'\0' * 40:
        raise ValueError('No empty section header')
    if max(s[4] + s[3] for s in sections) != len(image):
        raise ValueError('Unexpected executable overlay')
    rva = _align(max(s[2] + max(s[1], s[3]) for s in sections), sa)
    if struct.unpack_from('<I', image, optional + 56)[0] != rva:
        raise ValueError('Unexpected original SizeOfImage')
    raw_size, raw = _align(PAYLOAD_SIZE, fa), len(image)
    if raw != _align(raw, fa):
        raise ValueError('Unexpected original file alignment')
    code, offsets = _stub(rva)
    out = bytearray(image + b'\0' * raw_size)
    out[raw:raw + len(code)] = code
    for va, before, name in HOOKS:
        at = va - IMAGE_BASE
        if image[at:at + len(before)] != before:
            raise ValueError(f'Unexpected money hook {va:#x}')
        detour = b'\xe9' + struct.pack('<i', IMAGE_BASE + rva + offsets[name] - va - 5)
        out[at:at + len(before)] = detour + b'\x90' * (len(before) - 5)
    # Eight writable state bytes hold the canonical/guest skill identities.
    struct.pack_into('<8sIIIIIIHHI', out, header, SECTION_NAME, PAYLOAD_SIZE,
                     rva, raw_size, raw, 0, 0, 0, 0, 0xE0000020)
    struct.pack_into('<H', out, pe + 6, len(sections) + 1)
    code_size = struct.unpack_from('<I', image, optional + 4)[0]
    struct.pack_into('<I', out, optional + 4, code_size + raw_size)
    struct.pack_into('<I', out, optional + 56, _align(rva + PAYLOAD_SIZE, sa))
    result = bytes(out)
    return result, {
        'feature': FEATURE, 'baseline_sha256': BASELINE_SHA256,
        'input_sha256': _sha(image), 'output_sha256': _sha(result),
        'section_rva': rva, 'section_raw': raw, 'section_raw_size': raw_size,
        'section_virtual_size': PAYLOAD_SIZE, 'code_size': len(code),
        'hook_offsets': offsets, 'state_rva': rva + STATE_OFFSET,
        'commands': {'enable': EXT_ENABLE, 'status': EXT_STATUS},
        'command_result': 'enable 1; status 1 active/0 inactive; -1 pair unready, -2 caller not army0',
        'canonical_army': 0, 'guest_army': 3, 'skill': 18,
        'initial_balance': 'Existing canonical army0 balance; never sum or overwrite it',
        'routing': 'Synchronous native get/base-get/set/add redirect; no periodic reconciliation',
        'actor_callback': 'Original OnGetMoney executes on the collecting/acting owner before skill routing',
        'raw_shadow': 'Guest raw skill-array cells are non-authoritative; native getters use canonical storage',
        'scope': 'Live campaign pair; no durable saves, reconnect, or arbitrary player counts',
    }


def normalize_optional(image: bytes) -> tuple[bytes, bool]:
    """Verify/remove exact final .omoney after later shop/diagnostics removed."""
    pe, optional, table, sections = _headers(image)
    if sections[-1][0] != SECTION_NAME:
        if logical_section_count(sections) != 5 or any(image[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] != before
                                     for va, before, _ in HOOKS):
            raise ValueError('Unknown/partial money patch')
        return image, False
    _, _, rva, raw_size, raw = sections[-1]
    if raw + raw_size != len(image) or raw != max(s[4] + s[3] for s in sections[:-1]):
        raise ValueError('Invalid money section extent')
    prior = bytearray(image[:raw])
    for va, before, _ in HOOKS:
        prior[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] = before
    header = table + (len(sections) - 1) * 40
    prior[header:header + 40] = b'\0' * 40
    struct.pack_into('<H', prior, pe + 6, len(sections) - 1)
    code_size = struct.unpack_from('<I', prior, optional + 4)[0]
    if code_size < raw_size:
        raise ValueError('Invalid money code size')
    struct.pack_into('<I', prior, optional + 4, code_size - raw_size)
    struct.pack_into('<I', prior, optional + 56, rva)
    prior = bytes(prior)
    if patch(prior)[0] != image:
        raise ValueError('Money differs from exact guarded patch output')
    return prior, True
