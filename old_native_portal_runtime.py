"""Generate one shared logical-portal controller from the audited event catalog.

Native movement/fade/control stays in teleport-v1. This layer owns only event
activation, per-hero admission, queuing and completion. Historical per-map
patches are not part of this composition and remain reproducible separately.
"""
import hashlib
import json
from pathlib import Path
import re
import math

from old_native_interaction_registry import REGISTRY, PORTALS, BUNKER_PORTALS, ADMIN_PORTAL

FEATURE = 'old-campaign-shared-portals-v3'
TELEPORT_SHA256 = '4e5f8911233761edfdfb3a350e6c26d4d5af3866aa3c6cb772144f2b77677fb1'
LEVEL02_SHA256 = '36dd1d49878c5566f44c19b527047c19312813dc82faee18661e17635df6490a'

# The same controller supports every catalog row. Adding a portal does not
# require changing the helper, event dispatcher, finish hook or native ABI.
FIELDS = ('group', 'vid', 'sx', 'sy', 'sz', 'x', 'y', 'radius', 'gx', 'gy', 'gz',
          'reusable', 'margin', 'strict', 'check_z', 'min_z', 'max_z',
          'arrival_min_z', 'arrival_max_z', 'create_goal', 'leader_event', 'consume_invalid',
          'sx_max', 'sy_max', 'sz_max', 'closed_group', 'closed_quest', 'animation_z')

CORE = r'''
OldPortalSpec(int portal, int field)
{
    return OldPortalConfig[portal * OLD_PORTAL_FIELDS + field];
}

OldPortalGroupFlight(int group)
{
    if(OldPortalInFlight && OldPortalSpec(OldPortalInFlight - 1, OP_GROUP) == group)
        return OldPortalInFlight;
    return 0;
}

OldPortalNear(int hero, int portal, int margin)
{
    if(!hero) return false;
    int radius = OldPortalSpec(portal, OP_RADIUS) + margin;
    if(OldPortalSpec(portal, OP_STRICT))
        return SizeTo(hero, OldPortalSpec(portal, OP_X), OldPortalSpec(portal, OP_Y)) < radius;
    return SizeTo(hero, OldPortalSpec(portal, OP_X), OldPortalSpec(portal, OP_Y)) <= radius;
}

OldPortalSource(int unit, int portal)
{
    return unit && GetVid(unit) == OldPortalSpec(portal, OP_VID)
        && GetX(unit) >= OldPortalSpec(portal, OP_SX) && GetX(unit) <= OldPortalSpec(portal, OP_SX_MAX)
        && GetY(unit) >= OldPortalSpec(portal, OP_SY) && GetY(unit) <= OldPortalSpec(portal, OP_SY_MAX)
        && GetZ(unit) >= OldPortalSpec(portal, OP_SZ) && GetZ(unit) <= OldPortalSpec(portal, OP_SZ_MAX);
}

OldPortalOwnsUnit(int unit)
{
    OldPortalInit();
    for(int p = 0; p < OLD_PORTAL_COUNT; p++)
        if(OldPortalGroupActive[OldPortalSpec(p, OP_GROUP)] && OldPortalSource(unit, p))
            return true;
    return false;
}

OldPortalHoldArrival(int army, int hero)
{
    // A destination can be another group's source, even before its first map
    // event. Remember the arrival independently of registration and timers.
    // Each player must leave that zone before deliberately entering it again.
    for(int p = 0; p < OLD_PORTAL_COUNT; p++)
    {
        if(OldPortalGroupActive[OldPortalSpec(p, OP_GROUP)] && OldPortalSpec(p, OP_REUSABLE)
            && OldPortalNear(hero, p, OldPortalSpec(p, OP_MARGIN))
            && (!OldPortalSpec(p, OP_CHECK_Z)
                || (GetZ(hero) >= OldPortalSpec(p, OP_MIN_Z) && GetZ(hero) <= OldPortalSpec(p, OP_MAX_Z))))
        {
            OldPortalArrivalBlocked[p * 8 + army] = 1;
            OldPortalArmed[p * 8 + army] = 0;
        }
    }
}

OldPortalGoal(int unit, int portal, int createMissing)
{
    int goal = Action(unit, ACT_GET_GOAL);
    if(!goal && createMissing)
    {
        Action(unit, ACT_SET_GOAL_COOR, OldPortalSpec(portal, OP_GX),
            OldPortalSpec(portal, OP_GY), OldPortalSpec(portal, OP_GZ));
        goal = Action(unit, ACT_GET_GOAL);
    }
    return goal && GetX(goal) == OldPortalSpec(portal, OP_GX)
        && GetY(goal) == OldPortalSpec(portal, OP_GY)
        && GetZ(goal) == OldPortalSpec(portal, OP_GZ);
}

OldPortalRegister(int group)
{
    if(!OldPortalGroupActive[group] || OldPortalFault[group]) return false;
    for(int p = 0; p < OLD_PORTAL_COUNT; p++)
    {
        if(OldPortalSpec(p, OP_GROUP) == group)
        {
            // Reusable groups retain the original identity recheck. Single
            // event routes use their captured original event sprite.
            int unit = OldPortalUnits[p];
            if(OldPortalSpec(p, OP_REUSABLE) || !unit)
                unit = FindNearestSprite(GETSPRITE_VID(OldPortalSpec(p, OP_VID)),
                    OldPortalSpec(p, OP_SX), OldPortalSpec(p, OP_SY), 2);
            if(!OldPortalSource(unit, p))
            {
                OldPortalFault[group] = 1;
                return false;
            }
            if(OldPortalReady[group] && unit != OldPortalUnits[p])
            {
                OldPortalFault[group] = 2;
                return false;
            }
            if(!OldPortalGoal(unit, p, !OldPortalReady[group] && OldPortalSpec(p, OP_CREATE_GOAL)))
            {
                OldPortalFault[group] = 3;
                return false;
            }
            if(!OldPortalReady[group])
            {
                OldPortalUnits[p] = unit;
                for(int army = 0; army <= 3; army = army + 3)
                    OldPortalArmed[p * 8 + army] = !OldPortalArrivalBlocked[p * 8 + army];
            }
        }
    }
    OldPortalReady[group] = 1;
    return true;
}

OldPortalTryStart(int portal, int army)
{
    int group = OldPortalSpec(portal, OP_GROUP);
    int index = portal * 8 + army;
    if(OldPortalSpec(portal, OP_CLOSED_GROUP) >= 0
        && SendCommand(EXT_GETQUESTSSTATE, OldPortalSpec(portal, OP_CLOSED_GROUP),
            OldPortalSpec(portal, OP_CLOSED_QUEST), 1) == 1) return false;
    if(gCurrentTeleport || !OldPortalReady[group] || OldPortalFault[group]
        || !OldPortalArmed[index] || OldPortalArrivalBlocked[index])
        return false;
    int hero = Flagman(army);
    int unit = OldPortalUnits[portal];
    if(!hero || Action(hero, ACT_GET_HP) <= 0 || !OldPortalNear(hero, portal, 0)
        || Action(unit, ACT_GET_TIMER)) return false;
    if(OldPortalSpec(portal, OP_CHECK_Z)
        && (GetZ(hero) < OldPortalSpec(portal, OP_MIN_Z) || GetZ(hero) > OldPortalSpec(portal, OP_MAX_Z)))
        return false;
    int goal = Action(unit, ACT_GET_GOAL);
    if(!goal || CanPlace(GetVid(hero), GetX(goal), GetY(goal), GetZ(goal)))
    {
        OldPortalBlocked[group] = portal + 1;
        OldPortalBlockedArmy[group] = army;
        return false;
    }
    if(!BeginTeleporting2(unit, 0, 0, false, TELEPORT_TIME_SCRIPT, army)) return false;
    // Preserve the stock up/down animation for ScriptEvent11/12. Shared
    // admission still chooses the triggering army, including queued guests.
    giHeroAnimZ = OldPortalSpec(portal, OP_ANIMATION_Z);
    OldPortalArmed[index] = 0;
    OldPortalStarts[index]++;
    OldPortalStartTime[index] = GetTime();
    OldPortalInFlight = portal + 1;
    OldPortalBlocked[group] = 0;
    OldPortalBlockedArmy[group] = -1;
    if(army == 0 && OldPortalPendingLeader[group] == portal + 1)
        OldPortalPendingLeader[group] = 0;
    return true;
}

OldPortalFinished()
{
    int hero = Flagman(OldTeleportArmy);
    if(hero && hero == OldTeleportHero && Action(hero, ACT_GET_HP) > 0)
        OldPortalHoldArrival(OldTeleportArmy, hero);
    if(!OldPortalInFlight) return;
    int p = OldPortalInFlight - 1;
    if(hero && hero == OldTeleportHero && Action(hero, ACT_GET_HP) > 0
        && SizeTo(hero, OldPortalSpec(p, OP_GX), OldPortalSpec(p, OP_GY)) <= 5
        && GetZ(hero) >= OldPortalSpec(p, OP_ARRIVAL_MIN_Z)
        && GetZ(hero) <= OldPortalSpec(p, OP_ARRIVAL_MAX_Z))
    {
        int index = p * 8 + OldTeleportArmy;
        OldPortalArrivals[index]++;
        OldPortalFinishTime[index] = GetTime();
    }
    OldPortalInFlight = 0;
}

OldPortalTact()
{
    OldPortalInit();
    // Step-off is observed even before a quest's map event registers its
    // portal. Leaving an inactive arrival zone must not remain latched when
    // the player returns later, but it must not activate that route either.
    for(int p = 0; p < OLD_PORTAL_COUNT; p++)
    {
        int group = OldPortalSpec(p, OP_GROUP);
        if(OldPortalGroupActive[group] && OldPortalSpec(p, OP_REUSABLE))
        {
            for(int army = 0; army <= 3; army = army + 3)
            {
                int hero = Flagman(army);
                if(hero && !OldPortalNear(hero, p, OldPortalSpec(p, OP_MARGIN)))
                {
                    OldPortalArrivalBlocked[p * 8 + army] = 0;
                    if(OldPortalReady[group]) OldPortalArmed[p * 8 + army] = 1;
                }
            }
        }
    }
    for(int group = 0; group < OLD_PORTAL_GROUPS; group++)
    {
        if(OldPortalReady[group] && OldPortalRegister(group))
        {
            if(!gCurrentTeleport)
            {
                OldPortalBlocked[group] = 0;
                OldPortalBlockedArmy[group] = -1;
                if(OldPortalPendingLeader[group]
                    && OldPortalTryStart(OldPortalPendingLeader[group] - 1, 0)) return;
                for(int direction = 0; direction < OLD_PORTAL_COUNT; direction++)
                    if(OldPortalSpec(direction, OP_GROUP) == group)
                        for(int player = 0; player <= 3; player = player + 3)
                            if(OldPortalTryStart(direction, player)) return;
            }
        }
    }
}

OldPortalScriptEvent(int unit)
{
    OldPortalInit();
    for(int p = 0; p < OLD_PORTAL_COUNT; p++)
    {
        int group = OldPortalSpec(p, OP_GROUP);
        if(OldPortalGroupActive[group] && OldPortalSource(unit, p))
        {
            int consumeInvalid = OldPortalSpec(p, OP_CONSUME_INVALID);
            if(consumeInvalid) OldPortalEvents[p]++;
            if(!OldPortalGoal(unit, p, false))
            {
                if(consumeInvalid) OldPortalFault[group] = 3;
                return consumeInvalid;
            }
            if(!OldPortalReady[group] && !OldPortalSpec(p, OP_REUSABLE))
                OldPortalUnits[p] = unit;
            if(!OldPortalRegister(group)) return consumeInvalid;
            if(unit != OldPortalUnits[p])
            {
                OldPortalFault[group] = 2;
                return consumeInvalid;
            }
            if(!consumeInvalid) OldPortalEvents[p]++;
            if(OldPortalSpec(p, OP_LEADER_EVENT))
            {
                if(!OldPortalStarts[p * 8])
                {
                    OldPortalPendingLeader[group] = p + 1;
                    OldPortalTryStart(p, 0);
                }
            }
            else OldPortalTact();
            return true;
        }
    }
    return false;
}

'''


def script_hash(text):
    return hashlib.sha256(text.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251')).hexdigest()


def once(text, before, after):
    if text.count(before) != 1: raise ValueError('Shared portal source guard: ' + repr(before))
    return text.replace(before, after)


def configuration(portals=PORTALS):
    """Compile declarative geometry/policy only; no per-event control flow."""
    if not portals: raise ValueError('Portal catalog must not be empty')
    groups = tuple(dict.fromkeys(p.policy.activation_group for p in portals))
    values = []
    for p in portals:
        policy = p.policy
        z = policy.source_z_bounds or (0, 0)
        # The VM coordinate API returns integers. Original float32 identities
        # remain byte-exact in the catalog; admit only their floor/ceil interval.
        row = (groups.index(policy.activation_group), p.sprite.vid, *map(math.floor, p.sprite.xyz),
               *p.trigger, *p.goal, int(policy.reusable), policy.rearm_margin,
               int(policy.strict_radius), int(policy.source_z_bounds is not None), *z,
               *policy.arrival_z_bounds, int(policy.create_missing_peer_goal),
               int(policy.event_actor_policy == 'leader_pending'), int(policy.consume_invalid_event),
               *map(math.ceil, p.sprite.xyz),
               policy.closed_by_quest[0] - 1 if policy.closed_by_quest else -1,
               policy.closed_by_quest[1] if policy.closed_by_quest else 0,
               {11: -100, 12: 100, 13: 0}[p.event_id])
        if len(row) != len(FIELDS) or any(int(v) != v or not -(2**31) <= v < 2**31 for v in row):
            raise ValueError('Logical portal configuration requires audited integer coordinates')
        if p.trigger[2] + policy.rearm_margin >= 2**31: raise ValueError('Portal rearm radius overflows int32')
        values.extend(map(int, row))
    return groups, values


def generate(portals=PORTALS, maps=REGISTRY.maps):
    if len({m.key for m in maps}) != len(maps) or len({m.path for m in maps}) != len(maps):
        raise ValueError('Duplicate map identity')
    groups, values = configuration(portals)
    count, fields, group_count = len(portals), len(FIELDS), len(groups)
    declarations = '\n'.join(f'#define OP_{field.upper()} {i}' for i,field in enumerate(FIELDS)) + '\n'
    declarations += f'''#define OLD_PORTAL_COUNT {count}
#define OLD_PORTAL_FIELDS {fields}
#define OLD_PORTAL_GROUPS {group_count}
static int OldPortalConfig[{count * fields}] = {{{', '.join(map(str,values))}}};
static int OldPortalInitialized = 0;
static int OldPortalInFlight = 0;
'''
    for name in ('Ready','Fault','GroupActive','PendingLeader','Blocked','BlockedArmy'):
        initializer = ' = {' + ', '.join('-1' for _ in groups) + '}' if name == 'BlockedArmy' else ''
        declarations += f'static int OldPortal{name}[{group_count}]{initializer};\n'
    for name in ('Units','Events'):
        declarations += f'static int OldPortal{name}[{count}];\n'
    for name in ('Armed','ArrivalBlocked','Starts','Arrivals','StartTime','FinishTime'):
        declarations += f'static int OldPortal{name}[{count * 8}];\n'
    declarations += 'OldPortalFinished();\nOldPortalOwnsUnit(int unit);\n'
    init = 'OldPortalInit()\n{\n    if(OldPortalInitialized) return;\n    OldPortalInitialized = 1;\n'
    init += '    string map = ToLower(GetMapName());\n'
    for i, group in enumerate(groups):
        members = [p for p in portals if p.policy.activation_group == group]
        map_key = members[0].map_key
        if any(p.map_key != map_key for p in members): raise ValueError('Portal group spans maps')
        # Map names are generated below from registry identity, not inferred
        # by callers from mission numbers or localized display names.
        identity = next((m for m in maps if m.key == map_key), None)
        if identity is None: raise ValueError('Portal map identity missing')
        map_path = identity.path.lower().replace('/', '\\\\')
        init += f'    OldPortalGroupActive[{i}] = map == "{map_path}";\n'
        init += f'    OldPortalBlockedArmy[{i}] = -1;\n'
    init += '}\n\n'
    return declarations, init + CORE, groups


def patch(teleport_text, map_images, registry=REGISTRY):
    if script_hash(teleport_text) != TELEPORT_SHA256:
        raise ValueError('Expected exact teleport-v1 script before logical portal controllers')
    for identity in registry.maps:
        if identity.key not in map_images: raise ValueError('Missing original map: ' + identity.path)
        registry.validate_original_map(map_images[identity.key], identity.key)
    declarations, helper, groups = generate(registry.portals, registry.maps)
    text = teleport_text.replace('\r\n', '\n')
    text = once(text, 'static int OldTeleportNextUnit = 0;',
                'static int OldTeleportNextUnit = 0;\n' + declarations)
    text = once(text, 'FinishTeleporting( int unit )\n{',
                'FinishTeleporting( int unit )\n{\n    OldPortalFinished();')
    # VID1144 and other stock callbacks must not bypass this controller's
    # per-player admission, quest closure or step-off state for catalog units.
    signature = 'BeginTeleportingEx(int unit, int iNextVid, int iHeroAnimZ, int bMoveTeleport, int iTeleportTime)\n{'
    text = once(text, signature, signature + '\n    if(OldPortalOwnsUnit(unit)) return false;')
    text = once(text, 'TeleportTact()\n{', helper + 'TeleportTact()\n{\n    OldPortalTact();')
    for event in (11, 12, 13):
        signature = f'ScriptEvent{event}( int unit, int var2, int var3 )\n{{'
        text = once(text, signature, signature + '\n    if(OldPortalScriptEvent(unit)) return;')
    from old_native_teleport_landing import apply as protect_landings
    text = protect_landings(text)
    catalog = registry.manifest()
    return text, {'feature': FEATURE, 'input_sha256': TELEPORT_SHA256, 'output_sha256': script_hash(text),
        'catalog': catalog, 'catalog_sha256': hashlib.sha256(json.dumps(catalog, sort_keys=True).encode()).hexdigest(),
        'groups': list(groups), 'armies': [0,3], 'one_shared_controller': True,
        'map_identity_cached_per_script_load': True, 'active_groups_only': True,
        'quest_setters': False, 'item_grants': False, 'map_modified': False,
        'destination_reserved_during_transit': False, 'legacy_controllers_included': False,
        'arrival_rearm': 'per-hero leave destination zone plus catalog margin',
        'arrival_lock_survives_first_registration': True,
        'catalog_stock_callback_bypass_blocked': True,
        'party_landing_guard': {'phases': [2, 4], 'clearance_xy': 96, 'same_floor_z': 48,
                               'occupied_policy': 'wait', 'original_destinations_preserved': True,
                               'covers_stock_platforms_and_scripted_portals': True}}


def prepare(old_root):
    from old_native_teleport_patch import prepare as base
    from old_native_campaign_missions import mission_source
    root = Path(old_root)
    return patch(base(root)[0], {m.key:mission_source(root, m.path).read_bytes() for m in REGISTRY.maps})


def patch_level02(source):
    if script_hash(source) != LEVEL02_SHA256: raise ValueError('Expected exact Level02 shop/development script')
    text = once(source.replace('\r\n','\n'), '  QuestsTact();', '  TeleportTact();\n  QuestsTact();')
    return text, {'input_sha256': LEVEL02_SHA256, 'output_sha256': script_hash(text)}


def adapt_observer(source, kind):
    """Read-only expression adapters keep existing evidence schemas usable.

    They add no second set of counters or callbacks to the game controller.
    Catalog order is verified explicitly because historical keys have fixed
    meanings; new observers should address catalog names and generic arrays.
    """
    # Resolved from audited map and tuple, independent of user-facing labels.
    entry, leave = (PORTALS.index(p) for p in BUNKER_PORTALS)
    admin = PORTALS.index(ADMIN_PORTAL)
    groups, _ = configuration()
    bg = groups.index(PORTALS[entry].policy.activation_group)
    ag = groups.index(PORTALS[admin].policy.activation_group)
    if (entry,leave) != (0,1): raise ValueError('Historical bunker observer index ABI changed')
    if kind == 'bunker':
        scalars = {'OldBunkerPortalReady':f'OldPortalReady[{bg}]', 'OldBunkerFault':f'OldPortalFault[{bg}]',
            'OldBunkerInFlight':f'OldPortalGroupFlight({bg})', 'OldBunkerPendingLeader':f'OldPortalPendingLeader[{bg}]',
            'OldBunkerLandingBlocked':f'OldPortalBlocked[{bg}]', 'OldBunkerLandingBlockedArmy':f'OldPortalBlockedArmy[{bg}]'}
        arrays = {'OldBunkerEntries':('OldPortalArrivals',entry*8), 'OldBunkerExits':('OldPortalArrivals',leave*8),
            'OldBunkerStarts':('OldPortalStarts',0), 'OldBunkerStartTime':('OldPortalStartTime',0),
            'OldBunkerFinishTime':('OldPortalFinishTime',0)}
        prefix = 'OldBunker'
    elif kind == 'admin':
        scalars = {'OldAdminReady':f'OldPortalReady[{ag}]', 'OldAdminFault':f'OldPortalFault[{ag}]',
            'OldAdminEvents':f'OldPortalEvents[{admin}]', 'OldAdminInFlight':f'(OldPortalGroupFlight({ag}) != 0)',
            'OldAdminBlockedArmy':f'OldPortalBlockedArmy[{ag}]'}
        arrays = {'OldAdminStarts':('OldPortalStarts',admin*8), 'OldAdminArrivals':('OldPortalArrivals',admin*8)}
        prefix = 'OldAdmin'
    else: raise ValueError('Unknown legacy observer schema')
    # Only code tokens are rewritten; evidence keys, strings and comments
    # stay verbatim even if they mention historical variable names.
    parts = re.split(r'("(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/)', source, flags=re.S)
    for i in range(0, len(parts), 2):
        code = parts[i]
        for name, expression in scalars.items(): code = re.sub(r'\b' + name + r'\b', lambda _:expression, code)
        for name, (target, offset) in arrays.items():
            code = re.sub(r'\b' + name + r'\[([^\[\]\n]+)\]', lambda m:f'{target}[{offset} + {m[1]}]', code)
        if re.search(r'\b' + prefix + r'\w*', code): raise ValueError('Unknown legacy observer expression')
        parts[i] = code
    text = ''.join(parts)
    if text == source: raise ValueError('Expected legacy observer fields')
    return text
