"""Guarded deterministic inventory movement, emitted inside the shop backend.

Preview and commit share validation. No native mouse/held-item handler runs.
The shared placement path supports empty cells, swaps, stack merges and shop
purchases. Equipment replacement retains original native callbacks.
"""


def emit(c, api):
    get, put, arg, err, cmpi, result, vc, guard_vt = (
        api[k] for k in ('get', 'put', 'arg', 'err', 'cmpi', 'result', 'vc', 'guard_vt'))
    setl = api['setl']

    def call_item(target, container, coords=False):
        if coords:
            get('eax', 'dest_y'); c.push('eax'); get('eax', 'dest_x'); c.push('eax')
        get('eax', 'item'); c.push('eax'); get('ecx', container); c.call(target)

    # a = canonical owned locator; b = base ID + quantity*8192;
    # c = destination: x*64+y in backpack, or container<<16 for equipment.
    c.label('move_item')
    setl('buy_mode', 0)
    arg('eax', 1); cmpi('eax', 0x7FFFFFFF); err(-7, '87')
    c.rr('edx', 'eax'); c.alu(4, 'edx', 8191); put('id', 'edx')
    c.emit('c1e80d'); put('old_quantity', 'eax')
    vc('esi', 0x0C); get('edx', 'id'); c.cmp('eax', 'edx'); err(-7, '85')
    cmpi('eax', 1); err(-7, '82'); cmpi('eax', 4096); err(-7, '87')
    get('esi', 'item'); c.load('eax', 'esi', 0x40); get('edx', 'old_quantity')
    c.cmp('eax', 'edx'); err(-7, '85')
    c.label('move_validate')
    get('eax', 'x'); put('source_x', 'eax'); get('eax', 'y'); put('source_y', 'eax')
    c.call('alive'); c.test('eax'); err(-15, '84')
    get('eax', 'inventory'); c.load('eax', 'eax', 0xE0); c.test('eax'); err(-5, '85')
    get('esi', 'item'); c.call('supported'); c.test('eax'); err(-6, '84')
    arg('eax', 2); put('destination', 'eax'); c.emit('c1e810'); put('dest_ci', 'eax')
    cmpi('eax', 19); err(-5, '83'); c.test('eax'); c.jump('move_backpack', '84')
    # Native quick-equip selects the compatible slot, so require that exact
    # requested slot. Never silently equip somewhere other than the drop.
    arg('eax', 2); c.alu(4, 'eax', 65535); c.test('eax'); err(-5, '85')
    c.call('can_equip'); c.test('eax'); c.jump('refusal', '84')
    get('eax', 'target_ci'); get('edx', 'dest_ci'); c.cmp('eax', 'edx'); c.jump('refusal', '85')
    get('eax', 'buy_mode'); c.test('eax'); c.jump('buy_equipment', '85')
    get('edi', 'target_container'); c.load('eax', 'edi', 8); c.load('edx', 'edi', 12)
    c.rr('ecx', 'eax'); c.alu(0, 'ecx', 4); c.cmp('ecx', 'edx'); c.jump('move_equipment_ready', '85')
    c.load('eax', 'eax'); c.test('eax'); err(-10, '84'); put('other', 'eax'); c.jump('move_occupied')
    c.label('move_equipment_ready')
    c.load('eax', 'ebp', 8); cmpi('eax', 341); c.jump('success', '84')
    c.jump('toggle_item')

    c.label('move_backpack')
    get('eax', 'destination'); cmpi('eax', 4096); err(-5, '83')
    c.rr('edx', 'eax'); c.emit('c1e806'); put('dest_x', 'eax')
    c.alu(4, 'edx', 63); put('dest_y', 'edx')
    get('eax', 'ci'); c.test('eax'); c.jump('move_source_ready', '84')
    c.call('can_unequip'); c.test('eax'); c.jump('refusal', '84')
    c.label('move_source_ready')
    get('eax', 'x'); put('source_x', 'eax'); get('eax', 'y'); put('source_y', 'eax')
    get('edi', 'inventory'); c.load('edi', 'edi', 0x24); c.test('edi'); err(-10, '84')
    guard_vt('edi', 0x59BF78, -10); put('target_container', 'edi')
    for off, name in ((0x58, 'nx'), (0x5C, 'ny')):
        c.load('eax', 'edi', off); cmpi('eax', 1); err(-10, '8c')
        cmpi('eax', 64); err(-10, '8f'); put(name, 'eax')
    c.load('eax', 'edi', 0x84); c.test('eax'); err(-10, '84'); put('columns', 'eax')
    get('esi', 'item')
    for off, name, pos, limit in ((0x38, 'move_w', 'dest_x', 'nx'), (0x3C, 'move_h', 'dest_y', 'ny')):
        c.load('eax', 'esi', off); cmpi('eax', 1); err(-13, '8c')
        cmpi('eax', 64); err(-13, '8f'); put(name, 'eax')
        get('edx', pos); c.emit('03c2'); get('edx', limit)
        c.cmp('eax', 'edx'); c.jump('refusal', '87')
    # Collect at most one foreign object. A drop across several independent
    # objects cannot be an atomic two-item swap.
    setl('other', 0)
    get('eax', 'dest_x'); put('x', 'eax')
    c.label('move_column')
    get('eax', 'x'); get('edx', 'columns'); c.emit('8b1482'); c.test('edx'); err(-10, '84')
    put('move_column', 'edx'); get('eax', 'dest_y'); put('y', 'eax')
    c.label('move_cell')
    get('eax', 'y'); get('edx', 'move_column'); c.emit('8b0482')
    c.test('eax'); c.jump('move_cell_free', '84')
    get('edx', 'item'); c.cmp('eax', 'edx'); c.jump('move_cell_free', '84')
    get('edx', 'other'); c.test('edx'); c.jump('move_remember_other', '84')
    c.cmp('eax', 'edx'); c.jump('refusal', '85')
    c.label('move_remember_other'); put('other', 'eax')
    c.label('move_cell_free')
    get('eax', 'y'); c.alu(0, 'eax', 1); put('y', 'eax')
    get('edx', 'dest_y'); get('ecx', 'move_h'); c.emit('03d1'); c.cmp('eax', 'edx'); c.jump('move_cell', '82')
    get('eax', 'x'); c.alu(0, 'eax', 1); put('x', 'eax')
    get('edx', 'dest_x'); get('ecx', 'move_w'); c.emit('03d1'); c.cmp('eax', 'edx'); c.jump('move_column', '82')
    get('eax', 'other'); c.test('eax'); c.jump('move_occupied', '85')
    c.label('move_ready')
    c.load('eax', 'ebp', 8)
    for preview in (341, 343):
        cmpi('eax', preview); c.jump('success', '84')
    get('eax', 'buy_mode'); c.test('eax'); c.jump('buy_place', '85')
    get('eax', 'ci'); c.test('eax'); c.jump('move_from_equipment', '85')
    # Same-container move changes only its native occupancy grid. The vector,
    # ownership and reference counts stay intact throughout.
    call_item(0x477E30, 'container')
    call_item(0x477BF0, 'target_container', True)
    c.alu(4, 'eax', 1); c.test('eax'); c.jump('success', '85')
    get('eax', 'source_x'); put('dest_x', 'eax'); get('eax', 'source_y'); put('dest_y', 'eax')
    call_item(0x477BF0, 'container', True)
    c.alu(4, 'eax', 1); c.test('eax'); err(-24, '84'); c.jump('refusal')

    from old_native_inventory_transfer import emit as emit_transfer
    emit_transfer(c, api)
    c.label('move_from_equipment')
    # These are the same detach/insert primitives used by native quick-equip.
    # Their original owner callbacks update derived stats and weapon bindings.
    call_item(0x476A40, 'container'); get('edx', 'item'); c.cmp('eax', 'edx'); err(-24, '85')
    call_item(0x477B20, 'target_container', True)
    c.alu(4, 'eax', 1); c.test('eax'); c.jump('success', '85')
    c.pushi(0); get('eax', 'item'); c.push('eax'); get('ecx', 'container'); vc('ecx', 0x30)
    c.alu(4, 'eax', 1); c.test('eax'); err(-24, '84'); c.jump('refusal')
