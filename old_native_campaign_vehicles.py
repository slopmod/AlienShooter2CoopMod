"""Keep stock vehicles, with army-specific input and local presentation.

The original car code already owns separate hero descriptors and searches all
network armies when boarding. Its exit input and presentation still defaulted
to the local player, however. These corrections retain native boarding,
collision/escape, driving physics and the campaign's vehicle-loss failure.
"""
from pathlib import Path
import hashlib
import struct


FEATURE = 'old-campaign-vehicles-v1'
NAME = 'Maps/util_car.lgc'
SOURCE_SHA256 = '704346382008cafe31728b94a83d17cb74198b8aae6729cc792cbfbedf4f9831'
SECONDARY_NAME = 'Maps/util_car2.lgc'
SECONDARY_SHA256 = '970c713882d014a9ef54bb29b373731bb7d06e0b96b12903643a0a91b0a26ed8'
PARTY_NAME = 'Maps/old_campaign_party_vehicle.lgc'
LEVEL07_SHA256 = '78ca07180e0d2b17f9bf347dbd68c2778b926b2afee445c03ecad892d775821a'


PARTY_HELPER = r'''
// The caller provides a reviewed original car. No random placement, reward
// changes or ownership reservation: both heroes use the stock boarding code.
static int OldPartyVehicleStatus = 0;
static int OldPartyVehicle = 0;
static int OldPartyVehicleNotice = 0;

OldCampaignPartyVehicleInit(int vid, int originalX, int originalY, int originalZ)
{
    if(OldPartyVehicleStatus) return OldPartyVehicleStatus == 1;
    OldPartyVehicleStatus = 2;
    int original = FindNearestSprite(GETSPRITE_VID(vid), originalX, originalY, 12);
    if(original && abs(GetZ(original) - originalZ) <= 16)
    {
        int hx = GetX(original);
        int hy = GetY(original);
        int hz = GetZ(original);
        int ground0 = GetGroundZ(hx, hy);
        int groundOffset = hz - ground0;
        for(int radius = 320; radius <= 960; radius = radius + 80)
            for(int direction = 0; direction < 256; direction = direction + 16)
            {
                int x = hx + Cos(direction) * radius / 1024;
                int y = hy + Sin(direction) * radius / 1024;
                if(x >= 160 && y >= 160 && x < MapSizeX()-160 && y < MapSizeY()-160)
                {
                    int ground = GetGroundZ(x, y);
                    int z = ground + groundOffset;
                    int clear = abs(ground - ground0) <= 16;
                    for(int step = 1; step < 8; step++)
                        if(abs(GetGroundZ(hx+(x-hx)*step/8, hy+(y-hy)*step/8)-ground0) > 16)
                            clear = 0;
                    if(clear && !IsLineUnderGround(hx, hy, hz+24, x, y, z+24)
                        && !CanPlace(vid, x, y, z))
                    {
                        OldPartyVehicle = CreateSprite(vid, x, y, z, GetDirection(original));
                        if(OldPartyVehicle)
                        {
                            // CreateSprite dispatches stock F3000_14/OnCarBorn,
                            // registering wheels/lights, opening doors and setting neutral army.
                            OldPartyVehicleStatus = 1;
                            Log("Coop companion vehicle ready: " + itoa(x) + "," + itoa(y) + "," + itoa(z));
                            return 1;
                        }
                    }
                }
            }
    }
    Log("Coop companion vehicle unavailable: no safe place beside original vehicle");
    OldPartyVehicleNotice = CreateText(13, ScreenX()/2, ScreenY()/2+95, 0,
        "Не удалось поставить вторую машину. Доступна исходная машина.", BEH_CENTER);
    return 0;
}
'''


def patch(data):
    from old_native_campaign_progression import once, digest

    if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported stock vehicle script')
    source = data.decode('cp1251').replace('\r\n', '\n')

    # CarTact visits every participating army. An omitted army reads this
    # computer's input and can eject a different player on each peer.
    source = once(source, 'GetInputAction(IA_CAR_ESCAPE)',
                  'GetInputAction(IA_CAR_ESCAPE, nArmy)')
    source = once(source, 'GetInputAction(IA_SHOW_INVENTORY) && CanShowSurvMen()',
                  'GetInputAction(IA_SHOW_INVENTORY, nArmy) && CanShowSurvMen()')

    # Camera zoom, menu visibility and experience sprites belong to the local
    # player. Never place shared mutations behind this presentation condition.
    source = once(source, '\t\tEffect(EFF_SHIFT_SCALE, 100, 100, SCREEN_SCALE_TIME);',
                  '\t\tif(nArmy == giCurArmy)\n'
                  '\t\t\tEffect(EFF_SHIFT_SCALE, 100, 100, SCREEN_SCALE_TIME);')
    source = once(source, '\tShowInventory( false );',
                  '\tif(nArmy == giCurArmy) ShowInventory( false );')
    source = once(source, '\tif(!Z_DEBUG)\n',
                  '\tif(nArmy == giCurArmy && !Z_DEBUG)\n')
    source = once(source, '\tif(!IsCharacter(Flagman(nArmy)))\n',
                  '\tif(nArmy == giCurArmy && !IsCharacter(Flagman(nArmy)))\n')

    # A single static animation cache was shared by all cars. Keep one value
    # per the existing bounded vehicle slot, resetting it when a slot is reused.
    source = once(source, 'static int VehShadow[ MAX_CARS_NUM ];',
                  'static int VehShadow[ MAX_CARS_NUM ];\n'
                  'static int OldCarAnimation[ MAX_CARS_NUM ];')
    source = once(source, '\tVehicles[i] = pCar;\n',
                  '\tVehicles[i] = pCar;\n\tOldCarAnimation[i] = -1;\n')
    source = once(source, '\tstatic int PrevAnimation = -1;\n', '')
    # Whole-file hash above pins all uses to ControlWheels, after ind >= 0.
    if source.count('PrevAnimation') != 8:
        raise ValueError('Stock vehicle animation cache consumers changed')
    source = source.replace('PrevAnimation', 'OldCarAnimation[ind]')

    from old_native_level11_specials import adapt_vehicle
    source = adapt_vehicle(source)
    return source, {
        'feature': FEATURE,
        'source_sha256': SOURCE_SHA256,
        'output_sha256': digest(source),
        'output_name': NAME,
        'escape_input_by_army': True,
        'camera_and_menu_local_only': True,
        'animation_cache_per_vehicle': True,
        'boarding_and_escape_geometry_preserved': True,
        'campaign_car_destruction_still_fails_quest': True,
        'native_driving_physics_preserved': True,
        'explicit_actor_remote_control': True,
        'native_runtime_tested': False,
    }


def prepare(root):
    from old_native_campaign_progression import once, digest
    from old_native_party_vehicle_consoles import validate_sources

    root = Path(root)
    validate_sources(root)
    source, metadata = patch((root / NAME).read_bytes())
    secondary_data = (root / SECONDARY_NAME).read_bytes()
    if hashlib.sha256(secondary_data).hexdigest() != SECONDARY_SHA256:
        raise ValueError('Unsupported stock vehicle visual history script')
    secondary = secondary_data.decode('cp1251').replace('\r\n', '\n')
    secondary = once(secondary, '\tif(SendCommand(EXT_GETSURVIVEMODE))\n',
        '#ifdef COOP_CAMPAIGN\n'
        '\t// Registry history is local and absent from shared checkpoint state.\n'
        '\t// Start both peers with the same original vehicle appearance.\n'
        '\tgiMaxBloodInd = 0;\n'
        '#else\n\tif(SendCommand(EXT_GETSURVIVEMODE))\n')
    secondary = once(secondary, '\t//\n\tif(giMaxBloodInd >= 300)\n',
        '#endif\n\t//\n\tif(giMaxBloodInd >= 300)\n')

    level = (root / 'Maps/Level_07.map').read_bytes()
    if (hashlib.sha256(level).hexdigest() != LEVEL07_SHA256
            or struct.unpack_from('<IIfff', level, 0xA0EE0) != (
                0x18486FC0, 3000, 2062.496337890625, 11702.0888671875, 5.0)):
        raise ValueError('Unsupported original Level_07 companion vehicle anchor')
    files = {NAME: source, SECONDARY_NAME: secondary, PARTY_NAME: PARTY_HELPER}
    metadata.update({
        'remote_console_actor_policy': 'Living party hero inside the reviewed activation trigger; no nearest-to-weapon selection',
        'reviewed_stationary_console_missions': [5],
        'source_sha256_by_file': {NAME: SOURCE_SHA256, SECONDARY_NAME: SECONDARY_SHA256},
        'output_sha256_by_file': {name: digest(text) for name, text in files.items()},
        'local_registry_vehicle_history_ignored_in_coop': True,
        'companion_vehicle': {
            'mission': 7, 'source_map_sha256': LEVEL07_SHA256, 'vid': 3000,
            'source_sprite_offset': 0xA0EE0, 'source_sprite_saved_id': 0x18486FC0,
            'source_position': [2062.496337890625, 11702.0888671875, 5.0],
            'search_radius': [320, 960, 80], 'search_direction_step': 16,
            'same_floor_tolerance': 16, 'native_collision_required': True,
            'random': False, 'quest_or_reward_changes': False,
            'no_safe_place_policy': 'Visible notice; retain original car and continue',
        },
    })
    return files, metadata
