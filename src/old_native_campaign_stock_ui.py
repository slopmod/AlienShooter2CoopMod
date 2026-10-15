"""Original OLD HUD presentation, composed over the synchronized campaign UI.

Keep the stock statebar renderer/data binding. Only its resource selection and
the arena overlay differ. Binary layouts retain every property except position
and editor viewport, with explicit corner anchors derived from the stock files.
No inventory mutations, networking, hero setters or input injection are added.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct

from old_native_ui_resources import MenuResource
from old_native_campaign_settings import MODES

FEATURE = 'old-native-campaign-stock-hud-v1'
STOCK_HASHES = {
    'Maps/common_statebar.lgc': '882b190670ee45e546d9a825b4cb7680973c0e5852912248abc0c9895f00686d',
    'Maps/gamebar800.men': '36727cafba4891a086fdc09e98d1569714c42cd17b1d8a0ba30fbbaac64743ac',
    'Maps/gamebar1024.men': 'c56344e1e55b1b78df193c72b0ac529b7cec27b4df7c577cf87652b33b3a59ce',
}

# The campaign's existing personal panels use a local mode and synchronized
# commands. Hide/restore the real HUD without opening the stock single-player
# inventory, changing the global map/menu type, or pausing either engine.
PANEL_LIFECYCLE = r'''
static int OldHudSavedState = -1;

OldHudTact(int army, int mode)
{
    if(giMenuState != MT_NOMENU) return;
    if(mode)
    {
        if(OldHudSavedState < 0)
        {
            OldHudSavedState = StateBar;
            if(StateBar)
            {
                StateBar = 0;
                CreateStateBar();
            }
        }
    }
    else if(OldHudSavedState >= 0)
    {
        // Remove panel item icons before the original MenuFind calls bind HUD
        // icons with the same VIDs. These are local presentation handles only.
        if(OldShopVisible) OldShopClearPanel();
        StateBar = OldHudSavedState;
        OldHudSavedState = -1;
        if(StateBar) CreateStateBar();
    }
}
'''


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def once(text: str, before: str, after: str) -> str:
    if text.count(before) != 1:
        raise ValueError('Original HUD source guard differs: ' + before[:90])
    return text.replace(before, after, 1)


def encode(text: str) -> bytes:
    return text.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251')


def hud_path(width: int, height: int) -> str:
    return f'Maps/old_campaign_gamebar{width}x{height}.men'


def anchored_layout(raw: bytes, base_size: tuple[int, int], size: tuple[int, int]) -> bytes:
    """Translate complete HUD groups; preserve original native-size files exactly.

    The two pinned stock layouts keep every group in one corner, without a
    group straddling either centerline. Even offscreen stock sprites retain
    their distance from that corner. Never scale fonts, icons or health bars.
    """
    if size == base_size:
        return raw
    if size not in MODES or base_size not in ((800, 600), (1024, 768)):
        raise ValueError('Unsupported HUD display mode')
    resource = MenuResource.read(raw)
    rows = resource.describe()['sprites']
    width, height = size
    dx, dy = width - base_size[0], height - base_size[1]
    header = bytearray(resource.header)
    struct.pack_into('<4f', header, 20, width, height, 0, 0)
    records = []
    for record, row in zip(resource.records[:-1], rows):
        x, y = row['centered_xy']
        x += base_size[0] / 2 + (dx if x > 0 else 0)
        y += base_size[1] / 2 + (dy if y > 0 else 0)
        output = bytearray(record)
        struct.pack_into('<2f', output, 8, x, y + row['stored_xyz'][2])
        records.append(bytes(output))
    return MenuResource(bytes(header), resource.sprite_header,
                        tuple(records) + resource.records[-1:]).encode()


def prepare(old_root: Path, helper: str, previous_metadata: dict,
            common: str) -> tuple[str, dict[str, bytes], dict]:
    """Return composed local HUD helper + original resources; never write files."""
    from old_native_campaign_hud import HUD, _text, _sha
    helper = _text(helper)
    if _sha(helper) != previous_metadata['output_sha256']:
        raise ValueError('Expected exact predecessor HUD helper')
    sources = {}
    for path, expected in STOCK_HASHES.items():
        raw = (Path(old_root) / path).read_bytes()
        if sha(raw) != expected:
            raise ValueError('Unsupported original HUD resource: ' + path)
        sources[path] = raw
    # Reuse the existing inventory/shop skins while their native transaction
    # adapter is developed. Remove all approximate HUD art and help controls.
    helper = once(helper, HUD.strip(), PANEL_LIFECYCLE.strip())
    helper = once(helper,
        '    int hud_action = OldHudTact(army, mode);\n'
        '    if(hud_action == 5) inventory_edge = 1;\n'
        '    if(hud_action == 9) development_edge = 1;',
        '    OldHudTact(army, mode);')
    helper = once(helper, 'if(OldHudHover || SendCommandA', 'if(SendCommandA')
    # Campaign startup deliberately skips the single-player help splash. Its
    # ShowHelpScreen(false) does not PopMenuState(), so opening it in InitGame
    # otherwise leaves the HUD hidden until another menu happens to restore it.
    common = _text(common)
    splash = ('    if( giCurLevCmpgn == Z_FIRST_LEVEL_NUM )\n'
              '        ShowHelpScreen( true );\n    else\n        Pause(0);')
    common = once(common, splash,
        '#ifdef OLD_CAMPAIGN_SHOP_UI\n'
        '    // The cooperative entry already skips this single-player splash.\n'
        '    // Avoid leaving its PushMenuState pending with a hidden HUD.\n'
        '    Pause(0);\n#else\n' + splash + '\n#endif')
    # Tab belongs to shop list selection while a personal panel captures input.
    # F1 must not open a second local menu behind that panel either.
    for before, condition in (
            ('    if( HelpScreenTact() )', '!OldShopLocalCapture && !OldShopLocalOpening && HelpScreenTact()'),
            ('        if( GetKey() == 9 )', '!bOldShopCapture && !bMenuPause && GetKey() == 9')):
        common = once(common, before, '#ifdef OLD_CAMPAIGN_SHOP_UI\n'
            '        if(' + condition + ')\n#else\n' + before + '\n#endif')
    files = {'Maps/COMMON.LGC': encode(common)}
    for width, height in MODES:
        base = (800, 600) if width == 800 else (1024, 768)
        files[hud_path(width, height)] = anchored_layout(
            sources[f'Maps/gamebar{base[0]}.men'], base, (width, height))
    text = sources['Maps/common_statebar.lgc'].decode('cp1251').replace('\r\n', '\n')
    choices = '\n'.join(
        f'        if(ScreenX() == {w} && ScreenY() == {h}) return "'
        + hud_path(w, h).replace('/', '\\\\').lower() + '";' for w, h in MODES)
    text = once(text, 'GetCurGBName(bool bFirst)\n{',
        'GetCurGBName(bool bFirst)\n{\n#ifdef OLD_CAMPAIGN_SHOP_UI\n'
        '    if(bFirst)\n    {\n' + choices + '\n'
        '        // Unknown external display mode: use a real, existing layout.\n'
        '        return "maps\\\\gamebar800.men";\n    }\n#endif')
    for action in ('MenuRelease', 'MenuLoad'):
        line = f'\t\t{action}(GetCurGBName(false));' if action == 'MenuRelease' else '\t    \tMenuLoad(GetCurGBName(false));'
        # The load line has different indentation in the shipped script.
        if action == 'MenuLoad':
            line = next(s for s in text.splitlines() if 'MenuLoad(GetCurGBName(false));' in s)
        text = once(text, line, '#ifndef OLD_CAMPAIGN_SHOP_UI\n' + line + '\n#endif')
    files['Maps/common_statebar.lgc'] = encode(text)
    hashes = {path: sha(data) for path, data in sorted(files.items())}
    helper_hash = _sha(helper)
    combined = sha(json.dumps(dict(helper=helper_hash, assets=hashes), sort_keys=True).encode())
    metadata = dict(feature=FEATURE, output_sha256=combined, helper_output_sha256=helper_hash,
        input_sha256=previous_metadata['output_sha256'], source_hashes=STOCK_HASHES,
        files=hashes, modes=MODES, original_native_size_layouts_unchanged=True,
        original_statebar_data_binding=True, stock_animation_code_unchanged=True,
        arena_overlay=False, custom_hud_removed=True,
        startup_help_splash=False, panel_input_does_not_toggle_hud=True,
        controls='Original weapon controls; I inventory, C character, Tab HUD toggle, Esc options.',
        native_inventory_handlers_enabled=False, command_protocol=5,
        panel_status='Existing synchronized inventory/character/shop retained; original panels pending.',
        runtime_compiled=False, runtime_visual_tested=False)
    return helper, files, metadata
