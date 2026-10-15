"""CSI_HAVE reads either personal inventory at the original quest poll only.

48AA3F selects condition(type=3,state=1); 48AADB calls RPG.v50(id,3),
48AAE1 tests its result, and 48AAE5 alone executes the original quest update.
No inventory mutation, quest setter, grant, allocation or RNG is added here.
"""
import hashlib

HOOK_VA = 0x48AADB
HOOK_BYTES = bytes.fromhex('508bcdff525085c0')
CONTEXT_VA = 0x48AAC7
CONTEXT_BYTES = bytes.fromhex('8b066a038bce8b550089542420ff500c8b542420508bcdff525085c0')
OFFSET = 0x3C00
HAVE_QUESTS = {'1_2_27': 'Obj_stabil', '1_2_29': 'Obj_stabil', '1_3_12': 'Obj_transf'}


def validate_levels(data):
    from old_native_story_item_registry import LEVELS_SHA256, _quest_records
    if hashlib.sha256(data).hexdigest() != LEVELS_SHA256:
        raise ValueError('Unsupported CSI_HAVE quest database')
    actual = {q: f['ChangeStateItem'] for q, f in _quest_records(data).items()
              if 'CSI_HAVE' in f.get('ChangeStateItem', '')}
    if actual != {q: 'QS_BEGUN CSI_HAVE ' + name for q, name in HAVE_QUESTS.items()}:
        raise ValueError('Unreviewed inventory-presence quest')


def stub(rva, state_offset, personal_magic):
    from old_native_campaign_shop_patch import _Asm, IMAGE_BASE
    from old_native_campaign_missions import emit_native_map_guard
    c = _Asm(IMAGE_BASE + rva + OFFSET)
    # Preserve requested ID and issue the original query with duplicate args;
    # the original type=3 on the incoming stack is discarded at the tail.
    c.emit('506a03508bcdff52509c6085c0'); c.jump('done', '85')
    c.call('pic'); c.label('pic'); c.pop('ebx'); c.alu(5, 'ebx', rva + OFFSET + len(c.code) - 1)
    c.load('eax', 'ebx', rva + state_offset + 20)
    c.alu(7, 'eax', personal_magic); c.jump('done', '85')
    c.load('edi', 'esp', 8)  # original EBP: canonical RPG owner at this site
    c.load('eax', 'ebx', rva + state_offset + 8); c.cmp('eax', 'edi'); c.jump('done', '85')
    c.load('edx', 'ebx', 0x204DDC); c.test('edx'); c.jump('done', '84')
    c.load('esi', 'edx', 0x4C); c.test('esi'); c.jump('done', '84')
    emit_native_map_guard(c, 'esi', lambda condition: c.jump('done', condition), prefix='have_map')
    c.load('eax', 'edx', 0x9CC); c.test('eax'); c.jump('done', '84')
    c.load('ecx', 'eax', 0x194); c.test('ecx'); c.jump('done', '84')
    c.cmp('ecx', 'edi'); c.jump('done', '84')
    c.load('eax', 'ebx', rva + state_offset + 12); c.cmp('eax', 'ecx'); c.jump('done', '85')
    c.load('eax', 'esp', 36); c.load('edx', 'ecx'); c.pushi(3); c.push('eax'); c.emit('ff5250')
    c.store('esp', 28, 'eax')  # boolean/pointer consumed only by the original TEST
    c.label('done'); c.emit('619d8d64240885c0'); c.jump(HOOK_VA + len(HOOK_BYTES))
    return c.finish()
