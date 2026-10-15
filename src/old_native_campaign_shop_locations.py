"""Physical-map shop access with multiple vendors and independent hero range.

Native RPG/catalog indices remain unchanged. Logical stage IDs distinguish
the three road maps that intentionally share native campaign number seven.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path

from old_native_interaction_schema import MapCommand, SpriteIdentity


@dataclass(frozen=True)
class ShopSource:
    stage: int
    map_sha256: str
    source: SpriteIdentity
    trigger: tuple[int, int, int]
    commands: tuple[MapCommand, ...]


RELOADED_SOURCES = (
    ShopSource(72, '39c5c2388db497d2a86ada94ffd505d24ff715306801c30143c939b680246d18',
        SpriteIdentity(0xE1254, 0xB9925D0, 922, (11743, 12233, 0)),
        (11741, 12213, 25), (
            MapCommand(0x15BA61, (71, 3, 1, 0)),
            MapCommand(0x15BA71, (43, 11819, 12307, 100)),
            MapCommand(0x15BA81, (131, 6, 1, 0)),
            MapCommand(0x15BA91, (43, 11741, 12213, 25)),
        )),
    ShopSource(72, '39c5c2388db497d2a86ada94ffd505d24ff715306801c30143c939b680246d18',
        SpriteIdentity(0xE2E14, 0xB99ABD0, 922, (22095, 11479, 0)),
        (22092, 11459, 25), (
            MapCommand(0x15C762, (71, 3, 1, 0)),
            MapCommand(0x15C772, (43, 22170, 11553, 100)),
            MapCommand(0x15C782, (131, 6, 1, 0)),
            MapCommand(0x15C792, (43, 22092, 11459, 25)),
        )),
    ShopSource(73, '0c7b10edb58b1730b9e05bd62fcdefb8afe15ce719e9f29d683841bbc0443608',
        SpriteIdentity(0x9B7D4, 0x10DB0F78, 922, (3545, 514, 0)),
        (3542, 494, 25), (
            MapCommand(0xE67CC, (71, 3, 1, 0)),
            MapCommand(0xE67DC, (43, 3620, 588, 100)),
            MapCommand(0xE67EC, (131, 6, 1, 0)),
            MapCommand(0xE67FC, (43, 3542, 494, 25)),
        )),
)


def validate_sources(root):
    from old_native_campaign_missions import MISSIONS, mission_source
    missions = {m.number: m for m in MISSIONS}
    for stage in (72, 73):
        if stage not in missions:
            continue
        mission = missions[stage]
        sources = tuple(s for s in RELOADED_SOURCES if s.stage == stage)
        if tuple(s.trigger[:2] for s in sources) != mission.shop_locations:
            raise ValueError('Unreviewed road-stage shop locations')
        data = mission_source(Path(root), mission.path).read_bytes()
        if hashlib.sha256(data).hexdigest() != mission.map_sha256:
            raise ValueError('Unsupported road-stage shop map')
        for source in sources:
            if source.map_sha256 != mission.map_sha256:
                raise ValueError('Road-stage shop evidence identity mismatch')
            sprite = source.source
            if data[sprite.offset:sprite.offset + 20] != sprite.packed():
                raise ValueError('Changed road-stage shop sprite')
            for command in source.commands:
                if data[command.offset:command.offset + 16] != command.packed():
                    raise ValueError('Changed road-stage shop command')


def helper(missions):
    shops = tuple(m for m in missions if m.shop_locations or m.entry_shop)
    rows = [(m.number, x, y) for m in shops for x, y in m.shop_locations]
    cases = []
    for mission in shops:
        path = mission.path.lower().replace('/', '\\\\')
        cases.append(f'    if(giCurLevCmpgnReal == {mission.native} && map == "{path}") return {mission.number};')
    values = ', '.join(str(value) for row in rows for value in row)
    return f'''
static int OldShopLocations[{len(rows) * 3}] = {{{values}}};

OldShopPhysicalStage()
{{
    string map = ToLower(GetMapName());
''' + '\n'.join(cases) + f'''
    return 0;
}}

OldShopMissionAvailable()
{{
    return OldShopPhysicalStage() != 0;
}}

OldShopLocation(int army, int axis)
{{
    int stage = OldShopPhysicalStage();
    int unit = Flagman(army);
    if(!stage || !unit) return 0;
    int chosen = -1;
    int nearest = 0;
    for(int index = 0; index < {len(rows) * 3}; index = index + 3)
    {{
        if(OldShopLocations[index] == stage)
        {{
            int distance = SizeTo(unit, OldShopLocations[index+1], OldShopLocations[index+2]);
            if(chosen < 0 || distance < nearest)
            {{ chosen = index; nearest = distance; }}
        }}
    }}
    if(chosen < 0) return 0;
    return OldShopLocations[chosen+1+axis];
}}

OldShopLocationX(int army) {{ return OldShopLocation(army, 0); }}
OldShopLocationY(int army) {{ return OldShopLocation(army, 1); }}
'''
