"""Occupied-cell transactions and addressed native purchases for .cshop.

No preview calls 479280: even flag=0 mutates a fully mergeable stack.
Every swap checks both final footprints before touching either object.
"""


def emit(c, api):
    get, put, arg, err, cmpi, vc, setl, L = (
        api[k] for k in ('get', 'put', 'arg', 'err', 'cmpi', 'vc', 'setl', 'L'))

    def native(address, item='item', container='target_container', xy=None):
        if xy:
            for n in reversed(xy): get('eax', n); c.push('eax')
        get('eax', item); c.push('eax'); get('ecx', container); c.call(address)

    def inserted(failure):
        c.alu(4, 'eax', 1); c.test('eax'); c.jump(failure, '84')

    def preview():
        c.load('eax', 'ebp', 8)
        for command in (341, 343): cmpi('eax', command); c.jump('success', '84')

    def equip(item, container):
        c.pushi(0); get('eax', item); c.push('eax'); get('ecx', container); vc('ecx', 0x30)

    def detach(item, container):
        native(0x476A40, item, container)
        get('edx', item); c.cmp('eax', 'edx'); err(-24, '85')

    c.label('move_occupied')
    get('esi', 'other'); c.call('supported'); c.test('eax'); c.jump('refusal', '84')
    c.load('eax', 'esi', 0x24); get('edx', 'target_container'); c.cmp('eax', 'edx'); err(-24, '85')
    c.load('eax', 'esi', 0x40); cmpi('eax', 1); err(-24, '8c'); put('other_quantity', 'eax')
    # Only native stack categories merge: ammunition and stackable objects.
    c.load('eax', 'esi', 0x14); cmpi('eax', 3); c.jump('move_merge_id', '84')
    cmpi('eax', 6); c.jump('move_swap', '85')
    c.load('eax', 'esi', 0x44); cmpi('eax', 1); c.jump('move_swap', '86')
    c.label('move_merge_id'); vc('esi', 0x0C)
    get('edx', 'id'); c.cmp('eax', 'edx'); c.jump('move_swap', '85')
    get('esi', 'other'); c.load('eax', 'esi', 0x44)
    get('edx', 'other_quantity'); c.emit('2bc2'); put('merge_room', 'eax')
    get('edi', 'target_container'); c.emit('0fb6'); c.mem('eax', 'edi', 0x48)
    c.test('eax'); c.jump('merge_bounded', '84')
    c.ri('eax', 262143); get('edx', 'other_quantity'); c.emit('2bc2'); put('merge_room', 'eax')
    c.label('merge_bounded'); get('eax', 'merge_room'); c.test('eax'); c.jump('refusal', '8e')
    # Keep the packed source quote representable after a merge.
    get('edx', 'other_quantity'); get('ecx', 'old_quantity'); c.emit('03d1')
    cmpi('edx', 262143); c.jump('refusal', '87')
    get('edx', 'buy_mode'); c.test('edx'); c.jump('merge_checked', '84')
    get('edx', 'old_quantity'); c.cmp('eax', 'edx'); c.jump('refusal', '82')
    c.label('merge_checked'); preview()
    get('eax', 'buy_mode'); c.test('eax'); c.jump('buy_place', '85')
    detach('item', 'container')
    c.pushi(1); get('eax', 'item'); c.push('eax'); get('ecx', 'other'); c.call(0x479280)
    cmpi('eax', 3); c.jump('merge_full', '84')
    cmpi('eax', 6); err(-24, '85')
    # A partial merge leaves the remainder at its original source position.
    c.call('restore_move_source'); inserted('error24'); c.jump('success')
    c.label('merge_full')
    get('esi', 'item'); c.load('eax', 'esi', 0x40); c.test('eax'); err(-24, '85')
    get('eax', 'item'); c.push('eax'); get('ecx', 'registry'); vc('ecx', 0x38); c.jump('success')

    c.label('move_swap')
    get('eax', 'buy_mode'); c.test('eax'); c.jump('refusal', '85')
    get('eax', 'dest_ci'); c.test('eax'); c.jump('move_equipment_ready', '85')
    # Remember the foreign object's original top-left for rollback.
    for name in ('other_y', 'other_x'):
        c.lea('eax', 'ebp', L[name]); c.push('eax')
    get('eax', 'other'); c.push('eax'); get('ecx', 'target_container'); c.call(0x478390)
    c.alu(4, 'eax', 255); c.test('eax'); err(-24, '84')
    get('eax', 'ci'); c.test('eax'); c.jump('swap_to_equipment', '85')
    get('esi', 'other')
    for off, name, pos, limit in ((0x38, 'other_w', 'source_x', 'nx'), (0x3C, 'other_h', 'source_y', 'ny')):
        c.load('eax', 'esi', off); cmpi('eax', 1); err(-13, '8c')
        cmpi('eax', 64); err(-13, '8f'); put(name, 'eax')
        get('edx', pos); c.emit('03c2'); get('edx', limit); c.cmp('eax', 'edx'); c.jump('refusal', '87')
    # The two proposed final rectangles must not overlap each other.
    for a, size, b in (('source_x', 'other_w', 'dest_x'), ('dest_x', 'move_w', 'source_x'),
                       ('source_y', 'other_h', 'dest_y'), ('dest_y', 'move_h', 'source_y')):
        get('eax', a); get('edx', size); c.emit('03c2'); get('edx', b)
        c.cmp('eax', 'edx'); c.jump('swap_separate', '86')
    c.jump('refusal')
    c.label('swap_separate'); get('eax', 'source_x'); put('x', 'eax')
    c.label('swap_column'); get('eax', 'x'); get('edx', 'columns'); c.emit('8b1482')
    c.test('edx'); err(-10, '84'); put('move_column', 'edx'); get('eax', 'source_y'); put('y', 'eax')
    c.label('swap_cell'); get('eax', 'y'); get('edx', 'move_column'); c.emit('8b0482')
    c.test('eax'); c.jump('swap_cell_ok', '84')
    for name in ('item', 'other'):
        get('edx', name); c.cmp('eax', 'edx'); c.jump('swap_cell_ok', '84')
    c.jump('refusal')
    c.label('swap_cell_ok'); get('eax', 'y'); c.alu(0, 'eax', 1); put('y', 'eax')
    get('edx', 'source_y'); get('ecx', 'other_h'); c.emit('03d1'); c.cmp('eax', 'edx'); c.jump('swap_cell', '82')
    get('eax', 'x'); c.alu(0, 'eax', 1); put('x', 'eax')
    get('edx', 'source_x'); get('ecx', 'other_w'); c.emit('03d1'); c.cmp('eax', 'edx'); c.jump('swap_column', '82')
    c.jump('swap_ready')
    c.label('swap_to_equipment')
    c.pushi(0); get('eax', 'other'); c.push('eax'); get('ecx', 'container'); vc('ecx', 0x38)
    c.alu(4, 'eax', 1); c.test('eax'); c.jump('refusal', '84')
    get('eax', 'other'); c.push('eax'); get('ecx', 'owner'); c.alu(0, 'ecx', 4); vc('ecx', 0x14)
    c.alu(4, 'eax', 255); c.test('eax'); c.jump('refusal', '84')
    c.label('swap_ready'); preview()
    get('eax', 'ci'); c.test('eax'); c.jump('swap_cross_commit', '85')
    # Same-container swap preserves both vectors and ownership pointers.
    for name in ('item', 'other'): native(0x477E30, name)
    native(0x477BF0, xy=('dest_x', 'dest_y')); inserted('swap_grid_rollback')
    native(0x477BF0, 'other', xy=('source_x', 'source_y')); inserted('swap_grid_rollback')
    c.jump('success')
    c.label('swap_grid_rollback')
    for name in ('item', 'other'): native(0x477E30, name)
    native(0x477BF0, xy=('source_x', 'source_y')); inserted('error24')
    native(0x477BF0, 'other', xy=('other_x', 'other_y')); inserted('error24'); c.jump('refusal')
    c.label('swap_cross_commit')
    detach('item', 'container'); detach('other', 'target_container')
    equip('other', 'container'); inserted('swap_cross_rollback')
    native(0x477B20, xy=('dest_x', 'dest_y')); inserted('swap_cross_rollback'); c.jump('success')
    c.label('swap_cross_rollback')
    for name in ('item', 'other'):
        get('eax', name); c.load('ecx', 'eax', 0x24); c.test('ecx'); c.jump('swap_detached_' + name, '84')
        c.push('eax'); c.call(0x476A40)
        c.label('swap_detached_' + name)
    equip('item', 'container'); inserted('error24')
    native(0x477B20, 'other', xy=('other_x', 'other_y')); inserted('error24'); c.jump('refusal')

    c.label('restore_move_source')
    get('eax', 'ci'); c.test('eax'); c.jump('restore_move_equipment', '85')
    native(0x477B20, container='container', xy=('source_x', 'source_y')); c.emit('c3')
    c.label('restore_move_equipment'); equip('item', 'container'); c.emit('c3')

    # Addressed purchase shares placement validation. Do not call owner.v14
    # with insert=false: it charges but deliberately nulls the out pointer of
    # an unlinked clone (item.vC0 == -1). Compose its original primitives below.
    c.label('buy_at'); setl('buy_mode', 1); setl('ci', 0); setl('x', 0); setl('y', 0); setl('other', 0)
    arg('eax', 0); c.emit('c1e80d'); put('old_quantity', 'eax')
    cmpi('eax', 1); err(-7, '82')
    get('esi', 'item'); vc('esi', 0x104); get('edx', 'old_quantity'); c.cmp('eax', 'edx'); err(-7, '85')
    put('unit', 'eax'); get('edi', 'entry'); c.load('edx', 'edi', 4); c.cmp('edx', 'eax'); err(-8, '82')
    vc('esi', 0x108); arg('edx', 1); c.cmp('eax', 'edx'); err(-7, '85')
    cmpi('eax', 1); err(-13, '8c'); put('price', 'eax')
    get('ecx', 'owner'); vc('ecx', 8); get('edx', 'price'); c.cmp('eax', 'edx'); c.jump('refusal', '8c')
    c.jump('move_validate')
    c.label('buy_equipment')
    # Direct purchase into an empty slot or a compatible non-full stack.
    # Replacing an unrelated paid equipment item requires backpack placement.
    get('edi', 'target_container'); c.load('eax', 'edi', 8); c.load('edx', 'edi', 12)
    c.cmp('eax', 'edx'); c.jump('buy_equipment_empty', '84')
    c.rr('ecx', 'eax'); c.alu(0, 'ecx', 4); c.cmp('ecx', 'edx'); c.jump('refusal', '85')
    c.load('eax', 'eax'); c.test('eax'); err(-10, '84'); put('other', 'eax'); c.jump('move_occupied')
    c.label('buy_equipment_empty'); setl('other', 0); c.jump('move_ready')
    c.label('buy_place')
    get('esi', 'item'); vc('esi', 0xF0); c.test('eax'); err(-9, '84'); put('item', 'eax')
    c.rr('esi', 'eax'); get('eax', 'unit'); c.push('eax'); vc('esi', 0xA8)
    c.load('eax', 'esi', 0x14); cmpi('eax', 2); c.jump('buy_charge', '85')
    # Original 48E670 initializes a bought weapon's loaded ammunition.
    c.pushi(0x32); vc('esi', 0); c.test('eax'); err(-24, '84')
    c.rr('ecx', 'eax'); c.call(0x48FF40)
    c.label('buy_charge')
    c.pushi(0); get('eax', 'price'); c.emit('f7d8'); c.push('eax'); get('ecx', 'owner'); vc('ecx', 0x1C)
    c.alu(4, 'eax', 255); c.test('eax'); c.jump('buy_destroy_refused', '84')
    get('eax', 'other'); c.test('eax'); c.jump('buy_merge', '85')
    get('eax', 'dest_ci'); c.test('eax'); c.jump('buy_put_equipment', '85')
    native(0x477B20, xy=('dest_x', 'dest_y')); inserted('buy_refund'); c.jump('buy_success')
    c.label('buy_put_equipment'); equip('item', 'target_container'); inserted('buy_refund'); c.jump('buy_success')
    c.label('buy_merge')
    c.pushi(1); get('eax', 'item'); c.push('eax'); get('ecx', 'other'); c.call(0x479280)
    cmpi('eax', 3); err(-24, '85')
    get('eax', 'item'); c.push('eax'); get('ecx', 'registry'); vc('ecx', 0x38)
    c.label('buy_success')
    get('edi', 'entry'); c.load('eax', 'edi', 4); get('edx', 'unit'); c.emit('2bc2'); c.store('edi', 4, 'eax')
    c.jump('success')
    c.label('buy_refund')
    # Placement failed without mutation: use the native money callback for
    # the refund, then destroy the unowned paid clone. Stock stays unchanged.
    get('esi', 'item'); c.load('eax', 'esi', 0x24); c.test('eax'); err(-24, '85')
    c.pushi(1); get('eax', 'price'); c.push('eax'); get('ecx', 'owner'); vc('ecx', 0x1C)
    c.alu(4, 'eax', 255); c.test('eax'); err(-24, '84')
    c.label('buy_destroy_refused')
    get('eax', 'item'); c.push('eax'); get('ecx', 'registry'); vc('ecx', 0x38); c.jump('refusal')
