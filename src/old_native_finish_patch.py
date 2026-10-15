"""Pure, guarded live Level_01 completion; no runtime/original file writes.

prepare(OLD) returns the helper to include after common_compaign.lgc. Call
OldFinishTact after the passive observer and Ready guard, BEFORE GameTact.
Its true return skips the remaining level main for a completed/faulted run.
patch_monsters composes the narrow party-stat correction after the exact
passive combat observer. Durable saves and map transitions are not provided.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct


FEATURE = 'old-campaign-finish-v1'
SOURCES = {
    'Maps/Level_01.map': '5bdc5f4ff57e06feeb7b02d36c09d76e01ef5d258b05e3c45c4e47523df694ec',
    'Maps/Level_01.lgc': '84cb15346b52433dba442044bd746eccdb2e3f896c31f487e53ef81b7284dee0',
    'Maps/COMMON.LGC': '1801dd85cc564459122b00c08ad459394ba91bd8d0e53d8c92cc636cfbacde09',
    'Maps/common_compaign.lgc': '66b1844d3875c14188ba9002b47a1d5e8e0e020d768bbd64a15d56a0c2df9284',
    'Maps/common_defs2.lgc': '09ee502c90e701b8a6b8f5025a25aac9442c8ba2e2c175956e8d5822319e6795',
    'Maps/util_statistics.lgc': '00041377816c259a249f5f60072f5ef40537a331834afce5a7b3907d610a03fb',
    'levels.cfg': '5606461fbe14c683a323480b8e3b01203309153598d57ef57355ad20083ad01f',
}
MONSTERS_ORIGINAL_SHA256 = 'f06064f8847e5e206b751525fa17ac6401a17dcfdf6bccbc1e181d934053339a'
MONSTERS_OBSERVER_SHA256 = '284950c549e6fff5f205187c96b99ac4c86b0d88d54fef93ac079bcb91ba95af'


HELPER = r'''// Generated for original OLD Level_01, only in COOP_CAMPAIGN.
#ifndef OLD_CAMPAIGN_FINISH_H
#define OLD_CAMPAIGN_FINISH_H 1
static int OldFinishStage = 0; // 0=playing, 1=waiting for party, 2=completed
static int OldFinishFault = 0; // 1=unexpected request, 2=invalid live state
static int OldFinishRequests = 0;
static int OldFinishCompletions = 0;
static int OldFinishRequestTime = -1;
static int OldFinishCompletedTime = -1;
static int OldFinishLevelBefore = -1;
static int OldFinishLevelAfter = -1;
static int OldFinishMoneyAward = 0;
static int OldFinishRankAward = 0;
static int OldFinishMonsterCount = 0;
static int OldFinishMonstersKilled = 0;
static int OldFinishSecretCount = 0;
static int OldFinishSecretsFound = 0;
static int OldFinishRewardCalls[8];
static int OldFinishMoneyBefore[8];
static int OldFinishMoneyAfter[8];
static int OldFinishRankBefore[8];
static int OldFinishRankAfter[8];
static int OldFinishHeroX[8];
static int OldFinishHeroY[8];
static int OldFinishHeroZ[8];
static int OldFinishHeroHP[8];
static int OldFinishText1 = 0;
static int OldFinishText2 = 0;
static int OldFinishText3 = 0;

OldFinishHeroReady(int army)
{
    int hero = Flagman(army);
    if(!hero || Action(hero, ACT_GET_HP) <= 0)
        return false;
    return SizeTo(hero, 3831, 5334) < 120;
}

OldFinishShowText()
{
    // Presentation only; never use these handles for shared decisions.
    int x = ScreenX() / 2;
    int y = ScreenY() - MISSION_STATE_Y;
    OldFinishText1 = CreateText(10, x, y, 0,
        "Миссия завершена", BEH_CENTER);
    OldFinishText2 = CreateText(13, x, y + 20, 0,
        "Продолжение кампании пока недоступно.", BEH_CENTER);
    OldFinishText3 = CreateText(13, x, y + 40, 0,
        "Совместный прогресс пока не сохраняется.", BEH_CENTER);
}

OldFinishTact()
{
#ifndef COOP_CAMPAIGN
    return false;
#else
    if(ToLower(GetMapName()) != "maps\\level_01.map")
        return false;
    if(OldFinishFault || OldFinishStage == 2)
        return true;
    if(Action9 != 0)
    {
        // The hash-guarded map has exactly one Action9 writer, with value 1.
        if(Action9 != 1)
        {
            OldFinishFault = 1;
            return true;
        }
        Action9 = 0;
        if(OldFinishStage == 0)
        {
            OldFinishRequests = OldFinishRequests + 1;
            OldFinishRequestTime = GetTime();
            OldFinishStage = 1;
        }
    }
    if(OldFinishStage != 1)
        return false;
    if(!OldFinishHeroReady(0) || !OldFinishHeroReady(3))
        return false;
    if(!NetProperty(NET_IS_CONNECT) || NetProperty(NET_NO_PLAYERS) != 2
        || giCurLevCmpgn != 1 || giCurLevCmpgnReal != 1)
    {
        OldFinishFault = 2;
        return true;
    }

    // Capture original rank inputs before awards. No GetStatData: that path
    // reads local hero accuracy and can consume Random2 in a local branch.
    OldFinishMonsterCount = InitStatData[VSTAT_MMONSTERSCNT];
    OldFinishMonstersKilled = CurStatData[VSTAT_MMONSTERSKILLED];
    OldFinishSecretCount = InitStatData[VSTAT_MSECRETSCNT];
    OldFinishSecretsFound = GetFoundSecrets();
    OldFinishRankAward = MustAddRank();
    OldFinishMoneyAward = CurLevelMoney;
    OldFinishLevelBefore = giCurLevCmpgn;
    int army;
    for(army = 0; army <= 3; army = army + 3)
    {
        int hero = Flagman(army);
        OldFinishHeroX[army] = GetX(hero);
        OldFinishHeroY[army] = GetY(hero);
        OldFinishHeroZ[army] = GetZ(hero);
        OldFinishHeroHP[army] = Action(hero, ACT_GET_HP);
        OldFinishMoneyBefore[army] = SendCommand(EXT_GETSKILL,
            HeroID[army], RPGHERO_MONEY);
        OldFinishRankBefore[army] = SendCommand(EXT_GETSKILL,
            HeroID[army], RPGHERO_RANK);
    }

    // Guard before mutations. Do the original Win bookkeeping once, with
    // explicit party ownership instead of local -1 / giCurArmy selectors.
    OldFinishStage = 2;
    OldFinishCompletions = OldFinishCompletions + 1;
    OldFinishCompletedTime = GetTime();
    Destroy(ArrowHint);
    ArrowHint = 0;
    GameState = GAME_WIN;
    // Cancel pending local menu fades without using them in shared decisions.
    StartNextMap = 0;
    IncLevelNumber(false);
    LoadCurLevel(); // Original selects NextMapName; does not schedule a load.
    OldFinishLevelAfter = giCurLevCmpgn;
    for(army = 0; army <= 3; army = army + 3)
    {
        SendCommandA(army, EXT_ADDSKILL, RPGHERO_MONEY,
            OldFinishMoneyAward, false);
        OldFinishRewardCalls[army] = OldFinishRewardCalls[army] + 1;
    }
    if(OldFinishRankAward)
    {
        SendCommandA(0, EXT_ADDSKILL, RPGHERO_RANK, 1);
        SendCommandA(3, EXT_ADDSKILL, RPGHERO_RANK, 1);
    }
    // The original native serializer intentionally returns immediately when
    // connected. These calls preserve its lifecycle but DO NOT save co-op.
    SendCommandA(0, EXT_OnLevelWin);
    SendCommandA(3, EXT_OnLevelWin);
    RemeberCarBlood();
    for(army = 0; army <= 3; army = army + 3)
    {
        OldFinishMoneyAfter[army] = SendCommand(EXT_GETSKILL,
            HeroID[army], RPGHERO_MONEY);
        OldFinishRankAfter[army] = SendCommand(EXT_GETSKILL,
            HeroID[army], RPGHERO_RANK);
        // Immediate shared control stop; native NET Pause arrives via input.
        SendCommandA(army, EXT_DISABLEFLAGMANCONTROL, 1);
        // PLAYERCONTROL_NONE returns before native Control's usual stop.
        // Cancel the prior movement/command explicitly before that return.
        Action(Flagman(army), ACT_STOP, 1, 1);
        SetPlayerControl(army, PLAYERCONTROL_NONE);
    }
    SetScrollType(SCROLL_NONE);
    SetCursor(CURSOR_NORMAL);
    OldFinishShowText();
    Pause(1);
    return true;
#endif
}
#endif
'''


def _script_bytes(text: str) -> bytes:
    return text.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251')


def prepare(old_root: Path) -> tuple[str, dict]:
    root = Path(old_root)
    sources = {}
    for name, expected in SOURCES.items():
        data = (root / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Unsupported original completion source: ' + name)
        sources[name] = data
    commands = (
        (0xA2209, (43, 3700, 5458, 180)),
        (0xA21F9, (135, 76, 0, 0)),
        (0xA21E9, (40, 2000, 0, 0)),
        (0xA21D9, (6, 0, 0, 0)),
        (0xA21C9, (10, 0, 0, 0)),
        (0xA21B9, (43, 3831, 5334, 120)),
        (0xA21A9, (131, 9, 1, 0)),
    )
    for offset, expected in commands:
        if struct.unpack_from('<4i', sources['Maps/Level_01.map'], offset) != expected:
            raise ValueError('Original elevator completion stack guard failed')
    for name, fragment in (
        ('Maps/common_compaign.lgc', '                InstantWin();'),
        ('Maps/COMMON.LGC', 'SendCommandA( -1, EXT_ADDSKILL, RPGHERO_MONEY, CurLevelMoney, false );'),
        ('Maps/COMMON.LGC', 'SendCommandA( -1, EXT_OnLevelWin );'),
        ('Maps/common_defs2.lgc', 'SetLevelNumber( giCurLevCmpgn + 1, -1 );'),
    ):
        if sources[name].decode('cp1251').count(fragment) != 1:
            raise ValueError('Original completion operation guard failed: ' + name)
    return HELPER, {
        'feature': FEATURE,
        'source_sha256': dict(SOURCES),
        'helper_file': 'Maps/old_campaign_finish.lgc',
        'output_sha256': hashlib.sha256(_script_bytes(HELPER)).hexdigest(),
        'integration': 'Include after common_compaign; after observer and Ready check call if(OldFinishTact()) return; before GameTact.',
        'original_request': {'action': 9, 'value': 1, 'map_raw_offset': hex(0xA21A9)},
        'exit': {'x': 3831, 'y': 5334, 'radius_exclusive': 120, 'living_armies': [0, 3]},
        'reward_policy': 'Each hero gets full original CurLevelMoney and the same original aggregate MustAddRank result once.',
        'level_01_original_money': 0,
        'requires_party_monster_stat_patch': True,
        'quest_state_setters': [],
        'quest_rewards_reissued': False,
        'progression': 'Original IncLevelNumber(false), then LoadCurLevel selects Level_02 without loading it.',
        'profile_saves': 'SetLevelNumber writes isolated profile options; native EXT_OnLevelWin is a connected no-op. No durable co-op checkpoint.',
        'terminal': 'GAME_WIN; skip stock GameTact and level LGC, no NET stats, shop, disconnect or map load.',
        'pause': 'Requests native NET pause on both peers; immediately disables armies 0/3 control. World freeze not statically assumed.',
        'terminal_hero_stop': 'Action(hero, ACT_STOP, 1, 1) clears prior movement/command before PLAYERCONTROL_NONE.',
        'observer_before_helper': True,
        'observer_should_sample_every_frame_when_requested_or_completed': True,
        'rng_calls_added': 0,
        'runtime_tested': False,
    }


def patch_monsters(source: str) -> tuple[str, dict]:
    """Compose after original or exact old-campaign-combat-observer-v1 text."""
    if not isinstance(source, str):
        raise TypeError('Expected generated MONSTERS.LGC text')
    source = source.replace('\r\n', '\n')
    digest = hashlib.sha256(_script_bytes(source)).hexdigest()
    if digest not in (MONSTERS_ORIGINAL_SHA256, MONSTERS_OBSERVER_SHA256):
        raise ValueError('Unsupported MONSTERS source before party statistic patch')
    before = '            if( KillerArmy == 0 )\n'
    after = '''#ifdef COOP_CAMPAIGN
            if( KillerArmy == 0 || KillerArmy == 3 )
#else
            if( KillerArmy == 0 )
#endif
'''
    if source.count(before) != 1:
        raise ValueError('Army6 AddScores party-stat source guard failed')
    output = source.replace(before, after)
    return output, {
        'feature': 'old-campaign-party-kill-stat-v1',
        'source_file': 'Maps/MONSTERS.LGC',
        'input_sha256': digest,
        'output_sha256': hashlib.sha256(_script_bytes(output)).hexdigest(),
        'scope': 'COOP_CAMPAIGN only: original army6 scripted-monster stat inclusion accepts killer army0 or3.',
        'preserves_original_monster_eligibility_and_counters': True,
        'individual_kill_xp_reward_operations_changed': False,
        'rng_calls_added': 0,
        'runtime_tested': False,
    }
