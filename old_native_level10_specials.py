"""Preserve original downloads with independent shared state per terminal.

The original ScriptEvent16 callback owns one timer and one unit. Two heroes
at different terminals would replace that unit and combine unrelated progress.
The adapter keeps map-driven activation, stock ten-second downloads and the
five-terminal quest condition. Only presentation reads the local army.
"""
import hashlib

from old_native_interaction_schema import MapCommand, SpriteIdentity


# Original terminal number, source, ACT43 area, event and trigger evidence.
TERMINALS = (
    (1, SpriteIdentity(0x4FE20, 0x08D24F58, 1361, (3585, 6376.5791015625, 0)),
     (3585, 6378, 50), MapCommand(0x7958D, (136, 16, 0, 0)),
     MapCommand(0x7959D, (43, 3585, 6378, 50))),
    (2, SpriteIdentity(0x504E0, 0x08D287D8, 1361, (5542, 4974, 0)),
     (5542, 4975, 50), MapCommand(0x79D03, (136, 16, 0, 0)),
     MapCommand(0x79D13, (43, 5542, 4975, 50))),
    (3, SpriteIdentity(0x500F0, 0x08D270C0, 1361, (6857, 5784, 0)),
     (6857, 5785, 50), MapCommand(0x79909, (136, 16, 0, 0)),
     MapCommand(0x79919, (43, 6857, 5785, 50))),
    (4, SpriteIdentity(0x50B40, 0x08D2B740, 1361, (7289, 4277, 0)),
     (7289, 4278, 50), MapCommand(0x7A65E, (136, 16, 0, 0)),
     MapCommand(0x7A66E, (43, 7289, 4278, 50))),
    (5, SpriteIdentity(0x51B60, 0x08D32090, 1361, (8500, 832, 0)),
     (8500, 833, 50), MapCommand(0x7B77D, (136, 16, 0, 0)),
     MapCommand(0x7B78D, (43, 8500, 833, 50))),
)

SOURCE_BLOCK_SHA256 = '2e3f97b2a2b0ee00e115f71faa6e10c1f896e1b11ac598c75421efc4df142f29'

HELPER = r'''
#ifdef COOP_CAMPAIGN
static int OldLevel10DownloadUnit[5];
static int OldLevel10DownloadStart[5];
static int OldLevel10DownloadLast[5];
static int OldLevel10DownloadDone[5];
static int OldLevel10DownloadCompleted[5];

OldLevel10DownloadsActive()
{
    return giCurLevCmpgn == 10 && giCurLevCmpgnReal == 10
        && NetProperty(NET_IS_CONNECT) && NetProperty(NET_NO_PLAYERS) == 2
        && ToLower(GetMapName()) == "maps\\level_10.map";
}

OldLevel10DownloadNear(int army, int terminal)
{
    int hero = Flagman(army);
    int base = terminal * 9;
    return hero && Action(hero, ACT_GET_HP) > 0
        && SizeTo(hero, OldLevel10DownloadConfig[base+6],
            OldLevel10DownloadConfig[base+7]) < OldLevel10DownloadConfig[base+8];
}

OldLevel10DownloadEvent(int unit)
{
    if(!unit || GetVid(unit) != 1361) return;
    string name = SendCommand(EXT_GETSPRITENAME, unit);
    int terminal = itoa(name) - 1;
    if(terminal < 0 || terminal >= 5 || OldLevel10DownloadDone[terminal]) return;
    int base = terminal * 9;
    if(GetX(unit) < OldLevel10DownloadConfig[base]
        || GetX(unit) > OldLevel10DownloadConfig[base+1]
        || GetY(unit) < OldLevel10DownloadConfig[base+2]
        || GetY(unit) > OldLevel10DownloadConfig[base+3]
        || GetZ(unit) < OldLevel10DownloadConfig[base+4]
        || GetZ(unit) > OldLevel10DownloadConfig[base+5]) return;
    if(!OldLevel10DownloadNear(0, terminal) && !OldLevel10DownloadNear(3, terminal)) return;
    int now = GetTime();
    if(!OldLevel10DownloadLast[terminal]
        || now - OldLevel10DownloadLast[terminal] > LOADINF_MAX_DELAY)
        OldLevel10DownloadStart[terminal] = now;
    OldLevel10DownloadLast[terminal] = now;
    OldLevel10DownloadUnit[terminal] = unit;
}

OldLevel10DownloadView()
{
    // These stock display variables are never read by the shared controller.
    // Each window shows the terminal its own hero is using.
    StartLoadTime = 0;
    LastLoadTime = 0;
    CompleteTime = 0;
    for(int terminal = 0; terminal < 5; terminal++)
    {
        if(OldLevel10DownloadNear(giCurArmy, terminal))
        {
            if(!OldLevel10DownloadDone[terminal] && OldLevel10DownloadLast[terminal])
            {
                StartLoadTime = OldLevel10DownloadStart[terminal];
                LastLoadTime = OldLevel10DownloadLast[terminal];
            }
            if(OldLevel10DownloadDone[terminal]
                && GetTime() - OldLevel10DownloadCompleted[terminal] < 5000)
                CompleteTime = OldLevel10DownloadCompleted[terminal];
        }
    }
    RefreshLoadInfSpr();
}

OldLevel10DownloadTact()
{
    int now = GetTime();
    for(int terminal = 0; terminal < 5; terminal++)
    {
        if(!OldLevel10DownloadDone[terminal])
        {
            if(OldLevel10DownloadLast[terminal]
                && now - OldLevel10DownloadLast[terminal] > LOADINF_MAX_DELAY)
                OldLevel10DownloadLast[terminal] = 0;
            if(OldLevel10DownloadLast[terminal]
                && now - OldLevel10DownloadStart[terminal] > LOADINF_LOAD_LEN)
            {
                // ACT79 consumers in the map watch the singleton Action10 value.
                // Complete at most one terminal per tact so every original stack
                // receives a whole native map update to consume its notification.
                Action10 = terminal + 1;
                Destroy(OldLevel10DownloadUnit[terminal]);
                OldLevel10DownloadUnit[terminal] = 0;
                OldLevel10DownloadDone[terminal] = 1;
                OldLevel10DownloadCompleted[terminal] = now;
                OldLevel10DownloadLast[terminal] = 0;
                LoadedCnt++;
                if(LoadedCnt == 1)
                    SendCommandA(0, EXT_ADDITEMBYBASEID, SendCommandC(EXT_GetIdByName, "Obj_disk"));
                if(LoadedCnt == 5) giLvl10CompleteTime = now;
                break;
            }
        }
    }
    if(giLvl10CompleteTime && now - giLvl10CompleteTime >= 2000)
    {
        SendCommand(EXT_SETQUESTSTATE, 1, 58, QS_BEGUN);
        giLvl10CompleteTime = 0;
    }
    OldLevel10DownloadView();
}
#endif
'''


def helper():
    """Generate the same controller for the reviewed ordered terminal table."""
    import math
    config = []
    for _, sprite, trigger, _, _ in TERMINALS:
        for value in sprite.xyz:
            config.extend((math.floor(value), math.ceil(value)))
        config.extend(trigger)
    declaration = ('#ifdef COOP_CAMPAIGN\n'
                   'static int OldLevel10DownloadConfig[45] = {'
                   + ', '.join(map(str, config)) + '};\n#endif\n')
    return declaration + HELPER


def adapt_common(source):
    """Compose after the existing common-script adapters, with a block guard.

    The dynamite and money transformations change other functions in this
    file. Pin only the original download section so their composition remains
    possible without weakening the guard around the behavior replaced here.
    """
    source = source.replace('\r\n', '\n')
    start = source.index('static int StartLoadTime = 0;')
    end = source.index('    //\n    if( giCurLevCmpgn == 9 )', start)
    if hashlib.sha256(source[start:end].encode('utf-8')).hexdigest() != SOURCE_BLOCK_SHA256:
        raise ValueError('Unsupported original Level10 download controller')

    def once(before, after):
        nonlocal source
        if source.count(before) != 1:
            raise ValueError('Level10 download composition anchor changed')
        source = source.replace(before, after)

    once('ScriptEvent16( int unit, int var1, int var2 )\n{',
         '#ifdef COOP_CAMPAIGN\nOldLevel10DownloadsActive();\n'
         'OldLevel10DownloadEvent(int unit);\n#endif\n'
         'ScriptEvent16( int unit, int var1, int var2 )\n{\n'
         '#ifdef COOP_CAMPAIGN\n'
         '    if(OldLevel10DownloadsActive())\n'
         '    { OldLevel10DownloadEvent(unit); return; }\n#endif')
    once('RefreshLoadInfSpr();\n//', 'RefreshLoadInfSpr();\n' + helper() + '\n//')
    once('    if( giCurLevCmpgn == 10 || Z_DEBUG)\n',
         '#ifdef COOP_CAMPAIGN\n'
         '    if(OldLevel10DownloadsActive()) OldLevel10DownloadTact();\n'
         '    else\n#endif\n'
         '    if( giCurLevCmpgn == 10 || Z_DEBUG)\n')
    return source
