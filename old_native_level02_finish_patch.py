"""Pinned Level02 party completion, retaining the audited finish accounting.

Only the two original Action9 writers can request completion. Both living
heroes must gather at one quest-enabled exit. This is a terminal manual-play
checkpoint: it selects the original next mission but never loads Level03.
All functions are pure transformations or original-source readers.
"""
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import struct

from old_native_finish_patch import HELPER, SOURCES, prepare as prepare_finish
from old_native_interaction_schema import MapCommand, SpriteIdentity
from old_native_level02_interactions import LEVEL02
from old_native_level02_patch import LEVEL_SHA256
from old_native_shared_money_scripts import patch_finish as shared_money_finish


FEATURE = 'old-campaign-level02-finish-v1'
HELPER_NAME = 'Maps/old_campaign_finish_level02.lgc'
FINISH_SHA256 = 'f5d5b68f0367e5bf84976e2272089a101254c8f79dc039cb39b8e2373828f8d1'
LEVEL_HOOK_INPUT_SHA256 = 'a0886e281855128580ae8b56e6f4837e03e696d51ddf33ae21ac1d31eaada08e'


@dataclass(frozen=True, slots=True)
class FinishGate:
    name: str
    sprite: SpriteIdentity
    trigger: tuple[int, int, int]
    quest: tuple[int, int]
    commands: tuple[MapCommand, ...]


# Stored ACT77 var3 differs, but the native wait ignores it and asks the
# shared quest server whether state == 1 (4BADF0..4BAE91). The generated
# EXT_GETQUESTSSTATE calls use explicit source-ID mode, not list indices.
GATES = (
    FinishGate('interior_exit', SpriteIdentity(0x975E0, 0x18730508, 1712, (1852, 5888, 90)),
               (1852, 5948, 200), (1, 25), (
                   MapCommand(0xEBB67, (98, 1, 0, 0)),
                   MapCommand(0xEBB57, (77, 1, 25, 0)),
                   MapCommand(0xEBB47, (98, 0, 0, 0)),
                   MapCommand(0xEBB37, (43, 1852, 5948, 200)),
                   MapCommand(0xEBB27, (131, 9, 1, 0)),
               )),
    FinishGate('outer_exit', SpriteIdentity(0x8A680, 0x186DFCE0, 922,
               (3713.545166015625, 8032.154296875, 1.032938003540039)),
               (7230, 8409, 140), (1, 8), (
                   MapCommand(0xD7564, (77, 1, 8, 1)),
                   MapCommand(0xD7554, (43, 7230, 8409, 140)),
                   MapCommand(0xD7544, (131, 9, 1, 0)),
                   MapCommand(0xD7578, (134, -1, 0, 0)),
               )),
)

GATE_HELPER = r'''
OldFinishGateQuestReady(int gate)
{
    int base = gate * 5;
    // arg3=1 selects original quest IDs; it is not a flags selector.
    return SendCommand(EXT_GETQUESTSSTATE,
        OldFinishGateData[base + 3], OldFinishGateData[base + 4], 1) == 1;
}

OldFinishGateHeroNear(int army, int gate)
{
    int hero = Flagman(army);
    if(!hero || Action(hero, ACT_GET_HP) <= 0) return false;
    int base = gate * 5;
    return SizeTo(hero, OldFinishGateData[base], OldFinishGateData[base + 1])
        < OldFinishGateData[base + 2];
}

OldFinishSelectGate()
{
    for(int gate = 0; gate < OLD_LEVEL02_FINISH_GATES; gate++)
        if(OldFinishGateQuestReady(gate)
            && OldFinishGateHeroNear(0, gate) && OldFinishGateHeroNear(3, gate))
            return gate;
    return -1;
}

OldFinishHeroReady(int army)
{
    return OldFinishSelectedGate >= 0
        && OldFinishGateQuestReady(OldFinishSelectedGate)
        && OldFinishGateHeroNear(army, OldFinishSelectedGate);
}

OldFinishSessionValid()
{
    if(!NetProperty(NET_IS_CONNECT) || NetProperty(NET_NO_PLAYERS) != 2)
        return false;
    for(int army = 0; army < 8; army++)
        if((NetProperty(NET_IS_PLAYER_EXIST + army) != 0) != (army == 0 || army == 3))
            return false;
    return SendCommandA(0, 204, 0, 0, 0) == 1;
}
'''


def _bytes(text):
    return text.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251')


def _once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Level02 finish source anchor changed: ' + repr(before[:90]))
    return text.replace(before, after)


def patch(map_source, level_source, levels_source, finish_source=HELPER):
    sources = ((LEVEL02.path, map_source, LEVEL02.sha256),
               ('Maps/Level_02.lgc', level_source, LEVEL_SHA256),
               ('levels.cfg', levels_source, SOURCES['levels.cfg']))
    for name, data, expected in sources:
        if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Unsupported Level02 finish source: ' + name)
    if not isinstance(finish_source, str) or hashlib.sha256(_bytes(finish_source)).hexdigest() != FINISH_SHA256:
        raise ValueError('Expected exact original generated party finish helper')
    for gate in GATES:
        expected = gate.sprite.packed()
        if map_source[gate.sprite.offset:gate.sprite.offset + len(expected)] != expected:
            raise ValueError('Original Level02 finish source changed: ' + gate.name)
        for command in gate.commands:
            if map_source[command.offset:command.offset + 16] != command.packed():
                raise ValueError('Original Level02 finish command changed: ' + hex(command.offset))
    if map_source.count(struct.pack('<4i', 131, 9, 1, 0)) != len(GATES):
        raise ValueError('Unexpected number of original Level02 Action9 writers')
    if 'Map=Lvl_02\r\nTimeLine=0\r\nAddMoneyMAIN=1000' not in levels_source.decode('cp1251'):
        raise ValueError('Original Level02 completion reward changed')

    # Reuse the exact audited shared-wallet transformation. No duplicated
    # native award code or local-player reward selection is introduced.
    text, money = shared_money_finish(finish_source)
    text = _once(text, '// Generated for original OLD Level_01, only in COOP_CAMPAIGN.',
                 '// Generated for original OLD Level_02, only in COOP_CAMPAIGN; no onward map load.')
    text = text.replace('OLD_CAMPAIGN_FINISH_H', 'OLD_CAMPAIGN_LEVEL02_FINISH_H')
    values = tuple(value for gate in GATES for value in (*gate.trigger, gate.quest[0] - 1, gate.quest[1]))
    declarations = ('#define OLD_LEVEL02_FINISH_GATES ' + str(len(GATES)) + '\n'
                    'static int OldFinishSelectedGate = -1;\n'
                    'static int OldFinishGateData[' + str(len(values)) + '] = {'
                    + ', '.join(map(str, values)) + '};\n')
    text = _once(text, 'static int OldFinishText3 = 0;\n', 'static int OldFinishText3 = 0;\n' + declarations)
    original_ready = '''OldFinishHeroReady(int army)
{
    int hero = Flagman(army);
    if(!hero || Action(hero, ACT_GET_HP) <= 0)
        return false;
    return SizeTo(hero, 3831, 5334) < 120;
}'''
    text = _once(text, original_ready, GATE_HELPER.strip())
    text = _once(text, '"maps\\\\level_01.map"', '"maps\\\\level_02.map"')
    text = _once(text, '// The hash-guarded map has exactly one Action9 writer, with value 1.',
                 '// Both hash-guarded Level02 finish stacks write Action9=1.')
    text = _once(text, '    if(!OldFinishHeroReady(0) || !OldFinishHeroReady(3))',
                 '    if(OldFinishSelectedGate < 0) OldFinishSelectedGate = OldFinishSelectGate();\n'
                 '    if(!OldFinishHeroReady(0) || !OldFinishHeroReady(3))')
    text = _once(text, '''    if(!NetProperty(NET_IS_CONNECT) || NetProperty(NET_NO_PLAYERS) != 2
        || giCurLevCmpgn != 1 || giCurLevCmpgnReal != 1)''',
                 '''    if(!OldFinishSessionValid() || giCurLevCmpgn != 2 || giCurLevCmpgnReal != 2
        || CurLevelMoney != 1000)''')
    text = _once(text, '    // Guard before mutations. Do the original Win bookkeeping once, with',
                 '''    if(OldFinishMoneyBefore[0] != OldFinishMoneyBefore[3])
    {
        OldFinishFault = 2;
        return true;
    }
    // Guard before mutations. Do the original Win bookkeeping once, with''')
    text = _once(text, '"Продолжение кампании пока недоступно."',
                 '"Второй уровень завершён. Переход на третий пока отключён."')
    # Names are isolated from the outgoing Level01 transition helper.
    text = text.replace('OldFinish', 'OldLevel02Finish')
    return text, {
        'feature': FEATURE, 'helper_file': HELPER_NAME,
        'source_sha256': {name: expected for name, _, expected in sources},
        'input_finish_sha256': FINISH_SHA256,
        'output_sha256': hashlib.sha256(_bytes(text)).hexdigest(),
        'gates': [asdict(gate) for gate in GATES],
        'tact_call': 'if(OldLevel02FinishTact()) return;',
        'integration': 'Include after Level02 initialization; call after Ready and before shop tact/GameTact/CompaignGameTact.',
        'request_policy': 'Only original Action9=1; then both living armies0/3 at the same original quest-enabled exit.',
        'quest_policy': 'Original source IDs, native state==1; no quest writes or synthetic completion requests.',
        'source_request_count': 2, 'selected_gate_initial': -1,
        'native_shared_wallet_required': True, 'cash_awards_per_completion': 1,
        'cash_owner': 0, 'original_level02_money': 1000,
        'rank_and_on_level_win_owners': [0, 3], 'shared_money_transform': money,
        'requires_party_monster_stat_patch': True,
        'progression': 'Original bookkeeping increments campaign2 to3 and selects NextMapName, but never schedules or requests a load.',
        'terminal': 'GAME_WIN, both commands stopped/controlNONE, Pause(1), completion text; remaining level main skipped.',
        'native_pause_is_synchronized_input': True,
        'level03_entry_supported': False, 'onward_map_load': False,
        'durable_save_supported': False, 'rng_calls_added': 0,
        'map_modified': False, 'runtime_tested': False,
    }


def prepare(old_root):
    root = Path(old_root)
    finish, original = prepare_finish(root)
    text, metadata = patch((root / LEVEL02.path).read_bytes(),
                           (root / 'Maps/Level_02.lgc').read_bytes(),
                           (root / 'levels.cfg').read_bytes(), finish)
    metadata['inherited_original_source_sha256'] = original['source_sha256']
    return text, metadata


def patch_level02(source):
    """Integrate after the exact shop and logical-portal Level02 transforms."""
    if not isinstance(source, str):
        raise TypeError('Expected generated Level02 script text')
    if hashlib.sha256(_bytes(source)).hexdigest() != LEVEL_HOOK_INPUT_SHA256:
        raise ValueError('Expected exact portal-enabled Level02 shop/development script')
    text = source.replace('\r\n', '\n')
    include = '#include "maps\\old_campaign_init_level02.lgc"'
    text = _once(text, include, include + '\n#include "maps\\old_campaign_finish_level02.lgc"')
    ready = '  if(!OldCampaignReady) return;'
    text = _once(text, ready, ready + '\n  if(OldLevel02FinishTact()) return;')
    return text, {
        'feature': FEATURE + '-level-hook',
        'input_sha256': LEVEL_HOOK_INPUT_SHA256,
        'output_sha256': hashlib.sha256(_bytes(text)).hexdigest(),
        'helper_file': HELPER_NAME,
        'include_order': 'After Level02 initialization and before campaign shop helper.',
        'tact_order': 'After Ready and before shop, GameTact and CompaignGameTact.',
        'onward_map_load': False,
    }
