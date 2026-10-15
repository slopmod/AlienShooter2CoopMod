"""Exact OLD sprite provenance, without changing damage, armies, RPG or RNG.

All lifetime bookkeeping is native and synchronous. Only the original normal
ACT_DAMAGE -> SetHP call creates a kill receipt. Script-controlled deaths do
not borrow the last attacker.
"""
from __future__ import annotations

import hashlib
import struct
from old_native_campaign_missions import MAP_NUMBERS

from old_native_campaign_command_patch import _Code
from old_native_pe_sections import logical_section_count

IMAGE_BASE = 0x400000
FEATURE = 'old-native-campaign-reward-provenance-v2'
SECTION_NAME = b'.oreward'
HOOK_VA = 0x49A1A0
STATE_OFFSET = 0x3000
TABLE_OFFSET = 0x3100
CAPACITY = 65536
ENTRY_SIZE = 32
PAYLOAD_SIZE = TABLE_OFFSET + CAPACITY * ENTRY_SIZE
COMMANDS = {'source_owner': 332, 'peek_kill_owner': 333,
            'claim_kill_owner': 334, 'fault': 335}
ERRORS = {-1: 'nonparty_or_unsupported', -2: 'already_claimed',
          -3: 'invalid_caller_map_or_lifetime', -10: 'table_capacity',
          -11: 'generation_exhausted', -12: 'missing_native_lifetime'}
BARREL_VIDS = (401, 402, 435, 1740, 2333, 3308)
# Constructor is early enough for recursively born/linked descendants. The
# damage hook is a CALL, not a JMP: its tail calls the original ret4 SetHP.
HOOKS = (
    (0x44A540, bytes.fromhex('895e10895e1c'), 'birth', 0xE9),
    (0x44A928, bytes.fromhex('53558be956'), 'destroy', 0xE9),
    (0x44F40D, bytes.fromhex('e87e600000'), 'lethal', 0xE8),
    (0x41DAA0, bytes.fromhex('c7455c00000000'), 'reset', 0xE9),
    (0x44EF2F, bytes.fromhex('c1e811894d44'), 'change_vid', 0xE9),
)
S = dict(fault=0, generation=4, epoch=8, live=12, high_water=16)
E = dict(pointer=0, birth=4, descriptor=8, generation=12,
         source=16, killer=20, flags=24, reserved=28)


def _sha(value): return hashlib.sha256(value).hexdigest()
def _align(value, alignment): return (value + alignment - 1) & -alignment


def _headers(image):
    if not isinstance(image, bytes) or image[:2] != b'MZ' or len(image) < 0x200:
        raise ValueError('Expected PE bytes')
    pe = struct.unpack_from('<I', image, 0x3C)[0]
    if not 0x40 <= pe <= len(image) - 256 or image[pe:pe + 4] != b'PE\0\0':
        raise ValueError('Invalid PE header')
    machine, count = struct.unpack_from('<HH', image, pe + 4)
    optional = pe + 24
    if machine != 0x14C or struct.unpack_from('<H', image, optional)[0] != 0x10B:
        raise ValueError('Expected x86 PE32')
    if struct.unpack_from('<I', image, optional + 28)[0] != IMAGE_BASE or not 5 <= count <= 10:
        raise ValueError('Rewards must follow .ocmd and precede diagnostics')
    table = optional + struct.unpack_from('<H', image, pe + 20)[0]
    if table + count * 40 > len(image): raise ValueError('Truncated section table')
    sections = [struct.unpack_from('<8sIIII', image, table + i * 40) for i in range(count)]
    if not 5 <= logical_section_count(sections) <= 9:
        raise ValueError('Rewards must follow .ocmd and precede diagnostics')
    return pe, optional, table, sections


def _stub(rva, previous):
    c = _Code(IMAGE_BASE + rva)
    state, table = rva + STATE_OFFSET, rva + TABLE_OFFSET
    def get(reg, name): c.load(reg, 'ebx', state + S[name])
    def put(name, reg): c.store('ebx', state + S[name], reg)
    def set_(name, value): c.imm('ebx', state + S[name], value)
    def result(value): c.ri('edi', value); c.jump('command_done')

    c.label('command'); c.emit('9c50'); c.load('eax', 'esp', 12)
    c.alu(7, 'eax', 332); c.jump('original', '82')
    c.alu(7, 'eax', 335); c.jump('original', '87')
    c.emit('589d558bec535657'); c.rr('esi', 'ecx'); c.base(); c.ri('edi', -3)
    c.lea('eax', 'ebx', 0x1E5018); c.push('eax'); c.load('ecx', 'ebp', 28); c.call(0x42B420)
    c.load('edx', 'ebx', 0x204DDC); c.test('edx'); c.jump('command_done', '84')
    c.load('eax', 'edx'); c.lea('ecx', 'ebx', 0x19B774); c.cmp('eax', 'ecx'); c.jump('command_done', '85')
    c.load('eax', 'edx', 0x9C0); c.test('eax'); c.jump('command_done', '84')
    c.lea('ecx', 'eax', 0x160); c.cmp('ecx', 'esi'); c.jump('command_done', '85')
    c.load('ecx', 'edx', 0x9CC); c.test('ecx'); c.jump('command_done', '84')
    c.cmp('eax', 'ecx'); c.jump('command_done', '84')
    c.load('eax', 'edx', 0x3C); c.alu(4, 'eax', 0x80); c.jump('command_done', '85')
    c.load('esi', 'edx', 0x4C); c.test('esi'); c.jump('command_done', '84')
    from old_native_campaign_missions import emit_native_map_guard
    emit_native_map_guard(c, 'esi', lambda condition: c.jump('command_done', condition))
    c.load('ecx', 'ebx', 0x206428); c.test('ecx'); c.jump('command_done', '84')
    c.load('eax', 'ecx', 0x10254); c.alu(7, 'eax', 2); c.jump('command_done', '85')
    for army in range(8):
        c.load('eax', 'ecx', 0x1025C + army * 24); c.test('eax')
        c.jump('command_done', '84' if army in (0, 3) else '85')
    get('edi', 'fault'); c.load('eax', 'ebp', 8)
    c.alu(7, 'eax', 335); c.jump('command_done', '84')
    c.test('edi'); c.jump('command_done', '85')
    c.ri('edi', -3); c.load('eax', 'ebp', 12); c.call('checked')
    c.test('eax'); c.jump('command_done', '84'); c.rr('esi', 'eax')
    c.load('eax', 'ebp', 8); c.alu(7, 'eax', 332); c.jump('query_source', '84')
    c.load('edi', 'esi', E['killer'])
    c.alu(7, 'eax', 333); c.jump('command_done', '84')
    # Claims include unknown/nonparty deaths, so original world statistics can
    # remain once-only even when a personal reward is intentionally withheld.
    c.load('eax', 'esi', E['pointer']); c.load('eax', 'eax', 0x20)
    c.alu(7, 'eax', 15); c.jump('claim_invalid', '82')
    c.load('eax', 'esi', E['flags']); c.rr('ecx', 'eax'); c.alu(4, 'ecx', 2)
    c.test('ecx'); c.jump('claimed', '85')
    c.alu(1, 'eax', 2); c.store('esi', E['flags'], 'eax'); c.jump('command_done')
    c.label('query_source'); c.load('eax', 'ebp', 12); c.call('resolve'); c.rr('edi', 'eax'); c.jump('command_done')
    c.label('claimed'); result(-2)
    c.label('claim_invalid'); result(-3)
    c.label('command_done'); c.load('eax', 'ebp', 24); c.store('eax', 0, 'edi')
    c.ri('eax', 0); c.emit('5f5e5b5dc21800')
    c.label('original'); c.emit('589d'); c.jump(previous)

    # No native calls from bookkeeping. PUSHFD/PUSHAD preserve the complete
    # integer ABI; helpers do not touch x87/SSE and CLD is scoped to reset.
    c.label('birth'); c.emit('9c60'); c.base()
    c.rr('eax', 'esi'); c.rr('edx', 'ebp'); c.call('register')
    c.emit('619d895e10895e1c'); c.jump(0x44A546)
    c.label('destroy'); c.emit('9c60'); c.base(); c.rr('eax', 'ecx'); c.call('erase')
    c.emit('619d53558be956'); c.jump(0x44A92D)
    c.label('lethal'); c.emit('9c60'); c.base()
    # Original call-entry stack: ret, newHP. PUSHFD+PUSHAD added36 bytes.
    c.load('eax', 'esp', 40); c.alu(7, 'eax', 0); c.jump('lethal_done', '8f')
    c.alu(7, 'edi', 0); c.jump('lethal_done', '8e')
    c.rr('eax', 'ebp'); c.load('edx', 'esp', 16)  # saved original EBX = attacker
    c.call('record_kill')
    c.label('lethal_done'); c.emit('619d'); c.jump(0x455490)
    c.label('reset'); c.emit('9c60'); c.base()
    c.lea('edi', 'ebx', table); c.ri('ecx', CAPACITY * ENTRY_SIZE // 4); c.ri('eax', 0); c.emit('fcf3ab')
    for name in ('fault', 'generation', 'live', 'high_water'): set_(name, 0)
    get('eax', 'epoch'); c.alu(0, 'eax', 1); put('epoch', 'eax')
    c.emit('619dc7455c00000000'); c.jump(0x41DAA7)
    # Original ACT_CHANGE_VID is an in-place transformation, not a new life.
    # Update the guard while the old descriptor is still available; preserve
    # source/receipt/claim/generation. Do not overwrite its relocated operand.
    c.label('change_vid'); c.emit('9c60'); c.base()
    c.rr('eax', 'ebp'); c.load('edx', 'esp', 24); c.call('refresh_descriptor')
    c.emit('619dc1e811894d44'); c.jump(0x44EF35)

    # Hash table search: EAX pointer, ECX0=find/1=insert. Pointer0 is empty,
    # pointer1 tombstone. Search all collisions before reusing a tombstone.
    # EAX resultentry/0; only EAX/ECX/EDX are clobbered.
    c.label('find'); c.emit('55565751'); c.rr('esi', 'eax'); c.ri('ebp', 0)
    c.alu(7, 'esi', 1); c.jump('find_none', '86')
    c.rr('edx', 'esi'); c.shift('edx', 4, True); c.alu(4, 'edx', CAPACITY - 1); c.ri('edi', CAPACITY)
    c.label('find_loop'); c.rr('eax', 'edx'); c.shift('eax', 5); c.lea('ecx', 'ebx', table); c.emit('03c1')
    c.load('ecx', 'eax'); c.cmp('ecx', 'esi'); c.jump('find_done', '84')
    c.test('ecx'); c.jump('find_empty', '84')
    c.alu(7, 'ecx', 1); c.jump('find_next', '85')
    c.test('ebp'); c.jump('find_next', '85'); c.rr('ebp', 'eax')
    c.label('find_next'); c.alu(0, 'edx', 1); c.alu(4, 'edx', CAPACITY - 1)
    c.alu(5, 'edi', 1); c.jump('find_loop', '85')
    c.ri('eax', 0)
    c.label('find_empty'); c.load('ecx', 'esp'); c.test('ecx'); c.jump('find_none', '84')
    c.test('ebp'); c.jump('find_done', '84'); c.rr('eax', 'ebp'); c.jump('find_done')
    c.label('find_none'); c.ri('eax', 0)
    c.label('find_done'); c.emit('83c4045f5e5dc3')

    # No dereference of a query pointer until it is in our current live table.
    c.label('checked'); c.push('esi'); c.rr('esi', 'eax'); c.ri('ecx', 0); c.call('find')
    c.test('eax'); c.jump('checked_done', '84')
    c.load('ecx', 'eax', E['birth']); c.load('edx', 'esi', 0x40); c.cmp('ecx', 'edx'); c.jump('checked_bad', '85')
    c.load('ecx', 'eax', E['descriptor']); c.load('edx', 'esi', 0x44); c.cmp('ecx', 'edx'); c.jump('checked_bad', '85')
    c.load('ecx', 'eax', E['generation']); c.test('ecx'); c.jump('checked_done', '85')
    c.label('checked_bad'); c.ri('eax', 0)
    c.label('checked_done'); c.pop('esi'); c.emit('c3')

    # Resolve present controllable roots or immutable spawn inheritance. A
    # bounded physical uplink chain supports attached weapon sprites; all
    # links must themselves be tracked live objects. Army numbers never help.
    c.label('resolve'); c.emit('5657'); c.rr('esi', 'eax'); c.ri('edi', 16)
    c.label('resolve_loop'); c.rr('eax', 'esi'); c.call('checked'); c.test('eax'); c.jump('resolve_unknown', '84')
    c.push('eax'); c.load('edx', 'ebx', 0x204DDC); c.test('edx'); c.jump('resolve_saved', '84')
    c.load('ecx', 'edx'); c.lea('eax', 'ebx', 0x19B774); c.cmp('ecx', 'eax'); c.jump('resolve_saved', '85')
    for army in (0, 3):
        c.load('ecx', 'edx', 0x9C0 + army * 4); c.test('ecx'); c.jump('resolve_next' + str(army), '84')
        c.load('ecx', 'ecx', 0x100); c.cmp('ecx', 'esi'); c.jump('resolve_root' + str(army), '84')
        c.label('resolve_next' + str(army))
    c.label('resolve_saved'); c.pop('eax'); c.load('eax', 'eax', E['source'])
    c.test('eax'); c.jump('resolve_done', '84'); c.alu(7, 'eax', 3); c.jump('resolve_done', '84')
    c.load('esi', 'esi', 0x1C); c.test('esi'); c.jump('resolve_unknown', '84')
    c.alu(5, 'edi', 1); c.jump('resolve_loop', '85')
    c.label('resolve_unknown'); c.ri('eax', -1); c.jump('resolve_done')
    for army in (0, 3):
        c.label('resolve_root' + str(army)); c.alu(0, 'esp', 4); c.ri('eax', army); c.jump('resolve_done')
    c.label('resolve_done'); c.emit('5f5ec3')

    # Constructor EAX child/EDX parent. Invalidate/replace even if pointer,
    # descriptor and millisecond birthtime happen to repeat exactly.
    c.label('register'); c.emit('555657'); c.rr('esi', 'eax'); c.rr('ebp', 'edx')
    get('eax', 'fault'); c.test('eax'); c.jump('register_done', '85')
    c.rr('eax', 'esi'); c.ri('ecx', 1); c.call('find'); c.test('eax'); c.jump('capacity_fault', '84')
    c.rr('edi', 'eax'); c.load('ecx', 'edi'); c.cmp('ecx', 'esi'); c.jump('register_replace', '84')
    get('eax', 'live'); c.alu(0, 'eax', 1); put('live', 'eax'); get('ecx', 'high_water')
    c.cmp('eax', 'ecx'); c.jump('register_replace', '86'); put('high_water', 'eax')
    c.label('register_replace'); get('eax', 'generation'); c.alu(0, 'eax', 1); c.jump('generation_fault', '84')
    put('generation', 'eax'); c.store('edi', E['generation'], 'eax'); c.store('edi', E['pointer'], 'esi')
    c.load('eax', 'esi', 0x40); c.store('edi', E['birth'], 'eax')
    c.load('eax', 'esi', 0x44); c.store('edi', E['descriptor'], 'eax')
    c.imm('edi', E['source'], -1); c.imm('edi', E['killer'], -1)
    c.imm('edi', E['flags'], 0); c.imm('edi', E['reserved'], 0)
    c.rr('eax', 'ebp'); c.call('resolve'); c.store('edi', E['source'], 'eax'); c.jump('register_done')
    c.label('capacity_fault'); set_('fault', -10); c.jump('register_done')
    c.label('generation_fault'); set_('fault', -11)
    c.label('register_done'); c.emit('5f5e5dc3')

    c.label('erase'); c.ri('ecx', 0); c.call('find'); c.test('eax'); c.jump('erase_done', '84')
    c.imm('eax', E['pointer'], 1); get('eax', 'live'); c.test('eax'); c.jump('erase_done', '84')
    c.alu(5, 'eax', 1); put('live', 'eax')
    c.label('erase_done'); c.emit('c3')

    c.label('refresh_descriptor'); c.emit('5657'); c.rr('esi', 'eax'); c.rr('edi', 'edx')
    get('eax', 'fault'); c.test('eax'); c.jump('refresh_done', '85')
    c.rr('eax', 'esi'); c.call('checked'); c.test('eax'); c.jump('refresh_store', '85')
    # The other original constructor makes unregistered position dummies.
    # Only an exact native dummy -> VID conversion can introduce one here;
    # an unexplained descriptor/birth mismatch on a real sprite stays a fault.
    c.load('ecx', 'esi', 0x44); c.load('edx', 'ebx', 0x330660)
    c.cmp('ecx', 'edx'); c.jump('refresh_fault', '85')
    c.rr('eax', 'esi'); c.ri('edx', 0); c.call('register')
    c.rr('eax', 'esi'); c.call('checked'); c.test('eax'); c.jump('refresh_done', '84')
    c.label('refresh_store'); c.store('eax', E['descriptor'], 'edi'); c.jump('refresh_done')
    c.label('refresh_fault'); set_('fault', -12)
    c.label('refresh_done'); c.emit('5f5ec3')

    c.label('record_kill'); c.emit('5657'); c.rr('esi', 'eax'); c.rr('edi', 'edx')
    get('eax', 'fault'); c.test('eax'); c.jump('record_done', '85')
    c.rr('eax', 'esi'); c.call('checked'); c.test('eax'); c.jump('lifetime_fault', '84')
    c.rr('esi', 'eax'); c.load('eax', 'esi', E['flags']); c.alu(4, 'eax', 2)
    c.test('eax'); c.jump('record_done', '85')
    c.rr('eax', 'edi'); c.call('resolve'); c.store('esi', E['killer'], 'eax'); c.imm('esi', E['flags'], 1)
    # Only original Barrel_Damage VID aliases adopt the lethal source. Killing
    # an enemy cannot turn that enemy's later shots into the player's shots.
    c.load('ecx', 'esi', E['descriptor']); c.load('ecx', 'ecx', 4)
    for vid in BARREL_VIDS:
        c.alu(7, 'ecx', vid); c.jump('record_barrel', '84')
    c.jump('record_done')
    c.label('record_barrel'); c.store('esi', E['source'], 'eax'); c.jump('record_done')
    c.label('lifetime_fault'); set_('fault', -12)
    c.label('record_done'); c.emit('5f5ec3')

    code = c.finish()
    if len(code) > STATE_OFFSET: raise AssertionError('Reward code overlaps state')
    return code, dict(c.labels)


def patch(image: bytes) -> tuple[bytes, dict]:
    from old_native_campaign_command_patch import normalize_optional as normalize_commands
    _, present = normalize_commands(image)
    if not present: raise ValueError('Exact campaign command predecessor is required')
    pe, optional, table, sections = _headers(image)
    if logical_section_count(sections) != 8: raise ValueError('Rewards must immediately follow .ocmd')
    for va, before, _, _ in HOOKS:
        if image[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] != before:
            raise ValueError(f'Unknown reward hook at {va:#x}')
    sa, fa = struct.unpack_from('<II', image, optional + 32)
    if (sa, fa) != (0x1000, 0x1000): raise ValueError('Unexpected PE alignment')
    header = table + len(sections) * 40
    if header + 40 > min(s[4] for s in sections if s[3]) or image[header:header + 40] != b'\0' * 40:
        raise ValueError('No unused section header')
    raw = len(image)
    if max(s[4] + s[3] for s in sections) != raw or raw != _align(raw, fa): raise ValueError('Unexpected overlay/alignment')
    rva = _align(max(s[2] + max(s[1], s[3]) for s in sections), sa)
    if struct.unpack_from('<I', image, optional + 56)[0] != rva: raise ValueError('Unexpected SizeOfImage')
    prior_hook = image[HOOK_VA - IMAGE_BASE:HOOK_VA - IMAGE_BASE + 5]
    if prior_hook[0] != 0xE9: raise ValueError('Expected exact command predecessor branch')
    target = HOOK_VA + 5 + struct.unpack_from('<i', prior_hook, 1)[0]
    code, entries = _stub(rva, target)
    raw_size = _align(PAYLOAD_SIZE, fa); out = bytearray(image + b'\0' * raw_size)
    out[raw:raw + len(code)] = code
    for va, before, name, opcode in ((HOOK_VA, prior_hook, 'command', 0xE9),) + HOOKS:
        at = va - IMAGE_BASE
        out[at:at + len(before)] = bytes([opcode]) + struct.pack('<i', IMAGE_BASE + rva + entries[name] - va - 5) + b'\x90' * (len(before) - 5)
    struct.pack_into('<8sIIIIIIHHI', out, header, SECTION_NAME, PAYLOAD_SIZE, rva, raw_size, raw, 0, 0, 0, 0, 0xE0000020)
    struct.pack_into('<H', out, pe + 6, len(sections) + 1)
    struct.pack_into('<I', out, optional + 4, struct.unpack_from('<I', image, optional + 4)[0] + raw_size)
    struct.pack_into('<I', out, optional + 56, _align(rva + PAYLOAD_SIZE, sa))
    result_image = bytes(out)
    return result_image, {'feature': FEATURE, 'input_sha256': _sha(image), 'output_sha256': _sha(result_image),
        'section_rva': rva, 'section_raw': raw, 'section_raw_size': raw_size,
        'section_virtual_size': PAYLOAD_SIZE, 'code_size': len(code), 'state_offset': STATE_OFFSET,
        'table_offset': TABLE_OFFSET, 'capacity': CAPACITY, 'entry_size': ENTRY_SIZE,
        'entries': entries, 'commands': COMMANDS, 'errors': ERRORS, 'barrel_vids': list(BARREL_VIDS),
        'hook_vas': [HOOK_VA] + [v for v, _, _, _ in HOOKS], 'armies': [0, 3], 'maps': list(MAP_NUMBERS),
        'normal_lethal_only': True, 'world_armies_damage_rng_unchanged': True,
        'unproven_or_unsupported': ['script-controlled death', 'queen ret1', 'freeze/reducer/status death',
                                   'script-created drones without native parent', 'saved/reloaded receipts'],
        'lifetime': 'Descriptor-backed constructor; generation plus birth/descriptor; exact ChangeVID refresh; destruction tombstone; map cleanup reset',
        'source': 'Exact current Flagman0/3, inherited constructor parent, bounded16 physical uplinks; never army fallback',
        'claim': 'Once per live sprite lifetime, including nonparty/unsupported; PEEK remains nonconsuming'}


def normalize_optional(image: bytes) -> tuple[bytes, bool]:
    pe, optional, table, sections = _headers(image)
    if sections[-1][0] != SECTION_NAME:
        for va, before, _, _ in HOOKS:
            if image[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] != before:
                raise ValueError('Unknown/partial campaign reward hook')
        return image, False
    _, _, rva, raw_size, raw = sections[-1]
    if raw + raw_size != len(image) or raw != max(s[4] + s[3] for s in sections[:-1]): raise ValueError('Invalid reward extent')
    from old_native_campaign_command_patch import SECTION_NAME as COMMAND_SECTION
    if sections[-2][0] != COMMAND_SECTION: raise ValueError('Missing campaign command predecessor')
    prior = bytearray(image[:raw]); at = HOOK_VA - IMAGE_BASE
    prior[at:at + 5] = b'\xe9' + struct.pack('<i', IMAGE_BASE + sections[-2][2] - HOOK_VA - 5)
    for va, before, _, _ in HOOKS: prior[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] = before
    header = table + (len(sections) - 1) * 40; prior[header:header + 40] = b'\0' * 40
    struct.pack_into('<H', prior, pe + 6, len(sections) - 1)
    size = struct.unpack_from('<I', prior, optional + 4)[0]
    if size < raw_size: raise ValueError('Invalid code size')
    struct.pack_into('<I', prior, optional + 4, size - raw_size)
    struct.pack_into('<I', prior, optional + 56, rva)
    prior = bytes(prior)
    if patch(prior)[0] != image: raise ValueError('Reward section differs from exact guarded output')
    return prior, True
