"""Generate a bounded native-coop Level_02 entry from exact supplied sources.

This module only reads inputs and returns text/metadata. The caller writes an
isolated runtime and supplies old_campaign_transition.lgc with the passive
OldTransitionObserve function. No load request, RPG grant, quest reset, save,
shop transaction, or further campaign transition is implemented here.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct


FEATURE = 'old-campaign-level02-entry-v1'
MAP_SHA256 = 'e52d86951d508743ed625ef0b4910e7ba2c4ce633e3e94029c179a466186ff79'
LEVEL_SHA256 = 'ad0b9f7dce8e8b7634bb7e94e64de0eade8b849fea670bee4fb384690018471c'
INIT_SHA256 = 'f5022e4a80dc048c2f2b81396be4a7705ab0fa6051728675ec36af2132745268'
INIT_NAME = 'Maps/old_campaign_init_level02.lgc'
LEVEL_NAME = 'Maps/Level_02.lgc'

# The campaign's database identifier deliberately remains Level_01 on this
# physical map. Changing that identifier selects a different quest universe.
ORIGINAL_INIT_GUARD = '''    if(giMapType != MAP_TYPE_LEVEL || gsCampaignName != "Level_01" || gbSurviveMode)
        return OldCampaignFail(90); // This helper supports only campaign Level_01.'''
LEVEL02_INIT_GUARD = r'''    if(giMapType != MAP_TYPE_LEVEL || gsCampaignName != "Level_01" || gbSurviveMode
        || ToLower(GetMapName()) != "maps\\level_02.map"
        || giCurLevCmpgn != 2 || giCurLevCmpgnReal != 2)
        return OldCampaignFail(90); // Exact physical Level_02; same campaign database.'''

# These global executable-wrapper allowlist entries are Level_01-specific.
# The exact Level_02 bytes contain neither the source XYZ nor command tuple.
LEVEL01_TRIGGER_EXCLUSIONS = (
    ('dynamite_plant', (6446, 2600, 10), (6554, 2606, 70)),
    ('elevator_inspect', (3184, 5852, 90), (3204, 5833, 110)),
    ('elevator_unlock', (3089, 5880, 90), (3204, 5833, 110)),
)

SHOP_GUARD = '''
// Shared request bookkeeping; text handles below are presentation only.
static int OldLevel02ShopBlockedRequests = 0;
static int OldLevel02ShopNotice = 0;
static int OldLevel02ShopNoticeUntil = 0;

OldLevel02ShopGuard()
{
    if(OldLevel02ShopNoticeUntil && GetTime() >= OldLevel02ShopNoticeUntil)
    {
        Destroy(OldLevel02ShopNotice);
        OldLevel02ShopNotice = 0;
        OldLevel02ShopNoticeUntil = 0;
    }
    if(Action6 == -1)
        return;
    // Consume only the pending shop request before the stock campaign tact.
    // Do not open a menu, pause, or alter quests, items, money, or map type.
    Action6 = -1;
    OldLevel02ShopBlockedRequests = OldLevel02ShopBlockedRequests + 1;

    // Local presentation never determines shared request handling.
    Destroy(OldLevel02ShopNotice);
    OldLevel02ShopNotice = CreateText(5, ScreenX() / 2,
        ScreenY() - 140 + 4000, 4000,
        "Магазин для совместной игры пока недоступен", BEH_CENTER);
    OldLevel02ShopNoticeUntil = GetTime() + 4000;
}
'''


def _replace(text: str, before: str, after: str) -> str:
    if text.count(before) != 1:
        raise ValueError('Expected exactly one Level_02 source fragment: ' + before)
    return text.replace(before, after)


def _script_hash(text: str) -> str:
    return hashlib.sha256(text.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251')).hexdigest()


def patch(map_source: bytes, level_source: bytes, init_source: bytes) -> tuple[str, str, dict]:
    """Return ``(level_script, init_helper, metadata)`` without changing files."""
    sources = (
        ('Maps/Level_02.map', map_source, MAP_SHA256),
        (LEVEL_NAME, level_source, LEVEL_SHA256),
        ('templates/old_campaign_init.lgc', init_source, INIT_SHA256),
    )
    for name, source, expected in sources:
        if not isinstance(source, bytes):
            raise TypeError('Expected bytes for ' + name)
        if hashlib.sha256(source).hexdigest() != expected:
            raise ValueError('Unsupported Level_02 source: ' + name)

    # Pin the original single host spawn and immediate map-entry quest. The
    # full map digest also guards every remaining sprite and compiled stack.
    if struct.unpack_from('<IIfff', map_source, 0x89960) != (0x186D9EF0, 250, 2728, 9599, 90):
        raise ValueError('Original Level_02 host spawn changed')
    for offset, expected in (
        (0xD6A40, (131, 1, 14, 0)),
        (0xD6A30, (78, 1, 38, 0)),
        (0xD729C, (43, 3665, 8506, 25)),
        (0xD728C, (131, 6, 1, 0)),
    ):
        if struct.unpack_from('<4i', map_source, offset) != expected:
            raise ValueError('Original Level_02 entry/shop command changed at ' + hex(offset))
    exclusions = []
    for name, source_xyz, trigger in LEVEL01_TRIGGER_EXCLUSIONS:
        xyz_count = map_source.count(struct.pack('<3f', *source_xyz))
        command_count = map_source.count(struct.pack('<4i', 43, *trigger))
        if xyz_count or command_count:
            raise ValueError('Unexpected Level_01 party-trigger bytes in Level_02: ' + name)
        exclusions.append({'name': name, 'source_xyz_matches': xyz_count,
                           'act43_tuple_matches': command_count})

    init = init_source.decode('ascii').replace('\r\n', '\n')
    init = _replace(init, '// Disposable ORIGINAL-game Level_01 native-coop smoke only.',
                    '// Generated ORIGINAL-game Level_02 native-coop entry smoke only.')
    init = _replace(init, '// Include after COMMON. Call once after SetMapTypeEx / SetScrollBoxEx(0).',
                    '// Include after COMMON. Call once after the original Level_02 SetMapTypeEx.')
    init = _replace(init, ORIGINAL_INIT_GUARD, LEVEL02_INIT_GUARD)
    # Deliberately preserve the already-tested guest spawn/relations algorithm.
    # In this first lifecycle diagnostic it still resets guest HP to maximum;
    # it therefore cannot establish exact damaged-HP continuity by itself.
    init = _replace(init, '    SendCommandA(3, EXT_RESETHEROHP);',
                    '    // Provisional entry policy: refill guest HP, as in the Level_01 prototype.\n'
                    '    SendCommandA(3, EXT_RESETHEROHP);')
    init = _replace(init,
                    "    // player. Keep the engine's stock control type instead of overriding it.",
                    '    // player. Restore stock NORMAL after the previous level froze input.')
    init = _replace(init, '    SendCommandA(0, EXT_DISABLEFLAGMANCONTROL, 0);',
                    '    SetPlayerControl(0, PLAYERCONTROL_NORMAL);\n'
                    '    SetPlayerControl(3, PLAYERCONTROL_NORMAL);\n'
                    '    SendCommandA(0, EXT_DISABLEFLAGMANCONTROL, 0);')

    level = level_source.decode('cp1251').replace('\r\n', '\n')
    level = ('#define NET_GAME_RUN 111\n#define COOP_CAMPAIGN 1\n'
             '#define OLD_LEVEL02_SHOP_GUARD 1\n' + level)
    level = _replace(level, '#include "maps\\common_compaign.lgc"',
                     '#include "maps\\common_compaign.lgc"\n'
                     '#include "maps\\old_campaign_init_level02.lgc"\n' + SHOP_GUARD + '\n'
                     '#include "maps\\old_campaign_transition.lgc"')
    level = _replace(level, '    InitGame();', '    OldCampaignInit();')
    level = _replace(level, '  if( GameTact() )',
                     '  if(!OldCampaignReady) return;\n'
                     '  OldTransitionObserve();\n'
                     '  // OLD_LEVEL02_TRANSITION_TACT_HOOK\n'
                     '  if( GameTact() )')
    level = _replace(level, '  CompaignGameTact();',
                     '  OldLevel02ShopGuard();\n  CompaignGameTact();')

    metadata = {
        'feature': FEATURE,
        'scope': 'Bounded physical Level_02 entry after a native connected map change',
        'source_sha256': {name: expected for name, _, expected in sources},
        'output_sha256': {LEVEL_NAME: _script_hash(level), INIT_NAME: _script_hash(init)},
        'output_names': {'level': LEVEL_NAME, 'init': INIT_NAME},
        'required_caller_helper': 'Maps/old_campaign_transition.lgc: OldTransitionObserve()',
        'optional_tact_marker': '// OLD_LEVEL02_TRANSITION_TACT_HOOK',
        'physical_map': 'maps\\Level_02.map',
        'campaign_database': 'Level_01',
        'campaign_level': 2,
        'native_armies': [0, 3],
        'original_host_spawn': {'vid': 250, 'position': [2728, 9599, 90], 'count': 1},
        'guest_spawn': 'Existing deterministic same-floor CanPlace ring, 120..400 from host; no telefrag',
        'entry_effects': {'music': 14, 'quest_group': 1, 'quest_number': 38,
                          'quest_removes': ['Obj_accesskey', 'Obj_dynamite']},
        'first_shop_trigger': {'position': [3665, 8506], 'radius': 25, 'action6': 1},
        'shop_request_guard': {
            'scope': 'Hash-pinned physical Level_02 only',
            'native_request': {'offset': '0xD728C', 'command': [131, 6, 1, 0]},
            'policy': 'Consume Action6 != -1 before CompaignGameTact; leave bLegalShop untouched',
            'shared_counter': 'OldLevel02ShopBlockedRequests',
            'observer_macro': 'OLD_LEVEL02_SHOP_GUARD',
            'message': 'Магазин для совместной игры пока недоступен',
            'message_milliseconds': 4000,
            'message_modal': False,
            'text_handles_used_in_shared_logic': False,
            'pause_menu_quest_rpg_map_setters': False,
        },
        'level01_party_trigger_exclusions': exclusions,
        'static_charge_audit': {
            'original_map_vid770_count': 0,
            'original_map_build_vid770_count': 0,
            'original_map_dynamite_item_labels': 0,
            'claim': 'Hash-pinned original map/start only; not a general campaign charge audit',
        },
        'hp_policy': {
            'host': 'Original engine/map initialization; this helper does not call host EXT_RESETHEROHP',
            'guest': 'Explicit EXT_RESETHEROHP(3) before creating its sprite, preserved from Level_01 helper',
            'exact_damaged_hp_continuity_proven': False,
        },
        'control_policy': {
            'armies': [0, 3],
            'type': 'PLAYERCONTROL_NORMAL',
            'value': 2,
            'timing': 'After hero spawn, before clearing EXT_DISABLEFLAGMANCONTROL',
            'reason': 'Restore input explicitly after the previous finish set PLAYERCONTROL_NONE',
            'stock_default_evidence': 'player::Reset 0x4B6BA0 writes player+0xF8=2 at 0x4B6BE3',
        },
        'new_item_or_skill_grants': False,
        'quest_system_reset': False,
        'rpg_database_reload': False,
        'save_support': False,
        'shop_transactions_supported': False,
        'onward_transition_supported': False,
        'runtime_tested': False,
        'known_limitations': ['Death/revival is deferred',
                              'Radio presentation at the Level_01 gate remains a known issue'],
    }
    return level, init, metadata


def prepare(original_root: Path, init_template: Path | None = None) -> tuple[str, str, dict]:
    """Read the pinned originals/template and generate; never write a runtime."""
    root = Path(original_root)
    template = (Path(__file__).resolve().parent / 'templates' / 'old_campaign_init.lgc'
                if init_template is None else Path(init_template))
    return patch((root / 'Maps' / 'Level_02.map').read_bytes(),
                 (root / 'Maps' / 'Level_02.lgc').read_bytes(), template.read_bytes())
