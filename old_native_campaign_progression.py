"""Data-driven mission entry, shared completion and native onward loading.

Original maps, quests, rewards and RPG descriptors are retained. This is a
build-time composition of the audited entry/finish mechanisms, not save/load.
"""
from dataclasses import asdict
import hashlib
from pathlib import Path
import struct
import re
import json

from old_native_campaign_missions import MISSIONS, mission_by_number, mission_source, RELOADED_ENABLED
from old_native_campaign_exit import gate_helper
from old_native_campaign_entries import ENTRIES, GATES

FEATURE = 'old-campaign-progression-v3'
LEVEL03_GATES = GATES[3]


def script_bytes(text):
    if isinstance(text, bytes):
        return text
    return text.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251')


def digest(text):
    return hashlib.sha256(script_bytes(text)).hexdigest()


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Campaign composition anchor changed: ' + repr(before[:85]))
    return text.replace(before, after)


def guard_mission(root, number):
    from old_native_story_item_registry import LEVELS_SHA256
    mission = mission_by_number(number)
    data = mission_source(root, mission.path).read_bytes()
    if hashlib.sha256(data).hexdigest() != mission.map_sha256:
        raise ValueError('Unsupported mission map: ' + mission.path)
    levels = (root / 'levels.cfg').read_bytes()
    if hashlib.sha256(levels).hexdigest() != LEVELS_SHA256:
        raise ValueError('Unsupported campaign database')
    header = f'Map=Lvl_{mission.native:02d}\r\n'.encode()
    if levels.count(header) != 1:
        raise ValueError('Original mission metadata changed')
    section = levels.split(header, 1)[1].split(b';************', 1)[0]
    properties = dict(line.split(b'=', 1) for line in section.splitlines() if b'=' in line)
    # The stock road mission omits AddMoneyMAIN; the native default is zero.
    if properties.get(b'TimeLine') != b'0' or int(properties.get(b'AddMoneyMAIN', b'0')) != mission.finish_money:
        raise ValueError('Original completion reward changed')
    return mission, data


def finish(root, number, gates, *, target=None):
    from old_native_finish_patch import prepare
    from old_native_shared_money_scripts import patch_finish
    root = Path(root)
    mission, data = guard_mission(root, number)
    if mission.ending_only:
        if gates or target is not None or data.count(struct.pack('<4i', 131, 9, 1, 0)):
            raise ValueError('Ending-only mission must not have an ordinary exit')
        from old_native_campaign_finale_lifecycle import helper as finale_helper
        source = finale_helper(number)
        return source, dict(feature=FEATURE, mission=number, target=None, gates=[],
            source_map_sha256=mission.map_sha256, output_sha256=digest(source),
            helper_file=f'Maps/old_campaign_finish_level{number:02d}.lgc',
            tact_call=f'if(OldLevel{number:02d}FinishTact()) return;',
            onward_map_load=False, ending_only=True, cash_awards_per_completion=0,
            original_money=mission.finish_money, quest_state_setters=False)
    source, _ = prepare(root)
    source, _ = patch_finish(source)
    for gate in gates:
        packed = gate.sprite.packed()
        if data[gate.sprite.offset:gate.sprite.offset + len(packed)] != packed:
            raise ValueError('Finish sprite changed: ' + gate.name)
        for command in gate.commands:
            if data[command.offset:command.offset + 16] != command.packed():
                raise ValueError('Finish command changed: ' + gate.name)
    if data.count(struct.pack('<4i', 131, 9, 1, 0)) != len(gates):
        raise ValueError('Unreviewed mission completion writer')
    values = tuple(v for gate in gates for v in (*gate.trigger, gate.quest[0] - 1, gate.quest[1]))
    declarations = (f'\n#define OLD_MISSION_FINISH_GATES {len(gates)}\n'
                    'static int OldFinishSelectedGate = -1;\n'
                    f'static int OldFinishGateUnlocked[{len(gates)}];\n'
                    f'static int OldFinishGateData[{len(values)}] = {{' + ', '.join(map(str, values)) + '};\n')
    source = once(source, 'static int OldFinishText3 = 0;\n', 'static int OldFinishText3 = 0;\n' + declarations)
    start = source.index('OldFinishHeroReady(int army)')
    end = source.index('OldFinishShowText()', start)
    source = source[:start] + gate_helper() + '\n' + source[end:]
    source = once(source, '    if(OldFinishFault || OldFinishStage == 2)',
                  '    for(int gate = 0; gate < OLD_MISSION_FINISH_GATES; gate++)\n'
                  '        OldFinishGateQuestReady(gate);\n'
                  '    if(OldFinishFault || OldFinishStage == 2)')
    source = once(source, '    if(OldFinishStage != 1)\n',
                  '    if(OldFinishStage == 1) OldFinishSelectedGate = OldFinishSelectGate();\n'
                  '    if(OldFinishStage != 1)\n')
    source = once(source, '    if(!NetProperty(NET_IS_CONNECT) || NetProperty(NET_NO_PLAYERS) != 2\n'
                  '        || giCurLevCmpgn != 1 || giCurLevCmpgnReal != 1)',
                  f'    if(!OldFinishSessionValid() || giCurLevCmpgn != {mission.native} || giCurLevCmpgnReal != {mission.native}\n'
                  f'        || CurLevelMoney != {mission.finish_money})')
    source = once(source, '    // Guard before mutations. Do the original Win bookkeeping once, with',
                  '    if(OldFinishMoneyBefore[0] != OldFinishMoneyBefore[3])\n'
                  '    { OldFinishFault = 2; return true; }\n'
                  '    // Guard before mutations. Do the original Win bookkeeping once, with')
    # Stock WinOnBegin/Action8 is a story notice, not permission for one
    # peer's Space key to bypass the shared Action9 exit and award accounting.
    source = once(source, 'OldFinishTact()\n{', '''OldFinishNarrative()
{
    if(!Action8 && GameState != GAME_PREWIN) return;
    Action8 = 0;
    if(GameState == GAME_PREWIN) GameState = GAME_NORMAL;
    Destroy(WinText1); WinText1 = 0;
    Destroy(WinText2); WinText2 = 0;
    WinTextCreated = false;
}

OldFinishTact()
{
    OldFinishNarrative();''')
    source = source.replace('maps\\\\level_01.map', mission.path.lower().replace('/', '\\\\'))
    source = source.replace('Generated for original OLD Level_01', f'Generated for original OLD Level_{number:02d}')
    source = source.replace('The hash-guarded map has exactly one Action9 writer, with value 1.',
                            'All reviewed finish stacks request Action9=1 after their original quest wait.')
    if target is not None:
        guard_mission(root, target)
        source = onward(source, number, target)
    else:
        source = source.replace('Продолжение кампании пока недоступно.',
                                f'Миссия {mission.label} завершена. Следующая миссия пока не подключена.')
    prefix = f'OldLevel{number:02d}Finish'
    source = source.replace('OldFinish', prefix)
    source = source.replace('OLD_CAMPAIGN_FINISH_H', f'OLD_CAMPAIGN_LEVEL{number:02d}_FINISH_H')
    metadata = dict(feature=FEATURE, mission=number, target=target, gates=[asdict(g) for g in gates],
                    source_map_sha256=mission.map_sha256, output_sha256=digest(source),
                    helper_file=f'Maps/old_campaign_finish_level{number:02d}.lgc',
                    tact_call=f'if({prefix}Tact()) return;', onward_map_load=target is not None,
                    cash_awards_per_completion=1, original_money=mission.finish_money,
                    both_living_at_same_exit=True, quest_state_setters=False,
                    quest_gate_latched=True, archived_begun_quest_supported=True,
                    native_exit_request_required=True, waiting_gate_reselected=True,
                    native_host_load_only=True, durable_save_supported=False)
    return source, metadata


def onward(source, number, target):
    """Reuse the audited shared dwell / host-only native NET_GAME_START path."""
    from old_native_transition_patch import GLOBALS, TRANSITION
    current, following = mission_by_number(number), mission_by_number(target)
    transition = TRANSITION.replace('giCurLevCmpgn != 2', f'giCurLevCmpgn != {following.native}')
    transition = transition.replace('giCurLevCmpgnReal != 1', f'giCurLevCmpgnReal != {current.native}')
    transition = transition.replace('OldFinishLevelAfter != 2', f'OldFinishLevelAfter != {following.native}')
    transition = transition.replace('level_02.map', Path(following.path).name.lower())
    transition = transition.replace('Level_02', Path(following.path).stem)
    transition = transition.replace('OldCheckpointBegin(giCurLevCmpgn,', f'OldCheckpointBegin({target},')
    if following.native != current.native + 1 or following.physical_name:
        target_path = following.path.replace('/', '\\\\')
        source = once(source, '    IncLevelNumber(false);\n    LoadCurLevel(); // Original selects NextMapName; does not schedule a load.',
            f'    SetLevelNumber({following.native}, -1);\n'
            f'    NextMapName = "{target_path}"; // Explicit stage, unchanged native quest indices.')
    transition = transition.replace('внутри лифта', 'у одного выхода')
    source = once(source, 'static int OldFinishText3 = 0;\n', 'static int OldFinishText3 = 0;\n' + GLOBALS)
    source = once(source, 'OldFinishTact()\n{', transition + '\nOldFinishTact()\n{')
    source = once(source, '    if(OldFinishStage != 1)\n', '    OldFinishWaiting();\n    if(OldFinishStage != 1)\n')
    source = once(source, '    if(OldFinishFault || OldFinishStage == 2)\n        return true;\n',
                  '    OldTransitionTactCount = OldTransitionTactCount + 1;\n'
                  '    if(OldFinishFault) return true;\n'
                  '    if(OldFinishStage == 2) return OldTransitionTact();\n')
    source = once(source, '    OldFinishShowText();\n    Pause(1);\n    return true;\n',
                  '    OldFinishShowText();\n    OldTransitionStage = 1;\n'
                  '    OldTransitionCommitTact = OldTransitionTactCount;\n'
                  '    OldTransitionCommitTime = GetTime();\n    Pause(0);\n    return true;\n')
    return source.replace('Продолжение кампании пока недоступно.', f'Переход к миссии {following.label}...')


def entry(root, number):
    """Shared deterministic two-hero entry, preserving the active purse/RPG."""
    from old_native_level02_patch import prepare
    from old_native_shared_money_scripts import patch_init
    root = Path(root)
    mission, data = guard_mission(root, number)
    original = mission_source(root, mission.path.replace('.map', '.lgc')).read_bytes()
    evidence = ENTRIES[number]
    if hashlib.sha256(original).hexdigest() != evidence.script_sha256:
        raise ValueError('Unreviewed mission entry script')
    # Same stock entry script, host VID250 and no scripted guest/respawn.
    if data[evidence.spawn.offset:evidence.spawn.offset + 20] != evidence.spawn.packed():
        raise ValueError('Unreviewed mission spawn')
    _, init, _ = prepare(root)
    init, _ = patch_init(init, level=2)
    stem = Path(mission.path).stem
    init = init.replace('Level_02', stem).replace('level_02', stem.lower())
    init = once(init, 'giCurLevCmpgn != 2 || giCurLevCmpgnReal != 2',
                f'giCurLevCmpgn != {mission.native} || giCurLevCmpgnReal != {mission.native}')
    level = '#define NET_GAME_RUN 111\n#define COOP_CAMPAIGN 1\n#define OLD_CAMPAIGN_SHOP_UI 1\n'
    level += original.decode('cp1251').replace('\r\n', '\n')
    level = once(level, '#include "maps\\common_compaign.lgc"',
                 '#include "maps\\common_compaign.lgc"\n'
                 f'#include "maps\\old_campaign_init_level{number:02d}.lgc"\n'
                 f'#include "maps\\old_campaign_finish_level{number:02d}.lgc"\n'
                 '#include "maps\\old_campaign_shop.lgc"')
    # Original maps use different indentation, but exactly one lifecycle call.
    def statement(text, old, replacement):
        pattern = r'(?m)^[ \t]*' + re.escape(old) + r'[ \t]*$'
        if len(re.findall(pattern, text)) != 1:
            raise ValueError('Mission lifecycle anchor changed: ' + old)
        return re.sub(pattern, lambda _: replacement, text)
    level = statement(level, 'InitGame();', '    OldCampaignInit();')
    level = statement(level, 'if( GameTact() )',
                 '  if(!OldCampaignReady) return;\n'
                 f'  if(OldLevel{number:02d}FinishTact()) return;\n'
                 '  OldCampaignShopTact();\n  if( GameTact() )')
    level = statement(level, 'QuestsTact();', '  TeleportTact();\n  QuestsTact();')
    level = statement(level, 'CompaignGameTact();',
                 '  // Shared shop UI owns Action6. Never open the local mutating menu.\n'
                 '  if(Action6 != -1) Action6 = -1;\n'
                 f'  OldLevel{number:02d}FinishNarrative();\n  CompaignGameTact();')
    from old_native_campaign_specials import adapt
    level = adapt(level, number)
    if mission.physical_name:
        from old_native_reloaded_scripts import adapt_entry
        level = adapt_entry(level, number)
    return level, init


def extend_shop(source):
    """Keep the stock UI/transport; generate access rules from mission data."""
    from old_native_campaign_shop_locations import helper as shop_location_helper
    before = digest(source)
    scope = ' || '.join(f'(giCurLevCmpgnReal == {m.native} && map == "{m.path.lower().replace("/", chr(92) * 2)}")' for m in MISSIONS)
    old_scope = ('    if(!((giCurLevCmpgnReal == 1 && map == "maps\\\\level_01.map")\n'
                 '        || (giCurLevCmpgnReal == 2 && map == "maps\\\\level_02.map"))) return 0;')
    source = once(source, old_scope, '    if(!(' + scope + ')) return 0;')
    source = once(source, '    // Guarded levels.cfg: IDs1_1_39/40 occupy insertion indices35/36.',
                  '    // Reviewed stock shop stacks have no quest prerequisite.\n'
                  '    if(OldShopPhysicalStage() != 2) return OldShopMissionAvailable();\n'
                  '    // Guarded levels.cfg: IDs1_1_39/40 occupy insertion indices35/36.')
    helpers = shop_location_helper(MISSIONS)
    source = once(source, 'giCurLevCmpgnReal != 2 || !OldShopStoryReady()', '!OldShopMissionAvailable() || !OldShopStoryReady()')
    source = once(source, '        if(giCurLevCmpgnReal == 2)', '        if(OldShopMissionAvailable())')
    if source.count('3665, 8506') != 3:
        raise ValueError('Shop location consumers changed')
    source = source.replace('3665, 8506', 'OldShopLocationX(army), OldShopLocationY(army)')
    source = once(source, 'OldShopStoryReady()\n{', helpers + '\nOldShopStoryReady()\n{')
    from old_native_campaign_entry_shop import adapt_shop
    source = adapt_shop(source)
    return source, dict(feature=FEATURE, input_sha256=before, output_sha256=digest(source),
                        personal_maps=[m.number for m in MISSIONS],
                        shop_maps=[m.number for m in MISSIONS if m.shop_locations or m.entry_shop],
                        multiple_vendors=True, physical_map_scoped=True,
                        locations={str(m.number): m.shop_locations for m in MISSIONS if m.shop_locations})


def prepare(root):
    root = Path(root)
    from old_native_campaign_shop_locations import validate_sources as validate_shop_sources
    validate_shop_sources(root)
    from old_native_campaign_inventory_queries import validate_levels
    validate_levels((root / 'levels.cfg').read_bytes())
    from old_native_campaign_common import prepare as prepare_common_events
    common, _, _, common_events = prepare_common_events(root, shared_money=True, progression=True)
    files = {'Maps/common_compaign.lgc': common}
    finishes = {}
    for index, mission in enumerate(MISSIONS[1:], 1):
        number = mission.number
        target = MISSIONS[index + 1].number if index + 1 < len(MISSIONS) else None
        helper, metadata = finish(root, number, GATES[number], target=target)
        files[metadata['helper_file']] = helper
        finishes[str(number)] = metadata
    for number in ENTRIES:
        level, init = entry(root, number)
        files[mission_by_number(number).path.replace('.map', '.lgc')] = level
        files[f'Maps/old_campaign_init_level{number:02d}.lgc'] = init
    from old_native_campaign_vehicles import prepare as prepare_vehicles
    vehicle_files, vehicles = prepare_vehicles(root)
    files.update(vehicle_files)
    from old_native_level12_carrier import prepare as prepare_carrier
    carrier_files, carrier = prepare_carrier(root)
    files.update(carrier_files)
    from old_native_campaign_ending import NAME as ENDING_NAME, HELPER as ENDING_HELPER
    files[ENDING_NAME] = ENDING_HELPER
    from old_native_party_door_buttons import prepare as prepare_buttons
    button_files, buttons = prepare_buttons(root)
    files.update(button_files)
    from old_native_campaign_script_timing import prepare as prepare_timing
    timing_files, timing = prepare_timing(root)
    files.update(timing_files)
    reloaded = None
    resource_hashes = {}
    if RELOADED_ENABLED:
        from old_native_reloaded_scripts import extend_vehicle_files
        from old_native_reloaded_campaign import prepare_definitions
        from old_native_reloaded_assets import prepare as prepare_assets
        from old_native_campaign_missions import RELOADED_ROOT
        files, scripts = extend_vehicle_files(root, files, RELOADED_ROOT)
        from old_native_campaign_settings import _constants
        # CONST is shared with the existing display-settings adapter. Compose
        # both changes instead of overwriting the supported resolution table.
        files['Maps/CONST.LGC'] = _constants(files['Maps/CONST.LGC'])
        scripts['script_hashes']['Maps/CONST.LGC'] = digest(files['Maps/CONST.LGC'])
        files['Maps/common_defs2.lgc'] = prepare_definitions(root)
        imported, resources = prepare_assets(RELOADED_ROOT, root)
        resource_hashes = {name: hashlib.sha256(data).hexdigest() for name, data in imported.items()}
        reloaded = dict(scripts=scripts, resources=resources)
    file_hashes = {name: digest(text) for name, text in files.items()} | resource_hashes
    return files, dict(feature=FEATURE, finishes=finishes, output_sha256=hashlib.sha256(
        json.dumps(file_hashes, sort_keys=True).encode()).hexdigest(),
        files=file_hashes,
        vehicles=vehicles, carrier=carrier, door_buttons=buttons, script_timing=timing,
        reloaded=reloaded, common_events=common_events,
        supported_missions=[m.number for m in MISSIONS],
        onward_limit=MISSIONS[-1].number, runtime_tested=False)
