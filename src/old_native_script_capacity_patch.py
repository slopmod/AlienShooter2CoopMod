"""Bounded OLD LGC scratch bytecode, with stable pointers and checked writes.

This is a patch for one SHA-256-verified compiler, not recovered source code.
All forward reservations/copies are checked BEFORE writing. Backpatches refer
to checked reservations. Constant folding shrinks that range. Error consumers
are stopped before reading incomplete expressions or copying the final image.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct

from old_native_campaign_command_patch import _Code

BASE = 0x400000
FEATURE = 'old-native-script-capacity-v1'
SECTION_NAME = b'.ocap\0\0\0'
CAPACITY = 1024 * 1024
OLD_CAPACITY = 256000
MESSAGE_OFFSET = 0x4000
MESSAGE = b'CoopCompiler: aborted, limit=%u, line=%u, guard=%08X\n\0'
PAYLOAD_SIZE = MESSAGE_OFFSET + len(MESSAGE)


@dataclass(frozen=True)
class Hook:
    va: int
    signature: str
    name: str
    owner: str
    width: int | str
    failure: int | str
    offset: str = 'cursor'

    @property
    def before(self): return bytes.fromhex(self.signature)


HOOKS = (
    Hook(0x43b520, '8b8168080000', 'emit_byte', 'ecx', 1, 'ret4'),
    Hook(0x43b550, '8b413c8b5140', 'emit_dword', 'ecx', 5, 'ret8'),
    Hook(0x43ce99, '8b433c803c3001', 'integer_eval', 'ebx', 0, 'int_const'),
    Hook(0x43cf3d, '8b43408b533c', 'integer_result', 'ebx', 0, 'int_const'),
    Hook(0x43d00a, '8b453c8a0c30', 'string_eval', 'ebp', 0, 0x43cfeb),
    Hook(0x43d0de, '8b5424108b4d40', 'string_result', 'ebp', 0, 0x43cfeb),
    Hook(0x43d1d1, '3b45480f8312020000', 'literal_character', 'ebp', 1, 'literal', 'ebx'),
    Hook(0x43d48f, 'c603005f43', 'literal_terminator', 'ebp', 1, 'literal', 'ebx'),
    Hook(0x43e7bf, '8b55402bd1', 'label_fixup', 'ebp', 4, 0x43edad, 'offset:ecx'),
    Hook(0x43ed81, '8b553c8b4540', 'unary_prefix', 'ebp', 1, 0x43edad),
    Hook(0x43ed9d, '8b553c8b4d40', 'unary_postfix', 'ebp', 1, 0x43edad),
    Hook(0x43f07b, '8b40148b4d0c', 'array_loop', 'ebp', 0, 0x43edad),
    Hook(0x43f0d2, '8b7d3c03f8', 'array_string', 'ebp', 'ecx', 0x43edad),
    Hook(0x43f25a, '8bc88bd1c1e902', 'constant_string', 'ebp', 'eax', 0x43edad),
    Hook(0x43f37d, '8b75402bf3', 'index_capture', 'ebp', 0, 0x43edad),
    Hook(0x43f3a8, '8bce8b753c', 'index_allocation', 'ebp', 0, 0x43edad),
    Hook(0x43f6ed, '8b7d3c8b5540', 'index_restore', 'ebp', 'eax', 'index_cleanup'),
    Hook(0x43f8ae, '8b4d3c8b5540', 'array_postfix', 'ebp', 1, 0x43edad),
    Hook(0x440243, '8b463c8b4e40', 'or_reserve', 'esi', 5, 0x44028b),
    Hook(0x440260, '8b563c8b4640', 'or_finish', 'esi', 1, 0x44028b),
    Hook(0x4402cd, '8b7e408d4f04', 'and_reserve', 'esi', 4, 0x440308),
    Hook(0x4402dd, '8b56408b463c', 'and_finish', 'esi', 1, 0x440308),
    Hook(0x440419, '8b45408bcd', 'while_reserve', 'ebp', 4, 0x440bf0),
    Hook(0x440439, '8b45408b4d3c', 'while_finish', 'ebp', 4, 0x440bf0),
    Hook(0x4404f3, '8b45408b4d3c', 'do_finish', 'ebp', 4, 0x440bf0),
    Hook(0x44058c, '8b45408b4d3c', 'for_reserve', 'ebp', 10, 0x440bf0),
    Hook(0x4405cc, '8b45408b4d3c', 'for_condition', 'ebp', 5, 0x440bf0),
    Hook(0x44060c, '8b4d408b553c', 'for_finish', 'ebp', 5, 0x440bf0),
    Hook(0x44072d, '8b0733f63bc3', 'break_table', 'ebp', 0, 0x440bf0),
    Hook(0x440808, '8b553c8b4540', 'break_reserve', 'ebp', 5, 0x440bf0),
    Hook(0x440a59, '8b45408b4d3c', 'goto_reserve', 'ebp', 5, 'goto_cleanup'),
    Hook(0x440b8a, '8b75408bbc2434020000', 'if_reserve', 'ebp', 4, 0x440bf0),
    Hook(0x440ba2, '8b55408b453c', 'if_fixup', 'ebp', 0, 0x440bf0),
    Hook(0x440bd4, '8b7540578bcd', 'else_reserve', 'ebp', 4, 0x440bf0),
    Hook(0x440be5, '8b45408b4d3c', 'else_fixup', 'ebp', 0, 0x440bf0),
    Hook(0x43db23, '3b6c24140f8dab000000', 'integer_array_error', 'esi', 0, 0x43dbe4),
    Hook(0x43e296, '3b6c24180f8d7d010000', 'string_array_error', 'esi', 0, 0x43e429),
    Hook(0x43b2f8, '8b45048b4d24', 'compile_result', 'ebp', 0, 0x43b475),
    Hook(0x43b333, '8b45403bc3', 'finalize', 'ebp', 0, 0x43b475),
    Hook(0x43b051, '83c4083bc3', 'scratch_allocation', 'ebp', 0, 0x43b475),
    Hook(0x43b3b1, '8bd883c404', 'final_allocation', 'ebp', 0, 0x43b475),
)
IMMEDIATES = ((0x43B046, OLD_CAPACITY, CAPACITY), (0x43B33F, OLD_CAPACITY, CAPACITY))


def _sha(image): return hashlib.sha256(image).hexdigest()
def _align(value): return (value + 0xfff) & ~0xfff


def _stub(rva):
    c = _Code(BASE + rva)
    saved = dict(edi=0, esi=4, ebp=8, esp=12, ebx=16, edx=20, ecx=24, eax=28)
    def original(dst, reg): c.load(dst, 'esp', saved[reg])

    for h in HOOKS:
        c.label(h.name)
        allocation = h.name in ('scratch_allocation', 'final_allocation')
        # Allocation calls leave cdecl arguments on stack. Balance them before
        # taking the same compiler cleanup path as an ordinary parse failure.
        if allocation: c.emit(h.before)
        c.emit('9c60')
        original('esi', h.owner)
        c.load('eax', 'esi', 0x868); c.test('eax'); c.jump(h.name + '_failed', '85')
        if allocation:
            original('eax', 'eax'); c.test('eax'); c.jump(h.name + '_fault', '84')
        else:
            c.load('eax', 'esi', 0x3c); c.test('eax'); c.jump(h.name + '_fault', '84')
            if h.name == 'break_table':
                original('eax', 'edi'); c.test('eax'); c.jump(h.name + '_fault', '84')
            if h.name == 'break_reserve':
                original('eax', 'esi'); c.alu(7, 'eax', 127); c.jump(h.name + '_fault', '83')
            if h.offset == 'cursor': c.load('eax', 'esi', 0x40)
            elif h.offset.startswith('offset:'): original('eax', h.offset.split(':')[1])
            else:
                original('eax', h.offset); c.load('ecx', 'esi', 0x3c)
                c.emit('2bc1'); c.jump(h.name + '_fault', '82')
            # Subtraction-based range check also rejects negative cursor/width
            # and unsigned wraparound. Equality is valid for a zero-byte check.
            c.alu(7, 'eax', CAPACITY); c.jump(h.name + '_fault', '87')
            c.ri('ecx', CAPACITY); c.emit('2bc8')
            if isinstance(h.width, int): c.ri('edx', h.width)
            else: original('edx', h.width)
            c.cmp('edx', 'ecx'); c.jump(h.name + '_fault', '87')
        c.emit('619d')
        c.label(h.name + '_replay')
        # These three overwritten conditional branches require relocation.
        if h.name == 'literal_character':
            c.emit(h.before[:3]); c.jump(0x43D3EC, '83')
        elif h.name in ('integer_array_error', 'string_array_error'):
            c.emit(h.before[:4]); c.jump(0x43DBD8 if h.name == 'integer_array_error' else 0x43E41D, '8d')
        elif not allocation: c.emit(h.before)
        c.jump(h.va + len(h.before))

        c.label(h.name + '_fault')
        c.imm('esi', 0x868, 1)
        # No C++ temporaries or exception unwinding inside a guard. Log once,
        # through the game's existing logger; preserve integer registers/flags.
        c.base(); c.load('eax', 'ebx', 0x204E18); c.test('eax')
        c.jump(h.name + '_failed', '84')
        c.pushi(h.va); c.load('edx', 'esi', 0x50); c.push('edx'); c.pushi(CAPACITY)
        c.lea('edx', 'ebx', rva + MESSAGE_OFFSET); c.push('edx'); c.push('eax')
        c.call(0x42A9F0); c.alu(0, 'esp', 20)
        c.label(h.name + '_failed'); c.emit('619d')
        if h.name == 'scratch_allocation': c.store('ebp', 0x3c, 'eax')
        if h.name == 'final_allocation': c.load('edi', 'esp', 0x18)
        if isinstance(h.failure, int): c.jump(h.failure)
        elif h.failure.startswith('ret'): c.emit('c2'); c.emit(struct.pack('<H', int(h.failure[3:])))
        elif h.failure == 'int_const': c.pop('esi'); c.jump(0x43CE73)
        elif h.failure == 'literal':
            c.pop('edi'); c.pop('esi'); c.ri('eax', 0); c.jump(0x43D49D)
        elif h.failure == 'index_cleanup':
            c.load('eax', 'esp', 0x54); c.push('eax'); c.call(0x571650)
            c.alu(0, 'esp', 4); c.jump(0x43EDAD)
        elif h.failure == 'goto_cleanup':
            c.load('eax', 'esp', 0x18)
            c.base(); c.lea('ecx', 'ebx', 0x204E38); c.cmp('eax', 'ecx')
            c.jump(0x440BF0, '84'); c.push('eax'); c.call(0x571650)
            c.alu(0, 'esp', 4); c.jump(0x440BF0)
        else: raise AssertionError(h.failure)
    code = c.finish()
    if len(code) > MESSAGE_OFFSET: raise AssertionError('Guard code overlaps message')
    return code, dict(c.labels)


def _headers(image):
    # Reuse the structural reader; exact provenance is checked below, after
    # optional diagnostics have been excluded by the required section order.
    from old_native_image_validation import _headers as read
    return read(image)


def patch(image: bytes) -> tuple[bytes, dict]:
    from old_native_image_validation import _validate_input
    pe, opt, table, sections = _headers(image)
    if any(s['name'] in (SECTION_NAME, b'.oinput\0', b'.orng\0\0\0') for s in sections):
        raise ValueError('Compiler capacity must precede diagnostics and occur once')
    _validate_input(image)
    for h in HOOKS:
        if image[h.va - BASE:h.va - BASE + len(h.before)] != h.before:
            raise ValueError(f'Unknown compiler hook: {h.name}')
    for va, before, _ in IMMEDIATES:
        if struct.unpack_from('<I', image, va - BASE)[0] != before:
            raise ValueError('Unknown compiler capacity immediate')
    if struct.unpack_from('<II', image, opt + 32) != (0x1000, 0x1000):
        raise ValueError('Unexpected PE alignment')
    header = table + len(sections) * 40
    if header + 40 > min(s['raw'] for s in sections if s['raw_size']) or any(image[header:header + 40]):
        raise ValueError('No unused PE section header')
    raw = len(image)
    if raw != _align(raw) or max(s['raw'] + s['raw_size'] for s in sections) != raw:
        raise ValueError('Unexpected executable overlay')
    rva = _align(max(s['rva'] + max(s['virtual'], s['raw_size']) for s in sections))
    if struct.unpack_from('<I', image, opt + 56)[0] != rva:
        raise ValueError('Unexpected SizeOfImage')
    # No original relocation may now land in an injected relative branch.
    from old_native_image_validation import _raw
    rel_rva, rel_size = struct.unpack_from('<II', image, opt + 96 + 5 * 8)
    at = _raw(image, rel_rva, rel_size); end = at + rel_size
    while at < end:
        page, size = struct.unpack_from('<II', image, at)
        if size < 8 or size % 2 or at + size > end: raise ValueError('Bad relocations')
        for entry in struct.unpack_from('<' + 'H' * ((size - 8) // 2), image, at + 8):
            address = BASE + page + (entry & 0xfff)
            if entry >> 12 and any(address < h.va + len(h.before) and address + 4 > h.va for h in HOOKS):
                raise ValueError('Compiler hook overlaps a relocation')
        at += size
    code, entries = _stub(rva)
    raw_size = _align(PAYLOAD_SIZE); out = bytearray(image + b'\0' * raw_size)
    out[raw:raw + len(code)] = code
    out[raw + MESSAGE_OFFSET:raw + PAYLOAD_SIZE] = MESSAGE
    for h in HOOKS:
        branch = b'\xe9' + struct.pack('<i', BASE + rva + entries[h.name] - h.va - 5)
        out[h.va - BASE:h.va - BASE + len(h.before)] = branch + b'\x90' * (len(h.before) - 5)
    for va, _, after in IMMEDIATES: struct.pack_into('<I', out, va - BASE, after)
    struct.pack_into('<8sIIIIIIHHI', out, header, SECTION_NAME, PAYLOAD_SIZE, rva, raw_size, raw, 0, 0, 0, 0, 0x60000020)
    struct.pack_into('<H', out, pe + 6, len(sections) + 1)
    struct.pack_into('<I', out, opt + 4, struct.unpack_from('<I', image, opt + 4)[0] + raw_size)
    struct.pack_into('<I', out, opt + 56, _align(rva + PAYLOAD_SIZE))
    result = bytes(out)
    return result, dict(feature=FEATURE, input_sha256=_sha(image), output_sha256=_sha(result),
                        capacity=CAPACITY, previous_capacity=OLD_CAPACITY, break_capacity=127,
                        section_rva=rva, section_raw=raw, code_size=len(code), entries=entries,
                        guards=[h.name for h in HOOKS], stable_scratch_pointer=True,
                        overflow_policy='set compile error, unwind normal local cleanup, skip final copy')


def normalize_optional(image: bytes) -> tuple[bytes, bool]:
    pe, opt, table, sections = _headers(image)
    if sections[-1]['name'] != SECTION_NAME:
        for h in HOOKS:
            if image[h.va - BASE:h.va - BASE + len(h.before)] != h.before:
                raise ValueError('Unknown or partial compiler-capacity patch')
        for va, before, _ in IMMEDIATES:
            if struct.unpack_from('<I', image, va - BASE)[0] != before:
                raise ValueError('Unknown compiler-capacity immediate')
        return image, False
    last = sections[-1]; raw, size, rva = last['raw'], last['raw_size'], last['rva']
    if raw + size != len(image) or raw != max(s['raw'] + s['raw_size'] for s in sections[:-1]):
        raise ValueError('Invalid compiler section extent')
    prior = bytearray(image[:raw])
    for h in HOOKS: prior[h.va - BASE:h.va - BASE + len(h.before)] = h.before
    for va, before, _ in IMMEDIATES: struct.pack_into('<I', prior, va - BASE, before)
    prior[last['header']:last['header'] + 40] = b'\0' * 40
    struct.pack_into('<H', prior, pe + 6, len(sections) - 1)
    code_size = struct.unpack_from('<I', prior, opt + 4)[0]
    if code_size < size: raise ValueError('Invalid code size')
    struct.pack_into('<I', prior, opt + 4, code_size - size)
    struct.pack_into('<I', prior, opt + 56, rva)
    prior = bytes(prior)
    if patch(prior)[0] != image: raise ValueError('Compiler section differs from exact guarded output')
    return prior, True
