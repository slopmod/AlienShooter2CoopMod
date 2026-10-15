"""Reviewed remote consoles select their user, not the hero nearest the gun.

The original map retains its activation/return waits and stationary weapon.
This table only assigns the event to a living hero inside the source ACT43.
Remote robot phases with their own lifecycle are handled separately.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path

from old_native_interaction_schema import MapCommand, MapIdentity, SpriteIdentity
from old_native_level05_interactions import LEVEL05


@dataclass(frozen=True)
class VehicleConsole:
    map: MapIdentity
    native_mission: int
    source: SpriteIdentity
    vehicle: SpriteIdentity
    trigger: tuple[int, int, int]
    direction: int
    commands: tuple[MapCommand, ...]


CONSOLES = (
    VehicleConsole(
        LEVEL05, 5,
        SpriteIdentity(0x64730, 0x186AE5A8, 922, (5487, 7983, 0)),
        SpriteIdentity(0x649A0, 0x186AF0F0, 3010, (5670, 7812, 0)),
        (5506, 7954, 40), 38, (
            MapCommand(0xA007B, (71, 3, 0, 0)),
            MapCommand(0xA008B, (43, 5363, 8074, 130)),
            MapCommand(0xA009B, (136, 15, 3010, 38)),
            MapCommand(0xA00AB, (43, 5506, 7954, 40)),
        )),
)


def validate_sources(root):
    for console in CONSOLES:
        data = (Path(root) / console.map.path).read_bytes()
        if hashlib.sha256(data).hexdigest() != console.map.sha256:
            raise ValueError('Unsupported vehicle console map: ' + console.map.path)
        for sprite in (console.source, console.vehicle):
            if data[sprite.offset:sprite.offset + 20] != sprite.packed():
                raise ValueError('Changed vehicle console sprite')
        for command in console.commands:
            if data[command.offset:command.offset + 16] != command.packed():
                raise ValueError('Changed vehicle console command')


def helper():
    branches = []
    for console in CONSOLES:
        path = console.map.path.lower().replace('/', '\\\\')
        sx, sy, sz = (int(v) for v in console.source.xyz)
        vx, vy, vz = (int(v) for v in console.vehicle.xyz)
        tx, ty, radius = console.trigger
        branches.append(f'''    if(giCurLevCmpgn == {console.native_mission}
        && giCurLevCmpgnReal == {console.native_mission}
        && map == "{path}" && vid == {console.vehicle.vid})
    {{
        // Consume malformed calls within this admitted map rather than
        // falling through to the original nearest-hero search.
        if(!unit || GetVid(unit) != {console.source.vid}
            || GetX(unit) != {sx} || GetY(unit) != {sy} || GetZ(unit) != {sz}
            || direction != {console.direction}) return true;
        int weapon = FindNearestSprite(GETSPRITE_VID({console.vehicle.vid}), {vx}, {vy}, 3);
        if(!weapon || GetX(weapon) != {vx} || GetY(weapon) != {vy}
            || GetZ(weapon) != {vz}) return true;
        for(int army = 0; army <= 3; army = army + 3)
        {{
            int hero = Flagman(army);
            if(hero && IsCharacter(hero) && Action(hero, ACT_GET_HP) > 0
                && SizeTo(hero, {tx}, {ty}) < {radius}
                && TryBecomeAFlagman(weapon, 100000, true, direction, army))
            {{
                Log("Coop vehicle console: army=" + itoa(army) + " vid=" + itoa(vid));
                break;
            }}
        }}
        return true;
    }}''')
    return '''#ifdef COOP_CAMPAIGN
OldPartyVehicleConsoleEvent(int unit, int vid, int direction)
{
    if(!NetProperty(NET_IS_CONNECT) || NetProperty(NET_NO_PLAYERS) != 2) return false;
    string map = ToLower(GetMapName());
''' + '\n'.join(branches) + '''
    return false;
}
#endif
'''


def adapt_vehicle(source):
    from old_native_campaign_progression import once
    return once(source, 'ScriptEvent15( int unit, int iVidGun, int iHeroDir )\n{',
        helper() + '\nScriptEvent15( int unit, int iVidGun, int iHeroDir )\n{\n'
        '#ifdef COOP_CAMPAIGN\n'
        '    if(OldPartyVehicleConsoleEvent(unit, iVidGun, iHeroDir)) return;\n'
        '#endif')
