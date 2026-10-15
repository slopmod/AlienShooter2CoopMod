"""Pure, pinned campaign combat-reward adaptation for the OLD executable.

Compose MONSTERS after the existing observer and party-statistic transform.
Native source/lifetime tracking (EXT332..335) is required; an army number alone
is never accepted as personal kill ownership. No filesystem or runtime access.
"""
from __future__ import annotations

import hashlib
import re


FEATURE = 'old-native-campaign-rewards-scripts-v1'
MONSTERS_INPUT_SHA256 = '9c3427c83ddfd5bd09cea793bbfec5548a626f9f21173125611e26a10d69f907'
PERKS_INPUT_SHA256 = '511ebb4d32b391cb0dec5328b8722dbe9ab00bf3c2ed1e0c5286b41b6c508998'
NATIVE_COMMANDS = {'source_owner': 332, 'peek_death_owner': 333,
                   'claim_death': 334, 'fault': 335}

GLOBALS = '''
#ifdef COOP_CAMPAIGN
// Passive counters are claims/calls, not independent proof of RPG mutation.
static int OldRewardScriptFault = 0;
static int OldRewardClaimCalls = 0;
static int OldRewardDuplicateClaims = 0;
static int OldRewardUnknownDeaths = 0;
static int OldRewardPersonalDeaths[MAX_PLAYER];
static int OldRewardLastArmy = -1;
static int OldRewardLastVictimVid = 0;
static int OldRewardExpCalls[MAX_PLAYER];
static int OldRewardExpBase[MAX_PLAYER];
static int OldRewardVampireRemainder[MAX_PLAYER];
static int OldRewardVampireAddCalls[MAX_PLAYER];
static int OldRewardVampireRequested[MAX_PLAYER];
#endif
'''

CLAIM = '''#ifdef COOP_CAMPAIGN
    OldRewardClaimCalls = OldRewardClaimCalls + 1;
    int rewardOwner = SendCommandA(0, 334, unit, 0, 0);
    if(rewardOwner == -2)
    {
        OldRewardDuplicateClaims = OldRewardDuplicateClaims + 1;
        return;
    }
    if(rewardOwner != -1 && rewardOwner != 0 && rewardOwner != 3)
    {
        OldRewardScriptFault = rewardOwner;
        return;
    }
    KillerArmy = rewardOwner;
    OldRewardLastArmy = rewardOwner;
    OldRewardLastVictimVid = GetVid(unit);
    if(rewardOwner == -1)
        OldRewardUnknownDeaths = OldRewardUnknownDeaths + 1;
    else
    {
        OldRewardPersonalDeaths[rewardOwner] = OldRewardPersonalDeaths[rewardOwner] + 1;
        SendCommandA(KillerArmy, EXT_ADDSKILL, RPGHERO_KILLS, 1);
    }
#else
'''

PEEK = '''#ifdef COOP_CAMPAIGN
    // PEEK remains valid after CLAIM and across the original animation retry.
    KillerrArmy = SendCommandA(0, 333, unit, 0, 0);
    if(KillerrArmy != -1 && KillerrArmy != 0 && KillerrArmy != 3)
    {
        OldRewardScriptFault = KillerrArmy;
        return;
    }
    // Flagman(-1) is a local selector, not an unknown-owner test.
    if((KillerrArmy == 0 || KillerrArmy == 3) && Flagman(KillerrArmy))
#else
'''


def _bytes(text: str) -> bytes:
    return text.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251')


def _input(source: str | bytes, expected: str, name: str) -> tuple[str, str]:
    if isinstance(source, bytes):
        source = source.decode('cp1251')
    if not isinstance(source, str):
        raise TypeError('Expected script text/bytes: ' + name)
    text = source.replace('\r\n', '\n')
    digest = hashlib.sha256(_bytes(text)).hexdigest()
    if digest != expected:
        raise ValueError('Unsupported campaign-rewards source: ' + name)
    return text, digest


def _replace(text: str, before: str, after: str) -> str:
    if text.count(before) != 1:
        raise ValueError('Campaign-rewards anchor changed: ' + repr(before[:90]))
    return text.replace(before, after)


def _metadata(name: str, before: str, after: str, **values) -> dict:
    return {'feature': FEATURE, 'file': name, 'input_sha256': before,
            'output_sha256': hashlib.sha256(_bytes(after)).hexdigest(),
            'native_commands': dict(NATIVE_COMMANDS),
            'native_source_lifetime_patch_required': True,
            'scope': 'COOP_CAMPAIGN; exact OLD two-hero party, armies0/3',
            'non_coop_original_behavior_preserved': True,
            'file_writes': False, 'rng_calls_added': 0, 'runtime_tested': False,
            **values}


def patch_monsters(source: str | bytes) -> tuple[str, dict]:
    """Accept only observer-v1 followed by the existing party-stat patch."""
    name = 'Maps/MONSTERS.LGC'
    text, digest = _input(source, MONSTERS_INPUT_SHA256, name)
    original = '\tSendCommandA( KillerArmy, EXT_ADDSKILL, RPGHERO_KILLS, 1 );'
    text = _replace(text, original, CLAIM + original + '\n#endif')

    original = '''  #ifndef NET_GAME_RUN
    if( !SendCommand(EXT_GETSURVIVEMODE) && KillerArmy != 0 && MonstArmy != 4 )
        return;
  #endif
  #ifdef NET_GAME_RUN
    if( !NetProperty( NET_IS_PLAYER_EXIST + KillerArmy ) )
        return;
  #endif'''
    text = _replace(text, original, '''#ifdef COOP_CAMPAIGN
    // Unknown/NPC deaths still counted in the original world statistics above.
    if(KillerArmy != 0 && KillerArmy != 3)
        return;
#else
''' + original + '\n#endif')

    original = '\tif(Flagman(KillerrArmy))'
    text = _replace(text, original, PEEK + original + '\n#endif')
    original = '        int karmy = KillerrArmy;'
    text = _replace(text, original, original + '''
#ifdef COOP_CAMPAIGN
        // Match the original campaign fallback when no player owns the kill.
        if(karmy != 0 && karmy != 3)
            karmy = 0;
#endif''')

    original = '''#ifdef NET_GAME_RUN
	if(!ret && iBeatingUnit)
	{
	    int ExpToAdd = iDamage;
	    int hp = Action(iUnit, ACT_GET_HP);
	    if(ExpToAdd > hp)
	    	ExpToAdd = hp;
	    ExpToAdd = ExpToAdd * giScoresCoeff;
    	SendCommandA( Action(iBeatingUnit, ACT_GET_ARMY), EXT_ADDSKILL, RPGHERO_EXP, ExpToAdd );
	}
#endif'''
    text = _replace(text, original, '#ifndef COOP_CAMPAIGN\n' + original + '\n#endif')
    return text, _metadata(name, digest, text,
        input_variant='combat-observer-v1 + party-kill-stat-v1',
        reward_policy='One personal kill/death-XP reward to the verified source owner; no damage XP.',
        unknown_policy='No personal kills/XP/perks; retain original ordinary-monster world statistics.',
        army6_policy='World count includes only verified hero0/3 kills.',
        duplicate_policy='CLAIM -2 skips all AddScores accounting; PEEK remains available.',
        fault_policy='Unexpected PEEK/CLAIM result records OldRewardScriptFault and returns.',
        source_owner_used_for=['personal_kills', 'death_xp', 'army6_statistics',
                               'weapon_death_animation', 'current_ammo_bonus_owner'],
        unknown_current_ammo_owner=0,
        original_loot_generation_and_network_bonus_filter_preserved=True,
        status_damage_and_hypnosis_adapted=False)


def patch_perks(source: str | bytes) -> tuple[str, dict]:
    """Restore kill rewards and keep time-based hypnosis progress per hero."""
    name = 'Maps/common_perks.lgc'
    text, digest = _input(source, PERKS_INPUT_SHA256, name)
    text = _replace(text, '#define COMMONPERKS_H\taaa\n',
                    '#define COMMONPERKS_H\taaa\n' + GLOBALS)
    original = '#ifdef NET_GAME_RUN\n\treturn;\n#endif'
    text = _replace(text, original, '''#ifdef COOP_CAMPAIGN
    if(nArmy != 0 && nArmy != 3)
    {
        OldRewardScriptFault = -4;
        return;
    }
#else
''' + original + '\n#endif')
    original = '    SendCommandA( nArmy, EXT_ADDSKILL, RPGHERO_EXP, ExpToAdd );'
    text = _replace(text, original, '''#ifdef COOP_CAMPAIGN
    OldRewardExpCalls[nArmy] = OldRewardExpCalls[nArmy] + 1;
    OldRewardExpBase[nArmy] = OldRewardExpBase[nArmy] + ExpToAdd;
#endif
''' + original)

    start = text.index('\tstatic int AddHp = 0;', text.index('OnEnemyKill('))
    # The exact original function is the final function in this pinned file.
    end = text.rindex('\n}')
    original = text[start:end]
    personal = original.replace('\tstatic int AddHp = 0;',
                                '\t// One original integer remainder per hero.')
    personal = re.sub(r'\bAddHp\b', 'OldRewardVampireRemainder[nArmy]', personal)
    call = '\t\t\tSendCommandA( nArmy, EXT_ADDSKILL, RPGHERO__HP, HpToAdd );'
    personal = _replace(personal, call, '''            OldRewardVampireAddCalls[nArmy] = OldRewardVampireAddCalls[nArmy] + 1;
            OldRewardVampireRequested[nArmy] = OldRewardVampireRequested[nArmy] + HpToAdd;
''' + call)
    text = text[:start] + '#ifdef COOP_CAMPAIGN\n' + personal + '\n#else\n' + original + '\n#endif' + text[end:]
    from old_native_campaign_hypnosis import adapt as adapt_hypnosis, FEATURE as hypnosis_feature
    text = adapt_hypnosis(text)
    return text, _metadata(name, digest, text,
        experience='Original VID_MAXHP*giScoresCoeff passed once through native EXT_ADDSKILL EXP.',
        original_on_get_experience_and_money_callbacks_unchanged=True,
        original_level_and_skill_point_callbacks_unchanged=True,
        vampire_remainder='OldRewardVampireRemainder[MAX_PLAYER]; reset with the map VM like original static state.',
        vampire_arithmetic='Original denominator VAMPIRE_ADD_HP*100, whole-part removal before maxHP clamp.',
        original_time_bin_score_statistics_preserved=True,
        passive_fields=['OldRewardScriptFault', 'OldRewardClaimCalls', 'OldRewardDuplicateClaims',
                        'OldRewardUnknownDeaths', 'OldRewardPersonalDeaths', 'OldRewardLastArmy',
                        'OldRewardLastVictimVid', 'OldRewardExpCalls', 'OldRewardExpBase',
                        'OldRewardVampireRemainder', 'OldRewardVampireAddCalls',
                        'OldRewardVampireRequested'],
        hypnosis={'feature': hypnosis_feature, 'synchronized_aim_by_army': True,
                  'private_progress_and_cooldown': True, 'capacity_per_hero': 100,
                  'target_claim_policy': 'Original exclusive -555 marker; deterministic army order.',
                  'stock_duration_and_radius_preserved': True, 'minimum_progress_duration_ms': 1,
                  'death_cleanup_checks_both_heroes': True},
        freeze_reducer_and_other_perks_changed=False)


def apply(monsters: str | bytes, original_perks: str | bytes) -> tuple[dict[str, str], dict]:
    """Return both adapted files and metadata, without reading or writing files."""
    # Validate both before constructing either output, for atomic integration.
    _input(monsters, MONSTERS_INPUT_SHA256, 'Maps/MONSTERS.LGC')
    _input(original_perks, PERKS_INPUT_SHA256, 'Maps/common_perks.lgc')
    monsters_text, monsters_meta = patch_monsters(monsters)
    perks_text, perks_meta = patch_perks(original_perks)
    return {'Maps/MONSTERS.LGC': monsters_text,
            'Maps/common_perks.lgc': perks_text}, {
        'feature': FEATURE, 'native_commands': dict(NATIVE_COMMANDS),
        'files': {'Maps/MONSTERS.LGC': monsters_meta,
                  'Maps/common_perks.lgc': perks_meta},
        'script_initializer_required': False,
        'native_lifetime_tracking_required_before_map_construction': True,
        'runtime_tested': False,
    }
