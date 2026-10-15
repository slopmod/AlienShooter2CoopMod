"""Pure, guarded native settings assets for the supported OLD installation.

The game already exports SetGraphScreen(x, y).  We extend its original table
and menus, retaining their apply/cancel, audio and key binding handlers.  The
fullscreen choice is deliberately a next-launch preference: the native game
rewrites FullScreen from its current device on exit, so the launcher must copy
CoopFullScreen into FullScreen before starting a new process.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct


FEATURE = 'old-native-campaign-settings-v2'
MODES = ((800, 600), (1024, 768), (1280, 720), (1366, 768),
         (1600, 900), (1920, 1080))
FULLSCREEN_PREFERENCE = 'CoopFullScreen'
STOCK_HASHES = {
    'Maps/CONST.LGC': 'e56f809aebc85aeeb6957a7d02d5e975e4d7a741c3703187f609b5cdd4b77bd7',
    'Maps/common_menu.lgc': '8352d316e4b664e70b2f0d185988d806d6fa05971fa36c95aea7143a5875355e',
    'Maps/opt_graphics.men': '4d1ecb9df8a472f4663899c78be790f7ed46f540440f46467c44963c89eec3ad',
}


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _once(source: str, before: str, after: str) -> str:
    if source.count(before) != 1:
        raise ValueError('Settings source guard differs: ' + before[:80])
    return source.replace(before, after, 1)


def _encode(value: str) -> bytes:
    return value.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251')


DISPLAY_FUNCTION = r'''
SetNewCoopDisplay(int fullScreen)
{
    CoopFullScreen = fullScreen != 0;
    SetReg(GetDefaultRegPath(), "CoopFullScreen", CoopFullScreen);
    int button = MenuFindNamed("COOP_FULLSCREEN");
    if(button) Action(button, ACT_CHANGE_ANIMATION, ANI_MENUSTAND + CoopFullScreen);
    string label = "Полный экран";
    int text = MenuFindNamed("COOP_FULLSCREEN_TEXT");
    if(text) Action(text, ACT_SET_TEXT, &label);
    label = "После перезапуска: окно";
    if(CoopFullScreen) label = "После перезапуска: полный экран";
    text = MenuFindNamed("COOP_DISPLAY_NOTE");
    if(text) Action(text, ACT_SET_TEXT, &label);
}

'''


def _constants(source: str) -> str:
    source = _once(source, '#define RT_COUNT                2',
                   '#define RT_COUNT                ' + str(len(MODES)))
    # Keep the legacy indices 0/1; saved profiles therefore need no migration.
    source = _once(source, 'static int RT_SCREEN_X[] = { 800, 1024 };',
                   'static int RT_SCREEN_X[] = { '
                   + ', '.join(str(x) for x, _ in MODES) + ' };')
    source = _once(source, 'static int RT_SCREEN_Y[] = { 600, 768 };',
                   'static int RT_SCREEN_Y[] = { '
                   + ', '.join(str(y) for _, y in MODES) + ' };')
    # RT_TEXTS is no longer read by settings; retain its stock translations for
    # any unrelated original scripts.  Resolution labels use the actual pair.
    return source


def _common(source: str) -> str:
    source = _once(source, 'static int CurResolution = 0;',
                   'static int CurResolution = 0;\n'
                   'static int CoopFullScreen = 0;\n'
                   'static int PrevCoopFullScreen = 0;')
    source = _once(source, 'SetNewResolution( int iVal )\n{',
                   DISPLAY_FUNCTION + 'SetNewResolution( int iVal )\n{')
    source = _once(source,
                   'string buf = GetString( "menu", RT_TEXTS[ CurResolution ] );',
                   'string buf = itoa(RT_SCREEN_X[CurResolution]) + "x" + itoa(RT_SCREEN_Y[CurResolution]);')
    source = _once(source,
                   '    CurResolution = GetReg( GetPlayerRegPath(), "Resolution", GetCurResolution() );\n'
                   '    SetGraphScreen( RT_SCREEN_X[CurResolution], RT_SCREEN_Y[CurResolution] );',
                   '    CurResolution = GetReg( GetPlayerRegPath(), "Resolution", GetCurResolution() );\n'
                   '    // A profile may be corrupt or come from a different mode table.\n'
                   '    if(CurResolution < 0 || CurResolution >= RT_COUNT) CurResolution = GetCurResolution();\n'
                   '    SetReg(GetPlayerRegPath(), "Resolution", CurResolution);\n'
                   '    SetGraphScreen( RT_SCREEN_X[CurResolution], RT_SCREEN_Y[CurResolution] );')
    source = _once(source, '        SetNewResolution( RT_RES0 );',
                   '        SetNewResolution( RT_RES0 );\n        SetNewCoopDisplay(0);')
    source = _once(source, '    PrevCurResolution = CurResolution;',
                   '    PrevCurResolution = CurResolution;\n    PrevCoopFullScreen = CoopFullScreen;')
    source = _once(source, '    SetNewResolution( PrevCurResolution );',
                   '    SetNewResolution( PrevCurResolution );\n    SetNewCoopDisplay(PrevCoopFullScreen);')
    source = _once(source, '        CurResolution = GetCurResolution();',
                   '        CoopFullScreen = GetReg(GetDefaultRegPath(), "CoopFullScreen",\n'
                   '            GetReg(GetDefaultRegPath(), "FullScreen", 0)) != 0;\n'
                   '        CurResolution = GetCurResolution();')
    source = _once(source, '    SetNewResolution( CurResolution );',
                   '    SetNewResolution( CurResolution );\n    SetNewCoopDisplay(CoopFullScreen);')
    source = _once(source,
                   '        if( btn == MenuFindNamed( "INPUT_TYPE_NEXT" ) )',
                   '        if( btn == MenuFindNamed("COOP_FULLSCREEN") )\n'
                   '            SetNewCoopDisplay(!CoopFullScreen);\n'
                   '        else\n'
                   '        if( btn == MenuFindNamed( "INPUT_TYPE_NEXT" ) )')
    source = _once(source, '        AssignGameDifficulty();',
                   '#ifdef COOP_CAMPAIGN\n'
                   '        // InitGame runs on both peers; local options apply does not.\n'
                   '        if(giMenuState == MT_NOMENU) AssignGameDifficulty();\n'
                   '#else\n'
                   '        AssignGameDifficulty();\n'
                   '#endif')
    source = _once(source,
                   'SetNewDifficulty( int iVal )\n'
                   '{\n'
                   '    SetGameDifficulty( iVal, false );\n'
                   '    SetDifficultyText();\n'
                   '}',
                   'SetNewDifficulty( int iVal )\n'
                   '{\n'
                   '    // The campaign lobby currently has one shared difficulty.\n'
                   '    // Never offer a local preference as a network game setting.\n'
                   '    SetGameDifficulty(GT_DEFAULT, true);\n'
                   '    SetDifficultyText();\n'
                   '    string label = "Сетевая (фикс.)";\n'
                   '    if(gpDiffText) Action(gpDiffText, ACT_SET_TEXT, &label);\n'
                   '    int control = MenuFindNamed("MT_DIFFBAR");\n'
                   '    if(control) Action(control, ACT_CHANGE_ANIMATION, ANI_MENUDISABLE);\n'
                   '    control = MenuFindNamed("GAMEDIF_PREV");\n'
                   '    if(control) Action(control, ACT_CHANGE_ANIMATION, ANI_MENUDISABLE);\n'
                   '    control = MenuFindNamed("GAMEDIF_NEXT");\n'
                   '    if(control) Action(control, ACT_CHANGE_ANIMATION, ANI_MENUDISABLE);\n'
                   '}')
    # Original multiplayer protection of inventory/shop and all original sound,
    # control, pause and key-rebinding handlers remain byte-for-byte untouched.
    return source


def _graphics_menu(source: bytes) -> bytes:
    """Append native checkbox/text records inside the existing 800x600 layout.

    The menu is a HEAD plus one raw SPR block, not the MAP SPR/SPRD layout.
    Existing records and header anchors stay identical.  Clones use the stock
    text and checkbox graphics, which are centered by the engine at any size.
    """
    if source[:4] != b'RES ' or source[8:12] != b'MENU':
        raise ValueError('Unsupported graphics menu container')
    if struct.unpack_from('<I', source, 4)[0] != len(source) - 8:
        raise ValueError('Unsupported graphics menu length')
    cursor = 12
    chunks = []
    while cursor < len(source):
        size = struct.unpack_from('<I', source, cursor + 4)[0]
        end = cursor + 8 + size
        if end > len(source):
            raise ValueError('Graphics menu chunk exceeds file')
        chunks.append((source[cursor:cursor + 4], source[cursor + 8:end]))
        cursor = end
    if [tag for tag, _ in chunks] != [b'HEAD', b'SPR ']:
        raise ValueError('Graphics menu chunks differ')
    payload = chunks[1][1]
    marker, flags, count = struct.unpack_from('<III', payload)
    if (marker, flags) != (0x80000000, 0):
        raise ValueError('Graphics menu is not a raw sprite block')
    cursor = 12
    records = []
    for _ in range(count):
        size = struct.unpack_from('<I', payload, cursor)[0]
        cursor += 4
        record = payload[cursor:cursor + size]
        if len(record) != size:
            raise ValueError('Graphics menu sprite exceeds block')
        records.append(record)
        cursor += size
    if cursor != len(payload) or records[-1] != b'\xff\xff\xff\xff':
        raise ValueError('Graphics menu sprite terminator differs')
    originals = records[:-1]
    by_name = {r[60:].split(b'\0', 1)[0].decode('ascii'): r
               for r in originals if len(r) >= 61}
    if len(originals) != 25 or not {'SHD_CHECK', 'RES_TEXT'} <= by_name.keys():
        raise ValueError('Graphics menu layout differs')

    def clone(template, saved_id, x, y, z, name):
        record = bytearray(by_name[template][:60])
        struct.pack_into('<I', record, 0, saved_id)
        struct.pack_into('<fff', record, 8, x, y + z, z)
        # Preserve native properties including centered text behavior.
        suffix = name.encode('ascii') + b'\0'
        if template == 'RES_TEXT':
            suffix += b'\0'
        return bytes(record) + suffix

    additions = (
        clone('SHD_CHECK', 0x7FFF1101, 254, 426, 2070, 'COOP_FULLSCREEN'),
        clone('RES_TEXT', 0x7FFF1102, 408, 426, 2100, 'COOP_FULLSCREEN_TEXT'),
        clone('RES_TEXT', 0x7FFF1103, 400, 458, 2100, 'COOP_DISPLAY_NOTE'),
    )
    existing_ids = {struct.unpack_from('<I', r)[0] for r in originals}
    if any(struct.unpack_from('<I', r)[0] in existing_ids for r in additions):
        raise ValueError('Graphics menu custom sprite ID collision')
    new_records = originals + list(additions) + records[-1:]
    payload = struct.pack('<III', marker, flags, len(new_records))
    payload += b''.join(struct.pack('<I', len(r)) + r for r in new_records)
    body = b'MENU' + b'HEAD' + struct.pack('<I', len(chunks[0][1])) + chunks[0][1]
    body += b'SPR ' + struct.pack('<I', len(payload)) + payload
    return b'RES ' + struct.pack('<I', len(body)) + body


def prepare(old_root: Path) -> tuple[dict[str, bytes], dict]:
    """Read pinned original assets; return composed copies without any writes."""
    old_root = Path(old_root)
    stock = {}
    for name, expected in STOCK_HASHES.items():
        value = (old_root / name).read_bytes()
        if _sha(value) != expected:
            raise ValueError('Unsupported original settings asset: ' + name)
        stock[name] = value
    files = {
        'Maps/CONST.LGC': _encode(_constants(stock['Maps/CONST.LGC'].decode('cp1251').replace('\r\n', '\n'))),
        'Maps/common_menu.lgc': _encode(_common(stock['Maps/common_menu.lgc'].decode('cp1251').replace('\r\n', '\n'))),
        'Maps/opt_graphics.men': _graphics_menu(stock['Maps/opt_graphics.men']),
    }
    metadata = {
        'feature': FEATURE,
        'source_sha256': dict(STOCK_HASHES),
        'files': {name: {'sha256': _sha(value), 'size': len(value)} for name, value in files.items()},
        'resolutions': [list(pair) for pair in MODES],
        'resolution_script_api': 'SetGraphScreen(x, y), native export 161',
        'resolution_apply': 'Original OK/apply path changes resolution immediately; Cancel restores selection',
        'resolution_registry_value': '<isolated game key>/ProfileN/Resolution',
        'native_startup_values': ['ScreenX', 'ScreenY', 'FullScreen'],
        'fullscreen_preference': FULLSCREEN_PREFERENCE,
        'fullscreen_apply': 'Launcher copies CoopFullScreen to FullScreen before next process; engine owns live device mode',
        'settings_apply_cancel_preserved': True,
        'sound_and_controls_handlers_preserved': True,
        'native_multiplayer_inventory_protection_preserved': True,
        'difficulty_policy': 'Existing fixed native network difficulty retained at shared InitGame; local options apply cannot reset world coefficients',
        'difficulty_control': 'Explicitly fixed in UI; no writes to profile difficulty',
        'new_controls_reference_layout': {'width': 800, 'height': 600, 'rows': [426, 458]},
        'native_compilation_verified': False,
        'display_modes_manually_verified': False,
    }
    return files, metadata
