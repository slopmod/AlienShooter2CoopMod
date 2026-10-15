"""Pure, hash-guarded instrumentation of the original Spinner damage callback.

The generated script records callback inputs and read-only sprite properties,
then returns the original Common_Damage call unchanged. No firing, HP setters,
RNG, rewards or combat behavior is added. The caller writes only its isolated
diagnostic campaign copy of Maps/MONSTERS.LGC.
"""
import hashlib
from pathlib import Path


FEATURE = 'old-campaign-combat-observer-v1'
SOURCE_SHA256 = 'f06064f8847e5e206b751525fa17ac6401a17dcfdf6bccbc1e181d934053339a'
CALLBACK = '''F1025_DAMAGE( int iUnit, int iBeatingUnit, int iDamage )
{return Common_Damage( iUnit, iBeatingUnit, iDamage );}'''

OBSERVER = '''// Passive Spinner damage-callback diagnostics; incoming damage is not
// proof of HP application until paired with the original native death/state.
static int OldCombatGuestHits = 0;
static int OldCombatHostHits = 0;
static int OldCombatLastActorArmy = -1;
static int OldCombatLastActorVid = 0;
static int OldCombatLastTargetArmy = -1;
static int OldCombatLastTargetX = 0;
static int OldCombatLastTargetY = 0;
static int OldCombatLastTargetZ = 0;
static int OldCombatLastDamage = 0;
static int OldCombatLastHpBefore = 0;
static int OldCombatLastDamageTime = -1;

OldCombatObserveDamage(int unit, int attacker, int damage)
{
    if(!unit || !attacker || damage <= 0)
        return;
    int army = Action(attacker, ACT_GET_ARMY);
    if(army != 0 && army != 3)
        return;
    if(army == 3)
        OldCombatGuestHits = OldCombatGuestHits + 1;
    else
        OldCombatHostHits = OldCombatHostHits + 1;
    OldCombatLastActorArmy = army;
    OldCombatLastActorVid = GetVid(attacker);
    OldCombatLastTargetArmy = Action(unit, ACT_GET_ARMY);
    OldCombatLastTargetX = GetX(unit);
    OldCombatLastTargetY = GetY(unit);
    OldCombatLastTargetZ = GetZ(unit);
    OldCombatLastDamage = damage;
    OldCombatLastHpBefore = Action(unit, ACT_GET_HP);
    OldCombatLastDamageTime = GetTime();
}

F1025_DAMAGE( int iUnit, int iBeatingUnit, int iDamage )
{
    OldCombatObserveDamage(iUnit, iBeatingUnit, iDamage);
    return Common_Damage( iUnit, iBeatingUnit, iDamage );
}'''


def patch(source: bytes) -> tuple[str, dict]:
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported original MONSTERS.LGC for combat observer')
    text = source.decode('cp1251').replace('\r\n', '\n')
    if text.count(CALLBACK) != 1:
        raise ValueError('Spinner damage callback source guard failed')
    text = text.replace(CALLBACK, OBSERVER)
    encoded = text.replace('\n', '\r\n').encode('cp1251')
    return text, {
        'feature': FEATURE,
        'source_file': 'Maps/MONSTERS.LGC',
        'source_sha256': SOURCE_SHA256,
        'output_sha256': hashlib.sha256(encoded).hexdigest(),
        'callback': 'F1025_DAMAGE',
        'target_vid': 1025,
        'actor_armies': [0, 3],
        'counts_positive_incoming_callbacks': True,
        'callback_means_confirmed_applied_damage': False,
        'attacker_vid_is_not_assumed_to_be_hero_vid': True,
        'preserves_common_damage_arguments_and_return': True,
        'world_state_setters': [],
        'rng_calls_added': 0,
        'observer_fields': [
            'OldCombatGuestHits', 'OldCombatHostHits', 'OldCombatLastActorArmy',
            'OldCombatLastActorVid', 'OldCombatLastTargetArmy', 'OldCombatLastTargetX',
            'OldCombatLastTargetY', 'OldCombatLastTargetZ', 'OldCombatLastDamage',
            'OldCombatLastHpBefore', 'OldCombatLastDamageTime',
        ],
        'runtime_tested': False,
    }


def prepare(old_root: Path) -> tuple[str, dict]:
    return patch((Path(old_root) / 'Maps' / 'MONSTERS.LGC').read_bytes())
