"""Narrow OLD-script support for Reloaded's two additional road stages.

The common campaign composer owns entries, exits and stable stage IDs. These
adapters add the shipped VID3100 vehicle behavior without importing Reloaded's
RPG indices, option APIs, native quest mapping or local registry decisions.
"""
import hashlib
from pathlib import Path
import struct


FEATURE = 'old-reloaded-road-scripts-v1'
STOCK = {
    'Maps/CONST.LGC': 'e56f809aebc85aeeb6957a7d02d5e975e4d7a741c3703187f609b5cdd4b77bd7',
    'Maps/util_vehicleconst.lgc': '62f325335a200ff4d062647e98c17c2d55ffb48f07d5656078911551767478c2',
    'Maps/util_damageframe.lgc': '3b983c9c72e436d840ff58535cb576fb8e25aebb7781e1bcc817e4b4b9236bda',
}
RELOADED_CAR_SHA256 = '51393d43959ded45eb4dccea91d75a38d81e4aa618b0705914c524ce816dc1de'
RELOADED_CAR2_SHA256 = '1ab5ad282a4bacec286219b904fe748be0417080ad20b38607f9be789e9f8579'
VEHICLE_ANCHORS = {
    'Maps/Level_07_2.map': (
        '39c5c2388db497d2a86ada94ffd505d24ff715306801c30143c939b680246d18',
        0xDF6F4, (0xE4C180, 3000, 4748.0, 12808.0, 0.0)),
    'Maps/Level_07_3.map': (
        '0c7b10edb58b1730b9e05bd62fcdefb8afe15ce719e9f29d683841bbc0443608',
        0x89804, (0xE48C88, 3100, 441.0, 11691.0, 3.0)),
}


def adapt_entry(level, stage):
    """The normal shared entry already created two heroes before this call."""
    from old_native_campaign_progression import once
    if stage not in (72, 73):
        return level
    vid, x, y, z = {72: (3000, 4748, 12808, 0), 73: (3100, 441, 11691, 3)}[stage]
    level = once(level, '#include "maps\\old_campaign_shop.lgc"',
        '#include "maps\\old_campaign_shop.lgc"\n'
        '#include "maps\\old_campaign_party_vehicle.lgc"')
    level = once(level, '    OldCampaignInit();',
        '    OldCampaignInit();\n'
        f'    if(OldCampaignReady) OldCampaignPartyVehicleInit({vid}, {x}, {y}, {z});')
    if stage == 73:
        from old_native_reloaded_endwave import adapt_entry as adapt_endwave
        level = adapt_endwave(level)
    return level


def extend_vehicle_files(old_root, files, reloaded_root=None):
    """Return the supplied common vehicle scripts plus guarded VID3100 support.

    Call after old_native_campaign_vehicles.prepare, before writing its files.
    Existing OLD Level07 behavior and common coop input fixes stay intact.
    """
    from old_native_campaign_progression import once, digest
    from old_native_campaign_vehicles import prepare
    old_root = Path(old_root)
    reloaded_root = Path(reloaded_root) if reloaded_root is not None else Path(__file__).resolve().parent.parent
    expected, _ = prepare(old_root)
    for name in ('Maps/util_car.lgc', 'Maps/util_car2.lgc'):
        if files.get(name) != expected[name]:
            raise ValueError('Reloaded vehicle adapter requires current common coop output: ' + name)
    for name, sha in (('Maps/util_car.lgc', RELOADED_CAR_SHA256),
                      ('Maps/util_car2.lgc', RELOADED_CAR2_SHA256)):
        if hashlib.sha256((reloaded_root / name).read_bytes()).hexdigest() != sha:
            raise ValueError('Unsupported Reloaded vehicle evidence: ' + name)
    for name, (sha, offset, identity) in VEHICLE_ANCHORS.items():
        data = (reloaded_root / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha or struct.unpack_from('<IIfff', data, offset) != identity:
            raise ValueError('Unsupported Reloaded companion vehicle anchor: ' + name)
    out = dict(files)
    for name, sha in STOCK.items():
        data = (old_root / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError('Unsupported OLD vehicle dependency: ' + name)
        if name in out:
            raise ValueError('Unexpected prior vehicle dependency adapter: ' + name)
        out[name] = data.decode('cp1251').replace('\r\n', '\n')

    car = out['Maps/util_car.lgc']
    car = once(car, 'static int WheelsY_3000[] =\t{ 48, 48, -48, -48 };',
        'static int WheelsY_3000[] =\t{ 48, 48, -48, -48 };\n'
        'static int WheelsX_3100[] =\t{ 96, -72, -72, 96 };\n'
        'static int WheelsY_3100[] =\t{ 48, 48, -48, -48 };')
    car = once(car, 'static int WheelsA_3000[4];',
        'static int WheelsA_3000[4];\nstatic int WheelsR_3100[4];\nstatic int WheelsA_3100[4];')
    car = once(car, '\t\t\tWheelsR_3000[i] = SendCommand( EXT_CONVERFROMCARTESIAN, WheelsX_3000[i], WheelsY_3000[i], 2 );',
        '\t\t\tWheelsR_3000[i] = SendCommand( EXT_CONVERFROMCARTESIAN, WheelsX_3000[i], WheelsY_3000[i], 2 );\n'
        '\t\t\tWheelsA_3100[i] = SendCommand( EXT_CONVERFROMCARTESIAN, WheelsX_3100[i], WheelsY_3100[i], 1 );\n'
        '\t\t\tWheelsR_3100[i] = SendCommand( EXT_CONVERFROMCARTESIAN, WheelsX_3100[i], WheelsY_3100[i], 2 );')
    car = once(car, '\t\t\tradius = WheelsR_3000[ i ];\n\t\t}',
        '\t\t\tradius = WheelsR_3000[ i ];\n\t\t}\n'
        '\t\telse if(GetVid(iUnit)==3100)\n\t\t{\n'
        '\t\t\tangle = WheelsA_3100[ i ];\n'
        '\t\t\tradius = WheelsR_3100[ i ];\n\t\t}')
    car = once(car, 'F3000_14( int this ) { OnCarBorn( this ); }',
        'F3000_14( int this ) { OnCarBorn( this ); }\n'
        'F3100_14( int this ) { OnCarBorn( this ); }\n'
        'F3100_10( int this ) { TryBecomeAFlagman( this, 100, false ); }')
    # Reloaded explicitly permits car destruction in the two extra stages.
    # Use exact physical maps; native campaign index7 is also the original road.
    car = once(car, 'F1206_15(int unit)\n{\n\tif(!SendCommand(EXT_GETSURVIVEMODE))',
        'F1206_15(int unit)\n{\n'
        '\tstring map = ToLower(GetMapName());\n'
        '\tint extraRoad = map == "maps\\\\level_07_2.map" || map == "maps\\\\level_07_3.map";\n'
        '\tif(!SendCommand(EXT_GETSURVIVEMODE) && !extraRoad)')
    car = once(car, 'F3000_16(int unit) { F3000_15(unit); }',
        'F3000_16(int unit) { F3000_15(unit); }\n'
        'F3100_15(int unit) { F1206_15(unit); }\n'
        'F3100_16(int unit) { F1206_15(unit); }')
    out['Maps/util_car.lgc'] = car
    out['Maps/util_car2.lgc'] = once(out['Maps/util_car2.lgc'],
        '\t\tif( Vehicles[i] )\n\t\t{\n\t\t\tint dist = SizeTo',
        '\t\tif( Vehicles[i] && GetVid(Vehicles[i]) != 3100)\n\t\t{\n\t\t\tint dist = SizeTo')
    out['Maps/CONST.LGC'] = once(out['Maps/CONST.LGC'],
        'static int CarsVids[]  = { 1206, 3000, 1208 };',
        'static int CarsVids[]  = { 1206, 3000, 1208, 3100 };')
    out['Maps/util_vehicleconst.lgc'] = once(out['Maps/util_vehicleconst.lgc'],
        'iVidNum == 1206 || iVidNum == 3000', 'iVidNum == 1206 || iVidNum == 3000 || iVidNum == 3100')
    out['Maps/util_damageframe.lgc'] += '\nF3100_DAMAGE(int unit, int beating_unit, int damage)\n{ F250_DAMAGE(unit, beating_unit, damage); }\n'
    return out, {
        'feature': FEATURE, 'stages': [72, 73], 'vehicle_vid': 3100,
        'source_hashes': STOCK,
        'script_hashes': {name: digest(text) for name, text in out.items()},
        'old_rpg_and_native_physics_preserved': True,
        'vehicle_death_nonfatal_on_extra_maps': True,
        'old_level07_vehicle_death_policy_preserved': True,
        'requires_forward_declaration': 'F3100_15( int unit );',
        'companions': {72: [3000, 4748, 12808, 0], 73: [3100, 441, 11691, 3]},
        'local_NoCarOn9Lev_option_imported': False,
        'boundary_vehicle_ownership_persisted': False,
    }
