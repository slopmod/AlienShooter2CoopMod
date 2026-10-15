"""Bounded campaign commands carried by the original lockstep input exchange.

Only the three exact gameplay call sites use 39+24 bytes. The original input
allocation receives exactly 39 bytes. Arrival merely stages a trailer; the
completed-exchange hook publishes a FIFO, and shared LGC explicitly applies
and acknowledges its head. Both peers must acknowledge before a local sender
can issue another command. This module performs no native shop transaction.
"""
from __future__ import annotations

import hashlib
import struct
from old_native_pe_sections import logical_section_count

IMAGE_BASE = 0x400000
FEATURE = 'old-native-campaign-command-v7-retry-reset'
SECTION_NAME = b'.ocmd\0\0\0'
STATE_OFFSET = 0x3000
STATE_SIZE = 0x240
PAYLOAD_SIZE = STATE_OFFSET + STATE_SIZE
MAGIC = 0xC3510500
INPUT_SIZE, TRAILER_SIZE, WIRE_SIZE = 39, 24, 63
QUEUE_CAPACITY = 4
OPCODES = {'buy': 1, 'sell_unit': 2, 'sell_all': 3, 'close': 4,
           'open_inventory': 5, 'equip': 6, 'unequip': 7, 'use': 8,
           'open_development': 9, 'increase': 10, 'move_item': 11, 'buy_at': 12}
MAX_OPCODE = max(OPCODES.values())
HOOK_VA = 0x49A1A0
HOOKS = (
    (0x42FBB0, bytes.fromhex('b80c100000'), 'send'),
    (0x42FDB0, bytes.fromhex('64a100000000'), 'receive'),
    (0x42102C, bytes.fromhex('8b455c83f802'), 'complete'),
)
COMMANDS = {'stage': 320, 'commit': 321, 'poll': 322, 'ack': 323,
            'begin_epoch': 324, 'status': 325, 'local_pending': 326,
            'fault': 327, 'local_capture': 328, 'raw_input': 329,
            'retry_reset': 354}
POLL_FIELDS = {'army': 0, 'opcode': 1, 'a': 2, 'b': 3, 'c': 4,
               'sequence': 5, 'epoch': 6, 'exchange': 7}
ERRORS = {-1: 'invalid_caller_or_party', -2: 'bad_argument_or_inactive',
          -3: 'sequence_exhausted', -4: 'epoch_not_increasing',
          -10: 'partial_exchange', -11: 'invalid_wire_header',
          -12: 'sequence_gap_or_reused_payload', -13: 'fifo_capacity',
          -14: 'invalid_ack', -15: 'unexpected_army'}
S = dict(epoch=0, fault=4, issued=8, staged=12, stage_a=16, stage_b=20,
         pending=24, pending_op=28, pending_a=32, pending_b=36, pending_c=40,
         applied0=44, applied3=48, seen0=52, seen3=56, count=60, exchange=64,
         mask=68, capture=72, peer_ack0=76, peer_ack3=80,
         queue=0x80, last0=0x100, last3=0x118, in0=0x140, in3=0x158,
         send=0x180, receive=0x1C0, raw=0x200)


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
    if struct.unpack_from('<I', image, optional + 28)[0] != IMAGE_BASE or not 5 <= count <= 9:
        raise ValueError('Command transport must follow campaign shop and precede diagnostics')
    table = optional + struct.unpack_from('<H', image, pe + 20)[0]
    if table + count * 40 > len(image): raise ValueError('Truncated section table')
    sections = [struct.unpack_from('<8sIIII', image, table + i * 40) for i in range(count)]
    if not 5 <= logical_section_count(sections) <= 8:
        raise ValueError('Command transport must follow campaign shop and precede diagnostics')
    return pe, optional, table, sections


class _Code:
    R = {'eax': 0, 'ecx': 1, 'edx': 2, 'ebx': 3, 'esp': 4, 'ebp': 5, 'esi': 6, 'edi': 7}
    def __init__(self, va):
        self.va, self.code, self.labels, self.fixups = va, bytearray(), {}, []
    def emit(self, value): self.code.extend(bytes.fromhex(value) if isinstance(value, str) else value)
    def d(self, value): self.emit(struct.pack('<I', value & 0xFFFFFFFF))
    def mem(self, reg, base, disp=0):
        reg = self.R[reg] if isinstance(reg, str) else reg
        b = self.R[base]; self.emit(bytes([0x80 | reg << 3 | b]))
        if b == 4: self.emit('24')
        self.d(disp)
    def rr(self, dst, src): self.emit(bytes([0x8B, 0xC0 | self.R[dst] << 3 | self.R[src]]))
    def ri(self, dst, value): self.emit(bytes([0xB8 + self.R[dst]])); self.d(value)
    def load(self, dst, base, disp=0): self.emit('8b'); self.mem(dst, base, disp)
    def store(self, base, disp, src): self.emit('89'); self.mem(src, base, disp)
    def imm(self, base, disp, value): self.emit('c7'); self.mem(0, base, disp); self.d(value)
    def lea(self, dst, base, disp=0): self.emit('8d'); self.mem(dst, base, disp)
    def alu(self, op, reg, value): self.emit(bytes([0x81, 0xC0 | op << 3 | self.R[reg]])); self.d(value)
    def cmp(self, a, b): self.emit(bytes([0x3B, 0xC0 | self.R[a] << 3 | self.R[b]]))
    def test(self, reg): self.emit(bytes([0x85, 0xC0 | self.R[reg] << 3 | self.R[reg]]))
    def push(self, reg): self.emit(bytes([0x50 + self.R[reg]]))
    def pop(self, reg): self.emit(bytes([0x58 + self.R[reg]]))
    def pushi(self, value): self.emit('68'); self.d(value)
    def label(self, name):
        if name in self.labels: raise AssertionError(name)
        self.labels[name] = len(self.code)
    def jump(self, target, condition=None):
        self.emit('e9' if condition is None else '0f' + condition)
        self.fixups.append((len(self.code), target)); self.d(0)
    def call(self, target): self.emit('e8'); self.fixups.append((len(self.code), target)); self.d(0)
    def base(self):
        self.emit('e8000000005b81eb'); self.d(self.va - IMAGE_BASE + len(self.code) - 3)
    def shift(self, reg, count, right=False):
        self.emit(bytes([0xC1, 0xE8 if right else 0xE0])); self.code[-1] |= self.R[reg]
        self.emit(bytes([count]))
    def finish(self):
        for at, target in self.fixups:
            dest = self.labels[target] if isinstance(target, str) else target - self.va
            struct.pack_into('<i', self.code, at, dest - at - 4)
        return bytes(self.code)


def _stub(rva, backend_target):
    c = _Code(IMAGE_BASE + rva)
    state = rva + STATE_OFFSET
    def get(reg, name, extra=0): c.load(reg, 'ebx', state + S[name] + extra)
    def put(name, reg, extra=0): c.store('ebx', state + S[name] + extra, reg)
    def set_(name, value, extra=0): c.imm('ebx', state + S[name] + extra, value)
    def ptr(reg, name, extra=0): c.lea(reg, 'ebx', state + S[name] + extra)
    def test_state(name): get('eax', name); c.test('eax')
    def copy_bytes(dst, src, count):
        # Only wrappers/internal paths use ESI/EDI; ABI saves cover both.
        ptr('edi', dst); ptr('esi', src); c.ri('ecx', count); c.emit('fcf3a4')
    def result(value): c.ri('edi', value); c.jump('command_done')

    # Chain the exact preceding campaign backend for all other commands.
    c.label('command'); c.emit('9c50'); c.load('eax', 'esp', 12)
    c.alu(7, 'eax', 354); c.jump('command_enter', '84')
    c.alu(7, 'eax', 320); c.jump('command_original', '82')
    c.alu(7, 'eax', 329); c.jump('command_original', '87')
    c.label('command_enter')
    c.emit('589d558bec535657'); c.rr('esi', 'ecx'); c.base(); c.ri('edi', -1)
    c.lea('eax', 'ebx', 0x1E5018); c.push('eax'); c.load('ecx', 'ebp', 28); c.call(0x42B420)
    # Resolve current party and local identity; saved heap pointers are not used.
    c.load('edx', 'ebx', 0x204DDC); c.test('edx'); c.jump('command_done', '84')
    c.load('eax', 'edx', 0x9C0); c.test('eax'); c.jump('command_done', '84')
    c.load('ecx', 'edx', 0x9CC); c.test('ecx'); c.jump('command_done', '84')
    c.cmp('eax', 'ecx'); c.jump('command_done', '84')
    c.load('ecx', 'ebx', 0x206428); c.test('ecx'); c.jump('command_done', '84')
    c.load('eax', 'ecx', 0x10254); c.alu(7, 'eax', 2); c.jump('command_done', '85')
    for army in range(8):
        c.load('eax', 'ecx', 0x1025C + army * 24); c.test('eax')
        c.jump('command_done', '84' if army in (0, 3) else '85')
    c.load('eax', 'ebp', 8)
    for ext in (320, 321, 326, 328, 329):
        c.alu(7, 'eax', ext); c.jump('command_local', '84')
    c.load('eax', 'edx', 0x9C0); c.alu(0, 'eax', 0x160); c.cmp('eax', 'esi')
    c.jump('command_done', '85'); c.jump('command_dispatch')
    c.label('command_local'); c.load('eax', 'edx', 0x9BC)
    c.test('eax'); c.jump('command_local0', '84')
    c.alu(7, 'eax', 3); c.jump('command_done', '85')
    c.load('eax', 'edx', 0x9CC); c.jump('command_local_compare')
    c.label('command_local0'); c.load('eax', 'edx', 0x9C0)
    c.label('command_local_compare'); c.alu(0, 'eax', 0x160); c.cmp('eax', 'esi')
    c.jump('command_done', '85')
    c.label('command_dispatch'); c.load('eax', 'ebp', 8)
    # Only the connected retry menu can discard a previous world's requests.
    # In particular a fault never grants this reset to a live campaign map.
    c.alu(7, 'eax', 354); c.jump('ext_retry_reset', '84')
    # Faults still reject all gameplay requests. A local UI may only release
    # its input capture after failure, so Escape can reach the ordinary menu.
    c.alu(7, 'eax', 327); c.jump('fault_query', '84')
    get('edi', 'fault'); c.test('edi'); c.jump('command_healthy', '84')
    c.alu(7, 'eax', 328); c.jump('command_done', '85')
    c.load('edx', 'ebp', 12); c.test('edx'); c.jump('command_done', '85')
    c.jump('ext_local_capture')
    c.label('command_healthy')
    for name, ext in COMMANDS.items():
        if ext == 327: continue
        c.alu(7, 'eax', ext); c.jump('ext_' + name, '84')
    result(-2)
    c.label('fault_query'); get('edi', 'fault'); c.jump('command_done')

    c.label('ext_retry_reset')
    c.load('edx', 'edx', 0x4c); c.test('edx'); c.jump('command_done', '84')
    for i, value in enumerate(b'maps\\old_campaign_retry.map\0'):
        c.emit('0fb6'); c.mem('eax', 'edx', i)
        if value: c.alu(1, 'eax', 32)
        c.alu(7, 'eax', value | 32 if value else 0); c.jump('command_done', '85')
    ptr('edi', 'epoch'); c.ri('ecx', STATE_SIZE // 4); c.ri('eax', 0); c.emit('fcf3ab')
    result(1)

    c.label('ext_stage'); test_state('epoch'); c.jump('argument_error', '84')
    test_state('pending'); c.jump('busy', '85'); test_state('staged'); c.jump('busy', '85')
    c.load('eax', 'ebp', 12); c.alu(7, 'eax', 1); c.jump('argument_error', '82')
    c.alu(7, 'eax', MAX_OPCODE); c.jump('argument_error', '87'); put('staged', 'eax')
    c.load('eax', 'ebp', 16); put('stage_a', 'eax'); c.load('eax', 'ebp', 20); put('stage_b', 'eax'); result(1)
    c.label('ext_commit'); test_state('epoch'); c.jump('argument_error', '84')
    test_state('pending'); c.jump('busy', '85'); test_state('staged'); c.jump('argument_error', '84')
    get('eax', 'issued'); c.alu(7, 'eax', 65535); c.jump('sequence_error', '83')
    c.alu(0, 'eax', 1); put('issued', 'eax'); put('pending', 'eax'); c.rr('edi', 'eax')
    get('eax', 'staged'); put('pending_op', 'eax'); get('eax', 'stage_a'); put('pending_a', 'eax')
    get('eax', 'stage_b'); put('pending_b', 'eax'); c.load('eax', 'ebp', 12); put('pending_c', 'eax')
    set_('staged', 0); c.jump('command_done')
    c.label('ext_poll'); test_state('count'); c.jump('empty', '84')
    c.load('eax', 'ebp', 12); c.alu(7, 'eax', 7); c.jump('argument_error', '87')
    c.shift('eax', 2); ptr('edx', 'queue'); c.emit('03d0'); c.load('edi', 'edx'); c.jump('command_done')
    c.label('ext_ack'); test_state('count'); c.jump('ack_error', '84')
    for arg, field in ((12, 20), (16, 0), (20, 24)):
        c.load('eax', 'ebp', arg); get('edx', 'queue', field); c.cmp('eax', 'edx'); c.jump('ack_error', '85')
    get('eax', 'queue'); c.test('eax'); c.jump('ack0', '84')
    get('eax', 'queue', 20); put('applied3', 'eax'); c.jump('ack_pop')
    c.label('ack0'); get('eax', 'queue', 20); put('applied0', 'eax')
    c.label('ack_pop'); get('eax', 'count'); c.alu(5, 'eax', 1); put('count', 'eax')
    # Fixed bounded memmove; unused slots zeroed to keep passive state legible.
    ptr('edi', 'queue'); ptr('esi', 'queue', 32); c.ri('ecx', (QUEUE_CAPACITY - 1) * 32); c.emit('fcf3a4')
    for at in range(0, 32, 4): set_('queue', 0, 96 + at)
    result(1)
    c.label('ext_begin_epoch'); c.load('edx', 'ebp', 12)
    c.alu(7, 'edx', 1); c.jump('argument_error', '82'); c.alu(7, 'edx', 65535); c.jump('argument_error', '87')
    get('eax', 'epoch'); c.cmp('edx', 'eax'); c.jump('begin_same', '84'); c.jump('epoch_error', '82')
    # This intentionally cancels the previous map's pending commands. It does
    # not alter the backend, items, money, player input or native network queue.
    ptr('edi', 'epoch'); c.ri('ecx', STATE_SIZE // 4); c.ri('eax', 0); c.emit('fcf3ab')
    put('epoch', 'edx')
    c.label('begin_same'); result(1)
    c.label('ext_status'); get('edi', 'epoch'); c.test('edi'); c.jump('command_done', '84'); result(1)
    c.label('ext_local_pending'); get('edi', 'pending'); c.test('edi'); c.jump('command_done', '85')
    test_state('staged'); c.jump('command_done', '84'); result(-1)
    c.label('ext_local_capture'); c.load('eax', 'ebp', 12); c.alu(7, 'eax', 1); c.jump('argument_error', '87')
    put('capture', 'eax'); result(1)
    c.label('ext_raw_input'); c.load('eax', 'ebp', 12); c.alu(7, 'eax', 73); c.jump('argument_error', '87')
    c.push('eax'); ptr('ecx', 'raw'); c.call(0x4A8480); c.rr('edi', 'eax'); c.jump('command_done')
    c.label('busy'); result(0)
    c.label('empty'); result(-1)
    c.label('argument_error'); result(-2)
    c.label('sequence_error'); set_('staged', 0); result(-3)
    c.label('epoch_error'); result(-4)
    c.label('ack_error'); set_('fault', -14); result(-14)
    c.label('command_done'); c.load('eax', 'ebp', 24); c.store('eax', 0, 'edi')
    c.ri('eax', 0); c.emit('5f5e5b5dc21800')
    c.label('command_original'); c.emit('589d'); c.jump(backend_target)

    # Gameplay send: exact return address/size/tag guards, permanent wire
    # format from the first packet, before any map script initializes epoch.
    c.label('send'); c.emit('9c60'); c.rr('ebp', 'esp'); c.base()
    c.load('eax', 'ebp', 36); c.lea('edx', 'ebx', 0x20EB0); c.cmp('eax', 'edx'); c.jump('send_original', '85')
    for offset, value in ((44, INPUT_SIZE), (48, 0)):
        c.load('eax', 'ebp', offset); c.alu(7, 'eax', value); c.jump('send_original', '85')
    set_('mask', 0)
    c.load('esi', 'ebp', 40); ptr('edi', 'raw'); c.ri('ecx', INPUT_SIZE); c.emit('fcf3a4')
    copy_bytes('send', 'raw', INPUT_SIZE)
    test_state('capture'); c.jump('send_unmasked', '84')
    # +13..26 contains all five axes, key and both action masks. Mouse
    # coordinates and native tick/RNG/flags bytes are preserved.
    for at in range(0x13, 0x27, 4): set_('send', 0, at)
    c.label('send_unmasked')
    get('eax', 'pending_op'); c.alu(1, 'eax', MAGIC); put('send', 'eax', INPUT_SIZE)
    get('eax', 'epoch'); c.shift('eax', 16); get('edx', 'pending'); c.emit('0bc2'); put('send', 'eax', INPUT_SIZE + 4)
    for name, at in (('pending_a', 8), ('pending_b', 12), ('pending_c', 16)):
        get('eax', name); put('send', 'eax', INPUT_SIZE + at)
    get('eax', 'applied3'); c.shift('eax', 16); get('edx', 'applied0'); c.emit('0bc2'); put('send', 'eax', INPUT_SIZE + 20)
    c.load('eax', 'ebp', 52); c.push('eax'); c.pushi(0); c.pushi(WIRE_SIZE); ptr('eax', 'send'); c.push('eax')
    c.load('ecx', 'ebp', 24); c.call('send_trampoline'); c.store('ebp', 28, 'eax')
    c.emit('619dc21000')
    c.label('send_original'); c.emit('619d')
    c.label('send_trampoline'); c.emit(HOOKS[0][1]); c.jump(0x42FBB5)

    c.label('receive'); c.emit('9c60'); c.rr('ebp', 'esp'); c.base()
    c.load('eax', 'ebp', 36); c.lea('edx', 'ebx', 0x20F0D); c.cmp('eax', 'edx'); c.jump('receive_guard', '84')
    c.lea('edx', 'ebx', 0x20F5C); c.cmp('eax', 'edx'); c.jump('receive_original', '85')
    c.label('receive_guard'); c.load('eax', 'ebp', 44); c.alu(7, 'eax', INPUT_SIZE); c.jump('receive_original', '85')
    c.load('eax', 'ebp', 48); c.test('eax'); c.jump('receive_party', '84')
    c.alu(7, 'eax', 3); c.jump('receive_wrong_army', '85')
    c.label('receive_party'); c.push('eax'); c.pushi(WIRE_SIZE); ptr('eax', 'receive'); c.push('eax')
    c.load('ecx', 'ebp', 24); c.call('receive_trampoline'); c.store('ebp', 28, 'eax')
    c.test('eax'); c.jump('receive_done', '85')
    c.load('edi', 'ebp', 40); ptr('esi', 'receive'); c.ri('ecx', INPUT_SIZE); c.emit('fcf3a4')
    c.load('eax', 'ebp', 48); c.test('eax'); c.jump('receive0', '84')
    ptr('edi', 'in3'); c.ri('edx', 2); c.jump('receive_stage')
    c.label('receive0'); ptr('edi', 'in0'); c.ri('edx', 1)
    c.label('receive_stage'); c.ri('ecx', TRAILER_SIZE); c.emit('fcf3a4')
    get('eax', 'mask'); c.emit('0bc2'); put('mask', 'eax'); c.jump('receive_done')
    c.label('receive_wrong_army'); set_('fault', -15); c.imm('ebp', 28, 1)
    c.label('receive_done'); c.emit('619dc20c00')
    c.label('receive_original'); c.emit('619d')
    c.label('receive_trampoline'); c.emit(HOOKS[1][1]); c.jump(0x42FDB6)

    c.label('complete'); c.emit('9c60'); c.base()
    get('eax', 'mask'); c.test('eax'); c.jump('complete_done', '84')
    set_('mask', 0); c.alu(7, 'eax', 3); c.jump('fault_partial', '85')
    test_state('fault'); c.jump('complete_done', '85')
    get('eax', 'exchange'); c.alu(0, 'eax', 1); put('exchange', 'eax')
    # Always validate protocol/version, including epoch0 startup noops.
    for army in (0, 3):
        ptr('esi', 'in' + str(army)); ptr('edi', 'last' + str(army)); c.ri('edx', army)
        c.call('accept')
        test_state('fault'); c.jump('complete_done', '85')
    for peer in (0, 3):
        get('eax', 'in' + str(peer), 4); c.shift('eax', 16, True); get('edx', 'epoch'); c.cmp('eax', 'edx')
        c.jump('ack_checked_' + str(peer), '85')
        get('eax', 'peer_ack' + str(peer)); c.rr('ecx', 'eax'); c.alu(4, 'eax', 65535)
        get('edx', 'seen0'); c.cmp('eax', 'edx'); c.jump('complete_bad_ack', '87')
        c.shift('ecx', 16, True); get('edx', 'seen3'); c.cmp('ecx', 'edx'); c.jump('complete_bad_ack', '87')
        c.label('ack_checked_' + str(peer))
    # Sender releases its slot only after both replicated peers advertise
    # applied ACK for this pending request in this epoch.
    test_state('pending'); c.jump('complete_done', '84'); c.rr('edx', 'eax')
    c.load('eax', 'ebx', 0x204DDC); c.test('eax'); c.jump('complete_done', '84')
    c.load('ecx', 'eax', 0x9BC)
    for peer in (0, 3):
        get('eax', 'in' + str(peer), 4); c.shift('eax', 16, True); get('esi', 'epoch'); c.cmp('eax', 'esi'); c.jump('complete_done', '85')
        get('eax', 'peer_ack' + str(peer)); c.test('ecx'); c.jump('ack_low_' + str(peer), '84')
        c.shift('eax', 16, True)
        c.label('ack_low_' + str(peer)); c.alu(4, 'eax', 65535); c.cmp('eax', 'edx'); c.jump('complete_done', '82')
    for name in ('pending', 'pending_op', 'pending_a', 'pending_b', 'pending_c'): set_(name, 0)
    c.jump('complete_done')
    c.label('complete_bad_ack'); set_('fault', -14); c.jump('complete_done')
    c.label('fault_partial'); set_('fault', -10)
    c.label('complete_done'); c.emit('619d'); c.emit(HOOKS[2][1]); c.jump(0x421032)

    # ESI=staged trailer, EDI=last accepted first5DWORD, EDX=army.
    # All state writes remain transport-only. Script sees no partial packet.
    c.label('accept'); c.load('eax', 'esi'); c.rr('ecx', 'eax'); c.alu(4, 'ecx', 0xFFFFFF00)
    c.alu(7, 'ecx', MAGIC); c.jump('fault_wire', '85')
    c.alu(4, 'eax', 255); c.alu(7, 'eax', MAX_OPCODE); c.jump('fault_wire', '87')
    c.load('ecx', 'esi', 4); c.shift('ecx', 16, True); get('eax', 'epoch'); c.cmp('ecx', 'eax')
    c.jump('accept_done', '85')
    c.load('eax', 'esi', 20); c.test('edx'); c.jump('accept_ack0', '84')
    put('peer_ack3', 'eax'); c.jump('accept_body')
    c.label('accept_ack0'); put('peer_ack0', 'eax')
    c.label('accept_body'); c.load('eax', 'esi'); c.alu(4, 'eax', 255)
    c.load('ecx', 'esi', 4); c.alu(4, 'ecx', 65535)
    c.test('eax'); c.jump('accept_noop', '84')
    c.test('ecx'); c.jump('fault_wire', '84'); test_state('epoch'); c.jump('fault_wire', '84')
    c.test('edx'); c.jump('accept_seen0', '84')
    get('eax', 'seen3'); c.jump('accept_sequence')
    c.label('accept_seen0'); get('eax', 'seen0')
    c.label('accept_sequence'); c.cmp('ecx', 'eax'); c.jump('accept_duplicate', '84')
    c.alu(0, 'eax', 1); c.cmp('ecx', 'eax'); c.jump('fault_sequence', '85')
    get('eax', 'count'); c.alu(7, 'eax', QUEUE_CAPACITY); c.jump('fault_capacity', '83')
    # Append in completed-exchange army0->3 order. Copy fingerprint before
    # reusing EDI as queue pointer; ACK field is deliberately excluded.
    for at in range(0, 20, 4): c.load('eax', 'esi', at); c.store('edi', at, 'eax')
    c.test('edx'); c.jump('accept_save0', '84'); put('seen3', 'ecx'); c.jump('accept_append')
    c.label('accept_save0'); put('seen0', 'ecx')
    c.label('accept_append'); get('eax', 'count'); c.shift('eax', 5); ptr('edi', 'queue'); c.emit('03f8')
    c.store('edi', 0, 'edx'); c.load('eax', 'esi'); c.alu(4, 'eax', 255); c.store('edi', 4, 'eax')
    for at in (8, 12, 16): c.load('eax', 'esi', at); c.store('edi', at, 'eax')
    c.store('edi', 20, 'ecx'); get('eax', 'epoch'); c.store('edi', 24, 'eax')
    get('eax', 'exchange'); c.store('edi', 28, 'eax'); get('eax', 'count'); c.alu(0, 'eax', 1); put('count', 'eax'); c.emit('c3')
    c.label('accept_duplicate')
    for at in range(0, 20, 4):
        c.load('eax', 'esi', at); c.load('ecx', 'edi', at); c.cmp('eax', 'ecx'); c.jump('fault_sequence', '85')
    c.emit('c3')
    c.label('accept_noop'); c.test('ecx'); c.jump('fault_wire', '85')
    for at in (8, 12, 16): c.load('eax', 'esi', at); c.test('eax'); c.jump('fault_wire', '85')
    c.label('accept_done'); c.emit('c3')
    for label, number in (('fault_wire', -11), ('fault_sequence', -12), ('fault_capacity', -13)):
        c.label(label); set_('fault', number); c.emit('c3')
    code = c.finish()
    if len(code) > STATE_OFFSET: raise AssertionError(f'Transport code overlaps state ({len(code)})')
    return code, {name: c.labels[name] for name in ('command', 'send', 'receive', 'complete', 'accept')}


def patch(image: bytes) -> tuple[bytes, dict]:
    from old_native_campaign_shop_patch import normalize_optional as normalize_shop
    _, present = normalize_shop(image)
    if not present: raise ValueError('Exact campaign shop predecessor is required')
    pe, optional, table, sections = _headers(image)
    if logical_section_count(sections) != 7: raise ValueError('Command transport must immediately follow .cshop')
    for va, before, _ in HOOKS:
        if image[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] != before:
            raise ValueError(f'Unknown command transport hook at {va:#x}')
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
    if prior_hook[0] != 0xE9: raise ValueError('Expected exact campaign backend branch')
    target = HOOK_VA + 5 + struct.unpack_from('<i', prior_hook, 1)[0]
    code, entries = _stub(rva, target)
    raw_size = _align(PAYLOAD_SIZE, fa); out = bytearray(image + b'\0' * raw_size)
    out[raw:raw + len(code)] = code
    for va, before, name in ((HOOK_VA, prior_hook, 'command'),) + HOOKS:
        at = va - IMAGE_BASE
        out[at:at + len(before)] = b'\xe9' + struct.pack('<i', IMAGE_BASE + rva + entries[name] - va - 5) + b'\x90' * (len(before) - 5)
    struct.pack_into('<8sIIIIIIHHI', out, header, SECTION_NAME, PAYLOAD_SIZE, rva, raw_size, raw, 0, 0, 0, 0, 0xE0000020)
    struct.pack_into('<H', out, pe + 6, len(sections) + 1)
    struct.pack_into('<I', out, optional + 4, struct.unpack_from('<I', image, optional + 4)[0] + raw_size)
    struct.pack_into('<I', out, optional + 56, _align(rva + PAYLOAD_SIZE, sa))
    result = bytes(out)
    return result, {'feature': FEATURE, 'input_sha256': _sha(image), 'output_sha256': _sha(result),
                    'section_rva': rva, 'section_raw': raw, 'section_raw_size': raw_size,
                    'section_virtual_size': PAYLOAD_SIZE, 'code_size': len(code), 'state_offset': STATE_OFFSET,
                    'entries': entries, 'commands': COMMANDS, 'poll_fields': POLL_FIELDS,
                    'opcodes': OPCODES, 'wire_magic': MAGIC,
                    'input_size': INPUT_SIZE, 'trailer_size': TRAILER_SIZE, 'wire_size': WIRE_SIZE,
                    'queue_capacity': QUEUE_CAPACITY, 'armies': [0, 3], 'sequence_bits': 16, 'epoch_bits': 16,
                    'hook_vas': [HOOK_VA] + [v for v, _, _ in HOOKS], 'errors': ERRORS,
                    'dispatch': 'Shared script drains FIFO after completed native input exchange; arrivals do not mutate world',
                    'backpressure': 'One pending per sender, released only by both peers applied ACKs; no wrap',
                    'capture': 'Local pre-send mask; raw getters use unchanged private input snapshot',
                    'retry_reset': '354: current army0 and exact old_campaign_retry.map only; clear prior world state before restored map launch',
                    'compatibility': 'Protocol v3; both peers require identical build from first session input packet; v1/v2 headers rejected'}


def normalize_optional(image: bytes) -> tuple[bytes, bool]:
    pe, optional, table, sections = _headers(image)
    if sections[-1][0] != SECTION_NAME:
        for va, before, _ in HOOKS:
            if image[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] != before:
                raise ValueError('Unknown/partial campaign command hook')
        return image, False
    _, _, rva, raw_size, raw = sections[-1]
    if raw + raw_size != len(image) or raw != max(s[4] + s[3] for s in sections[:-1]): raise ValueError('Invalid command section extent')
    prior = bytearray(image[:raw])
    # Exact backend entry is its section start, fixed by its own full rebuild.
    from old_native_campaign_shop_patch import SECTION_NAME as SHOP_SECTION
    if sections[-2][0] != SHOP_SECTION: raise ValueError('Missing campaign backend predecessor')
    at = HOOK_VA - IMAGE_BASE
    prior[at:at + 5] = b'\xe9' + struct.pack('<i', IMAGE_BASE + sections[-2][2] - HOOK_VA - 5)
    for va, before, _ in HOOKS: prior[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] = before
    header = table + (len(sections) - 1) * 40; prior[header:header + 40] = b'\0' * 40
    struct.pack_into('<H', prior, pe + 6, len(sections) - 1)
    size = struct.unpack_from('<I', prior, optional + 4)[0]
    if size < raw_size: raise ValueError('Invalid code size')
    struct.pack_into('<I', prior, optional + 4, size - raw_size)
    struct.pack_into('<I', prior, optional + 56, rva)
    prior = bytes(prior)
    if patch(prior)[0] != image: raise ValueError('Command transport differs from exact guarded output')
    return prior, True


SCRIPT_NAME = 'Maps/old_campaign_shop_transport.lgc'
SCRIPT = r'''// Native completed-exchange command FIFO. Local UI only enqueues.
#ifndef OLD_CAMPAIGN_SHOP_TRANSPORT_H
#define OLD_CAMPAIGN_SHOP_TRANSPORT_H 1
static int OldShopTransportError = 0;
static int OldShopTransportReportedError = 1;

@@EPOCH_FUNCTION@@

OldShopTransportReport(int error)
{
    // Write once on map initialization, then only on a changed failure. This
    // also replaces an earlier session's stale diagnostic, never every frame.
    if(error == OldShopTransportReportedError) return;
    OldShopTransportReportedError = error;
    int file = FCreate("old-network-command-state.txt");
    if(!file) return;
    FWrite(file, "AS2COMMANDSTATE1");
    FWrite(file, "map=" + GetMapName());
    FWrite(file, "time=" + itoa(GetTime()));
    FWrite(file, "epoch=" + itoa(OldShopTransportEpoch()));
    FWrite(file, "local_army=" + itoa(NetProperty(NET_N_LOCAL_PLAYER)));
    FWrite(file, "transport_error=" + itoa(error));
    FWrite(file, "transport_fault=" + itoa(SendCommandA(0, 327)));
    FWrite(file, "END");
    FClose(file);
}

OldShopQueue(int op, int a, int b, int c)
{
    int army = NetProperty(NET_N_LOCAL_PLAYER);
    int staged = SendCommandA(army, 320, op, a, b);
    if(staged != 1)
        return staged;
    return SendCommandA(army, 321, c);
}

OldShopTransportBegin(int epoch)
{
    int result = SendCommandA(0, 324, epoch);
    if(result != 1)
    {
        OldShopTransportError = result;
        OldShopTransportReport(result);
    }
    else OldShopTransportReport(0);
    return result;
}

OldShopTransportTact()
{
    // Called only after shared campaign readiness. No local UI/clock decision.
    if(OldShopTransportBegin(OldShopTransportEpoch()) != 1)
        return;
    int status = SendCommandA(0, 325);
    if(status != 1)
    {
        OldShopTransportError = status;
        OldShopTransportReport(status);
        return;
    }
    for(int i = 0; i < 4; i++)
    {
        int army = SendCommandA(0, 322, 0);
        if(army < 0)
            return;
        int op = SendCommandA(0, 322, 1);
        int a = SendCommandA(0, 322, 2);
        int b = SendCommandA(0, 322, 3);
        int c = SendCommandA(0, 322, 4);
        int seq = SendCommandA(0, 322, 5);
        int epoch = SendCommandA(0, 322, 6);
        OldCampaignShopApply(army, op, a, b, c);
        int ack = SendCommandA(0, 323, seq, army, epoch);
        if(ack != 1)
        {
            OldShopTransportError = ack;
            OldShopTransportReport(ack);
            return;
        }
    }
}
#endif
'''


def prepare_script() -> tuple[str, dict]:
    # Physical road stages reuse native level seven, but must cancel old-map
    # requests independently. Keep later epochs stable with extras disabled.
    from old_native_campaign_missions import campaign_missions
    epochs = {m.path.lower(): (index, m.native)
              for index, m in enumerate(campaign_missions(True), 1)}
    lines = ['OldShopTransportEpoch()', '{', '    string map = ToLower(GetMapName());']
    for path, (epoch, native) in epochs.items():
        script_path = path.replace('/', '\\\\')
        lines.append(f'    if(giCurLevCmpgnReal == {native} && map == "{script_path}") return {epoch};')
    lines.extend(('    return 0;', '}'))
    script = SCRIPT.replace('@@EPOCH_FUNCTION@@', '\n'.join(lines))
    return script, {'feature': FEATURE, 'output_name': SCRIPT_NAME,
                    'output_sha256': _sha(script.replace('\n', '\r\n').encode('cp1251')), 'commands': COMMANDS,
                    'opcodes': OPCODES, 'wire_magic': MAGIC,
                    'epoch_initialization': 'Shared physical-map campaign ordinal; distinct 7/7.2/7.3 epochs, stable with optional content disabled',
                    'map_epochs': {path: values[0] for path, values in epochs.items()},
                    'fault_policy': 'Reject world mutations; EXT328(0) may release local capture. EXT354 clears state only on the empty connected retry map. Report once per map and changed error.',
                    'callback': 'OldCampaignShopApply(army,op,a,b,c) must be defined before include'}
