"""Generate the bounded Level_01 shared roof trigger helper without file writes.

Only h5 and h6 have been admitted: their original map stacks contain proximity
checks followed by Action5, with no delay, quest, reward, or other world action.
The caller writes the generated helper into an isolated campaign runtime,
includes it after common_compaign.lgc, and calls OldRoofTact immediately before
CompaignGameTact. Original maps and the global ACT43 story policy stay intact.
"""
import hashlib
from pathlib import Path
import struct


FEATURE = 'old-campaign-roofs-v1'
MAP_SHA256 = '5bdc5f4ff57e06feeb7b02d36c09d76e01ef5d258b05e3c45c4e47523df694ec'
LEVEL_SHA256 = '84cb15346b52433dba442044bd746eccdb2e3f896c31f487e53ef81b7284dee0'
COMMON_SHA256 = '66b1844d3875c14188ba9002b47a1d5e8e0e020d768bbd64a15d56a0c2df9284'

ROOFS = {
    5: {'vid': 1212, 'positions': [(5197, 3223, 0)],
        'triggers': [(5301, 3239, 60)],
        'commands': [(0xA3A35, (131, 5, 5, 0)), (0xA3A45, (43, 5301, 3239, 60))]},
    6: {'vid': 1521,
        'positions': [(4325, 2274, 180), (4244, 2330, 180), (4712, 2000, 180),
                      (4457, 2184, 180), (4581, 2090, 180), (4186, 1992, 180),
                      (3973, 2139, 180), (4054, 2083, 180), (4966, 1817, 180),
                      (5094, 1724, 180), (4838, 1909, 180), (4440, 1808, 180),
                      (4565, 1717, 180), (4310, 1899, 180), (5172, 1669, 180),
                      (4901, 1478, 180), (4693, 1625, 180), (4822, 1532, 180)],
        'triggers': [(4612, 2262, 150), (4968, 2030, 150)],
        'commands': [(0xA3FE3, (131, 5, 6, 0)), (0xA3FF3, (43, 4612, 2262, 150)),
                     (0xA4007, (131, 5, 6, 0)), (0xA4017, (43, 4968, 2030, 150))]},
}


def patch(map_source: bytes, level_source: bytes, common_source: bytes) -> tuple[str, dict]:
    for name, source, expected in (
        ('Level_01.map', map_source, MAP_SHA256),
        ('Level_01.lgc', level_source, LEVEL_SHA256),
        ('common_compaign.lgc', common_source, COMMON_SHA256),
    ):
        if hashlib.sha256(source).hexdigest() != expected:
            raise ValueError('Unsupported original roof source: ' + name)
    common_text = common_source.decode('cp1251')
    if common_text.count('SendCommand( EXT_KILLOBJECTS, Action5 );') != 1:
        raise ValueError('Roof Action5 consumption guard failed')
    if level_source.decode('cp1251').count('  CompaignGameTact();') != 1:
        raise ValueError('Roof campaign call guard failed')
    for roof in ROOFS.values():
        for offset, expected in roof['commands']:
            if struct.unpack_from('<4i', map_source, offset) != expected:
                raise ValueError('Roof map command guard failed at ' + hex(offset))

    text = '''// Generated only for the hash-guarded original Level_01 campaign.
// Both native simulations must call this once before CompaignGameTact.
#ifndef OLD_CAMPAIGN_ROOFS_H
#define OLD_CAMPAIGN_ROOFS_H 1
static int OldRoof5Done = 0;
static int OldRoof6Done = 0;
static int OldRoof5Army = -1;
static int OldRoof6Army = -1;
static int OldRoof5Time = -1;
static int OldRoof6Time = -1;
static int OldRoofObservedTime = -1;
static int OldRoof5Remaining = 0;
static int OldRoof6Remaining = 0;

OldRoofNearbyArmy(int group)
{
    for(int army = 0; army <= 3; army = army + 3)
    {
        int hero = Flagman(army);
        if(hero && Action(hero, ACT_GET_HP) > 0)
        {
            if(group == 5 && SizeTo(hero, 5301, 3239) < 60)
                return army;
            if(group == 6 && (SizeTo(hero, 4612, 2262) < 150
                || SizeTo(hero, 4968, 2030) < 150))
                return army;
        }
    }
    return -1;
}

OldRoofTact()
{
    // Preserve a queued stock host event even if the hero has already left.
    // Clear subsequent host events for these groups after our earlier removal.
    int request = Action5;
    if(request == 5 || request == 6)
        Action5 = -1;
    if(!OldRoof5Done)
    {
        int army5 = OldRoofNearbyArmy(5);
        if(request == 5)
            army5 = 0;
        if(army5 != -1)
        {
            SendCommand(EXT_KILLOBJECTS, 5);
            OldRoof5Done = 1;
            OldRoof5Army = army5;
            OldRoof5Time = GetTime();
            OldRoofObservedTime = -1;
        }
    }
    if(!OldRoof6Done)
    {
        int army6 = OldRoofNearbyArmy(6);
        if(request == 6)
            army6 = 0;
        if(army6 != -1)
        {
            SendCommand(EXT_KILLOBJECTS, 6);
            OldRoof6Done = 1;
            OldRoof6Army = army6;
            OldRoof6Time = GetTime();
            OldRoofObservedTime = -1;
        }
    }
}

// Diagnostic only. Do not call from inside an existing FirstSprite loop.
// Counts real map objects, independently of the Done flags; no cached handles.
OldRoofCount(int group)
{
    if(group != 5 && group != 6)
        return -1;
    if(OldRoofObservedTime != GetTime())
    {
        OldRoof5Remaining = 0;
        OldRoof6Remaining = 0;
        for(int unit = FirstSprite(); unit; unit = NextSprite())
        {
            int vid = GetVid(unit);
'''
    for group, roof in ROOFS.items():
        checks = ['(GetX(unit) == %d && GetY(unit) == %d && GetZ(unit) == %d)' % xyz
                  for xyz in roof['positions']]
        condition = '\n                || '.join(checks)
        text += f'''            if(vid == {roof['vid']} && ({condition}))
                OldRoof{group}Remaining = OldRoof{group}Remaining + 1;
'''
    text += '''        }
        OldRoofObservedTime = GetTime();
    }
    if(group == 5)
        return OldRoof5Remaining;
    return OldRoof6Remaining;
}
#endif
'''
    encoded = text.replace('\n', '\r\n').encode('cp1251')
    return text, {
        'feature': FEATURE,
        'map_name': 'Level_01',
        'source_sha256': {'Maps/Level_01.map': MAP_SHA256,
                          'Maps/Level_01.lgc': LEVEL_SHA256,
                          'Maps/common_compaign.lgc': COMMON_SHA256},
        'output_sha256': hashlib.sha256(encoded).hexdigest(),
        'helper_file': 'Maps/old_campaign_roofs.lgc',
        'tact_call': 'OldRoofTact();',
        'insert_immediately_before': 'CompaignGameTact();',
        'army_order': [0, 3],
        'requires_live_hero_for_new_proximity_trigger': True,
        'preserves_queued_stock_host_action5': True,
        'world_removal_on_both_peers': True,
        'local_render_only': False,
        'source_map_unchanged': True,
        'source_stacks_have_pause': False,
        'roof_groups': {str(group): {'vid': roof['vid'], 'positions': roof['positions'],
                                   'triggers': roof['triggers'],
                                   'initial_count': len(roof['positions'])}
                        for group, roof in ROOFS.items()},
        'observer_fields': ['OldRoof5Done', 'OldRoof6Done', 'OldRoof5Army', 'OldRoof6Army',
                            'OldRoof5Time', 'OldRoof6Time', 'OldRoofCount(5)', 'OldRoofCount(6)'],
        'runtime_tested': False,
    }


def prepare(old_root: Path) -> tuple[str, dict]:
    maps = Path(old_root) / 'Maps'
    return patch((maps / 'Level_01.map').read_bytes(), (maps / 'Level_01.lgc').read_bytes(),
                 (maps / 'common_compaign.lgc').read_bytes())
