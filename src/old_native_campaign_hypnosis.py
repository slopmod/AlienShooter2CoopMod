"""Keep stock hypnosis arithmetic with synchronized aim and private progress.

Called only by the whole-file-guarded perks adapter. The local cursor and one
shared cooldown were unsafe inside a callback run for every network army.
The stock -555 claim still gives a target to one hero at a time; callbacks use
the existing deterministic army order. No extra network commands or RNG.
"""
import hashlib
import re


FEATURE = 'old-campaign-party-hypnosis-v1'


GLOBALS = '''
// Two independent progress lists, addressed by army / 3 after validation.
static int OldHypnUnits[2 * MAX_HYPN_UNITS];
static int OldHypnTimes[2 * MAX_HYPN_UNITS];
static int OldHypnStarts[2 * MAX_HYPN_UNITS];
static int OldHypnLabels[2 * MAX_HYPN_UNITS];
static int OldHypnCount[2];
static int OldHypnPrevTime[2];

OldHypnDelete(int slot, int i)
{
    if(slot < 0 || slot > 1 || i < 0 || i >= OldHypnCount[slot]) return;
    int base = slot * MAX_HYPN_UNITS;
    OldHypnCount[slot] = OldHypnCount[slot] - 1;
    int last = base + OldHypnCount[slot];
    int index = base + i;
    if(OldHypnUnits[index]) Action(OldHypnUnits[index], ACT_DELETE_ITEM, -555);
    Destroy(OldHypnLabels[index]);
    OldHypnUnits[index] = OldHypnUnits[last];
    OldHypnTimes[index] = OldHypnTimes[last];
    OldHypnStarts[index] = OldHypnStarts[last];
    OldHypnLabels[index] = OldHypnLabels[last];
    OldHypnUnits[last] = 0;
    OldHypnTimes[last] = 0;
    OldHypnStarts[last] = 0;
    OldHypnLabels[last] = 0;
}

DeleteHypnMonster(int unit)
{
    for(int slot = 0; slot < 2; slot++)
        for(int i = 0; i < OldHypnCount[slot]; i++)
            if(OldHypnUnits[slot * MAX_HYPN_UNITS + i] == unit)
            { OldHypnDelete(slot, i); return; }
}

'''


def adapt(source):
    """Transform the pinned stock subsection, retaining it outside coop."""
    start = source.index('static int UnitsToHypn[MAX_HYPN_UNITS];')
    function_start = source.index('HypnosisTact( int nArmy, int heroId )\n{', start)
    end = source.index('\n}\n', function_start) + 3
    original = source[start:end]
    # Parent validates the whole original perks file before any edits. Pin the
    # exact subsection too, so another adapter cannot silently change it.
    if hashlib.sha256(original.encode('cp1251')).hexdigest() != SOURCE_BLOCK_SHA256:
        raise ValueError('Unsupported stock hypnosis subsection')
    body = source[function_start:end]

    def once(before, after):
        nonlocal body
        if body.count(before) != 1:
            raise ValueError('Party hypnosis anchor changed: ' + repr(before))
        body = body.replace(before, after)

    once('HypnosisTact( int nArmy, int heroId )\n{',
         'HypnosisTact( int nArmy, int heroId )\n{\n'
         '    if(nArmy != 0 && nArmy != 3) return;\n'
         '    int slot = nArmy / 3;\n'
         '    int base = slot * MAX_HYPN_UNITS;')
    once('\tstatic int PrevTime = 0;\n', '')
    body = re.sub(r'\bPrevTime\b', 'OldHypnPrevTime[slot]', body)
    for before, after in (('UnitsToHypn', 'OldHypnUnits'),
                          ('TimesToHypn', 'OldHypnTimes'),
                          ('InitTimes', 'OldHypnStarts'),
                          ('HypnLabels', 'OldHypnLabels')):
        body = re.sub(r'\b' + before + r'\[(i|HypnCnt)\]',
                      lambda match: after + '[base + ' + match[1] + ']', body)
    body = re.sub(r'\bHypnCnt\b', 'OldHypnCount[slot]', body)
    once('GetInputAction(IA_MOUSE_X)', 'GetInputAction(IA_MOUSE_X, nArmy)')
    once('GetInputAction(IA_MOUSE_Y)', 'GetInputAction(IA_MOUSE_Y, nArmy)')
    once('DeleteHypnUnitNum(i);', 'OldHypnDelete(slot, i);')
    # The original marked an uncounted slot when full. Stop before taking a
    # claim, so every -555 marker remains owned and removable on death/exit.
    once('\t\tif( SizeTo(i,',
         '\t\tif(OldHypnCount[slot] >= MAX_HYPN_UNITS) break;\n\t\tif( SizeTo(i,')
    once('if(OldHypnCount[slot] < MAX_HYPN_UNITS - 1 )',
         'if(OldHypnCount[slot] < MAX_HYPN_UNITS)')
    # A low-HP enemy can round the stock duration to zero; labels divide by
    # this value on the next tact. One millisecond preserves next-tact finish.
    line = 'OldHypnTimes[base + OldHypnCount[slot]] = OldHypnTimes[base + OldHypnCount[slot]] * Hp / HYPNOSIS_ENEMY_HP;'
    once(line, line + '\n'
         '                if(OldHypnTimes[base + OldHypnCount[slot]] < 1)\n'
         '                    OldHypnTimes[base + OldHypnCount[slot]] = 1;')
    return (source[:start] + '#ifdef COOP_CAMPAIGN\n' + GLOBALS + body
            + '#else\n' + original + '#endif\n' + source[end:])


SOURCE_BLOCK_SHA256 = 'dfc53e57eedba21a4f7e623d1233a4a265111ae3bcf64673f29e3467b6bb0db9'
