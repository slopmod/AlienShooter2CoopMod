"""Bounded checkpoint I/O through the pinned game's own RPG serializers.

350 exports both heroes and quests to fixed staging names; 351 restores one
hero in the pre-game/retry lobby; 352 restores quests there. 353 releases
mod-owned purse/catalog bindings only in the connected retry lobby.
No profile switching,
world snapshots, arbitrary filenames, gameplay input or network hook.
"""
import hashlib
import struct

from old_native_campaign_shop_patch import _Asm, _align

BASE = 0x400000
HOOK = 0x49A1A0
SECTION = b'.osave\0\0'
FEATURE = 'old-campaign-checkpoint-native-v2'
SIZE = 0x3000
PRIOR = 0x2000


def _headers(image):
    from old_native_image_validation import _headers as read
    pe,opt,table,sections=read(image)
    return pe,opt,table,[(s['name'],s['virtual'],s['rva'],s['raw_size'],s['raw']) for s in sections]


IMPORT_MAPS=(b'maps\\old_campaign_lobby.map\0',b'maps\\old_campaign_retry.map\0')


def _map_guard(c, names, *, prefix):
    """EDX is the physical map name, exact case-insensitive terminated match."""
    for number,name in enumerate(names):
        following=prefix+'_next_'+str(number)
        for i,v in enumerate(name):
            c.emit('0fb6');c.mem('eax','edx',i)
            if v:c.alu(1,'eax',32)
            c.alu(7,'eax',v|32 if v else 0);c.jump(following,'85')
        c.jump(prefix+'_allowed');c.label(following)
    c.jump('done');c.label(prefix+'_allowed')


def _stub(rva, prior, retry_resets):
    c = _Asm(BASE + rva)
    c.emit('9c817c24085e010000'); c.jump('original', '82')
    c.emit('817c240861010000'); c.jump('original', '87')
    c.emit('9d558bec53565783ec20')
    c.rr('esi', 'ecx')
    c.call('pic'); c.label('pic'); c.pop('ebx'); c.alu(5, 'ebx', rva + len(c.code) - 1)
    c.imm('ebp', -16, -1)
    c.lea('eax', 'ebx', 0x1e5018); c.push('eax'); c.load('ecx', 'ebp', 28); c.call(0x42B420)
    c.load('edi', 'ebx', 0x204ddc); c.test('edi'); c.jump('done', '84')
    c.lea('edx', 'esi', -0x160)
    c.load('eax', 'edi', 0x9c0); c.cmp('eax', 'edx'); c.jump('party', '84')
    c.load('eax', 'edi', 0x9cc); c.cmp('eax', 'edx'); c.jump('done', '85')
    c.label('party'); c.load('eax', 'ebp', 8); c.alu(7, 'eax', 350); c.jump('export', '84')
    c.alu(7,'eax',353);c.jump('retry_prepare','84')
    # Import only before map start, with no live hero to invalidate.
    c.load('edx', 'edi', 0x4c); c.test('edx'); c.jump('done', '84')
    _map_guard(c,IMPORT_MAPS,prefix='import_map')
    c.load('eax', 'ebp', 8); c.alu(7, 'eax', 352); c.jump('quest_load', '84')
    # Preserve destination descriptor. Load into a native empty temporary,
    # then copy with the same virtual method used by original profile loading.
    c.rr('ecx', 'esi'); c.call(0x49ba00); c.test('eax'); c.jump('done', '84')
    c.rr('edi', 'eax'); c.pushi(9); c.virtual('edi', 0)
    c.test('eax'); c.jump('done', '84'); c.store('ebp', -20, 'eax')
    c.load('edi', 'ebx', 0x33a488); c.test('edi'); c.jump('done', '84')
    c.pushi(0); c.pushi(0); c.virtual('edi', 8)
    c.test('eax'); c.jump('done', '84'); c.store('ebp', -24, 'eax')
    c.rr('edi', 'eax'); c.pushi(1); c.virtual('edi', 0x98)
    # An empty profile object otherwise becomes the destination's RPG parent
    # during v38 copy (478960). Inherit the existing preset's definitions first,
    # without copying its inventory. The stable base survives temporary release.
    c.load('edi', 'ebp', -20); c.pushi(0x21); c.virtual('edi', 0)
    c.push('eax'); c.load('ecx', 'ebp', -24); c.call(0x493cc0)
    c.load('edi', 'ebx', 0x33a484); c.test('edi'); c.jump('release', '84')
    c.load('eax', 'ebx', 0x33a488); c.push('eax'); c.virtual('edi', 8)
    c.load('eax', 'ebx', 0x33a488); c.push('eax'); c.virtual('edi', 12)
    c.lea('edx', 'ebx', rva + 0x2130)
    c.load('eax', 'ebx', 0x204ddc); c.load('eax', 'eax', 0x9c0); c.alu(0, 'eax', 0x160)
    c.cmp('eax', 'esi'); c.jump('load_name', '84'); c.lea('edx', 'ebx', rva + 0x2160)
    c.label('load_name'); c.push('edx'); c.load('eax', 'ebp', -24); c.push('eax'); c.virtual('edi', 0x14)
    c.emit('0fb6c0'); c.test('eax'); c.jump('release', '84')
    c.load('edi', 'ebp', -20); c.load('eax', 'ebp', -24); c.push('eax'); c.virtual('edi', 0x38)
    # Native generic v38 omits the per-hero generation seed. 491AC8 stores the
    # parsed Srand at QI9+F8; 491B40/48F91B serialize that same field.
    c.load('eax', 'ebp', -24); c.load('edx', 'eax', 0xf8); c.store('edi', 0xf8, 'edx')
    c.imm('ebp', -16, 1)
    c.label('release'); c.load('edi', 'ebx', 0x33a488); c.load('eax', 'ebp', -24)
    c.push('eax'); c.virtual('edi', 0x38); c.jump('done')
    c.label('quest_load'); c.load('edi', 'ebx', 0x33a48c); c.test('edi'); c.jump('done', '84')
    c.lea('eax', 'ebx', rva + 0x2190); c.push('eax'); c.virtual('edi', 0x80)
    c.emit('0fb6c0'); c.store('ebp', -16, 'eax'); c.jump('done')
    c.label('export')
    # Caller army0 only; explicit phase selects staging versus load proof.
    c.load('eax', 'edi', 0x9c0); c.alu(0, 'eax', 0x160); c.cmp('eax', 'esi'); c.jump('done', '85')
    c.load('eax', 'ebp', 12); c.alu(7, 'eax', 1); c.jump('done', '87')
    for army, offset in ((0, 0x2100), (3, 0x2118)):
        c.load('eax', 'ebx', 0x204ddc); c.load('ecx', 'eax', 0x9c0 + army * 4)
        c.test('ecx'); c.jump('done', '84'); c.alu(0, 'ecx', 0x160); c.call(0x49ba00)
        c.test('eax'); c.jump('done', '84'); c.rr('edi', 'eax'); c.pushi(9); c.virtual('edi', 0)
        c.test('eax'); c.jump('done', '84'); c.store('ebp', -20, 'eax')
        c.lea('eax', 'ebx', rva + offset); c.load('edx', 'ebp', 12); c.test('edx')
        c.jump('export_name' + str(army), '84'); c.lea('eax', 'ebx', rva + offset + 0x100)
        c.label('export_name' + str(army))
        c.lea('edx', 'ebx', rva + 0x21c0); c.push('edx'); c.push('eax'); c.call(0x57fe73); c.alu(0, 'esp', 8)
        c.test('eax'); c.jump('done', '84'); c.store('ebp', -28, 'eax')
        c.push('eax'); c.load('edi', 'ebp', -20); c.virtual('edi', 0x94)
        c.emit('0fb6c0'); c.store('ebp', -32, 'eax')
        c.load('eax', 'ebp', -28); c.push('eax'); c.call(0x57fdc5); c.alu(0, 'esp', 4)
        c.test('eax'); c.jump('done', '85'); c.load('eax', 'ebp', -32); c.test('eax'); c.jump('done', '84')
    c.load('edi', 'ebx', 0x33a48c); c.test('edi'); c.jump('done', '84')
    c.lea('eax', 'ebx', rva + 0x21a8); c.load('edx', 'ebp', 12); c.test('edx'); c.jump('quest_name', '84')
    c.lea('eax', 'ebx', rva + 0x22a8)
    c.label('quest_name'); c.push('eax'); c.virtual('edi', 0x7c)
    c.emit('0fb6c0'); c.store('ebp', -16, 'eax');c.jump('done')
    c.label('retry_prepare')
    c.load('eax','edi',0x9c0);c.alu(0,'eax',0x160);c.cmp('eax','esi');c.jump('done','85')
    c.load('edx','edi',0x4c);c.test('edx');c.jump('done','84')
    _map_guard(c,(IMPORT_MAPS[1],),prefix='retry_map')
    # These sections own only integer headers and identity pointers, never
    # heap allocations. Do not carry active money routing through descriptor
    # import or keep depleted finite stock after loading the same mission.
    for offset,size in retry_resets:
        for i in range(0,size,4):c.imm('ebx',offset+i,0)
    c.imm('ebp',-16,1)
    c.label('done'); c.load('eax', 'ebp', 24); c.load('edx', 'ebp', -16); c.store('eax', 0, 'edx')
    c.ri('eax', 0)  # dispatcher result type: integer, not a script string
    c.emit('83c4205f5e5b5dc21800')
    c.label('original'); c.emit('9d'); c.jump(prior)
    return c.finish()


def patch(image):
    from old_native_script_capacity_patch import normalize_optional
    _, present = normalize_optional(image)
    if not present: raise ValueError('Checkpoint patch requires exact production capacity predecessor')
    pe, opt, table, sections = _headers(image)
    header = table + len(sections) * 40
    if any(image[header:header+40]) or header+40 > min(s[4] for s in sections if s[3]):
        raise ValueError('No checkpoint section header')
    prior = image[HOOK-BASE:HOOK-BASE+5]
    if prior[0] != 0xe9: raise ValueError('Missing command chain')
    target = HOOK + 5 + struct.unpack_from('<i', prior, 1)[0]
    raw = len(image); rva = _align(max(s[2]+max(s[1],s[3]) for s in sections), 0x1000)
    from old_native_shared_money_patch import SECTION_NAME as MONEY_SECTION, STATE_OFFSET as MONEY_STATE
    from old_native_campaign_shop_patch import SECTION_NAME as SHOP_SECTION, STATE_OFFSET as SHOP_STATE
    states={name:section_rva for name,_,section_rva,_,_ in sections}
    if MONEY_SECTION not in states or SHOP_SECTION not in states:
        raise ValueError('Retry checkpoint requires guarded purse and shop sections')
    retry_resets=((states[MONEY_SECTION]+MONEY_STATE,8),(states[SHOP_SECTION]+SHOP_STATE,32))
    code = _stub(rva, target, retry_resets)
    if len(code) >= PRIOR: raise ValueError('Checkpoint code overflow')
    out = bytearray(image + bytes(SIZE)); out[raw:raw+len(code)] = code
    out[raw+PRIOR:raw+PRIOR+5] = prior
    names = {0x2100:'coop-out-0.txt', 0x2118:'coop-out-3.txt', 0x2130:'coop-in-0.txt',
             0x2160:'coop-in-3.txt', 0x2190:'coop-in-quests.txt', 0x21a8:'coop-out-quests.txt',
             0x21c0:'wb', 0x2200:'coop-proof-0.txt', 0x2218:'coop-proof-3.txt', 0x22a8:'coop-proof-quests.txt'}
    for offset, name in names.items():
        data=name.encode()+b'\0'; out[raw+offset:raw+offset+len(data)] = data
    out[HOOK-BASE:HOOK-BASE+5] = b'\xe9'+struct.pack('<i',BASE+rva-HOOK-5)
    struct.pack_into('<8sIIIIIIHHI',out,header,SECTION,SIZE,rva,SIZE,raw,0,0,0,0,0x60000020)
    struct.pack_into('<H',out,pe+6,len(sections)+1)
    struct.pack_into('<I',out,opt+4,struct.unpack_from('<I',image,opt+4)[0]+SIZE)
    struct.pack_into('<I',out,opt+56,rva+SIZE)
    result=bytes(out)
    return result,dict(feature=FEATURE,input_sha256=hashlib.sha256(image).hexdigest(),
        output_sha256=hashlib.sha256(result).hexdigest(),section_rva=rva,code_size=len(code),
        import_maps=[name[:-1].decode('ascii') for name in IMPORT_MAPS],
        retry_prepare_command=353,retry_resets=[dict(rva=offset,size=size) for offset,size in retry_resets])


def normalize_optional(image):
    pe,opt,table,sections=_headers(image)
    if sections[-1][0] != SECTION: return image,False
    _,_,rva,size,raw=sections[-1]
    if size != SIZE or raw+size != len(image): raise ValueError('Bad checkpoint section')
    prior=bytearray(image[:raw]); prior[HOOK-BASE:HOOK-BASE+5]=image[raw+PRIOR:raw+PRIOR+5]
    prior[table+(len(sections)-1)*40:table+len(sections)*40]=bytes(40)
    struct.pack_into('<H',prior,pe+6,len(sections)-1)
    struct.pack_into('<I',prior,opt+4,struct.unpack_from('<I',image,opt+4)[0]-SIZE)
    struct.pack_into('<I',prior,opt+56,rva)
    prior=bytes(prior)
    if patch(prior)[0]!=image: raise ValueError('Checkpoint patch changed')
    return prior,True
