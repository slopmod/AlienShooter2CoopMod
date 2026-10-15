"""Shared boarding latch for reviewed one-way, script-driven party carriers.

The original map keeps its quest wait, reward and movement commands. Only
its proximity wait is replaced by an unused ACT79 script-variable latch.
The latch is committed atomically with a nearby living party; animation
callbacks subsequently carry the captured heroes in separate seats.
"""
from dataclasses import dataclass
import hashlib
import re

from old_native_interaction_schema import MapCommand, MapIdentity, SpriteIdentity


@dataclass(frozen=True)
class PartyCarrier:
    prefix: str
    map: MapIdentity
    sprite: SpriteIdentity
    commands: tuple[MapCommand, ...]
    proximity: MapCommand
    quest: tuple[int, int]
    gathering_radius: int
    height_tolerance: int
    seats: tuple[tuple[int, int, int], tuple[int, int, int]]
    latch: tuple[int, int]

    def __post_init__(self):
        if not re.fullmatch(r'Old[A-Za-z0-9]+', self.prefix):
            raise ValueError('Invalid carrier script prefix')
        if self.proximity.values[0] != 43 or self.proximity not in self.commands:
            raise ValueError('Carrier must replace its pinned original ACT43')
        if self.gathering_radius < self.proximity.values[3] or self.height_tolerance <= 0:
            raise ValueError('Invalid carrier boarding bounds')
        if not any(c.values == (77, *self.quest, 0) for c in self.commands):
            raise ValueError('Carrier requires its unchanged native ACT77 quest wait')
        if not 1 <= self.latch[0] <= 31 or self.latch[1] == 0:
            raise ValueError('Invalid reserved carrier latch')
        if len(self.seats) != 2 or any(len(seat) != 3 for seat in self.seats):
            raise ValueError('Carrier requires two explicit seat offsets')
        dx, dy = (abs(self.seats[0][i] - self.seats[1][i]) for i in (0, 1))
        if max(dx, dy) + min(dx, dy) * 0.398 < 96:
            raise ValueError('Party carrier seats overlap the shared landing clearance')


def patch_map(data: bytes, route: PartyCarrier):
    """One pinned command overlay; never alter the source installation."""
    if hashlib.sha256(data).hexdigest() != route.map.sha256:
        raise ValueError('Unsupported carrier map: ' + route.map.path)
    start = route.sprite.offset
    if data[start:start + 20] != route.sprite.packed():
        raise ValueError('Carrier sprite changed')
    for command in route.commands:
        if data[command.offset:command.offset + 16] != command.packed():
            raise ValueError('Carrier source stack changed')
    replacement = MapCommand(route.proximity.offset, (79, *route.latch, 0))
    start = route.proximity.offset
    result = data[:start] + replacement.packed() + data[start + 16:]
    return result, {
        'feature': 'old-party-carrier-v1',
        'file': route.map.path,
        'source_sha256': route.map.sha256,
        'output_sha256': hashlib.sha256(result).hexdigest(),
        'command_offset': start,
        'before': list(route.proximity.values),
        'after': list(replacement.values),
        'source_quest_wait_preserved': True,
        'source_movement_and_reward_preserved': True,
        'both_living_required': True,
        'gathering_radius': route.gathering_radius,
        'source_initiator_radius': route.proximity.values[3],
        'seat_offsets': [list(seat) for seat in route.seats],
        'native_runtime_tested': False,
    }


def helper(route: PartyCarrier):
    """Generate one bounded instance using only deterministic world state."""
    prefix = route.prefix
    x, y, z = (int(v) for v in route.sprite.xyz)
    _, tx, ty, original_radius = route.proximity.values
    seat_values = ', '.join(str(value) for seat in route.seats for value in seat)
    # ActionN is a stock shared map variable. Its ACT79 equality wait must
    # remain raised: do not consume it on a main-tact/animation ordering guess.
    return f'''
static int {prefix}Unit = 0;
static int {prefix}Boarded = 0;
static int {prefix}Riders[8];
static int {prefix}Seats[6] = {{{seat_values}}};
static int {prefix}Notice = 0;

{prefix}Near(int army, int radius)
{{
    int hero = Flagman(army);
    if(!hero || Action(hero, ACT_GET_HP) <= 0) return false;
    return abs(GetZ(hero) - {z}) <= {route.height_tolerance}
        && SizeTo(hero, {tx}, {ty}) < radius;
}}

{prefix}ShowWaiting(int visible)
{{
    if(visible && !{prefix}Notice)
        {prefix}Notice = CreateText(13, ScreenX()/2, ScreenY()/2+95, 0,
            "Подойдите к тележке вместе с напарником.", BEH_CENTER);
    if(!visible && {prefix}Notice)
    {{
        Destroy({prefix}Notice);
        {prefix}Notice = 0;
    }}
}}

{prefix}Carry(int unit)
{{
    if(!{prefix}Boarded || unit != {prefix}Unit) return;
    int seat = 0;
    for(int army = 0; army <= 3; army = army + 3)
    {{
        int hero = Flagman(army);
        // Capture identity at boarding. A dead or replacement flagman must
        // never be pulled from another room by an old animation callback.
        if(hero && hero == {prefix}Riders[army] && Action(hero, ACT_GET_HP) > 0)
            Action(hero, ACT_CHANGE_COOR,
                GetX(unit) + {prefix}Seats[seat],
                GetY(unit) + {prefix}Seats[seat+1],
                GetZ(unit) + {prefix}Seats[seat+2]);
        seat = seat + 3;
    }}
}}

{prefix}Tact()
{{
    if(!{prefix}Unit)
    {{
        int candidate = FindNearestSprite(GETSPRITE_VID({route.sprite.vid}), {x}, {y}, 3);
        if(candidate && GetX(candidate) == {x} && GetY(candidate) == {y}
            && GetZ(candidate) == {z}) {prefix}Unit = candidate;
    }}
    if(!{prefix}Unit) return;
    if(!{prefix}Boarded)
    {{
        int state = SendCommand(EXT_GETQUESTSSTATE, {route.quest[0]-1}, {route.quest[1]}, 1);
        if(state != QS_BEGUN && state != (QS_BEGUN | QS_NOTACTUAL))
        {{ {prefix}ShowWaiting(0); return; }}
        int near0 = {prefix}Near(0, {route.gathering_radius});
        int near3 = {prefix}Near(3, {route.gathering_radius});
        // Preserve the original activation radius for an initiating hero;
        // the second hero can gather beside it without overlapping bodies.
        int initiating = {prefix}Near(0, {original_radius}) || {prefix}Near(3, {original_radius});
        if(!near0 || !near3 || !initiating)
        {{ {prefix}ShowWaiting(near0 || near3); return; }}
        {prefix}Riders[0] = Flagman(0);
        {prefix}Riders[3] = Flagman(3);
        {prefix}Boarded = 1;
        Action{route.latch[0]} = {route.latch[1]};
        {prefix}ShowWaiting(0);
        Log2("Coop carrier: both heroes boarded");
    }}
    // Also position riders during native pauses/arrival, where ANI_GO may
    // stop firing before the original delayed Action9 exit request arrives.
    {prefix}Carry({prefix}Unit);
}}
'''
