"""Compose the production campaign and verify every patched game resource."""
import hashlib
import json
from old_native_runtime import OLD, OLD_SHA, prepare
from old_native_installation import BUNDLE
from old_native_campaign_missions import mission_source, RELOADED_ENABLED, RELOADED_ROOT

SOURCE = BUNDLE / 'templates'


def write_script(path, text):
    path.write_bytes(text.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251'))

def build(role):
    """Build the complete shipping campaign in an isolated host/client copy."""
    campaign = True
    transition = True
    shared_money = True
    campaign_shop = True
    campaign_rewards = True
    admin_portal = True
    shared_portals = True
    registered_interactions = True
    level02_finish = True
    gameplay_hud = True
    campaign_menu = True
    campaign_progression = True
    startup_menu = True
    controls = False
    controls_host = False
    observe_frames = 1800
    folder = prepare(role)
    (folder / 'compiler-capacity-patch.json').unlink(missing_ok=True)
    campaign_input_patch = None
    from old_native_campaign_input import patch as patch_input
    data, campaign_input_patch = patch_input((OLD / 'input.cfg').read_bytes())
    (folder / 'input.cfg').write_bytes(data)
    (folder / 'transition-probe-build.json').unlink(missing_ok=True)
    (folder / 'Maps/old_campaign_shop_probe.lgc').unlink(missing_ok=True)
    (folder / 'Maps/old_campaign_money_probe.lgc').unlink(missing_ok=True)
    (folder / 'Maps/old_campaign_shop_route_probe.lgc').unlink(missing_ok=True)
    (folder / 'Maps/old_campaign_inventory_probe.lgc').unlink(missing_ok=True)
    (folder / 'Maps/old_campaign_development_probe.lgc').unlink(missing_ok=True)
    (folder / 'Maps/old_campaign_reward_probe.lgc').unlink(missing_ok=True)
    (folder / 'Maps/old_campaign_admin_probe.lgc').unlink(missing_ok=True)
    (folder / 'Maps/old_campaign_interior_probe.lgc').unlink(missing_ok=True)
    (folder / 'admin-portal-patch.json').unlink(missing_ok=True)
    (folder / 'portal-runtime.json').unlink(missing_ok=True)
    (folder / 'level02-finish-patch.json').unlink(missing_ok=True)
    (folder / 'Maps/old_campaign_finish_level02.lgc').unlink(missing_ok=True)
    (folder / 'campaign-menu-patch.json').unlink(missing_ok=True)
    (folder / 'gameplay-hud-patch.json').unlink(missing_ok=True)
    for name in ('Maps/mainmenu.lgc', 'Maps/mainmenu.men', 'Maps/common_charscreen.lgc', 'Maps/util_invuln.lgc',
                 'Maps/util_car.lgc', 'Maps/util_car2.lgc', 'Maps/CONST.LGC', 'Maps/common_defs2.lgc',
                 'Maps/util_vehicleconst.lgc', 'Maps/util_damageframe.lgc', 'Weapon.cfg'):
        (folder / name).write_bytes((OLD / name).read_bytes())
    (folder / 'Maps/old_campaign_party_vehicle.lgc').unlink(missing_ok=True)
    for name in ('Maps/old_campaign_lobby.map', 'Maps/old_campaign_lobby.lgc'):
        (folder / name).unlink(missing_ok=True)
    from old_native_campaign_settings import STOCK_HASHES as settings_assets
    for name in settings_assets:
        (folder / name).write_bytes((OLD / name).read_bytes())
    settings_files = {}
    stock_ui_files = {}
    # prepare() only fills missing assets; explicitly restore previously patched
    # shared UI scripts when building another composition in the same runtime.
    (folder / 'Maps/common_statebar.lgc').write_bytes((OLD / 'Maps/common_statebar.lgc').read_bytes())
    campaign_settings_patch = None
    from old_native_campaign_settings import prepare as prepare_settings
    settings_files, campaign_settings_patch = prepare_settings(OLD)
    for name, data in settings_files.items():
        (folder / name).write_bytes(data)
    (folder / 'campaign-reward-patch.json').unlink(missing_ok=True)
    for name in ('Maps/old_campaign_shop.lgc', 'Maps/old_campaign_shop_transport.lgc',
                 'campaign-shop-patch.json'):
        (folder / name).unlink(missing_ok=True)
    (folder / 'Maps/common_perks.lgc').write_bytes((OLD / 'Maps/common_perks.lgc').read_bytes())
    shared_scripts = {}
    for name, operation in (('COMMON.LGC', 'patch_common'), ('util_help.lgc', 'patch_debug')):
        original = (OLD / 'Maps' / name).read_bytes()
        import old_native_shared_money_scripts as money_scripts
        script, metadata = getattr(money_scripts, operation)(original)
        write_script(folder / 'Maps' / name, script)
        shared_scripts['common' if name == 'COMMON.LGC' else 'debug'] = metadata
    (folder / 'Maps' / 'old_game_lobby.map').write_bytes((OLD / 'Maps' / 'shop.map').read_bytes())
    lobby = (SOURCE / 'old_game_lobby.lgc').read_text('ascii')
    lobby = lobby.replace('#define OLD_GAME_HOST 1', '#define OLD_GAME_HOST ' + str(int(role == 'host')))
    lobby = lobby.replace('maps\\\\cooperative\\\\cooperative.map', 'maps\\\\Level_01.map')
    lobby = lobby.replace('"CharSurv1"', '"Char1"').replace('EXT_SetPlayerMenuType, 1', 'EXT_SetPlayerMenuType, 0')
    lobby = lobby.replace('AS2_OLD_GAME_PROBE', 'AS2_OLD_CAMPAIGN_PROBE')
    lobby = lobby.replace('SendCommand(EXT_ReloadDB);', 'SendCommand(EXT_ReloadDB);\n        SendCommand(EXT_ResetAllQuests);')
    lobby = lobby.replace('AS2_OLD_CAMPAIGN_PROBE', 'AS2_OLD_CAMPAIGN_DEVELOPMENT_V3')
    lobby = lobby.replace('AS2_OLD_CAMPAIGN_DEVELOPMENT_V3', 'AS2_OLD_CAMPAIGN_REWARDS_V1')
    lobby = lobby.replace('AS2_OLD_CAMPAIGN_REWARDS_V1', 'AS2_OLD_CAMPAIGN_ADMIN_V1')
    write_script(folder / 'Maps' / 'old_game_lobby.lgc', lobby)
    observer = (SOURCE / 'old_game_observe.lgc').read_text('ascii')
    quest_observer = None
    from old_native_quest_observer import prepare as prepare_quest_observer
    quest_observer = prepare_quest_observer(folder)
    values = '\n'.join('    OldGameValue(file, "' + field
        + '", SendCommand(EXT_GETQUESTSSTATE, 0, ' + str(mapping['subquest_index']) + '));'
        for field, mapping in quest_observer['fields'].items())
    assert observer.count('    // OLD_STORY_QUEST_VALUES') == 1
    observer = observer.replace('    // OLD_STORY_QUEST_VALUES', values)
    observer = observer.replace('OldGameFrame > 1800', 'OldGameFrame > ' + str(observe_frames))
    from old_native_portal_runtime import adapt_observer
    observer = adapt_observer(observer, 'bunker')
    write_script(folder / 'Maps' / 'old_game_observe.lgc', observer)
    gameplay = (OLD / 'Maps' / 'COOPERATIVE' / 'cooperative.lgc').read_text('cp1251')
    assert gameplay.count('NetGameTact();') == 1
    gameplay = gameplay.replace('#include "maps\\common.lgc"',
                                '#include "maps\\common.lgc"\n#include "maps\\old_game_observe.lgc"')
    gameplay = gameplay.replace('NetGameTact();', 'NetGameTact();\n    OldGameObserve();')
    write_script(folder / 'Maps' / 'COOPERATIVE' / 'cooperative.lgc', gameplay)
    campaign_common = (OLD / 'Maps' / 'common_compaign.lgc').read_text('cp1251')
    roof_patch = None
    combat_observer = None
    finish_patch = None
    party_stat_patch = None
    dynamite_patch = None
    transition_patch = None
    level02_patch = None
    mission_statistics_patch = None
    rat_observer = None
    from old_native_party_statistics_patch import patch as patch_mission_statistics
    statistics, mission_statistics_patch = patch_mission_statistics((OLD / 'Maps/util_statistics.lgc').read_bytes())
    write_script(folder / 'Maps/util_statistics.lgc', statistics)
    (folder / 'mission-statistics-patch.json').write_text(json.dumps(mission_statistics_patch, indent=2), 'utf-8')
    from old_native_combat_observer import prepare as prepare_combat_observer
    from old_native_finish_patch import prepare as prepare_finish, patch_monsters
    monsters_text, combat_observer = prepare_combat_observer(OLD)
    monsters_text, party_stat_patch = patch_monsters(monsters_text)
    write_script(folder / 'Maps' / 'MONSTERS.LGC', monsters_text)
    (folder / 'combat-observer.json').write_text(json.dumps(combat_observer, indent=2), 'utf-8')
    finish_text, finish_patch = prepare_finish(OLD)
    from old_native_transition_patch import patch as patch_transition
    finish_text, transition_patch = patch_transition(finish_text)
    finish_patch['output_sha256'] = transition_patch['output_sha256']
    finish_patch['transition_feature'] = transition_patch['feature']
    from old_native_level02_patch import prepare as prepare_level02
    level02, init02, level02_patch = prepare_level02(OLD)
    init02, shared_scripts['init02'] = money_scripts.patch_init(init02, level=2)
    write_script(folder / 'Maps/Level_02.lgc', level02)
    write_script(folder / 'Maps/old_campaign_init_level02.lgc', init02)
    write_script(folder / 'Maps/old_campaign_transition.lgc',
                 (SOURCE / 'old_campaign_transition.lgc').read_text('ascii'))
    (folder / 'transition-patch.json').write_text(json.dumps(transition_patch, indent=2), 'utf-8')
    (folder / 'level02-patch.json').write_text(json.dumps(level02_patch, indent=2), 'utf-8')
    finish_text, shared_scripts['finish'] = money_scripts.patch_finish(finish_text)
    finish_patch['output_sha256'] = shared_scripts['finish']['output_sha256']
    finish_patch['reward_policy'] = 'One original CurLevelMoney credit to the shared pool; the original rank award remains individual for both heroes.'
    write_script(folder / 'Maps' / 'old_campaign_finish.lgc', finish_text)
    (folder / 'finish-patch.json').write_text(json.dumps(finish_patch, indent=2), 'utf-8')
    (folder / 'party-stat-patch.json').write_text(json.dumps(party_stat_patch, indent=2), 'utf-8')
    from old_native_roof_patch import prepare as prepare_roof
    roof_text, roof_patch = prepare_roof(OLD)
    write_script(folder / 'Maps' / 'old_campaign_roofs.lgc', roof_text)
    (folder / 'roof-patch.json').write_text(json.dumps(roof_patch, indent=2), 'utf-8')
    init01 = (SOURCE / 'old_campaign_init.lgc').read_text('ascii')
    init01, shared_scripts['init01'] = money_scripts.patch_init(init01, level=1)
    write_script(folder / 'Maps' / 'old_campaign_init.lgc', init01)
    campaign_script = (OLD / 'Maps' / 'Level_01.lgc').read_text('cp1251')
    campaign_script = '#define NET_GAME_RUN 111\n#define COOP_CAMPAIGN 1\n' + campaign_script
    campaign_script = campaign_script.replace('#include "maps\\common_compaign.lgc"',
        '#include "maps\\common_compaign.lgc"\n#include "maps\\old_campaign_roofs.lgc"\n#include "maps\\old_campaign_init.lgc"\n#include "maps\\old_campaign_finish.lgc"\n#include "maps\\old_game_observe.lgc"')
    assert campaign_script.count('InitGame();') == 1
    campaign_script = campaign_script.replace('InitGame();', 'OldCampaignInit();')
    campaign_script = campaign_script.replace('  if( GameTact() )',
        '  OldGameObserve();\n  if(!OldCampaignReady) return;\n  if(OldFinishTact()) return;\n  if( GameTact() )')
    campaign_script = campaign_script.replace('  QuestsTact();', '  TeleportTact();\n  QuestsTact();')
    campaign_script = campaign_script.replace('  CompaignGameTact();', '  OldRoofTact();\n  CompaignGameTact();')
    campaign_script = '#define OLD_CAMPAIGN_TRANSITION 1\n' + campaign_script
    before = '#include "maps\\old_campaign_finish.lgc"'
    assert campaign_script.count(before) == 1
    campaign_script = campaign_script.replace(before, before + '\n#include "maps\\old_campaign_transition.lgc"')
    campaign_script = campaign_script.replace('  if(OldFinishTact()) return;',
        '  OldTransitionObserve();\n  if(OldFinishTact()) return;')
    write_script(folder / 'Maps' / 'Level_01.lgc', campaign_script)
    from old_native_campaign_common import prepare as prepare_common_events
    campaign_common, dynamite_patch, campaign_money, _ = prepare_common_events(
        OLD, shared_money=shared_money, progression=campaign_progression)
    shared_scripts['campaign'] = campaign_money
    (folder / 'dynamite-patch.json').write_text(json.dumps(dynamite_patch, indent=2), 'utf-8')
    write_script(folder / 'Maps' / 'common_compaign.lgc', campaign_common)
    (folder / 'Maps' / 'monsters_rats.lgc').write_bytes((OLD / 'Maps' / 'monsters_rats.lgc').read_bytes())
    (folder / 'rat-observer.json').unlink(missing_ok=True)
    radio = (OLD / 'Maps' / 'util_radiotalk.lgc').read_text('cp1251')
    assert radio.count('SendCommandA( -1, EXT_GETRADIO') == 5
    radio = radio.replace('SendCommandA( -1, EXT_GETRADIO', 'SendCommandA( 0, EXT_GETRADIO')
    write_script(folder / 'Maps' / 'util_radiotalk.lgc', radio)
    teleport_patch = None
    bunker_patch = None
    portal_runtime = None
    from old_native_teleport_patch import prepare as prepare_teleport
    teleport_text, teleport_patch = prepare_teleport(OLD)
    from old_native_portal_runtime import patch as patch_portals
    from old_native_interaction_registry import REGISTRY
    teleport_text, portal_runtime = patch_portals(teleport_text,
        {m.key: mission_source(OLD, m.path).read_bytes() for m in REGISTRY.maps})
    (folder / 'bunker-patch.json').unlink(missing_ok=True)
    write_script(folder / 'Maps' / 'util_teleport.lgc', teleport_text)
    (folder / 'teleport-patch.json').write_text(json.dumps(teleport_patch, indent=2), 'utf-8')
    if bunker_patch:
        (folder / 'bunker-patch.json').write_text(json.dumps(bunker_patch, indent=2), 'utf-8')
    dialogue_timing = None
    from old_native_dialogue_timing import prepare as prepare_dialogue
    dialogue_text, dialogue_timing = prepare_dialogue(OLD)
    write_script(folder / 'Text' / 'dialogs.txt', dialogue_text)
    (folder / 'dialogue-timing.json').write_text(json.dumps(dialogue_timing, indent=2), 'utf-8')
    story_patch = None
    spawn_rng_patch = None
    crush_sync_patch = None
    party_items_patch = None
    party_triggers_patch = None
    shared_money_patch = None
    campaign_shop_patch = None
    campaign_command_patch = None
    campaign_shop_scripts = None
    campaign_command_script = None
    campaign_inventory_level01_script = None
    gameplay_hud_patch = None
    from old_native_campaign_patch import patch as patch_story
    executable = folder / 'AlienShooter.exe'
    patched, story_patch = patch_story(executable.read_bytes())
    executable.write_bytes(patched)
    (folder / 'campaign-patch.json').write_text(json.dumps(story_patch, indent=2), 'utf-8')
    from old_native_spawn_rng_patch import patch as patch_spawn_rng
    patched, spawn_rng_patch = patch_spawn_rng(executable.read_bytes())
    executable.write_bytes(patched)
    (folder / 'spawn-rng-patch.json').write_text(json.dumps(spawn_rng_patch, indent=2), 'utf-8')
    from old_native_crush_sync_patch import patch as patch_crush_sync
    patched, crush_sync_patch = patch_crush_sync(executable.read_bytes())
    executable.write_bytes(patched)
    (folder / 'crush-sync-patch.json').write_text(json.dumps(crush_sync_patch, indent=2), 'utf-8')
    from old_native_party_items_patch import patch_registered as registered_items
    patched, party_items_patch = registered_items(executable.read_bytes(), (OLD / 'levels.cfg').read_bytes())
    executable.write_bytes(patched)
    (folder / 'party-items-patch.json').write_text(json.dumps(party_items_patch, indent=2), 'utf-8')
    from old_native_party_triggers_patch import patch_registered as registered_triggers
    from old_native_interaction_registry import REGISTRY
    patched, party_triggers_patch = registered_triggers(executable.read_bytes(),
        {m.key:mission_source(OLD, m.path).read_bytes() for m in REGISTRY.maps})
    executable.write_bytes(patched)
    (folder / 'party-triggers-patch.json').write_text(json.dumps(party_triggers_patch, indent=2), 'utf-8')
    from old_native_shared_money_patch import patch as patch_money
    patched, shared_money_patch = patch_money(executable.read_bytes())
    executable.write_bytes(patched)
    (folder / 'shared-money-patch.json').write_text(json.dumps({'native': shared_money_patch,
        'scripts': shared_scripts}, indent=2), 'utf-8')
    progression_files, progression_patch = {}, None
    reloaded_files, reloaded_assets = {}, None
    from old_native_campaign_progression import prepare as prepare_progression
    progression_files, progression_patch = prepare_progression(OLD)
    if RELOADED_ENABLED:
        from old_native_reloaded_assets import prepare as prepare_reloaded
        reloaded_files, reloaded_assets = prepare_reloaded(RELOADED_ROOT, OLD)
        for name, data in reloaded_files.items():
            destination = folder / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
    from old_native_campaign_shop_patch import patch as patch_campaign_shop
    from old_native_campaign_command_patch import patch as patch_commands, prepare_script
    from old_native_campaign_shop_scripts import prepare as prepare_shop_scripts, patch_level01
    patched, campaign_shop_patch = patch_campaign_shop(executable.read_bytes())
    patched, campaign_command_patch = patch_commands(patched)
    executable.write_bytes(patched)
    level02, common, helper, campaign_shop_scripts = prepare_shop_scripts(
        OLD, (folder / 'Maps/Level_02.lgc').read_text('cp1251'),
        (folder / 'Maps/COMMON.LGC').read_text('cp1251'))
    level01, campaign_inventory_level01_script = patch_level01(
        (folder / 'Maps/Level_01.lgc').read_text('cp1251'))
    command_helper, campaign_command_script = prepare_script()
    from old_native_campaign_hud import patch as patch_hud
    helper, gameplay_hud_patch = patch_hud(helper)
    from old_native_campaign_stock_ui import prepare as prepare_stock_ui
    helper, stock_ui_files, gameplay_hud_patch = prepare_stock_ui(OLD, helper, gameplay_hud_patch, common)
    from old_native_campaign_stock_inventory import prepare as prepare_stock_inventory
    helper, stock_ui_files, gameplay_hud_patch = prepare_stock_inventory(OLD, helper, gameplay_hud_patch, stock_ui_files)
    from old_native_campaign_stock_shop import prepare as prepare_stock_shop
    helper, stock_ui_files, gameplay_hud_patch = prepare_stock_shop(OLD, helper, gameplay_hud_patch, stock_ui_files)
    common = stock_ui_files['Maps/COMMON.LGC'].decode('cp1251')
    for name, data in stock_ui_files.items():
        (folder / name).write_bytes(data)
    (folder / 'gameplay-hud-patch.json').write_text(json.dumps(gameplay_hud_patch, indent=2), 'utf-8')
    from old_native_campaign_progression import extend_shop, digest
    helper, progression_patch['shop'] = extend_shop(helper)
    progression_patch['files']['Maps/old_campaign_shop.lgc'] = digest(helper)
    progression_patch['output_sha256'] = hashlib.sha256(
        json.dumps(progression_patch['files'], sort_keys=True).encode()).hexdigest()
    for name, text in (('Maps/Level_01.lgc', level01), ('Maps/Level_02.lgc', level02), ('Maps/COMMON.LGC', common),
                       ('Maps/old_campaign_shop.lgc', helper),
                       ('Maps/old_campaign_shop_transport.lgc', command_helper)):
        write_script(folder / name, text)
    (folder / 'campaign-shop-patch.json').write_text(json.dumps({
        'native': campaign_shop_patch, 'commands': campaign_command_patch,
        'inventory_level01_script': campaign_inventory_level01_script,
        'scripts': campaign_shop_scripts, 'transport_script': campaign_command_script}, indent=2), 'utf-8')
    campaign_reward_patch = None
    campaign_reward_scripts = None
    from old_native_campaign_reward_patch import patch as patch_rewards
    from old_native_campaign_rewards_scripts import apply as patch_reward_scripts
    patched, campaign_reward_patch = patch_rewards(executable.read_bytes())
    executable.write_bytes(patched)
    scripts, campaign_reward_scripts = patch_reward_scripts(
        (folder / 'Maps/MONSTERS.LGC').read_text('cp1251'),
        (OLD / 'Maps/common_perks.lgc').read_bytes())
    for name, text in scripts.items():
        write_script(folder / name, text)
    (folder / 'campaign-reward-patch.json').write_text(json.dumps({
        'native': campaign_reward_patch, 'scripts': campaign_reward_scripts}, indent=2), 'utf-8')
    compiler_capacity_patch = None
    checkpoint_patch = None
    from old_native_script_capacity_patch import patch as patch_compiler_capacity
    patched, compiler_capacity_patch = patch_compiler_capacity(executable.read_bytes())
    executable.write_bytes(patched)
    (folder / 'compiler-capacity-patch.json').write_text(
        json.dumps(compiler_capacity_patch, indent=2), 'utf-8')
    from old_native_campaign_checkpoint import HELPER_PATH, HELPER
    from old_native_checkpoint_patch import patch as patch_checkpoint
    patched, checkpoint_patch = patch_checkpoint(executable.read_bytes())
    executable.write_bytes(patched)
    write_script(folder / HELPER_PATH, HELPER)
    admin_portal_patch = None
    campaign_profile = None
    level02_finish_patch = None
    from old_native_portal_runtime import patch_level02
    level02, portal_runtime['level02_hook'] = patch_level02((folder / 'Maps/Level_02.lgc').read_text('cp1251'))
    from old_native_level02_finish_patch import prepare as prepare_finish02, patch_level02 as finish_level02
    helper, level02_finish_patch = prepare_finish02(OLD)
    level02, level02_finish_patch['level02_hook'] = finish_level02(level02)
    helper = progression_files[level02_finish_patch['helper_file']]
    level02_finish_patch.update(progression_patch['finishes']['2'])
    level02_finish_patch.update(level03_entry_supported=True, terminal='Shared dwell then native host load',
        progression='Original completion and single shared reward, then Level03')
    level02_finish_patch['level02_hook']['onward_map_load'] = True
    write_script(folder / level02_finish_patch['helper_file'], helper)
    (folder / 'level02-finish-patch.json').write_text(json.dumps(level02_finish_patch, indent=2), 'utf-8')
    write_script(folder / 'Maps/Level_02.lgc', level02)
    # Data and controller changes automatically separate native sessions.
    signature = hashlib.sha256((portal_runtime['catalog_sha256'] + portal_runtime['output_sha256']).encode()).hexdigest()[:12]
    portal_runtime['session_name'] = 'AS2_SHARED_' + signature
    from old_native_campaign_profile import identity
    campaign_profile = identity(portal_runtime, party_items_patch, party_triggers_patch,
                                level02_finish=level02_finish_patch,
                                gameplay_hud=gameplay_hud_patch,
                                commands=campaign_command_patch if gameplay_hud else None,
                                compiler_capacity=compiler_capacity_patch, progression=progression_patch,
                                checkpoint=checkpoint_patch)
    portal_runtime['session_name'] = campaign_profile['session_name']
    write_script(folder / 'Maps/old_game_lobby.lgc', lobby.replace('AS2_OLD_CAMPAIGN_ADMIN_V1', portal_runtime['session_name']))
    (folder / 'portal-runtime.json').write_text(json.dumps(portal_runtime, indent=2), 'utf-8')
    for name, text in progression_files.items():
        if isinstance(text, bytes):
            (folder / name).write_bytes(text)
        else:
            write_script(folder / name, text)
    (folder / 'campaign-progression.json').write_text(json.dumps(progression_patch, indent=2), 'utf-8')
    revival_files = {}
    revival_patch = None
    # Compose last: all physical maps share the same death/assistance path,
    # including the original first two entries and both imported road maps.
    from old_native_campaign_revival import (prepare as prepare_revival,
        adapt_level as revive_level, adapt_init as revive_init, FEATURE as revival_feature)
    from old_native_campaign_missions import MISSIONS
    revival_files = prepare_revival(OLD)
    for mission in MISSIONS:
        name = mission.path.replace('.map', '.lgc')
        revival_files[name] = revive_level((folder / name).read_text('cp1251'))
        name = ('Maps/old_campaign_init.lgc' if mission.number == 1
                else f'Maps/old_campaign_init_level{mission.number:02d}.lgc')
        revival_files[name] = revive_init((folder / name).read_text('cp1251'))
    for name, text in revival_files.items():
        write_script(folder / name, text)
    from old_native_campaign_progression import digest
    revival_patch = dict(feature=revival_feature, duration_ms=5000, radius=120,
        missions=[m.number for m in MISSIONS],
        files={name: digest(text) for name, text in revival_files.items()})
    (folder / 'campaign-revival.json').write_text(json.dumps(revival_patch, indent=2), 'utf-8')
    campaign_menu_patch = None
    menu_files = {}
    from old_native_campaign_menu import prepare as prepare_menu
    menu_files, campaign_menu_patch = prepare_menu(OLD,
        (folder / 'Maps/old_game_lobby.lgc').read_text('cp1251'), campaign_profile['session_name'])
    for name, data in menu_files.items():
        (folder / name).write_bytes(data)
    (folder / 'campaign-menu-patch.json').write_text(json.dumps(campaign_menu_patch, indent=2), 'utf-8')
    (folder / 'input-fixture.json').unlink(missing_ok=True)
    trace_metadata = None
    (folder / 'rng-trace.json').unlink(missing_ok=True)
    paths = ['AlienShooter.exe', 'AlienShooter.cfg', 'input.cfg', 'Maps/old_game_lobby.lgc',
             'Maps/old_game_observe.lgc', 'Maps/COOPERATIVE/cooperative.lgc', 'Maps/common_compaign.lgc',
             'Maps/util_radiotalk.lgc', 'Maps/util_teleport.lgc', 'Text/dialogs.txt',
             'Maps/COMMON.LGC', 'Maps/util_help.lgc', 'Maps/common_perks.lgc']
    paths += ['Maps/old_campaign_checkpoint.lgc']
    paths += ['levels.cfg', 'Maps/Level_01.map', 'Maps/Level_01.lgc', 'Maps/old_campaign_init.lgc', 'Maps/old_campaign_roofs.lgc',
              'Maps/old_campaign_finish.lgc', 'Maps/MONSTERS.LGC']
    paths += ['Maps/monsters_rats.lgc', 'Maps/util_statistics.lgc']
    from old_native_finish_patch import SOURCES as finish_sources
    if hashlib.sha256((folder / 'Maps/Level_01.map').read_bytes()).hexdigest() != finish_sources['Maps/Level_01.map']:
        raise ValueError('Runtime Level_01 map differs from the guarded original')
    paths += ['Maps/Level_02.map', 'Maps/Level_02.lgc', 'Maps/old_campaign_init_level02.lgc', 'Maps/old_campaign_transition.lgc']
    from old_native_level02_patch import MAP_SHA256 as level02_map_sha256
    level02_map_sha256 = progression_patch['script_timing']['maps']['Maps/Level_02.map']['output_sha256']
    if hashlib.sha256((folder / 'Maps/Level_02.map').read_bytes()).hexdigest() != level02_map_sha256:
        raise ValueError('Runtime Level_02 map differs from the guarded campaign data')
    paths += ['Maps/old_campaign_shop.lgc', 'Maps/old_campaign_shop_transport.lgc']
    paths += [level02_finish_patch['helper_file']]
    paths += list(menu_files) + list(settings_files) + list(stock_ui_files) + list(progression_files) + list(revival_files)
    paths += list(reloaded_files)
    from old_native_campaign_missions import MISSIONS
    paths += [m.path for m in MISSIONS if m.number >= 3]
    localization = None
    from old_native_localization import get_language
    from old_native_campaign_localization import apply as localize_ui
    language = get_language()
    localized_files = {name: (folder / name).read_bytes() for name in set(paths)
                       if name.lower().endswith(('.lgc', '.men'))}
    localization = localize_ui(localized_files, language)
    for name, content in localized_files.items():
        (folder / name).write_bytes(content)
    (folder / 'campaign-localization.json').write_text(json.dumps(localization, indent=2), 'utf-8')
    paths += ['campaign-localization.json']
    # Native patch hashes alone do not cover script-only protocol changes.
    # Bind the complete generated script set before admitting either peer.
    from old_native_campaign_profile import bind_scripts
    previous_session = campaign_profile['session_name']
    campaign_profile = bind_scripts(campaign_profile, {
        name: (folder / name).read_bytes() for name in set(paths)
        if name.lower().endswith('.lgc') or name in ('Weapon.cfg', 'levels.cfg')},
        language=language, dialogue_timing=dialogue_timing)
    session = campaign_profile['session_name']
    lobby_path = folder / 'Maps/old_game_lobby.lgc'
    lobby_source = lobby_path.read_text('cp1251').replace(previous_session, session)
    write_script(lobby_path, lobby_source)
    menu_files, campaign_menu_patch = prepare_menu(OLD, lobby_source, session)
    # Recomposition embeds the final session token and emits Russian source
    # again. Apply the same catalogue before writing those final menus.
    campaign_menu_patch['localization'] = localize_ui(menu_files, language)
    for name, data in menu_files.items():
        (folder / name).write_bytes(data)
        campaign_menu_patch['files'][name] = {'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)}
    (folder / 'campaign-menu-patch.json').write_text(json.dumps(campaign_menu_patch, indent=2), 'utf-8')
    portal_runtime['session_name'] = session
    (folder / 'portal-runtime.json').write_text(json.dumps(portal_runtime, indent=2), 'utf-8')
    manifest = {'role': role, 'campaign': campaign, 'controls': controls, 'controls_host': controls_host,
                'story_patch': story_patch,
                'spawn_rng_patch': spawn_rng_patch,
                'crush_sync_patch': crush_sync_patch,
                'party_items_patch': party_items_patch,
                'party_triggers_patch': party_triggers_patch,
                'shared_money': shared_money,
                'shared_money_patch': shared_money_patch,
                'shared_money_scripts': shared_scripts,
                'campaign_shop': campaign_shop,
                'campaign_shop_patch': campaign_shop_patch,
                'campaign_command_patch': campaign_command_patch,
                'campaign_shop_scripts': campaign_shop_scripts,
                'campaign_inventory_level01_script': campaign_inventory_level01_script,
                'campaign_command_script': campaign_command_script,
                'campaign_rewards': campaign_rewards,
                'campaign_reward_patch': campaign_reward_patch,
                'campaign_reward_scripts': campaign_reward_scripts,
                'compiler_capacity_patch': compiler_capacity_patch,
                'checkpoint_patch': checkpoint_patch,
                'campaign_revival': revival_patch,
                'dialogue_timing': dialogue_timing,
                'localization': localization,
                'teleport_patch': teleport_patch,
                'bunker_patch': bunker_patch, 'roof_patch': roof_patch,
                'admin_portal': admin_portal, 'admin_portal_patch': admin_portal_patch,
                'shared_portals': shared_portals, 'portal_runtime': portal_runtime,
                'registered_interactions': registered_interactions, 'campaign_profile': campaign_profile,
                'level02_finish': level02_finish, 'level02_finish_patch': level02_finish_patch,
                'campaign_progression': campaign_progression, 'progression_patch': progression_patch,
                'reloaded_assets': reloaded_assets,
                'gameplay_hud': gameplay_hud, 'gameplay_hud_patch': gameplay_hud_patch,
                'campaign_input_patch': campaign_input_patch,
                'campaign_menu': campaign_menu, 'campaign_menu_patch': campaign_menu_patch,
                'campaign_settings_patch': campaign_settings_patch,
                'startup_menu': startup_menu,
                'combat_observer': combat_observer,
                'finish_patch': finish_patch, 'party_stat_patch': party_stat_patch,
                'dynamite_patch': dynamite_patch,
                'transition_patch': transition_patch, 'level02_patch': level02_patch,
                'mission_statistics_patch': mission_statistics_patch,
                'rat_observer': rat_observer,
                'quest_observer': quest_observer,
                'rng_trace': trace_metadata,
                'source_sha256': OLD_SHA, 'observe_frames': observe_frames,
                'files': {path: hashlib.sha256((folder / path).read_bytes()).hexdigest() for path in paths}}
    (folder / 'native-gameplay-build.json').write_text(json.dumps(manifest, indent=2), 'utf-8')
    return folder
