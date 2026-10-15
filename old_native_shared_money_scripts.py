"""Pure, pinned script composition for the OLD campaign's single money pool.

The native wallet patch is required. This module never implements a second
wallet or a per-frame balance copy, and performs no file/process access.
Compose after the ordinary dynamite/finish/transition/Level02 generators.
"""
from __future__ import annotations

import hashlib


FEATURE = 'old-native-shared-money-scripts-v1'
SOURCE_SHA256 = {
    'Maps/COMMON.LGC': '1801dd85cc564459122b00c08ad459394ba91bd8d0e53d8c92cc636cfbacde09',
    'Maps/common_compaign.lgc': '66b1844d3875c14188ba9002b47a1d5e8e0e020d768bbd64a15d56a0c2df9284',
    'Maps/util_help.lgc': '08bb755bba8248cd37be2a031aa2727b14af0fedffc53d8288aeb936c9b2c0e6',
}
CAMPAIGN_INPUTS = {
    SOURCE_SHA256['Maps/common_compaign.lgc']: 'original',
    'd7d10a8c9755d7dd1035955ed94d0d2b62b5614b7fd214a6199a4789398ed3cf': 'party-dynamite',
    '97f7843ba820f23582631e372e220d5200b4608ad927f53f06e010912513623a': 'party-dynamite-story-owner0',
}
FINISH_INPUTS = {
    '26a94dff8c942e27d0b21a453d06c22b73e367dbd25cb7bef5630cdab9448278': 'finish-level02-transition-checkpoint',
    '627a692fcfb68b69b3a0d0857d474b89e183a194e6f8e4157785163da691f4b0': 'finish-level02-transition',
    'f5d5b68f0367e5bf84976e2272089a101254c8f79dc039cb39b8e2373828f8d1': 'finish',
    '037dcc85174be1ce2ae17440c0830e4791f0d0697a2bf1886fd04d25f9441782': 'finish-level02-transition',
}
INIT_INPUTS = {
    1: 'f5022e4a80dc048c2f2b81396be4a7705ab0fa6051728675ec36af2132745268',
    2: '6785eeb50cdc27723906faa9935a933fd6623d0a1bc367202c69593a62419252',
}
INIT_GLOBALS = '''
#define OLD_SHARED_MONEY 1
static int OldSharedMoneyEnableCalls = 0;
static int OldSharedMoneyEnableResult = 0;
static int OldSharedMoneyStatus = 0;
static int OldSharedMoneyHostBefore = 0;
static int OldSharedMoneyGuestBefore = 0;
static int OldSharedMoneyHostAfter = 0;
static int OldSharedMoneyGuestAfter = 0;
'''
INIT_CAPTURE_BEFORE = '''#ifdef COOP_CAMPAIGN
    // Both sprites/RPG owners are bound. Never add the two private balances.
    int money_host = SendCommandA(0, EXT_GETHEROID);
    int money_guest = SendCommandA(3, EXT_GETHEROID);
    OldSharedMoneyHostBefore = SendCommand(EXT_GETSKILL, money_host, RPGHERO_MONEY);
    OldSharedMoneyGuestBefore = SendCommand(EXT_GETSKILL, money_guest, RPGHERO_MONEY);
'''
INIT_ENABLE = '''    OldSharedMoneyEnableCalls = OldSharedMoneyEnableCalls + 1;
    OldSharedMoneyEnableResult = SendCommandA(0, 203, 0, 0, 0);
    if(OldSharedMoneyEnableResult != 1)
        return OldCampaignFail(101);
'''
INIT_VERIFY = '''    OldSharedMoneyStatus = SendCommandA(0, 204, 0, 0, 0);
    if(OldSharedMoneyStatus != 1)
        return OldCampaignFail(102);
    OldSharedMoneyHostAfter = SendCommand(EXT_GETSKILL, money_host, RPGHERO_MONEY);
    OldSharedMoneyGuestAfter = SendCommand(EXT_GETSKILL, money_guest, RPGHERO_MONEY);
    if(OldSharedMoneyHostAfter < 0
        || OldSharedMoneyHostAfter != OldSharedMoneyHostBefore
        || OldSharedMoneyHostAfter != OldSharedMoneyGuestAfter)
        return OldCampaignFail(102);
#endif

'''


def _script_hash(text: str) -> str:
    return hashlib.sha256(text.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251')).hexdigest()


def _input(source: str | bytes, expected, name):
    if isinstance(source, bytes):
        source = source.decode('cp1251')
    if not isinstance(source, str):
        raise TypeError('Expected script text/bytes for ' + name)
    text = source.replace('\r\n', '\n')
    digest = _script_hash(text)
    if digest not in expected:
        raise ValueError('Unsupported shared-money source: ' + name)
    return text, digest


def _replace(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Shared-money script anchor changed: ' + repr(before[:80]))
    return text.replace(before, after)


def _metadata(name, before, after, **values):
    return {'feature': FEATURE, 'file': name, 'input_sha256': before,
            'output_sha256': _script_hash(after), 'native_wallet_patch_required': True,
            'file_writes': False, 'rng_calls_added': 0, 'runtime_tested': False, **values}


def patch_campaign(source: str | bytes) -> tuple[str, dict]:
    """Compose after the exact optional party dynamite/story-owner edits."""
    name = 'Maps/common_compaign.lgc'
    text, digest = _input(source, CAMPAIGN_INPUTS, name)
    original = '                SendCommandA( -2, EXT_ADDSKILL, RPGHERO_MONEY, Action3, true );'
    replacement = '''#ifdef COOP_CAMPAIGN
                // One shared story reward; -2 would broadcast into one pool twice.
                SendCommandA( 0, EXT_ADDSKILL, RPGHERO_MONEY, Action3, true );
#else
''' + original + '\n#endif'
    text = _replace(text, original, replacement)
    return text, _metadata(name, digest, text, input_variant=CAMPAIGN_INPUTS[digest],
                           story_cash_owner=0, story_cash_calls_per_action3=1,
                           action3_consumption_preserved=True, non_coop_original_preserved=True)


def patch_finish(source: str | bytes) -> tuple[str, dict]:
    """Change cash only, after the optional exact Level02 transition helper."""
    name = 'Maps/old_campaign_finish.lgc'
    text, digest = _input(source, FINISH_INPUTS, name)
    original = '''    for(army = 0; army <= 3; army = army + 3)
    {
        SendCommandA(army, EXT_ADDSKILL, RPGHERO_MONEY,
            OldFinishMoneyAward, false);
        OldFinishRewardCalls[army] = OldFinishRewardCalls[army] + 1;
    }'''
    replacement = '''    // Both heroes read this one native pool; cash is credited once.
    SendCommandA(0, EXT_ADDSKILL, RPGHERO_MONEY,
        OldFinishMoneyAward, false);
    OldFinishRewardCalls[0] = OldFinishRewardCalls[0] + 1;'''
    text = _replace(text, original, replacement)
    return text, _metadata(name, digest, text, input_variant=FINISH_INPUTS[digest],
                           cash_awards_per_completion=1, cash_owner=0,
                           completed_reward_calls={'0': 1, '3': 0},
                           rank_and_on_level_win_owners=[0, 3],
                           shared_balance_before_after_observed_by_both_heroes=True)


def patch_common(source: str | bytes) -> tuple[str, dict]:
    """Canonicalize the legacy Win cash target; this does not adapt its UI/load."""
    name = 'Maps/COMMON.LGC'
    text, digest = _input(source, (SOURCE_SHA256[name],), name)
    original = '    \tSendCommandA( -1, EXT_ADDSKILL, RPGHERO_MONEY, CurLevelMoney, false );'
    text = _replace(text, original, '''#ifdef COOP_CAMPAIGN
        SendCommandA( 0, EXT_ADDSKILL, RPGHERO_MONEY, CurLevelMoney, false );
#else
''' + original + '\n#endif')
    return text, _metadata(name, digest, text, legacy_win_cash_owner=0,
                           non_coop_original_preserved=True,
                           later_campaign_completion_supported=False)


def patch_debug(source: str | bytes) -> tuple[str, dict]:
    """Stop local-key cheat mutations in coop even if engine DebugMode is set."""
    name = 'Maps/util_help.lgc'
    text, digest = _input(source, (SOURCE_SHA256[name],), name)
    text = _replace(text, 'CheatsTact()\n{', '''CheatsTact()
{
#ifdef COOP_CAMPAIGN
    // This function consumes local keys and is not a shared command channel.
    return;
#endif''')
    return text, _metadata(name, digest, text, local_cheat_mutations_blocked_in_coop=True,
                           non_coop_original_preserved=True,
                           reason='Diagnostic runtimes can set DebugMode=1, bypassing stock NET early return.')


def patch_init(source: str | bytes, *, level: int) -> tuple[str, dict]:
    """Level01 enables once; Level02 only verifies the retained native pair."""
    if type(level) is not int or level not in INIT_INPUTS:
        raise ValueError('Shared-money initialization supports only Level01/Level02')
    name = 'Maps/old_campaign_init' + ('_level02' if level == 2 else '') + '.lgc'
    text, digest = _input(source, (INIT_INPUTS[level],), name)
    text = _replace(text, '#define OLD_CAMPAIGN_INIT_H 1\n',
                    '#define OLD_CAMPAIGN_INIT_H 1\n' + INIT_GLOBALS)
    text = _replace(text, '// 0 not attempted; 1 ready; 2 initializing; 90..99 guard failures.',
                    '// 0 not attempted; 1 ready; 2 initializing; 90..99 and101..102 guard failures.')
    insertion = INIT_CAPTURE_BEFORE
    if level == 1:
        insertion += INIT_ENABLE
    else:
        insertion += ('    // Map loading replaces VM statics, not the native owner pair/pool.\n'
                      '    // Status only: never re-enable a replacement pair or reset spent cash.\n')
    insertion += INIT_VERIFY
    text = _replace(text, '    OldCampaignRestoreRelations();', insertion + '    OldCampaignRestoreRelations();')
    fields = (
        ('shared_money_enable_calls', 'OldSharedMoneyEnableCalls'),
        ('shared_money_enable_result', 'OldSharedMoneyEnableResult'),
        ('shared_money_status', 'OldSharedMoneyStatus'),
        ('shared_money_host_before', 'OldSharedMoneyHostBefore'),
        ('shared_money_guest_before', 'OldSharedMoneyGuestBefore'),
        ('shared_money_host_after', 'OldSharedMoneyHostAfter'),
        ('shared_money_guest_after', 'OldSharedMoneyGuestAfter'),
    )
    anchor = '    OldCampaignValue(file, "ready", OldCampaignReady);'
    text = _replace(text, anchor, anchor + '\n' + '\n'.join(
        f'    OldCampaignValue(file, "{key}", {value});' for key, value in fields))
    return text, _metadata(name, digest, text, level=level,
                           native_enable_command=203 if level == 1 else None,
                           native_status_command=204, initialization_cash_writes=0,
                           balance_policy='Existing host balance; never sum owners or assign a fixed amount.',
                           current_fresh_profile_expected_pool=520,
                           level02_policy='Require retained active owner identities; status only, no re-enable.',
                           fail_codes={'101': 'Native Level01 activation failed',
                                       '102': 'Inactive/replaced owner pair or unequal/changed/negative pool'},
                           caller_order='After both hero bindings and before relations/control/Ready.')
