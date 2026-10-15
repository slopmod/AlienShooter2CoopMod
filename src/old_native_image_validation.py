"""Validate native image layout and normalize the complete guarded patch chain."""
import hashlib
import struct
from old_native_campaign_patch import BASELINE_SHA256, ISOLATION_PATCHES, STORY_PATCHES
from old_native_spawn_rng_patch import SPAWN_PATCHES
from old_native_crush_sync_patch import normalize_optional as normalize_crush
from old_native_party_items_patch import normalize_optional as normalize_party_items
from old_native_party_triggers_patch import normalize_optional as normalize_party_triggers
from old_native_pe_sections import logical_section_count

BASE = 0x400000


def _sha(data):
    return hashlib.sha256(data).hexdigest()

def _headers(image):
    if not isinstance(image, bytes) or len(image) < 0x200 or image[:2] != b'MZ':
        raise ValueError('Expected PE bytes')
    pe = struct.unpack_from('<I', image, 0x3c)[0]
    if not 0x40 <= pe <= len(image) - 256 or image[pe:pe + 4] != b'PE\0\0':
        raise ValueError('Invalid PE header')
    machine, count = struct.unpack_from('<HH', image, pe + 4)
    opt_size = struct.unpack_from('<H', image, pe + 20)[0]
    opt = pe + 24
    if machine != 0x14c or struct.unpack_from('<H', image, opt)[0] != 0x10b:
        raise ValueError('Expected x86 PE32')
    if struct.unpack_from('<I', image, opt + 28)[0] != BASE or not 5 <= count <= 14:
        raise ValueError('Unexpected image base/section count')
    table = opt + opt_size
    if table + count * 40 > len(image):
        raise ValueError('Truncated section table')
    sections = []
    for i in range(count):
        h = table + i * 40
        name, virtual, rva, raw_size, raw = struct.unpack_from('<8sIIII', image, h)
        sections.append({'name': name, 'virtual': virtual, 'rva': rva,
                         'raw_size': raw_size, 'raw': raw, 'header': h})
    if not 5 <= logical_section_count(sections) <= 11:
        raise ValueError('Unexpected image base/section count')
    return pe, opt, table, sections

def _raw(image, rva, size):
    for s in _headers(image)[3]:
        if s['rva'] <= rva and rva + size <= s['rva'] + s['raw_size']:
            offset = s['raw'] + rva - s['rva']
            if offset + size <= len(image):
                return offset
    raise ValueError('Address is not file-backed')

def _validate_input(image):
    """Prove every input byte is baseline or known production patch output."""
    sections = _headers(image)[3]
    if sections[-1]['name'] == b'.oinput\0':
        raise ValueError('Automated-input images are not supported by the production builder')
    from old_native_checkpoint_patch import normalize_optional as normalize_checkpoint
    image, _ = normalize_checkpoint(image)
    from old_native_script_capacity_patch import normalize_optional as normalize_capacity
    image, _ = normalize_capacity(image)
    from old_native_campaign_command_patch import normalize_optional as normalize_commands
    from old_native_campaign_shop_patch import normalize_optional as normalize_campaign_shop
    from old_native_campaign_reward_patch import normalize_optional as normalize_rewards
    image, _ = normalize_rewards(image)
    image, _ = normalize_commands(image)
    image, _ = normalize_campaign_shop(image)
    from old_native_shop_patch import normalize_optional as normalize_shop
    image, _ = normalize_shop(image)
    from old_native_shared_money_patch import normalize_optional as normalize_money
    image, _ = normalize_money(image)
    without_triggers, _ = normalize_party_triggers(image)
    if len(_headers(without_triggers)[3]) != 5:
        raise ValueError('Unsupported extra image section')
    without_items, _ = normalize_party_items(without_triggers)
    without_crush, _ = normalize_crush(without_items)
    normalized = bytearray(without_crush)
    accepted_spawn = 0
    for va, before, after in ISOLATION_PATCHES + STORY_PATCHES + SPAWN_PATCHES:
        # The spawn patch also extends .text VirtualSize in the PE header.
        # All guarded patch locations in this exact image use raw == RVA.
        at = va - BASE
        if without_crush[at:at + len(before)] not in (before, after):
            raise ValueError(f'Unknown input patch at {va:#x}')
        if (va, before, after) in SPAWN_PATCHES and without_crush[at:at + len(before)] == after:
            accepted_spawn += 1
        normalized[at:at + len(before)] = before
    if accepted_spawn not in (0, len(SPAWN_PATCHES)):
        raise ValueError('Incomplete synchronized spawn patch')
    if _sha(normalized) != BASELINE_SHA256:
        raise ValueError('Input executable normalized hash mismatch')
    return False
