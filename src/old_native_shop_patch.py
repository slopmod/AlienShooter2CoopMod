"""Bounded OLD native shop diagnostic, after optional money, before input/RNG.

EXT200/201 quote Ammo_pistol's native purchase unit/price. EXT202 performs one
owner.virtual+60 purchase using a temporary native stock clone. The caller must
schedule this on every peer from synchronized input; this is not a shop UI.
"""
from __future__ import annotations

import hashlib
import struct

from old_native_campaign_patch import BASELINE_SHA256, ISOLATION_PATCHES, STORY_PATCHES
from old_native_spawn_rng_patch import SPAWN_PATCHES
from old_native_crush_sync_patch import normalize_optional as normalize_crush
from old_native_party_items_patch import normalize_optional as normalize_items
from old_native_party_triggers_patch import normalize_optional as normalize_triggers
from old_native_shared_money_patch import normalize_optional as normalize_money
from old_native_pe_sections import logical_section_count

FEATURE = 'old-native-ammo-shop-diagnostic-v2'
IMAGE_BASE = 0x400000
SECTION_NAME = b'.oshop\0\0'
HOOK_VA = 0x49A1A0
HOOK_BYTES = bytes.fromhex('518b442418')
EXT_QUANTITY, EXT_PRICE, EXT_BUY = 200, 201, 202
ITEM_NAME = b'Ammo_pistol\0'
NAME_OFFSET = 0x600
PAYLOAD_SIZE = 0x610
GUARD_ERRORS = {
    -1: 'missing_game', -2: 'not_party_player', -3: 'missing_owner',
    -4: 'owner_vtable', -5: 'missing_registry', -6: 'registry_vtable',
    -7: 'missing_descriptor', -8: 'ammo_vtable', -9: 'not_base_descriptor',
    -10: 'catalog_level', -11: 'nonpositive_cost', -12: 'nonpositive_unit',
    -13: 'whole_stack_quote_mode', -14: 'allocation_failed',
}


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
    if struct.unpack_from('<I', image, optional + 28)[0] != IMAGE_BASE or not 5 <= count <= 8:
        raise ValueError('Shop must precede other diagnostic sections')
    table = optional + size
    if table + count * 40 > len(image):
        raise ValueError('Truncated section table')
    sections = [struct.unpack_from('<8sIIII', image, table + i * 40) for i in range(count)]
    if logical_section_count(sections) not in (5, 6, 7):
        raise ValueError('Shop must precede other diagnostic sections')
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

    def call(self, va):
        self.emit(b'\xe8' + struct.pack('<i', va - self.va - len(self.code) - 5))

    def finish(self):
        for at, target in self.fixups:
            destination = self.labels[target] if isinstance(target, str) else target - self.va
            struct.pack_into('<i', self.code, at, destination - at - 4)
        return bytes(self.code)


def _stub(section_rva):
    c = _Code(IMAGE_BASE + section_rva)
    rejected = []

    def reject(opcode, result):
        label = 'reject_' + str(-result)
        rejected.append((label, result))
        c.branch(opcode, label)
    # Preserve the exact incoming state on the original dispatch path.
    c.emit('9c817c2408c8000000')
    c.branch('0f82', 'original')
    c.emit('817c2408ca000000')
    c.branch('0f87', 'original')
    c.emit('9d558bec53565783ec14')
    # Stack locals: -10 result, -14 outItem, -18 unit, -1C temp, -20 registry.
    c.emit('c745f0ffffffffc745ec00000000c745e4000000008bf1')
    c.emit('e8000000005b81eb')
    c.emit(struct.pack('<I', section_rva + len(c.code) - 3))
    # EBX=image base, ESI=explicit player's +160 interface.
    # The native dispatcher also clears its secondary string-result object.
    c.emit('8d8318501e00508b4d1c')
    c.call(0x42B420)
    c.emit('8b83dc4d200085c0')
    reject('0f84', -1)
    c.emit('8d96a0feffff')  # EDX=ESI-160, the player's primary object.
    c.emit('3b90c0090000')
    c.branch('0f84', 'party')
    c.emit('3b90cc090000')
    reject('0f85', -2)
    c.label('party')
    c.emit('8b7e3485ff')
    reject('0f84', -3)
    c.emit('8d83b4ce19003907')  # exact RPG owner vtable
    reject('0f85', -4)
    c.emit('8bb388a4330085f6')  # ESI=registry, EDI=owner
    reject('0f84', -5)
    # Global registry factory472880 ->4728F0 installs59BD18 at472A1E.
    # 59CBAC is the different registry interface embedded in the quest server.
    c.emit('8975e08d8318bd19003906')
    reject('0f85', -6)
    # Native name lookup, template-only. No base ID assumption or global UI.
    c.emit('8d83' + struct.pack('<I', section_rva + NAME_OFFSET).hex())
    c.emit('8b168bce6a0150ff520c85c0')
    reject('0f84', -7)
    c.emit('8bf08d83fccf19003906')  # exact native ammo item vtable
    reject('0f85', -8)
    c.emit('837e1c00')  # base descriptor, never an inventory instance
    reject('0f85', -9)
    c.emit('837e2c00')  # only Add_level0 catalog entry
    reject('0f85', -10)
    c.emit('837e3400')
    reject('0f8e', -11)
    c.emit('837e4800')  # MaxBay denominator must be positive
    reject('0f8e', -12)
    c.emit('80bbb506330000')  # reject native whole-stack quote mode
    reject('0f85', -13)
    c.emit('8b068bceff90040100008945e8')
    c.emit('817d08c8000000')
    c.branch('0f84', 'quote')
    c.emit('8b068bceff9008010000')
    c.emit('817d08c9000000')
    c.branch('0f84', 'quote')
    # Create stock with the exact native item clone, then MaxInv quantity as
    # the vanilla stock builder does at481D39..481D56. Never mutate template.
    c.emit('8b068bceff90f000000085c0')
    reject('0f84', -14)
    c.emit('8bf08975e48b068bceff90cc000000')
    c.emit('8b168bce50ff92a8000000')
    # Native purchase does money/capacity validation, debit, purchased clone,
    # native insertion/merge and its own incomplete-insertion refund branch.
    c.emit('ff75e88d45ec50568bcf8b17ff52608945f0')
    c.emit('85c0')
    c.branch('0f84', 'cleanup')
    # Match stock helper4822C0's nonzero-result source stock decrement.
    c.emit('8b45e8f7d8508b168bceff92ac000000')
    c.label('cleanup')
    # Registered native clones MUST be removed via registry+38 (474040),
    # which unregisters and destroys. Direct item+4 leaves a dangling entry.
    c.emit('8b4de08b1156ff5238')
    c.branch('e9', 'done')
    c.label('quote')
    c.emit('8945f0')
    c.label('done')
    c.emit('8b45188b55f0891033c083c4145f5e5b5dc21800')
    c.label('original')
    c.emit('9d')
    c.emit(HOOK_BYTES)
    c.branch('e9', HOOK_VA + len(HOOK_BYTES))
    for label, result in rejected:
        c.label(label)
        c.emit('c745f0' + struct.pack('<i', result).hex())
        c.branch('e9', 'done')
    code = c.finish()
    if len(code) > NAME_OFFSET:
        raise AssertionError('Shop code overlaps fixed catalog name')
    return code


def _validate_preimage(image):
    # Money and optional party sections are accepted only through their exact
    # normalizers. Their native hooks remain in the shop output.
    _headers(image)
    normalized, money = normalize_money(image)
    normalized, triggers = normalize_triggers(normalized)
    normalized, items = normalize_items(normalized)
    normalized, crush = normalize_crush(normalized)
    if not (triggers and items and crush):
        raise ValueError('Complete campaign party patches are required')
    normalized = bytearray(normalized)
    for va, before, after in SPAWN_PATCHES + ISOLATION_PATCHES + STORY_PATCHES:
        at = va - IMAGE_BASE
        current = normalized[at:at + len(before)]
        if current not in (before, after) or ((va, before, after) in SPAWN_PATCHES and current != after):
            raise ValueError(f'Unknown/incomplete pre-shop patch at {va:#x}')
        normalized[at:at + len(before)] = before
    if _sha(normalized) != BASELINE_SHA256:
        raise ValueError('Unsupported shop executable: normalized hash mismatch')
    return money


def patch(image: bytes) -> tuple[bytes, dict]:
    money = _validate_preimage(image)
    pe, optional, table, sections = _headers(image)
    sa, fa = struct.unpack_from('<II', image, optional + 32)
    if (sa, fa) != (0x1000, 0x1000):
        raise ValueError('Unexpected original PE alignment')
    header = table + len(sections) * 40
    first_raw = min(s[4] for s in sections if s[3])
    if header + 40 > first_raw or image[header:header + 40] != b'\0' * 40:
        raise ValueError('No empty section header')
    if max(s[4] + s[3] for s in sections) != len(image):
        raise ValueError('Unexpected executable overlay')
    new_rva = _align(max(s[2] + max(s[1], s[3]) for s in sections), sa)
    if struct.unpack_from('<I', image, optional + 56)[0] != new_rva:
        raise ValueError('Unexpected original SizeOfImage')
    raw_size = _align(PAYLOAD_SIZE, fa)
    raw = len(image)
    if raw != _align(raw, fa):
        raise ValueError('Unexpected original file alignment')
    code = _stub(new_rva)
    out = bytearray(image + b'\0' * raw_size)
    out[raw:raw + len(code)] = code
    out[raw + NAME_OFFSET:raw + NAME_OFFSET + len(ITEM_NAME)] = ITEM_NAME
    hook = b'\xe9' + struct.pack('<i', IMAGE_BASE + new_rva - HOOK_VA - 5)
    at = HOOK_VA - IMAGE_BASE
    if image[at:at + len(HOOK_BYTES)] != HOOK_BYTES:
        raise ValueError('Unexpected SendCommandA entry')
    out[at:at + len(hook)] = hook
    struct.pack_into('<8sIIIIIIHHI', out, header, SECTION_NAME, PAYLOAD_SIZE,
                     new_rva, raw_size, raw, 0, 0, 0, 0, 0x60000020)
    struct.pack_into('<H', out, pe + 6, len(sections) + 1)
    code_size = struct.unpack_from('<I', image, optional + 4)[0]
    struct.pack_into('<I', out, optional + 4, code_size + raw_size)
    struct.pack_into('<I', out, optional + 56, _align(new_rva + PAYLOAD_SIZE, sa))
    result = bytes(out)
    return result, {
        'feature': FEATURE, 'baseline_sha256': BASELINE_SHA256,
        'input_sha256': _sha(image), 'output_sha256': _sha(result),
        'shared_money_predecessor': money,
        'section_rva': new_rva, 'section_raw': raw, 'section_raw_size': raw_size,
        'section_virtual_size': PAYLOAD_SIZE, 'code_size': len(code),
        'hook_va': HOOK_VA, 'commands': {'quantity': EXT_QUANTITY, 'price': EXT_PRICE, 'buy': EXT_BUY},
        'catalog': 'Ammo_pistol', 'armies': [0, 3],
        'buy_result': 'Native inventory bitmask; bit0 success, 0 rejection; negative guard failure',
        'guard_errors': GUARD_ERRORS,
        'transaction': 'RPGowner.v60; no direct hero item grant or wallet update',
        'temporary_cleanup': 'registry.v38 unregisters and destroys source clone',
        'scope': 'Diagnostic native transaction only; no stock UI/finite catalog/transport implementation',
    }


def normalize_optional(image: bytes) -> tuple[bytes, bool]:
    """Remove exact final .oshop, preserving its validated optional .omoney."""
    pe, optional, table, sections = _headers(image)
    at = HOOK_VA - IMAGE_BASE
    if sections[-1][0] != SECTION_NAME:
        if image[at:at + len(HOOK_BYTES)] != HOOK_BYTES:
            raise ValueError('Unknown/partial shop patch')
        # Verify, but do not strip, a possible money predecessor. Unknown
        # sixth sections and partial/mutated money hooks fail in its guard.
        normalize_money(image)
        return image, False
    name, virtual, rva, raw_size, raw = sections[-1]
    if raw + raw_size != len(image) or raw != max(s[4] + s[3] for s in sections[:-1]):
        raise ValueError('Invalid shop section extent')
    prior = bytearray(image[:raw])
    prior[at:at + len(HOOK_BYTES)] = HOOK_BYTES
    header = table + (len(sections) - 1) * 40
    prior[header:header + 40] = b'\0' * 40
    struct.pack_into('<H', prior, pe + 6, len(sections) - 1)
    code_size = struct.unpack_from('<I', prior, optional + 4)[0]
    if code_size < raw_size:
        raise ValueError('Invalid shop code size')
    struct.pack_into('<I', prior, optional + 4, code_size - raw_size)
    struct.pack_into('<I', prior, optional + 56, rva)
    prior = bytes(prior)
    rebuilt, _ = patch(prior)
    if rebuilt != image:
        raise ValueError('Shop differs from exact guarded patch output')
    return prior, True
