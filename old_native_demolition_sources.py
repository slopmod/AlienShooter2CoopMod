"""Consume planted campaign charges from their actual party inventory owner.

Source admission is explicit: the original map still creates VID770 and runs
the explosion. This shared callback serves the two reviewed planting locations;
scripted Level06 explosions do not consume a player's carried item. The legacy
Level01-only patch remains unchanged for non-progression builds.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path

from old_native_dynamite_patch import CALLBACK
from old_native_interaction_schema import MapCommand, MapIdentity, SpriteIdentity


FEATURE = 'old-campaign-admitted-demolition-v1'


@dataclass(frozen=True)
class DemolitionSource:
    map: MapIdentity
    source: SpriteIdentity
    trigger: tuple[int, int, int]
    charge: tuple[int, int]
    commands: tuple[MapCommand, ...]


SOURCES = (
    DemolitionSource(
        MapIdentity('level01', 'Maps/Level_01.map',
                    '5bdc5f4ff57e06feeb7b02d36c09d76e01ef5d258b05e3c45c4e47523df694ec'),
        SpriteIdentity(0x6CCE0, 0x189B34E8, 922, (6446, 2600, 10)),
        (6554, 2606, 70), (6553, 2615), (
            MapCommand(0xA3B30, (35, 770, 6553, 2615)),
            MapCommand(0xA3B50, (43, 6554, 2606, 70)),
            MapCommand(0xA3B60, (77, 1, 5, 0)),
            MapCommand(0xA3BB4, (35, 770, 6553, 2615)),
            MapCommand(0xA3BC4, (43, 6554, 2606, 70)),
            MapCommand(0xA3BD4, (77, 2, 8, 0)),
        )),
    DemolitionSource(
        MapIdentity('level13', 'Maps/Level_13.map',
                    '83d5e267e1069a7d6861737f8807b88a5180db60ecd39d2823818c0ca788fd0e'),
        SpriteIdentity(0x5C8A0, 0x50168090, 922, (7787, 1718, 0)),
        (7966, 1692, 50), (7967, 1692), (
            MapCommand(0x8D427, (131, 10, 1, 0)),
            MapCommand(0x8D437, (35, 770, 7967, 1692)),
            MapCommand(0x8D447, (43, 7966, 1692, 50)),
            MapCommand(0x8D457, (77, 1, 69, 0)),
        )),
)


def validate_sources(root):
    for source in SOURCES:
        data = (Path(root) / source.map.path).read_bytes()
        if hashlib.sha256(data).hexdigest() != source.map.sha256:
            raise ValueError('Unsupported demolition map: ' + source.map.path)
        if data[source.source.offset:source.source.offset + 20] != source.source.packed():
            raise ValueError('Changed demolition source sprite')
        for command in source.commands:
            if data[command.offset:command.offset + 16] != command.packed():
                raise ValueError('Changed demolition source command')


def _callback():
    selectors = []
    for index, source in enumerate(SOURCES):
        path = source.map.path.lower().replace('/', '\\\\')
        x, y = source.charge
        selectors.append(f'    if(map == "{path}" && GetX(unit) == {x} && GetY(unit) == {y}) return {index};')
    triggers = ', '.join(str(v) for source in SOURCES for v in source.trigger)
    return r'''static int OldDynamitePlantArmy = -1;
static int OldDynamiteOwnerArmy = -1;
static int OldDynamitePlantTime = -1;
static int OldDynamitePlantCalls = 0;
static int OldDynamiteConsumeCalls = 0;
static int OldDynamiteFault = 0;
static int OldDemolitionDone[@@COUNT@@];
static int OldDemolitionTrigger[] = {@@TRIGGERS@@};

OldDemolitionSource(int unit)
{
    if(!unit || GetVid(unit) != 770) return -1;
    string map = ToLower(GetMapName());
@@SELECTORS@@
    return -1;
}

F770_14(int unit)
{
    int source = OldDemolitionSource(unit);
    // Other uses of VID770 are scripted explosions, not item planting.
    if(source < 0) return;
    OldDynamitePlantCalls++;
    if(OldDemolitionDone[source])
    {
        OldDynamiteFault = 1;
        return;
    }
    OldDynamitePlantArmy = -1;
    OldDynamiteOwnerArmy = -1;
    OldDynamitePlantTime = GetTime();
    int base = source * 3;
    for(int army = 0; army <= 3; army = army + 3)
    {
        int hero = Flagman(army);
        if(OldDynamitePlantArmy == -1 && hero && Action(hero, ACT_GET_HP) > 0
            && SizeTo(hero, OldDemolitionTrigger[base], OldDemolitionTrigger[base + 1])
                < OldDemolitionTrigger[base + 2])
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
    // The native callback is synchronous with the admitted map stack.
    // Owner preference is deterministic and consumes only one party item.
    OldDemolitionDone[source] = 1;
    SendCommandA(OldDynamiteOwnerArmy, EXT_REMOVEITEMIFHAS, ITM_DYNAMITE);
    OldDynamiteConsumeCalls++;
}
'''.replace('@@COUNT@@', str(len(SOURCES))).replace('@@TRIGGERS@@', triggers).replace(
        '@@SELECTORS@@', '\n'.join(selectors))


def adapt_common(source, root):
    """Apply after the existing hash-guarded campaign common composition."""
    validate_sources(root)
    original = CALLBACK.rstrip()
    if source.count(original) != 1:
        raise ValueError('Expected original party dynamite callback exactly once')
    return source.replace(original, _callback().rstrip())
