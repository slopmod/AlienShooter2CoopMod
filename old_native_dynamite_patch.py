"""Consume the original Level_01 charge from its actual party inventory owner.

The native map stack still creates the charge and performs the demolition.
This guarded script transformation only replaces its inventory callback and
records the synchronous actor/owner for the ordinary-input regression.
"""
import hashlib

FEATURE = 'old-campaign-party-dynamite-v1'
SOURCE_SHA256 = '66b1844d3875c14188ba9002b47a1d5e8e0e020d768bbd64a15d56a0c2df9284'

CALLBACK = '''static int OldDynamitePlantArmy = -1;
static int OldDynamiteOwnerArmy = -1;
static int OldDynamitePlantTime = -1;
static int OldDynamitePlantCalls = 0;
static int OldDynamiteConsumeCalls = 0;
static int OldDynamiteFault = 0;

F770_14(int unit)
{
    OldDynamitePlantCalls++;
    if(OldDynamitePlantCalls != 1)
    {
        OldDynamiteFault = 1;
        return;
    }
    OldDynamitePlantTime = GetTime();
    // The admitted native stack creates VID770 immediately after ACT43.
    // Use that same native distance export and the same army preference.
    for(int army = 0; army <= 3; army = army + 3)
    {
        int hero = Flagman(army);
        if(OldDynamitePlantArmy == -1 && hero
            && SizeTo(hero, 6554, 2606) < 70)
            OldDynamitePlantArmy = army;
        if(OldDynamiteOwnerArmy == -1
            && SendCommandA(army, EXT_IFHASITEM, ITM_DYNAMITE))
            OldDynamiteOwnerArmy = army;
    }
    if(OldDynamitePlantArmy == -1 || OldDynamiteOwnerArmy == -1)
    {
        OldDynamiteFault = 2;
        return;
    }
    SendCommandA(OldDynamiteOwnerArmy, EXT_REMOVEITEMIFHAS, ITM_DYNAMITE);
    OldDynamiteConsumeCalls++;
    if(SendCommandA(OldDynamiteOwnerArmy, EXT_IFHASITEM, ITM_DYNAMITE))
        OldDynamiteFault = 3;
}
'''


def patch(source: bytes) -> tuple[str, dict]:
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported original common_compaign.lgc')
    text = source.decode('cp1251').replace('\r\n', '\n')
    start = text.index('F770_14( int unit )\n{')
    end = text.index('\n}', start) + 2
    original = text[start:end]
    if original.count('SendCommandA( -1, EXT_REMOVEITEMIFHAS, ITM_DYNAMITE );') != 1:
        raise ValueError('Original dynamite inventory callback changed')
    text = text[:start] + CALLBACK.rstrip() + text[end:]
    return text, {
        'feature': FEATURE, 'source_sha256': SOURCE_SHA256,
        'output_sha256': hashlib.sha256(text.replace('\n', '\r\n').encode('cp1251')).hexdigest(),
        'owner_order': [0, 3], 'actor_order': [0, 3],
        'scope': 'Level_01 original VID770 callback; either party inventory',
        'native_spawn_and_demolition_preserved': True,
    }
