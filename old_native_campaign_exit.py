"""Party admission after an original map exit request.

ACT77 pops when a quest reaches state1; later quest advancement marks it33
(QS_BEGUN | QS_NOTACTUAL). Preserve that passed condition while the party
gathers. Action9 from the reviewed original map remains mandatory.
"""
from old_native_level02_finish_patch import GATE_HELPER as LEGACY_GATE_HELPER


def gate_helper():
    source = LEGACY_GATE_HELPER.replace('OLD_LEVEL02_FINISH_GATES', 'OLD_MISSION_FINISH_GATES')
    start = source.index('OldFinishGateQuestReady(int gate)')
    end = source.index('OldFinishGateHeroNear(int army, int gate)', start)
    source = source[:start] + r'''OldFinishGateQuestReady(int gate)
{
    if(OldFinishGateUnlocked[gate]) return true;
    int base = gate * 5;
    if(OldFinishGateData[base + 3] < 0)
        OldFinishGateUnlocked[gate] = 1;
    else
    {
        // Source-ID addressing, group index. Ignore only the archive flag:
        // a later quest must not re-arm an ACT77 already popped by the map.
        int state = SendCommand(EXT_GETQUESTSSTATE,
            OldFinishGateData[base + 3], OldFinishGateData[base + 4], 1);
        if(state == QS_BEGUN || state == (QS_BEGUN | QS_NOTACTUAL))
            OldFinishGateUnlocked[gate] = 1;
    }
    return OldFinishGateUnlocked[gate];
}

''' + source[end:]
    anchor = '            return gate;\n    return -1;'
    assert source.count(anchor) == 1
    # Prefer a complete party. Otherwise select a waiting hero's gate for
    # feedback, and recompute while gathering so a different exit still works.
    return source.replace(anchor, '''            return gate;
    for(int waiting = 0; waiting < OLD_MISSION_FINISH_GATES; waiting++)
        if(OldFinishGateQuestReady(waiting)
            && (OldFinishGateHeroNear(0, waiting) || OldFinishGateHeroNear(3, waiting)))
            return waiting;
    return -1;''')
