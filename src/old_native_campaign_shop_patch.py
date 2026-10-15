"""Exact OLD Level02 campaign shop backend; synchronized caller owns scheduling.

No network, direct grants or wallet writes. EXT300 initializes a finite shared
ordinary-item catalog once. EXT304/+313/+314 call native purchase/sale.
Guarded local presentation uses EXT318/319 and EXT336/337/338; input stays off.
"""
from __future__ import annotations

import struct
from old_native_campaign_missions import MAP_NUMBERS, SHOP_NUMBERS

from old_native_shop_patch import _headers, _align, _sha, _validate_preimage
from old_native_pe_sections import logical_section_count

FEATURE = 'old-native-campaign-shop-backend-v12'
IMAGE_BASE = 0x400000
SECTION_NAME = b'.cshop\0\0'
HOOK_VA = 0x49A1A0
HOOK_BYTES = bytes.fromhex('518b442418')
STATE_OFFSET = 0x4000
NAME_OFFSET = 0x3F00
PAYLOAD_SIZE = 0x4820
MAX_CATALOG = 256
MAX_BASE_ID = 4096
MAGIC = 0x31534843
PERSONAL_MAGIC = 0x31564E49
MAP_NAME = b'maps\\level_02.map\0'
SUPPORTED = {2: 0x59D168, 3: 0x59CFFC, 4: 0x59D2DC, 6: 0x59D74C}
COMMANDS = {'init': 300, 'catalog_count': 301, 'catalog_id': 302,
            'catalog_property': 303, 'buy': 304, 'personal_init': 305, 'owned_count': 310,
            'owned_locator': 311, 'owned_property': 312,
            'sell_unit': 313, 'sell_all': 314, 'equip': 315, 'unequip': 316, 'use_medkit': 317,
            'local_inventory_view': 318, 'local_inventory_hit': 319,
            'development_property': 330, 'increase_skill': 331,
            'local_owned_info': 336, 'local_catalog_info': 337, 'local_hide_info': 338,
            'move_item': 339, 'local_inventory_cell': 340, 'can_move_item': 341,
            'buy_at': 342, 'can_buy_at': 343, 'creation_perk': 344, 'clear_menu_items': 345}
DEVELOPMENT_PROPERTIES = {'base': 0, 'effective': 1, 'unspent': 2, 'cost': 3,
                          'can_increase': 4, 'increment': 5, 'limit': 6}
PROPERTIES = {'base_id': 0, 'buy_price': 1, 'unit': 2, 'quantity': 3,
              'sell_price': 4, 'type': 5, 'class': 6, 'name_key': 7,
              'container': 8, 'sellable': 11, 'can_equip': 12, 'can_unequip': 13,
              'can_use': 14, 'equip_target': 15, 'cell_width': 16, 'cell_height': 17}
ERRORS = {-1: 'invalid_party_runtime', -2: 'not_level02', -3: 'not_initialized',
          -4: 'stale_owner_or_registry', -5: 'bad_argument_or_missing_item',
          -6: 'unsupported_item_or_property', -7: 'stale_quote_or_selection',
          -8: 'out_of_stock', -9: 'native_allocation_failed',
          -10: 'catalog_or_inventory_bound', -11: 'whole_stack_quote_mode',
          -12: 'init_requires_army0', -13: 'invalid_catalog_descriptor',
          -14: 'personal_inventory_not_initialized', -15: 'hero_not_alive_or_bound',
          -16: 'invalid_live_development_binding', -17: 'development_draft_not_empty',
          -18: 'unsupported_development_step', -19: 'unexpected_native_development_outcome',
          -24: 'unexpected_native_move_outcome'}


class _Asm:
    """Small explicit x86 encoder, every branch fixed after code generation."""
    R = {'eax': 0, 'ecx': 1, 'edx': 2, 'ebx': 3, 'esp': 4, 'ebp': 5, 'esi': 6, 'edi': 7}

    def __init__(self, va):
        self.va, self.code, self.labels, self.fixups = va, bytearray(), {}, []

    def emit(self, data):
        self.code.extend(bytes.fromhex(data) if isinstance(data, str) else data)

    def d(self, value):
        self.emit(struct.pack('<I', value & 0xFFFFFFFF))

    def mem(self, reg, base, disp=0):
        r, b = self.R[reg] if isinstance(reg, str) else reg, self.R[base]
        self.emit(bytes([0x80 | r << 3 | b]))
        if b == 4:
            self.emit(b'\x24')
        self.d(disp)

    def rr(self, dst, src):
        self.emit(bytes([0x8B, 0xC0 | self.R[dst] << 3 | self.R[src]]))

    def ri(self, dst, value):
        self.emit(bytes([0xB8 + self.R[dst]])); self.d(value)

    def load(self, dst, base, disp=0):
        self.emit('8b'); self.mem(dst, base, disp)

    def store(self, base, disp, src):
        self.emit('89'); self.mem(src, base, disp)

    def imm(self, base, disp, value):
        self.emit('c7'); self.mem(0, base, disp); self.d(value)

    def lea(self, dst, base, disp=0):
        self.emit('8d'); self.mem(dst, base, disp)

    def alu(self, operation, dst, value):
        self.emit('81'); self.emit(bytes([0xC0 | operation << 3 | self.R[dst]])); self.d(value)

    def cmp(self, a, b):
        self.emit(bytes([0x3B, 0xC0 | self.R[a] << 3 | self.R[b]]))

    def test(self, reg):
        self.emit(bytes([0x85, 0xC0 | self.R[reg] << 3 | self.R[reg]]))

    def push(self, reg): self.emit(bytes([0x50 + self.R[reg]]))
    def pop(self, reg): self.emit(bytes([0x58 + self.R[reg]]))
    def pushi(self, value): self.emit('68'); self.d(value)
    def label(self, name):
        if name in self.labels: raise AssertionError(name)
        self.labels[name] = len(self.code)

    def jump(self, name, condition=None):
        self.emit('e9' if condition is None else '0f' + condition)
        self.fixups.append((len(self.code), name)); self.d(0)

    def call(self, target):
        self.emit('e8'); self.fixups.append((len(self.code), target)); self.d(0)

    def virtual(self, obj, slot):
        self.rr('ecx', obj); self.load('eax', obj)
        self.emit('ff'); self.mem(2, 'eax', slot)

    def finish(self):
        for at, target in self.fixups:
            dest = self.labels[target] if isinstance(target, str) else target - self.va
            struct.pack_into('<i', self.code, at, dest - at - 4)
        return bytes(self.code)


def _stub(rva):
    c = _Asm(IMAGE_BASE + rva)
    # Locals are shared with our leaf helpers, which preserve EBX/EBP/EDI/ESI.
    L = {name: -16 - i * 4 for i, name in enumerate((
        'result', 'game', 'owner', 'registry', 'inventory', 'state', 'item',
        'entry', 'unit', 'price', 'temp', 'out', 'id', 'count', 'remaining',
        'ci', 'container', 'index', 'row', 'locator', 'x', 'y', 'nx', 'ny',
        'columns', 'vector', 'end', 'owner0', 'owner3', 'stock', 'result_type',
        'map_number', 'target_ci', 'target_container', 'old_quantity', 'player', 'pd',
        'skill', 'old_base', 'old_points', 'step', 'destination', 'dest_ci',
        'dest_x', 'dest_y', 'source_x', 'source_y', 'move_w', 'move_h', 'move_column',
        'other', 'other_x', 'other_y', 'other_w', 'other_h', 'other_quantity',
        'buy_mode', 'merge_room'))}
    def get(reg, name): c.load(reg, 'ebp', L[name])
    def put(name, reg): c.store('ebp', L[name], reg)
    def setl(name, value): c.imm('ebp', L[name], value)
    def arg(reg, n): c.load(reg, 'ebp', 12 + n * 4)
    def err(number, cond=None): c.jump('error' + str(-number), cond)
    def cmpi(reg, value): c.alu(7, reg, value)
    def result(reg='eax'): put('result', reg); c.jump('done')
    def vc(obj, slot): c.virtual(obj, slot)
    def guard_vt(obj, preferred, error=-1):
        c.lea('edx', 'ebx', preferred - IMAGE_BASE); c.load('eax', obj)
        c.cmp('eax', 'edx'); err(error, '85')

    c.emit('9c817c24082c010000'); c.jump('original', '82')
    c.emit('817c24083f010000'); c.jump('ours', '86')
    # The transport owns320..329 and chains through this dispatcher.
    c.emit('817c24084a010000'); c.jump('original', '82')
    c.emit('817c24084b010000'); c.jump('ours', '86')
    # 332..335 belong to reward provenance; never intercept them here.
    c.emit('817c240850010000'); c.jump('original', '82')
    c.emit('817c240859010000'); c.jump('original', '87')
    c.label('ours')
    c.emit('9d558bec53565781ec40010000')
    c.rr('esi', 'ecx'); setl('result', -1); setl('temp', 0); setl('out', 0); setl('result_type', 0)
    c.call('pic'); c.label('pic'); c.pop('ebx'); c.alu(5, 'ebx', rva + len(c.code) - 1)
    c.lea('eax', 'ebx', 0x5E5018 - IMAGE_BASE); c.push('eax')
    c.load('ecx', 'ebp', 28); c.call(0x42B420)
    c.load('edi', 'ebx', 0x604DDC - IMAGE_BASE); c.test('edi'); err(-1, '84')
    guard_vt('edi', 0x59B774); put('game', 'edi')
    c.lea('edx', 'esi', -0x160); put('player', 'edx'); c.load('eax', 'edi', 0x9C0); c.cmp('eax', 'edx')
    c.jump('party', '84'); c.load('eax', 'edi', 0x9CC); c.cmp('eax', 'edx'); err(-1, '85')
    c.label('party')
    # Original EXT199 changes the perk of EVERY preset in the RPG registry.
    # Creation needs the same native operation on this player's descriptor only.
    c.load('eax', 'ebp', 8); cmpi('eax', 344); c.jump('creation_perk', '84')
    cmpi('eax', 345); c.jump('clear_menu_items', '84')
    c.load('edi', 'esi', 0x34); c.test('edi'); err(-1, '84')
    guard_vt('edi', 0x59CEB4); put('owner', 'edi')
    c.load('edi', 'edi', 0x1A8); c.test('edi'); err(-1, '84')
    guard_vt('edi', 0x59C258); put('inventory', 'edi')
    c.load('eax', 'edi', 0x18); get('edx', 'owner'); c.cmp('eax', 'edx'); err(-4, '85')
    get('eax', 'game'); c.load('eax', 'eax', 0x3C); c.alu(4, 'eax', 0x80); err(-2, '85')
    get('eax', 'game'); c.load('esi', 'eax', 0x4C); c.test('esi'); err(-2, '84')
    from old_native_campaign_missions import emit_native_map_guard
    emit_native_map_guard(c, 'esi', lambda condition: err(-2, condition))
    put('map_number', 'eax')
    c.load('esi', 'ebx', 0x73A488 - IMAGE_BASE); c.test('esi'); err(-1, '84')
    guard_vt('esi', 0x59BD18); put('registry', 'esi')
    c.emit('0fb6'); c.mem('eax', 'ebx', 0x7306B5 - IMAGE_BASE)
    c.test('eax'); err(-11, '85')
    c.lea('edi', 'ebx', rva + STATE_OFFSET); put('state', 'edi')
    for off, name in ((0x9C0, 'owner0'), (0x9CC, 'owner3')):
        get('eax', 'game'); c.load('eax', 'eax', off); c.test('eax'); err(-1, '84')
        c.load('esi', 'eax', 0x194); c.test('esi'); err(-1, '84')
        guard_vt('esi', 0x59CEB4); put(name, 'esi')
    c.load('eax', 'ebp', 8); cmpi('eax', 305); c.jump('personal_init', '84')
    # Personal inventory is usable before any shop catalog exists. Trade and
    # catalog commands retain the explicit mission allowlist and stock guards.
    for command in (310, 311, 312, 315, 316, 317, 318, 319, 330, 331, 336, 338, 339, 340, 341):
        cmpi('eax', command); c.jump('personal_active', '84')
    get('eax', 'map_number')
    for number in SHOP_NUMBERS:
        cmpi('eax', number); c.jump('trade_map', '84')
    err(-2)
    c.label('trade_map')
    c.load('eax', 'ebp', 8); cmpi('eax', 300); c.jump('init', '84')
    c.label('active'); c.load('eax', 'edi', 4); cmpi('eax', MAGIC); err(-3, '85')
    c.load('eax', 'edi', 24); get('edx', 'map_number'); c.cmp('eax', 'edx'); err(-3, '85')
    c.jump('identity_active')
    c.label('personal_active'); c.load('eax', 'edi', 20); cmpi('eax', PERSONAL_MAGIC); err(-14, '85')
    c.label('identity_active')
    for off, name in ((8, 'owner0'), (12, 'owner3'), (16, 'registry')):
        c.load('eax', 'edi', off); get('edx', name); c.cmp('eax', 'edx'); err(-4, '85')
    c.load('eax', 'edi'); cmpi('eax', MAX_CATALOG); err(-10, '87')
    for command, label in ((301, 'catalog_count'), (302, 'catalog_id'),
                           (303, 'catalog_get'), (304, 'catalog_get'),
                           (310, 'owned_enumerate'), (311, 'owned_enumerate'),
                           (312, 'owned_resolve'), (313, 'owned_resolve'), (314, 'owned_resolve'),
                           (315, 'owned_resolve'), (316, 'owned_resolve'), (317, 'owned_resolve'),
                           (318, 'local_view'), (319, 'local_view'),
                           (330, 'development'), (331, 'development'),
                           (336, 'owned_resolve'), (337, 'catalog_get'), (338, 'hide_info'),
                           (339, 'owned_resolve'), (340, 'local_view'), (341, 'owned_resolve'),
                           (342, 'catalog_get'), (343, 'catalog_get')):
        c.load('eax', 'ebp', 8); cmpi('eax', command); c.jump(label, '84')
    err(-5)

    c.label('creation_perk')
    get('eax', 'game'); c.load('edi', 'eax', 0x4C); c.test('edi'); err(-2, '84')
    for i, char in enumerate(b'maps\\old_campaign_lobby.map\0'):
        c.emit('0fb6'); c.mem('eax', 'edi', i)
        if char: c.alu(1, 'eax', 0x20)
        cmpi('eax', char | 0x20 if char else 0); err(-2, '85')
    arg('eax', 0); cmpi('eax', 22); err(-5, '82'); cmpi('eax', 32); err(-5, '87')
    # This is precisely EXT24's current-descriptor/interface-9 lookup.
    get('ecx', 'player'); c.alu(0, 'ecx', 0x160); c.call(0x49BA00)
    c.test('eax'); err(-1, '84'); c.rr('edi', 'eax')
    c.pushi(9); vc('edi', 0); c.test('eax'); err(-1, '84'); c.rr('edi', 'eax')
    c.load('eax', 'edi'); c.load('eax', 'eax', 0x40)
    c.lea('edx', 'ebx', 0x472280 - IMAGE_BASE); c.cmp('eax', 'edx'); err(-4, '85')
    arg('eax', 0); c.push('eax'); vc('edi', 0x40)
    c.jump('success')

    c.label('clear_menu_items')
    get('eax', 'game'); c.load('edi', 'eax', 0x4C); c.test('edi'); err(-2, '84')
    for index, name in enumerate((b'maps\\mainmenu.map\0',
                                 b'maps\\old_campaign_lobby.map\0',
                                 b'maps\\old_campaign_retry.map\0')):
        next_label = 'clear_menu_next_' + str(index)
        # Group the ASCII path into dwords to keep the bounded backend below
        # its inventory-query island. The terminating NUL is still exact.
        full=(len(name)-1)//4*4
        for i in range(0,full,4):
            c.load('eax','edi',i);c.alu(1,'eax',0x20202020)
            cmpi('eax',int.from_bytes(name[i:i+4],'little')|0x20202020)
            c.jump(next_label,'85')
        for i in range(full,len(name)):
            char=name[i]
            c.emit('0fb6'); c.mem('eax', 'edi', i)
            if char: c.alu(1, 'eax', 0x20)
            cmpi('eax', char | 0x20 if char else 0); c.jump(next_label, '85')
        c.jump('clear_menu_allowed'); c.label(next_label)
    err(-2)
    c.label('clear_menu_allowed')
    # Native parameter-dialog item windows are separately owned, outside .men.
    # Use their original release method, preserving the RPG descriptor itself.
    c.load('edi', 'ebx', 0x73A49C - IMAGE_BASE); c.test('edi'); c.jump('clear_menu_inventory', '84')
    guard_vt('edi', 0x59C4D4, -4); vc('edi', 0x0C)
    c.label('clear_menu_inventory')
    c.load('esi', 'ebx', 0x73A498 - IMAGE_BASE); c.test('esi'); c.jump('success', '84')
    guard_vt('esi', 0x59C3F8, -4)
    c.pushi(0); c.lea('ecx', 'esi', 4); c.call(0x47E990)
    c.pushi(0); c.lea('ecx', 'esi', 4); c.call(0x47EA40)
    c.jump('success')

    # Presentation only, restricted to this process's native local owner.
    # Never use EXT0 (which also enables native input) or inventory.v68 (which
    # starts dragging an item). Native 4778C0 only computes a container hit;
    # restore even its transient hover fields before returning a stable locator.
    c.label('local_view')
    c.call('local_ui_guard')
    c.load('eax', 'ebp', 8); cmpi('eax', 319); c.jump('view_hit', '84')
    cmpi('eax', 340); c.jump('view_hit', '84')
    arg('eax', 0); cmpi('eax', 2); err(-5, '87')
    c.jump('view_refresh', '84')
    # An existing popup must not survive closing. Reopening also updates its
    # owner and size after a map or display-mode change, just like stock UI.
    c.load('edi', 'esi', 0x1AC); c.test('edi'); c.jump('view_popup_ready', '84')
    guard_vt('edi', 0x59C634, -4)
    c.pushi(0); c.pushi(0); c.rr('ecx', 'esi'); c.call(0x47DEE0)
    c.label('view_popup_ready'); arg('eax', 0)
    c.push('eax'); c.lea('ecx', 'esi', 4); c.call(0x47E990)
    c.pushi(0); c.lea('ecx', 'esi', 4); c.call(0x47EA40)
    c.ri('eax', 1); result()

    # 318(2): refresh the existing local grid without toggling visibility or
    # enabling native drag input. 47E990(1) is a no-op when already visible.
    # The original show routine rebuilds cached item sprites via 47E090(0).
    c.label('view_refresh')
    c.emit('0fb6'); c.mem('eax', 'esi', 8); c.test('eax'); err(-5, '84')
    c.pushi(0); c.rr('ecx', 'esi'); c.call(0x47E090)
    c.rr('ecx', 'esi'); c.call(0x47E200)
    c.ri('eax', 1); result()

    c.label('local_ui_guard')
    get('eax', 'game'); c.load('edx', 'eax', 0x9BC)
    cmpi('edx', 3); err(-1, '87'); c.emit('8b8490c0090000')
    get('edx', 'player'); c.cmp('eax', 'edx'); err(-4, '85')
    c.load('esi', 'ebx', 0x73A498 - IMAGE_BASE); c.test('esi'); err(-4, '84')
    guard_vt('esi', 0x59C3F8, -4)
    c.load('eax', 'esi', 0x1C0); get('edx', 'owner'); c.cmp('eax', 'edx'); err(-4, '85')
    c.load('eax', 'esi', 0x1BC); get('edx', 'inventory'); c.cmp('eax', 'edx'); err(-4, '85')
    c.load('eax', 'edx', 0xE0); c.test('eax'); err(-5, '85')
    c.emit('c3')

    # Reuse the inventory's native floating item-info window. Its initializer
    # binds owner+4, fonts, maximum size and stock art without entering input.
    # The item argument is the actual owned object (336) or catalog template
    # (337); no cloning, RNG, inventory insertion, purchase or item setter.
    c.label('show_info'); c.call('local_ui_guard')
    c.emit('0fb6'); c.mem('eax', 'esi', 8); c.test('eax'); err(-5, '84')
    for n in (1, 2):
        arg('eax', n); cmpi('eax', 0); err(-5, '8c'); cmpi('eax', 16384); err(-5, '8f')
    c.load('edi', 'esi', 0x1AC); c.test('edi'); c.jump('info_initialized', '85')
    c.pushi(0); c.pushi(0); c.rr('ecx', 'esi'); c.call(0x47DEE0)
    c.load('edi', 'esi', 0x1AC)
    c.label('info_initialized'); c.test('edi'); err(-4, '84'); guard_vt('edi', 0x59C634, -4)
    # Hero.v0(1) in the stock initializer returns this exact guarded hero's
    # +4 requirements interface. Refresh it even when the popup already exists.
    get('eax', 'owner'); c.alu(0, 'eax', 4); c.push('eax'); vc('edi', 0x24)
    for n in (2, 1):
        c.emit('db'); c.mem(0, 'ebp', 12 + n * 4)
        c.alu(5, 'esp', 4); c.emit('d91c24')
    vc('edi', 0x0C)
    c.pushi(0); c.pushi(1); get('eax', 'item'); c.push('eax'); vc('edi', 0x18)
    # Refresh dynamic ammo/condition/requirements for the same selected object.
    vc('edi', 0x2C)
    c.ri('eax', 1); result()
    c.label('hide_info'); c.call('local_ui_guard')
    c.load('edi', 'esi', 0x1AC); c.test('edi'); c.jump('info_hidden', '84')
    guard_vt('edi', 0x59C634, -4)
    c.pushi(0); c.pushi(0); c.pushi(0); vc('edi', 0x18)
    c.label('info_hidden'); c.ri('eax', 1); result()
    c.label('view_hit')
    c.emit('0fb6'); c.mem('eax', 'esi', 8); c.test('eax'); err(-5, '84')
    for n in (0, 1):
        arg('eax', n); cmpi('eax', 0); err(-5, '8c'); cmpi('eax', 16384); err(-5, '8f')
    setl('index', 0)
    c.label('hit_next')
    get('eax', 'index'); cmpi('eax', 19); err(-5, '83')
    get('edx', 'inventory'); c.emit('8b74827c'); c.test('esi'); c.jump('hit_advance', '84')
    # Presentation grids use the base native container, including equipment.
    guard_vt('esi', 0x59BF78, -10)
    c.emit('0fb6'); c.mem('eax', 'esi', 0x99); c.test('eax'); c.jump('hit_advance', '84')
    c.load('eax', 'esi', 0x64); c.push('eax')
    c.load('eax', 'esi', 0x68); c.push('eax')
    c.load('eax', 'esi', 0x6C); c.push('eax')
    c.load('eax', 'ebp', 8); cmpi('eax', 340); c.jump('hit_cell', '84')
    # Convert integer screen coordinates to the original float ABI, y then x.
    for n in (1, 0):
        c.emit('db'); c.mem(0, 'ebp', 12 + n * 4)
        c.alu(5, 'esp', 4); c.emit('d91c24')
    c.rr('ecx', 'esi'); c.call(0x4778C0); put('out', 'eax'); c.jump('hit_restore')
    # Empty-cell hit: use the same screen->grid conversion as 4778C0, but
    # retain 4771E0's success flag instead of requiring an existing item.
    c.label('hit_cell'); c.pushi(0); c.pushi(0)
    for n, origin, scroll in ((1, 0x90, 0x74), (0, 0x8C, 0x70)):
        c.emit('db'); c.mem(0, 'ebp', 12+n*4)
        c.emit('d8'); c.mem(4, 'esi', origin)
        c.emit('d8'); c.mem(0, 'esi', scroll)
        c.call(0x57EAC8); c.push('eax')
    c.pushi(0); c.rr('ecx', 'esi'); c.call(0x4771E0)
    c.alu(4, 'eax', 255); put('out', 'eax')
    c.load('eax', 'esi', 0x68); c.emit('c1e006'); c.load('edx', 'esi', 0x6C); c.emit('03c2')
    get('edx', 'index'); c.emit('c1e210'); c.emit('03c2'); put('locator', 'eax')
    c.label('hit_restore')
    for offset in (0x6C, 0x68, 0x64):
        c.pop('edx'); c.store('esi', offset, 'edx')
    get('eax', 'out'); c.test('eax'); c.jump('hit_advance', '84')
    c.load('eax', 'ebp', 8); cmpi('eax', 340); c.jump('hit_cell_result', '84')
    c.jump('owned_enumerate')
    c.label('hit_cell_result'); get('eax', 'locator'); result()
    c.label('hit_advance'); get('eax', 'index'); c.alu(0, 'eax', 1); put('index', 'eax'); c.jump('hit_next')

    c.label('personal_init'); get('eax', 'owner'); get('edx', 'owner0'); c.cmp('eax', 'edx'); err(-12, '85')
    c.call('bind_personal'); c.ri('eax', 1); result()

    c.label('init'); get('eax', 'owner'); get('edx', 'owner0'); c.cmp('eax', 'edx'); err(-12, '85')
    c.call('bind_personal'); get('edi', 'state')
    # A different mission gets its own catalog once. Reopening on the same
    # mission retains finite stock. Personal identities remain unchanged.
    c.load('eax', 'edi', 24); get('edx', 'map_number'); c.cmp('eax', 'edx')
    c.jump('catalog_same_map', '84'); c.imm('edi', 4, 0)
    c.label('catalog_same_map')
    c.load('eax', 'edi', 4); cmpi('eax', MAGIC); c.jump('init_existing', '84')
    c.imm('edi', 0, 0); setl('id', 1)
    c.label('init_loop'); get('eax', 'id'); cmpi('eax', MAX_BASE_ID); c.jump('init_done', '87')
    c.push('eax'); get('ecx', 'registry'); vc('ecx', 0x3C)
    c.rr('esi', 'eax'); c.test('esi'); c.jump('init_next', '84')
    c.load('eax', 'esi', 0x1C); c.test('eax'); c.jump('init_next', '85')
    c.call('supported'); c.test('eax'); c.jump('init_next', '84')
    c.load('eax', 'esi', 0x34); c.test('eax'); c.jump('init_next', '8e')
    # Exact supported item classes all expose these non-mutating getters.
    c.load('eax', 'esi', 0x48); cmpi('eax', 1); err(-13, '8c'); cmpi('eax', 100000); err(-13, '8f')
    c.load('eax', 'esi', 0x44); cmpi('eax', 1); err(-13, '8c'); cmpi('eax', 100000); err(-13, '8f')
    vc('esi', 0xC4); get('edx', 'map_number'); c.cmp('eax', 'edx'); c.jump('init_next', '8f')
    vc('esi', 0xD0); c.alu(4, 'eax', 255); c.test('eax'); c.jump('init_next', '85')
    vc('esi', 0x108); c.test('eax'); c.jump('init_next', '8e')
    c.load('eax', 'esi', 0x14); cmpi('eax', 3); c.jump('ammo_stock', '84')
    get('eax', 'map_number'); c.push('eax'); vc('esi', 0x120); c.jump('stock_count')
    c.label('ammo_stock'); c.load('ecx', 'esi', 0x54)
    cmpi('ecx', 0); err(-13, '8c'); cmpi('ecx', 64); err(-13, '8f')
    c.ri('eax', 0); c.test('ecx'); c.jump('ammo_min', '84')
    get('eax', 'id'); get('edx', 'map_number'); c.emit('03c2'); c.ri('edx', 0); c.emit('f7f1'); c.rr('eax', 'edx')
    c.label('ammo_min'); c.load('ecx', 'esi', 0x50)
    cmpi('ecx', 0); err(-13, '8c'); cmpi('ecx', 64); err(-13, '8f'); c.emit('03c1')
    c.label('stock_count'); cmpi('eax', 0); err(-13, '8c'); cmpi('eax', 128); err(-13, '8f')
    c.load('edx', 'esi', 0x44); c.emit('0fafc2'); put('stock', 'eax')
    get('edi', 'state'); c.load('eax', 'edi'); cmpi('eax', MAX_CATALOG); err(-10, '83')
    c.emit('c1e003'); c.emit('03f8'); c.alu(0, 'edi', 32)
    get('eax', 'id'); c.store('edi', 0, 'eax'); get('eax', 'stock'); c.store('edi', 4, 'eax')
    get('edi', 'state'); c.load('eax', 'edi'); c.alu(0, 'eax', 1); c.store('edi', 0, 'eax')
    c.label('init_next'); get('eax', 'id'); c.alu(0, 'eax', 1); put('id', 'eax'); c.jump('init_loop')
    c.label('init_done'); get('edi', 'state')
    for off, name in ((8, 'owner0'), (12, 'owner3'), (16, 'registry')):
        get('eax', name); c.store('edi', off, 'eax')
    c.imm('edi', 4, MAGIC)
    get('eax', 'map_number'); c.store('edi', 24, 'eax')
    c.label('init_existing')
    for off, name in ((8, 'owner0'), (12, 'owner3'), (16, 'registry')):
        c.load('eax', 'edi', off); get('edx', name); c.cmp('eax', 'edx'); err(-4, '85')
    c.label('catalog_count'); c.load('eax', 'edi'); result()
    c.label('catalog_id'); arg('eax', 0); c.load('edx', 'edi'); c.cmp('eax', 'edx'); err(-5, '83')
    c.emit('c1e00303f8'); c.load('eax', 'edi', 32); result()
    c.label('catalog_get'); arg('eax', 0)
    c.load('edx', 'ebp', 8); cmpi('edx', 342); c.jump('catalog_plain_id', '82')
    cmpi('eax', 0x7FFFFFFF); err(-7, '87'); c.alu(4, 'eax', 8191)
    c.label('catalog_plain_id'); put('id', 'eax'); c.load('ecx', 'edi'); c.alu(0, 'edi', 32)
    c.label('find_entry'); c.test('ecx'); err(-5, '84'); c.load('edx', 'edi'); c.cmp('eax', 'edx')
    c.jump('found_entry', '84'); c.alu(0, 'edi', 8); c.alu(5, 'ecx', 1); c.jump('find_entry')
    c.label('found_entry'); put('entry', 'edi'); c.push('eax'); get('ecx', 'registry'); vc('ecx', 0x3C)
    c.rr('esi', 'eax'); c.test('esi'); err(-5, '84'); put('item', 'esi')
    c.call('supported'); c.test('eax'); err(-6, '84')
    c.load('eax', 'esi', 0x1C); c.test('eax'); err(-6, '85')
    c.load('eax', 'ebp', 8); cmpi('eax', 304); c.jump('buy', '84')
    cmpi('eax', 337); c.jump('show_info', '84')
    cmpi('eax', 342); c.jump('buy_at', '83')
    c.jump('property')

    # Enumerate backpack by its canonical top-left cell, then containers1..18.
    c.label('owned_enumerate'); setl('ci', 0); setl('row', 0); setl('index', 0)
    c.label('enumerate_container'); get('eax', 'ci'); cmpi('eax', 19); c.jump('enumerate_done', '83')
    get('edx', 'inventory'); c.emit('8b748224'); put('container', 'esi')
    c.test('esi'); err(-10, '84'); c.call('container_guard')
    setl('index', 0); get('eax', 'ci'); c.test('eax'); c.jump('enumerate_vector', '85')
    c.call('grid_setup'); setl('x', 0); setl('y', 0)
    c.label('enumerate_grid'); get('eax', 'x'); get('edx', 'nx'); c.cmp('eax', 'edx'); c.jump('enumerate_next_container', '83')
    get('eax', 'x'); c.emit('c1e006'); get('edx', 'y'); c.emit('03c2'); put('locator', 'eax')
    c.call('grid_item'); c.test('eax'); c.jump('grid_next', '84')
    c.rr('esi', 'eax'); c.call('emit_owned');
    c.label('grid_next'); get('eax', 'y'); c.alu(0, 'eax', 1); put('y', 'eax'); get('edx', 'ny'); c.cmp('eax', 'edx')
    c.jump('enumerate_grid', '82'); setl('y', 0); get('eax', 'x'); c.alu(0, 'eax', 1); put('x', 'eax'); c.jump('enumerate_grid')
    c.label('enumerate_vector'); get('eax', 'index'); get('edx', 'count'); c.cmp('eax', 'edx'); c.jump('enumerate_next_container', '83')
    get('edx', 'vector'); c.emit('8b3482'); c.test('esi'); err(-10, '84')
    get('eax', 'ci'); c.emit('c1e010'); get('edx', 'index'); c.emit('03c2'); put('locator', 'eax'); c.call('emit_owned')
    get('eax', 'index'); c.alu(0, 'eax', 1); put('index', 'eax'); c.jump('enumerate_vector')
    c.label('enumerate_next_container'); get('eax', 'ci'); c.alu(0, 'eax', 1); put('ci', 'eax'); c.jump('enumerate_container')
    c.label('enumerate_done'); c.load('eax', 'ebp', 8); cmpi('eax', 310); err(-5, '85'); get('eax', 'row'); result()

    c.label('owned_resolve'); arg('eax', 0); put('locator', 'eax'); c.emit('c1e810'); put('ci', 'eax')
    cmpi('eax', 19); err(-5, '83'); get('edx', 'inventory'); c.emit('8b748224'); put('container', 'esi')
    c.test('esi'); err(-10, '84'); c.call('container_guard'); get('eax', 'ci'); c.test('eax'); c.jump('resolve_vector', '85')
    c.call('grid_setup'); get('eax', 'locator'); cmpi('eax', 4096); err(-5, '83')
    c.rr('edx', 'eax'); c.emit('c1e806'); put('x', 'eax'); c.alu(4, 'edx', 63); put('y', 'edx')
    get('edx', 'nx'); c.cmp('eax', 'edx'); err(-5, '83'); get('eax', 'y'); get('edx', 'ny'); c.cmp('eax', 'edx'); err(-5, '83')
    c.call('grid_item'); c.rr('esi', 'eax'); c.jump('resolved')
    c.label('resolve_vector'); get('eax', 'locator'); c.alu(4, 'eax', 65535); get('edx', 'count'); c.cmp('eax', 'edx'); err(-5, '83')
    get('edx', 'vector'); c.emit('8b3482')
    c.label('resolved'); c.test('esi'); err(-5, '84'); c.call('owned_guard'); put('item', 'esi')
    c.load('eax', 'ebp', 8); cmpi('eax', 312); c.jump('property', '84')
    cmpi('eax', 336); c.jump('show_info', '84')
    cmpi('eax', 339); c.jump('move_item', '84')
    cmpi('eax', 341); c.jump('move_item', '84')
    cmpi('eax', 315); c.jump('personal_mutation', '83'); c.jump('sell')

    c.label('property'); arg('eax', 1)
    for prop, label in ((0, 'prop_base'), (1, 'prop_buy'), (2, 'prop_unit'), (3, 'prop_quantity'),
                        (4, 'prop_sell'), (5, 'prop_type'), (6, 'prop_class'), (7, 'prop_name'),
                        (8, 'prop_container'), (11, 'prop_sellable'),
                        (12, 'prop_equip'), (13, 'prop_unequip'), (14, 'prop_use'), (15, 'prop_target'),
                        (16, 'prop_width'), (17, 'prop_height')):
        cmpi('eax', prop); c.jump(label, '84')
    err(-6)
    for label, slot in (('prop_base', 0x0C), ('prop_buy', 0x108), ('prop_unit', 0x104),
                        ('prop_sell', 0x10C), ('prop_type', 0x28), ('prop_class', 0x2C)):
        c.label(label); vc('esi', slot); result()
    c.label('prop_quantity'); c.load('eax', 'ebp', 8); cmpi('eax', 303); c.jump('prop_stock', '84')
    c.load('eax', 'esi', 0x40); result()
    c.label('prop_stock'); get('eax', 'entry'); c.load('eax', 'eax', 4); result()
    # Original Size parser 478B9A..478BA8 stores the integer cell dimensions.
    for label, offset in (('prop_width', 0x38), ('prop_height', 0x3C)):
        c.label(label); c.load('eax', 'esi', offset)
        cmpi('eax', 1); err(-13, '8c'); cmpi('eax', 64); err(-13, '8f'); result()
    c.label('prop_container'); c.load('eax', 'ebp', 8); cmpi('eax', 303); c.jump('catalog_container', '84')
    get('eax', 'ci'); result(); c.label('catalog_container'); c.ri('eax', -1); result()
    c.label('prop_name'); vc('esi', 0xF8); c.test('eax'); err(-6, '84')
    c.push('eax'); c.load('ecx', 'ebp', 28); c.call(0x42B420)
    # VM4C1044/4C107A tests returned AL, not the assignment's script type.
    setl('result_type', 1); c.ri('eax', 0); result()
    c.label('prop_sellable'); c.call('supported'); c.test('eax'); c.jump('not_sellable', '84')
    vc('esi', 0x10C); c.test('eax'); c.jump('not_sellable', '8e'); c.ri('eax', 1); result()
    c.label('not_sellable'); c.ri('eax', 0); result()

    for label, helper in (('prop_equip', 'can_equip'), ('prop_unequip', 'can_unequip'), ('prop_use', 'can_use')):
        c.label(label); c.load('eax', 'ebp', 8); cmpi('eax', 312); err(-6, '85')
        c.call(helper); result()
    c.label('prop_target'); c.load('eax', 'ebp', 8); cmpi('eax', 312); err(-6, '85')
    c.call('can_equip'); c.test('eax'); c.jump('no_target', '84'); get('eax', 'target_ci'); result()
    c.label('no_target'); c.ri('eax', -1); result()

    c.label('personal_mutation'); vc('esi', 0x0C); arg('edx', 1); c.cmp('eax', 'edx'); err(-7, '85')
    c.load('eax', 'esi', 0x40); arg('edx', 2); c.cmp('eax', 'edx'); err(-7, '85'); put('old_quantity', 'eax')
    c.call('alive'); c.test('eax'); err(-15, '84')
    c.load('eax', 'ebp', 8); cmpi('eax', 317); c.jump('use_item', '84')
    cmpi('eax', 316); c.jump('remove_item', '84')
    c.call('can_equip'); c.test('eax'); c.jump('refusal', '84'); c.jump('toggle_item')
    c.label('remove_item'); c.call('can_unequip'); c.test('eax'); c.jump('refusal', '84')
    get('eax', 'inventory'); c.load('eax', 'eax', 0x24); put('target_container', 'eax')
    c.label('toggle_item'); get('esi', 'item'); c.push('esi'); get('ecx', 'inventory'); vc('ecx', 0x94)
    # The original helper always clears AL, including successful moves.
    # Inspect its native outcome; do not synthesize movement or callbacks.
    get('esi', 'item'); c.load('eax', 'esi', 0x24); get('edx', 'target_container'); c.cmp('eax', 'edx')
    c.jump('success', '84'); c.test('eax'); c.jump('refusal', '85')
    # Native insertion may completely merge an equipment stack in the backpack.
    c.load('eax', 'ebp', 8); cmpi('eax', 316); c.jump('refusal', '85')
    c.load('eax', 'esi', 0x40); c.test('eax'); c.jump('refusal', '85'); c.jump('success')
    c.label('use_item'); c.call('can_use'); c.test('eax'); c.jump('refusal', '84')
    get('esi', 'item'); c.push('esi'); get('ecx', 'owner'); c.call(0x48DE50)
    get('esi', 'item'); get('eax', 'old_quantity'); c.load('edx', 'esi', 0x40); c.emit('2bc2')
    cmpi('eax', 1); c.jump('refusal', '85'); c.jump('success')
    c.label('success'); c.ri('eax', 1); result()
    c.label('refusal'); c.ri('eax', 0); result()

    from old_native_inventory_move import emit as emit_inventory_move
    emit_inventory_move(c, dict(get=get, put=put, arg=arg, err=err, cmpi=cmpi,
                               result=result, vc=vc, guard_vt=guard_vt, setl=setl, L=L))

    c.label('development'); arg('eax', 0); cmpi('eax', 1); err(-5, '82')
    cmpi('eax', 11); err(-5, '87'); put('skill', 'eax')
    c.call('alive'); c.test('eax'); err(-15, '84')
    get('eax', 'player'); c.load('esi', 'eax', 0x32C); c.test('esi'); err(-16, '84')
    guard_vt('esi', 0x59C798, -16); put('pd', 'esi')
    get('edx', 'owner'); c.alu(0, 'edx', 12)
    c.load('eax', 'esi', 4); c.cmp('eax', 'edx'); err(-16, '85')
    get('eax', 'player'); c.load('eax', 'eax', 0x1A0); c.cmp('eax', 'edx'); err(-16, '85')
    c.rr('edi', 'edx'); guard_vt('edi', 0x59CD38, -16)
    c.load('eax', 'esi', 0x1C); c.test('eax'); err(-16, '84')
    # Reject template-selection profiles: Assign would replace the whole hero.
    vc('edi', 0x3C); c.alu(4, 'eax', 255); c.test('eax'); err(-16, '85')
    c.call('draft_empty')
    get('eax', 'skill'); c.push('eax'); vc('edi', 0x1C); put('old_base', 'eax')
    c.pushi(33); vc('edi', 0x18); put('old_points', 'eax')
    c.load('eax', 'ebp', 8); cmpi('eax', 331); c.jump('development_spend', '84')
    arg('eax', 1)
    for prop, label in ((0, 'development_base'), (1, 'development_effective'),
                        (2, 'development_points'), (3, 'development_cost'),
                        (4, 'development_can'), (5, 'development_step'), (6, 'development_limit')):
        cmpi('eax', prop); c.jump(label, '84')
    err(-6)
    c.label('development_base'); get('eax', 'old_base'); result()
    c.label('development_effective'); get('eax', 'skill'); c.push('eax'); vc('edi', 0x18); result()
    c.label('development_points'); get('eax', 'old_points'); result()
    c.label('development_cost'); c.ri('eax', 1); result()
    c.label('development_limit'); c.ri('eax', 200); result()
    c.label('development_step'); get('eax', 'skill'); c.push('eax'); get('ecx', 'pd'); c.call(0x486B70); result()
    c.label('development_can'); get('eax', 'skill'); c.push('eax'); get('ecx', 'pd'); vc('ecx', 0x40)
    c.test('eax'); c.jump('refusal', '84'); c.jump('success')
    c.label('development_spend'); get('eax', 'old_base'); arg('edx', 1); c.cmp('eax', 'edx'); err(-7, '85')
    get('eax', 'old_points'); arg('edx', 2); c.cmp('eax', 'edx'); err(-7, '85')
    get('eax', 'skill'); c.push('eax'); get('ecx', 'pd'); vc('ecx', 0x40)
    c.test('eax'); c.jump('refusal', '84')
    get('eax', 'skill'); c.push('eax'); get('ecx', 'pd'); c.call(0x486B70)
    cmpi('eax', 1); err(-18, '85')
    # This is the original PD operation, not a low-level skill/points write.
    # Its descriptor Add callback applies derived stats and native point cost.
    c.pushi(1); get('eax', 'skill'); c.push('eax'); get('ecx', 'pd'); vc('ecx', 8)
    get('ecx', 'pd'); vc('ecx', 0x3C)
    c.call('draft_empty')
    get('eax', 'skill'); c.push('eax'); vc('edi', 0x1C)
    get('edx', 'old_base'); c.alu(0, 'edx', 1); c.cmp('eax', 'edx'); err(-19, '85')
    c.pushi(33); vc('edi', 0x18); get('edx', 'old_points'); c.alu(5, 'edx', 1)
    c.cmp('eax', 'edx'); err(-19, '85'); c.jump('success')

    c.label('buy'); vc('esi', 0x104); put('unit', 'eax'); arg('edx', 1); c.cmp('eax', 'edx'); err(-7, '85')
    cmpi('eax', 1); err(-13, '8c'); get('edi', 'entry'); c.load('edx', 'edi', 4); c.cmp('edx', 'eax'); err(-8, '8c')
    vc('esi', 0x108); arg('edx', 2); c.cmp('eax', 'edx'); err(-7, '85'); c.test('eax'); err(-13, '8e')
    vc('esi', 0xF0); c.test('eax'); err(-9, '84'); c.rr('esi', 'eax'); put('temp', 'esi')
    vc('esi', 0xCC); c.push('eax'); vc('esi', 0xA8)
    get('eax', 'unit'); c.push('eax'); c.lea('eax', 'ebp', L['out']); c.push('eax'); c.push('esi'); get('ecx', 'owner'); vc('ecx', 0x60)
    put('result', 'eax'); c.test('eax'); c.jump('buy_cleanup', '84')
    get('eax', 'unit'); c.emit('f7d8'); c.push('eax'); vc('esi', 0xAC)
    get('edi', 'entry'); c.load('eax', 'edi', 4); get('edx', 'unit'); c.emit('2bc2'); c.store('edi', 4, 'eax')
    c.label('buy_cleanup'); c.push('esi'); get('ecx', 'registry'); vc('ecx', 0x38); c.jump('done')
    c.label('sell'); c.call('supported'); c.test('eax'); err(-6, '84')
    vc('esi', 0x0C); arg('edx', 1); c.cmp('eax', 'edx'); err(-7, '85')
    c.load('eax', 'esi', 0x40); arg('edx', 2); c.cmp('eax', 'edx'); err(-7, '85')
    vc('esi', 0x10C); c.test('eax'); err(-6, '8e')
    c.load('eax', 'ebp', 8); cmpi('eax', 314); c.jump('sell_whole', '84'); c.pushi(0); c.jump('sell_call')
    c.label('sell_whole'); c.pushi(1)
    c.label('sell_call'); c.push('esi'); get('ecx', 'owner'); vc('ecx', 0x64); result()

    # Leaf helpers, preserving callee-saved registers except documented ESI.
    c.label('draft_empty'); get('ecx', 'pd'); c.load('eax', 'ecx', 0xE0)
    c.test('eax'); err(-17, '85'); c.alu(0, 'ecx', 0x2C); c.ri('edx', 44)
    c.label('draft_loop'); c.load('eax', 'ecx'); c.test('eax'); err(-17, '85')
    c.alu(0, 'ecx', 4); c.alu(5, 'edx', 1); c.jump('draft_loop', '85'); c.emit('c3')
    c.label('bind_personal'); get('edi', 'state'); c.load('eax', 'edi', 20)
    cmpi('eax', PERSONAL_MAGIC); c.jump('personal_existing', '84')
    c.test('eax'); err(-4, '85')
    for off, name in ((8, 'owner0'), (12, 'owner3'), (16, 'registry')):
        get('eax', name); c.store('edi', off, 'eax')
    c.imm('edi', 20, PERSONAL_MAGIC)
    c.label('personal_existing')
    for off, name in ((8, 'owner0'), (12, 'owner3'), (16, 'registry')):
        c.load('eax', 'edi', off); get('edx', name); c.cmp('eax', 'edx'); err(-4, '85')
    c.emit('c3')
    c.label('alive'); get('ecx', 'owner')
    c.load('eax', 'ecx', 0x1A0); c.test('eax'); c.jump('cap_false', '84')
    vc('ecx', 0x24); c.test('eax'); c.jump('cap_false', '8e'); c.ri('eax', 1); c.emit('c3')
    c.label('equip_category'); get('esi', 'item'); c.call('supported'); c.test('eax'); c.jump('cap_false', '84')
    c.load('eax', 'esi', 0x14); cmpi('eax', 4); c.jump('cap_true', '84')
    cmpi('eax', 6); c.jump('cap_true', '84'); cmpi('eax', 2); c.jump('cap_false', '85')
    # Unarmed/HAND class0 is the native fallback, not user equipment.
    c.load('eax', 'esi', 0x18); cmpi('eax', 1); c.jump('cap_false', '82'); cmpi('eax', 5); c.jump('cap_false', '87')
    c.ri('eax', 1); c.emit('c3')
    c.label('can_equip'); get('eax', 'ci'); c.test('eax'); c.jump('cap_false', '85')
    c.call('equip_category'); c.test('eax'); c.jump('cap_false', '84')
    get('ecx', 'owner'); c.alu(0, 'ecx', 4); guard_vt('ecx', 0x59CE94)
    c.push('esi'); vc('ecx', 0x14); c.alu(4, 'eax', 255); c.test('eax'); c.jump('cap_false', '84')
    setl('target_ci', 1)
    c.label('target_loop'); get('eax', 'target_ci'); cmpi('eax', 19); c.jump('cap_false', '83')
    get('edx', 'inventory'); c.emit('8b7c8224'); c.test('edi'); err(-10, '84')
    # Exact ordinary category containers have one compatible target. Query
    # only class/type acceptance (flag0); capacity/swap is native at mutation.
    cmpi('eax', 1); c.jump('target_hand', '84'); guard_vt('edi', 0x59BF78, -10); c.jump('target_guarded')
    c.label('target_hand'); guard_vt('edi', 0x59BE78, -10)
    c.label('target_guarded'); vc('edi', 0x0C); c.alu(4, 'eax', 255); c.test('eax'); c.jump('target_next', '84')
    get('esi', 'item'); c.pushi(0); c.push('esi'); vc('edi', 0x38); c.alu(4, 'eax', 1); c.test('eax'); c.jump('target_next', '84')
    put('target_container', 'edi'); c.ri('eax', 1); c.emit('c3')
    c.label('target_next'); get('eax', 'target_ci'); c.alu(0, 'eax', 1); put('target_ci', 'eax'); c.jump('target_loop')
    c.label('can_unequip'); get('eax', 'ci'); c.test('eax'); c.jump('cap_false', '84')
    c.call('equip_category'); c.test('eax'); c.jump('cap_false', '84')
    get('ecx', 'container'); vc('ecx', 0x0C); c.alu(4, 'eax', 255); c.test('eax'); c.jump('cap_false', '84')
    c.ri('eax', 1); c.emit('c3')
    c.label('can_use'); get('esi', 'item'); c.load('eax', 'esi'); c.lea('edx', 'ebx', 0x59D74C - IMAGE_BASE)
    c.cmp('eax', 'edx'); c.jump('cap_false', '85')
    c.load('eax', 'esi', 0x14); cmpi('eax', 6); c.jump('cap_false', '85')
    vc('esi', 0xC8); cmpi('eax', 9); c.jump('cap_false', '85')
    get('eax', 'ci'); c.test('eax'); c.jump('cap_false', '84')
    get('ecx', 'container'); vc('ecx', 0x0C); c.alu(4, 'eax', 255); c.test('eax'); c.jump('cap_false', '84')
    c.call('alive'); c.emit('c3')
    c.label('cap_false'); c.ri('eax', 0); c.emit('c3')
    c.label('cap_true'); c.ri('eax', 1); c.emit('c3')
    c.label('supported')
    for kind, table in SUPPORTED.items():
        c.lea('edx', 'ebx', table - IMAGE_BASE); c.load('eax', 'esi'); c.cmp('eax', 'edx'); c.jump('supported_' + str(kind), '84')
    c.ri('eax', 0); c.emit('c3')
    for kind in SUPPORTED:
        c.label('supported_' + str(kind)); c.load('eax', 'esi', 0x14); cmpi('eax', kind); c.jump('unsupported_type', '85')
        c.ri('eax', 1); c.emit('c3')
    c.label('unsupported_type'); c.ri('eax', 0); c.emit('c3')
    c.label('container_guard'); get('eax', 'ci'); cmpi('eax', 1); c.jump('container1', '84')
    guard_vt('esi', 0x59BF78, -10); c.jump('vector_guard')
    c.label('container1'); guard_vt('esi', 0x59BE78, -10)
    c.label('vector_guard'); c.load('eax', 'esi', 8); c.load('edx', 'esi', 12); c.cmp('edx', 'eax'); err(-10, '82')
    put('vector', 'eax'); c.emit('2bd0'); c.rr('ecx', 'edx'); c.alu(4, 'ecx', 3); err(-10, '85')
    cmpi('edx', 2048); err(-10, '87'); c.emit('c1ea02'); put('count', 'edx'); c.emit('c3')
    c.label('grid_setup'); get('esi', 'container')
    for off, name in ((0x58, 'nx'), (0x5C, 'ny')):
        c.load('eax', 'esi', off); cmpi('eax', 1); err(-10, '8c'); cmpi('eax', 64); err(-10, '8f'); put(name, 'eax')
    c.load('eax', 'esi', 0x84); c.test('eax'); err(-10, '84'); put('columns', 'eax'); c.emit('c3')
    c.label('grid_item'); get('eax', 'x'); get('edx', 'columns'); c.emit('8b1482'); c.test('edx'); err(-10, '84')
    get('eax', 'y'); c.emit('8b0c82'); c.test('ecx'); c.jump('grid_empty', '84')
    c.test('eax'); c.jump('grid_check_left', '84'); c.emit('3b4c82fc'); c.jump('grid_empty', '84')
    c.label('grid_check_left'); get('eax', 'x'); c.test('eax'); c.jump('grid_return', '84')
    get('edx', 'columns'); c.emit('8b5482fc'); c.test('edx'); err(-10, '84'); get('eax', 'y'); c.emit('3b0c82'); c.jump('grid_empty', '84')
    c.label('grid_return'); c.rr('eax', 'ecx'); c.emit('c3')
    c.label('grid_empty'); c.ri('eax', 0); c.emit('c3')
    c.label('owned_guard'); c.load('eax', 'esi'); c.lea('edx', 'ebx', 0x59B000 - IMAGE_BASE); c.cmp('eax', 'edx'); err(-10, '82')
    c.lea('edx', 'ebx', 0x5C0000 - IMAGE_BASE); c.cmp('eax', 'edx'); err(-10, '83')
    c.load('eax', 'eax', 12); c.lea('edx', 'ebx', 0x4794E0 - IMAGE_BASE); c.cmp('eax', 'edx'); err(-10, '85')
    c.load('eax', 'esi', 0x24); get('edx', 'container'); c.cmp('eax', 'edx'); err(-5, '85')
    c.load('eax', 'esi', 0x40); c.test('eax'); err(-5, '8e'); c.emit('c3')
    c.label('emit_owned'); c.call('owned_guard'); c.load('eax', 'ebp', 8)
    cmpi('eax', 319); c.jump('emit_by_row', '85')
    get('eax', 'out'); c.cmp('eax', 'esi'); c.jump('emit_count', '85')
    get('eax', 'locator'); result()
    c.label('emit_by_row'); cmpi('eax', 311); c.jump('emit_count', '85')
    get('eax', 'row'); arg('edx', 0); c.cmp('eax', 'edx'); c.jump('emit_count', '85')
    get('eax', 'locator'); result()
    c.label('emit_count'); get('eax', 'row'); c.alu(0, 'eax', 1); put('row', 'eax'); c.emit('c3')

    for number in ERRORS:
        c.label('error' + str(-number)); setl('result', number); c.jump('done')
    c.label('done'); c.load('eax', 'ebp', 24); get('edx', 'result'); c.store('eax', 0, 'edx')
    # Helpers may exit to done from nested calls: restore from EBP, not ESP.
    get('eax', 'result_type'); c.lea('esp', 'ebp', -12); c.emit('5f5e5b5dc21800')
    c.label('original'); c.emit('9d'); c.emit(HOOK_BYTES); c.jump(HOOK_VA + len(HOOK_BYTES))
    code = c.finish()
    from old_native_campaign_inventory_queries import OFFSET, stub
    if len(code) > OFFSET: raise AssertionError(f'Inventory backend overlaps query helper: {len(code)}')
    code = code.ljust(OFFSET, b'\0') + stub(rva, STATE_OFFSET, PERSONAL_MAGIC)
    if len(code) > NAME_OFFSET: raise AssertionError(f'Campaign shop code too large: {len(code)}')
    return code


def patch(image: bytes) -> tuple[bytes, dict]:
    if not _validate_preimage(image):
        raise ValueError('Campaign shop requires the exact shared-money predecessor')
    pe, optional, table, sections = _headers(image)
    if logical_section_count(sections) != 6:
        raise ValueError('Campaign shop must follow .omoney and precede .ocmd')
    sa, fa = struct.unpack_from('<II', image, optional + 32)
    if (sa, fa) != (0x1000, 0x1000): raise ValueError('Unexpected PE alignment')
    header = table + len(sections) * 40
    if header + 40 > min(s[4] for s in sections if s[3]) or image[header:header + 40] != b'\0' * 40:
        raise ValueError('No unused section header')
    raw = len(image)
    if max(s[4] + s[3] for s in sections) != raw or raw != _align(raw, fa): raise ValueError('Unexpected overlay/alignment')
    rva = _align(max(s[2] + max(s[1], s[3]) for s in sections), sa)
    if struct.unpack_from('<I', image, optional + 56)[0] != rva: raise ValueError('Unexpected SizeOfImage')
    code, raw_size = _stub(rva), _align(PAYLOAD_SIZE, fa)
    out = bytearray(image + b'\0' * raw_size)
    out[raw:raw + len(code)] = code
    out[raw + NAME_OFFSET:raw + NAME_OFFSET + len(MAP_NAME)] = MAP_NAME
    at = HOOK_VA - IMAGE_BASE
    if image[at:at + len(HOOK_BYTES)] != HOOK_BYTES: raise ValueError('Incompatible dispatcher/diagnostic shop')
    out[at:at + 5] = b'\xe9' + struct.pack('<i', IMAGE_BASE + rva - HOOK_VA - 5)
    from old_native_campaign_inventory_queries import HOOK_VA as have_va, HOOK_BYTES as have_bytes, OFFSET, CONTEXT_VA, CONTEXT_BYTES
    have_at = have_va - IMAGE_BASE
    if image[CONTEXT_VA - IMAGE_BASE:CONTEXT_VA - IMAGE_BASE + len(CONTEXT_BYTES)] != CONTEXT_BYTES:
        raise ValueError('Unsupported native CSI_HAVE caller')
    out[have_at:have_at + len(have_bytes)] = b'\xe9' + struct.pack('<i', IMAGE_BASE + rva + OFFSET - have_va - 5) + b'\x90' * 3
    struct.pack_into('<8sIIIIIIHHI', out, header, SECTION_NAME, PAYLOAD_SIZE, rva, raw_size, raw, 0, 0, 0, 0, 0xE0000020)
    struct.pack_into('<H', out, pe + 6, len(sections) + 1)
    struct.pack_into('<I', out, optional + 4, struct.unpack_from('<I', image, optional + 4)[0] + raw_size)
    struct.pack_into('<I', out, optional + 56, _align(rva + PAYLOAD_SIZE, sa))
    result = bytes(out)
    return result, {'feature': FEATURE, 'input_sha256': _sha(image), 'output_sha256': _sha(result),
                    'section_rva': rva, 'section_raw': raw, 'section_raw_size': raw_size,
                    'section_virtual_size': PAYLOAD_SIZE, 'code_size': len(code), 'state_offset': STATE_OFFSET,
                    'hook_va': HOOK_VA, 'commands': COMMANDS, 'properties': PROPERTIES, 'errors': ERRORS,
                    'development_properties': DEVELOPMENT_PROPERTIES, 'development_skills': list(range(1, 12)),
                    'development_native': 'Live per-player PD CanInc4868D0, step486B70==1, Add4865E0(skill,+1), Assign486A70; native point consumption/callbacks. Empty draft, base and unspent guards.',
                    'creation_perk_native': '344: exact lobby only, army0/3; native current descriptor 49BA00, interface9, SetPerk472280. No registry-wide EXT199 during draft replay.',
                    'menu_item_cleanup': '345: exact mainmenu/lobby/retry only; native parameter-menu release480090 and inventory hide/input-off. No item or RPG mutation.',
                    'catalog_types': list(SUPPORTED), 'catalog_levels': list(SHOP_NUMBERS), 'maximum_catalog': MAX_CATALOG,
                    'stock_policy': 'Finite shared stock per mission; ammo MaxInv*(ShopNumMin+(baseID+mission)%ShopNumRange), zero range contributes zero; other types native.v120(mission)*MaxInv. No RNG calls.',
                    'buy_result': 'Native mask; 0 refusal, bit0 success; negative backend guard error',
                    'sell_result': 'Native actual quantity removed; negative backend guard error',
                    'personal_maps': list(MAP_NUMBERS),
                    'quest_inventory_presence': 'Original CSI_HAVE query, canonical owner first then validated guest owner; original quest update, no item transfer or grant',
                    'local_inventory_view': '318(0/1): original inventory hidden/visible, native input inactive; 318(2): rebuild visible local cached grids without visibility/input toggle. Local owner and empty drag guards. 319: native container hit with restored hover scratch, returns guarded owned locator. No game item mutations.',
                    'local_item_info': '336 owned locator / 337 catalog base ID, screen x,y: native per-inventory tooltip, live owner/requirements and original fonts/art; 338 hides and releases selection. No native input handlers.',
                    'equip_native': 'Inventory.v94=47A3B0, native owner+4.v14 requirements; actual container outcome returns1, refusal0',
                    'personal_identity': 'Exact retained owner pair/registry initialized by305 independently of catalog; locator+base+quantity guard',
                    'inventory_move': '339 commit / 341 preview: source locator, base+quantity*8192, target cell/slot. 340 local empty-cell hit. Empty footprints, two-item swaps, stack merges and native compatible equipment replacement; no native held item.',
                    'addressed_purchase': '342 commit / 343 preview: base+unit*8192, expected price, target. Native clone, quantity, weapon preparation and money callbacks with refund; finite shared stock.',
                    'unsupported': ['purchase over occupied equipment', 'random implants', 'repair', 'buyback', 'unarmed fallback movement', 'perk allocation', 'development drafts/refunds', 'durable stock saves', 'missions outside the explicit registry']}


def normalize_optional(image: bytes) -> tuple[bytes, bool]:
    from old_native_campaign_inventory_queries import HOOK_VA as have_va, HOOK_BYTES as have_bytes
    pe, optional, table, sections = _headers(image)
    at = HOOK_VA - IMAGE_BASE
    if sections[-1][0] != SECTION_NAME:
        if image[have_va - IMAGE_BASE:have_va - IMAGE_BASE + len(have_bytes)] != have_bytes:
            raise ValueError('Unknown/partial campaign inventory query hook')
        if sections[-1][0] == b'.oshop\0\0':
            from old_native_shop_patch import normalize_optional as normalize_diagnostic
            normalize_diagnostic(image)
            return image, False
        if image[at:at + 5] != HOOK_BYTES: raise ValueError('Unknown/partial campaign shop hook')
        return image, False
    _, _, rva, raw_size, raw = sections[-1]
    if raw + raw_size != len(image) or raw != max(s[4] + s[3] for s in sections[:-1]): raise ValueError('Invalid campaign shop section extent')
    prior = bytearray(image[:raw]); prior[at:at + 5] = HOOK_BYTES
    prior[have_va - IMAGE_BASE:have_va - IMAGE_BASE + len(have_bytes)] = have_bytes
    header = table + (len(sections) - 1) * 40; prior[header:header + 40] = b'\0' * 40
    struct.pack_into('<H', prior, pe + 6, len(sections) - 1)
    size = struct.unpack_from('<I', prior, optional + 4)[0]
    if size < raw_size: raise ValueError('Invalid code size')
    struct.pack_into('<I', prior, optional + 4, size - raw_size)
    struct.pack_into('<I', prior, optional + 56, rva)
    prior = bytes(prior)
    if patch(prior)[0] != image: raise ValueError('Campaign shop differs from exact guarded output')
    return prior, True
