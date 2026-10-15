"""Bounded gameplay HUD composed after the exact campaign shop helper.

Presentation reads only the local army. Inventory and character clicks use
the existing key paths and transport protocol 5. Weapon selection keeps the
original synchronized 1..5, Q/E and wheel input; its strip is not clickable.
No native compilation, files, processes, or world changes occur in patch().
"""
from __future__ import annotations

import hashlib
import re


FEATURE = 'old-native-campaign-hud-v4'
INPUT_SHA256 = 'f98d4ec4014ba25f38a30ecd646118f5cb1109c2b8ab7d99ea95375d5812ed22'
HELPER_NAME = 'Maps/old_campaign_shop.lgc'
NAME_COUNT = 130

# Original Weapon.cfg VidMENU pairs, in the guarded localization order.
ICON_PAIRS = (
    (1619, 6), (1619, 5), (1619, 3), (1619, 2), (1619, 0), (1619, 4), (1619, 1), (1625, 5),
    (1625, 4), (1625, 1), (1625, 2), (1625, 0), (1625, 6), (1625, 7), (1625, 8), (1625, 3),
    (1625, 9), (1625, 8), (0, 0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 0),
    (0, 0), (0, 0), (0, 0), (0, 0), (0, 0), (1613, 1), (1617, 7), (1617, 1),
    (1617, 0), (1617, 5), (1617, 6), (1617, 3), (1617, 2), (1617, 8), (1617, 4), (1617, 9),
    (1617, 6), (1621, 4), (1621, 5), (1621, 0), (1621, 2), (1621, 1), (1621, 12), (1621, 13),
    (1621, 11), (1621, 3), (1621, 8), (1613, 2), (1613, 13), (1609, 14), (1609, 11), (1609, 4),
    (1609, 9), (1609, 10), (1609, 5), (1609, 2), (1609, 0), (1609, 3), (1609, 12), (1609, 1),
    (1609, 13), (1609, 6), (1609, 7), (1609, 8), (1637, 6), (1637, 10), (1637, 5), (1637, 12),
    (1637, 1), (1637, 0), (0, 0), (0, 0), (0, 0), (0, 0), (1637, 8), (1637, 9),
    (1637, 6), (1637, 2), (1637, 7), (1637, 4), (1637, 3), (1637, 11), (1601, 5), (1601, 4),
    (1601, 1), (1601, 3), (1601, 9), (1601, 10), (1601, 7), (1601, 13), (1601, 12), (1601, 2),
    (1601, 6), (1601, 0), (1601, 8), (1601, 11), (1613, 9), (1613, 7), (1613, 8), (1613, 4),
    (1613, 11), (1613, 6), (1613, 12), (1613, 3), (0, 0), (1605, 6), (1605, 6), (1605, 4),
    (1605, 3), (1605, 5), (1605, 7), (1605, 0), (1605, 2), (1605, 1), (0, 0), (1613, 10),
    (1623, 0), (1623, 3), (1623, 6), (1623, 1), (1623, 4), (1623, 7), (1623, 2), (1623, 5),
    (1623, 8), (0, 0),
)


HUD = r'''
// Local presentation only. Native game inputs still own weapon changes.
static int OldHudTextIds[11];
static string OldHudTextValues[11];
static int OldHudArt[12];
static int OldHudHover = 0;
static int OldHudHelp = 0;
static int OldHudLastClick = 0;
static string OldHudWeaponNames[] = {"Без оружия", "Пистолет", "Дробовик", "Пулемёт", "Ракетница", "Энергооружие"};

OldHudText(int index, int x, int y, string value)
{
    if(!OldHudTextIds[index])
        OldHudTextIds[index] = CreateText(8, x, y + 4000, 4000, value);
    else if(OldHudTextValues[index] != value)
        Action(OldHudTextIds[index], ACT_SET_TEXT, &value);
    OldHudTextValues[index] = value;
}

OldHudClear()
{
    int i;
    for(i = 0; i < 11; i++)
    {
        if(OldHudTextIds[i]) Destroy(OldHudTextIds[i]);
        OldHudTextIds[i] = 0;
    }
    for(i = 0; i < 12; i++)
    {
        if(OldHudArt[i]) Destroy(OldHudArt[i]);
        OldHudArt[i] = 0;
    }
    OldHudHover = 0;
    OldHudHelp = 0;
}

OldHudTact(int army, int mode)
{
    int click = SendCommandA(army, 329, IM_LBUTTONCLICK);
    int edge = click && !OldHudLastClick;
    OldHudLastClick = click;
    if(mode || giMenuState != MT_NOMENU || !OldInventoryCanUse(army))
    {
        OldHudClear();
        return 0;
    }
    int hero = SendCommandA(army, EXT_GETHEROID);
    if(!hero) { OldHudClear(); return 0; }
    int weapon = SendCommandA(army, EXT_GETWEAPONID);
    int slot = 0;
    if(weapon) slot = SendCommand(EXT_GETSKILL, weapon, RPGWEAPON_CLASSS);
    if(slot < 0 || slot > 5) slot = 0;
    int x = ScreenX()/2 - 370;
    int y = ScreenY() - 120;
    int mx = SendCommandA(army, 329, IA_SCREEN_MOUSE_X) - x;
    int my = SendCommandA(army, 329, IA_SCREEN_MOUSE_Y) - y;
    int button = -1;
    if(my >= 82 && my < 116 && mx >= 220 && mx < 730) button = (mx - 220)/170;
    OldHudHover = mx >= 0 && mx < 740 && my >= 0 && my < 120;
    if(OldHudHelp && mx >= 0 && mx < 740 && my >= -130 && my < 0) OldHudHover = 1;
    int i;
    if(!OldHudArt[0])
    {
        OldHudArt[0] = OldUiVisual(2228, 0, x + 370, y + 61, 2150, 620);
        OldHudArt[1] = OldUiVisual(730, 0, x + 80, y + 58, 700, 700);
        OldHudArt[2] = OldUiVisual(736, 0, x + 114, y + 59, 700, 700);
        for(i = 0; i < 5; i++)
            OldHudArt[3 + i] = OldUiVisual(732, i*51, x + 250 + i*52, y + 54, 800, 800);
        for(i = 0; i < 3; i++)
            OldHudArt[8 + i] = OldUiVisual(2222, 0, x + 305 + i*170, y + 99, 630, 1250);
    }
    int hp = SendCommand(EXT_GETSKILL, hero, RPGHERO__HP);
    int maxhp = SendCommand(EXT_GETSKILL, hero, RPGHERO_MAXHP);
    int hpdir = 250;
    if(maxhp > 0) hpdir = 255 - hp*255/maxhp;
    if(hpdir > 250) hpdir = 250;
    if(hpdir < 0) hpdir = 0;
    Action(OldHudArt[2], ACT_CHANGE_DIRECTION, hpdir);
    OldHudText(0, x + 20, y + 102, "HP " + itoa(hp) + "/" + itoa(maxhp));
    OldHudText(1, x + 218, y + 9,
        "ОБЩАЯ КАССА  " + itoa(SendCommand(EXT_GETSKILL, hero, RPGHERO_MONEY)) + " $");
    int ammo = SendCommand(EXT_GETSKILL, hero, RPGHERO_CURAMMOCNT);
    string text = "ПАТРОНЫ  " + itoa(ammo);
    if(ammo == 999999) text = "ПАТРОНЫ  --";
    OldHudText(2, x + 520, y + 9, text);
    OldHudText(3, x + 520, y + 43, OldHudWeaponNames[slot]);
    OldHudText(4, x + 520, y + 61, "1-5 / Q / E / колесо");
    OldHudText(5, x + 239, y + 93, "I  Инвентарь");
    OldHudText(6, x + 409, y + 93, "C  Персонаж");
    OldHudText(7, x + 579, y + 93, "?  Управление");
    for(i = 0; i < 5; i++)
    {
        int anim = ANI_MENUSTAND;
        if(slot == i + 1) anim = ANI_MENUSTANDUP;
        Action(OldHudArt[3 + i], ACT_CHANGE_ANIMATION, anim);
    }
    for(i = 0; i < 3; i++) OldUiTone(OldHudArt[8 + i], 1, button == i);
    text = "";
    if(OldHudHelp)
    {
        if(!OldHudArt[11]) OldHudArt[11] = OldUiVisual(2228, 0, x + 370, y - 65, 2150, 780);
        text = "УПРАВЛЕНИЕ\nWASD / стрелки — движение; ЛКМ — огонь; ПКМ — идти к курсору.";
        text = text + "\n1-5 / Q / E / колесо — оружие; R — перезарядка; F — фонарик.";
        text = text + "\nI — вещи; C — персонаж. В инвентаре: E — надеть, R — снять, U — аптечка.";
        text = text + "\nEsc — закрыть панель. Инвентарь и персонаж не ставят игру на паузу.";
    }
    else if(OldHudArt[11]) { Destroy(OldHudArt[11]); OldHudArt[11] = 0; }
    OldHudText(10, x + 20, y - 122, text);
    if(OldHudHover && !OldShopLocalCapture)
    {
        SendCommandA(army, 328, 1);
        OldShopLocalCapture = 1;
        SetCursor(CURSOR_NORMAL);
    }
    if(!edge || button < 0) return 0;
    if(button == 0) return 5;
    if(button == 1) return 9;
    OldHudHelp = 1 - OldHudHelp;
    return 0;
}
'''


SKIN = r'''
static int OldUiArt[24];
static string OldUiIconKeys[16];
static int OldUiRows[2];
static int OldUiAllowed[4];

OldUiVisual(int vid, int dir, int x, int y, int sx, int sy, int z = 3950)
{
    // This helper takes an absolute direction, like ACT_CHANGE_DIRECTION.
    // MenuCreate expects a frame ordinal and converts it internally. Start
    // with frame zero, then apply the angle once (also for catalog/drag art).
    int sprite = MenuCreate(vid, 0, x, y, z);
    Action(sprite, ACT_CHANGE_DIRECTION, dir);
    Action(sprite, ACT_SET_SCALE, sx, sy, 1000);
    return sprite;
}

OldUiTone(int sprite, int enabled, int selected)
{
    int gamma = 0;
    if(!enabled) gamma = GammaEncodeToDword(-80, -80, -80);
    else if(selected) gamma = GammaEncodeToDword(90, 55, 0);
    if(sprite) Action(sprite, ACT_SET_GAMMA, gamma);
}

OldUiClear()
{
    for(int i = 0; i < 24; i++)
    {
        if(OldUiArt[i]) Destroy(OldUiArt[i]);
        OldUiArt[i] = 0;
    }
}

OldUiIcon(int index, string key, int x, int y)
{
    if(OldUiArt[index] && OldUiIconKeys[index] == key) return;
    if(OldUiArt[index]) Destroy(OldUiArt[index]);
    OldUiArt[index] = 0;
    OldUiIconKeys[index] = key;
    for(int i = 0; i < 130; i++)
    {
        if(key == OldHudItemKeys[i])
        {
            if(OldHudItemVids[i])
                OldUiArt[index] = OldUiVisual(OldHudItemVids[i],
                    SendCommand(EXT_GETABSDIR, OldHudItemVids[i], OldHudItemDirs[i]), x, y, 300, 300);
            return;
        }
    }
}

OldUiPanelSkin(int army, int mode)
{
    int x = ScreenX()/2 - 360;
    int y = ScreenY()/2 - 235;
    int mx = SendCommandA(army, 329, IA_SCREEN_MOUSE_X) - x;
    int my = SendCommandA(army, 329, IA_SCREEN_MOUSE_Y) - y;
    int i, row, locator, base, enabled, bx, bw;
    int busy = SendCommandA(army, 326) || SendCommandA(0, 327);
    int count = SendCommandA(army, 310);
    int selected = OldShopSellPage*8 + OldShopSellRow;
    locator = -1;
    if(selected < count) locator = SendCommandA(army, 311, selected);
    string key;
    for(i = 0; i < 4; i++)
    {
      if(mode != 3 || i == 0 || i == 3)
      {
        bx = i*190; bw = 175; enabled = 1;
        if(mode == 1)
        {
            if(i == 0) { bx = 0; bw = 170; }
            if(i == 1) { bx = 300; bw = 150; }
            if(i == 2) { bx = 450; bw = 125; }
            if(i == 3) { bx = 585; bw = 145; }
            if(i == 0)
            {
                row = OldShopBuyPage*8 + OldShopBuyRow;
                base = SendCommandA(0, 302, row);
                int hero = SendCommandA(army, EXT_GETHEROID);
                enabled = base > 0 && SendCommandA(0, 303, base, 3) > 0
                    && SendCommandA(0, 303, base, 1) <= SendCommand(EXT_GETSKILL, hero, RPGHERO_MONEY);
            }
            else if(i < 3) enabled = locator >= 0 && SendCommandA(army, 312, locator, 11) == 1;
        }
        else if(mode == 2)
        {
            if(i == 0) bw = 180;
            if(i == 1) bw = 160;
            if(i == 2) { bx = 360; bw = 200; }
            if(i == 3) { bx = 585; bw = 145; }
            if(i < 3) enabled = locator >= 0 && SendCommandA(army, 312, locator, 12 + i) == 1;
        }
        else
        {
            bx = 50; bw = 310;
            if(i == 3) { bx = 545; bw = 185; }
            else enabled = SendCommandA(army, 330, OldDevelopmentSkills[OldDevelopmentRow], 4) == 1;
        }
        if(busy && i < 3) enabled = 0;
        OldUiAllowed[i] = enabled;
        if(!OldUiArt[16 + i])
            OldUiArt[16 + i] = OldUiVisual(2222, 0, x + bx + bw/2, y + 420, bw*1000/258, 1460);
        int hover = mx >= bx && mx < bx + bw && my >= 400 && my < 440;
        OldUiTone(OldUiArt[16 + i], enabled, hover);
        int label = 23 + i;
        if(mode == 3) { label = 30; if(i == 3) label = 31; }
        OldUiTone(OldShopPanel[label], enabled, hover);
      }
    }
    int side, pos;
    int sides = 1;
    if(mode == 1) sides = 2;
    for(side = 0; side < sides; side++)
    {
        pos = OldShopSellRow; bx = 0; bw = 400;
        if(mode == 1)
        {
            bw = 350;
            if(side) bx = 370;
            else pos = OldShopBuyRow;
        }
        int height = 32; int stride = 34;
        if(mode == 3) { pos = OldDevelopmentRow; height = 24; stride = 26; bw = 730; }
        if(!OldUiArt[20 + side] || OldUiRows[side] != pos)
        {
            if(OldUiArt[20 + side]) Destroy(OldUiArt[20 + side]);
            OldUiArt[20 + side] = OldUiVisual(2222, 0, x + bx + bw/2,
                y + 100 + pos*stride, bw*1000/258, height*1000/26, 3930);
            OldUiRows[side] = pos;
        }
        OldUiTone(OldUiArt[20 + side], 1, mode != 1 || side == OldShopSelectionSide);
        if(mode != 3)
        {
          for(i = 0; i < 8; i++)
          {
            key = "";
            row = OldShopSellPage*8 + i;
            if(mode == 1 && !side)
            {
                row = OldShopBuyPage*8 + i;
                if(row < SendCommandA(0, 301)) key = SendCommandA(0, 303, SendCommandA(0, 302, row), 7);
            }
            else if(row < count) key = SendCommandA(army, 312, SendCommandA(army, 311, row), 7);
            OldUiIcon(side*8 + i, key, x + bx + 24, y + 104 + i*34);
          }
        }
    }
}
'''


def _text(source):
    if isinstance(source, bytes):
        source = source.decode('cp1251')
    if not isinstance(source, str):
        raise TypeError('Expected cp1251 bytes or generated shop text')
    return source.replace('\r\n', '\n')


def _sha(text):
    return hashlib.sha256(text.replace('\n', '\r\n').encode('cp1251')).hexdigest()


def _once(text, anchor, replacement):
    if text.count(anchor) != 1:
        raise ValueError('Campaign HUD anchor changed: ' + repr(anchor[:80]))
    return text.replace(anchor, replacement)


def _compact_names(text):
    """Retain every exact translation and the unknown-key fallback, using one loop."""
    match = re.search(r'OldShopItemTitle\(string key\)\n\{\n(?P<rows>(?:    if\(key == "[^"\n]+"\) return "[^"\n]*";\n)+)'
                      r'    return key;\n\}', text)
    if match is None:
        raise ValueError('Expected exact generated item title function')
    pairs = re.findall(r'    if\(key == "([^"\n]+)"\) return "([^"\n]*)";', match['rows'])
    if len(pairs) != NAME_COUNT or len({key for key, _ in pairs}) != NAME_COUNT:
        raise ValueError('Unexpected item title catalog')
    lines = []
    for name, column in (('OldHudItemKeys', 0), ('OldHudItemTitles', 1)):
        lines.append(f'static string {name}[{NAME_COUNT}] = {{')
        lines += ['    "' + pair[column] + '"' + (',' if i + 1 < NAME_COUNT else '')
                  for i, pair in enumerate(pairs)]
        lines.append('};')
    lines += ['OldShopItemTitle(string key)', '{', f'    for(int i = 0; i < {NAME_COUNT}; i++)',
              '        if(key == OldHudItemKeys[i]) return OldHudItemTitles[i];',
              '    return key;', '}']
    compact = '\n'.join(lines)
    if max(map(len, compact.splitlines())) > 160:
        raise ValueError('Item title initializer exceeds legacy source line bound')
    return text[:match.start()] + compact + text[match.end():], len(match[0]), len(compact)


def _skin_panels(text):
    icons = []
    for name, column in (('OldHudItemVids', 0), ('OldHudItemDirs', 1)):
        icons.append(f'static int {name}[{NAME_COUNT}] = {{')
        for offset in range(0, NAME_COUNT, 12):
            icons.append('    ' + ', '.join(str(pair[column]) for pair in ICON_PAIRS[offset:offset + 12])
                         + (',' if offset + 12 < NAME_COUNT else ''))
        icons.append('};')
    marker = 'OldShopText(int index, int font, int x, int y, string text, int behavior = 0)'
    text = _once(text, marker, '\n'.join(icons) + '\n' + SKIN.strip() + '\n\n' + marker)
    text = _once(text, 'OldShopClearPanel()\n{', 'OldShopClearPanel()\n{\n    OldUiClear();')
    # Use a single native frame/header/footer constructor for all personal views.
    frame = r'''OldUiFrame(string title, string help, string footer)
{
    int x = ScreenX()/2 - 360;
    int y = ScreenY()/2 - 235;
    OldShopPanel[0] = OldUiVisual(2228, 0, ScreenX()/2, ScreenY()/2 + 20, 2200, 2850, 3900);
    OldShopText(1, 4, ScreenX()/2, y, title, BEH_CENTER_X);
    OldShopText(2, 3, x + 10, y + 30, "");
    OldShopText(27, 3, x + 10, y + 446, "");
    OldShopText(28, 8, x + 10, y + 470, help);
    OldShopText(29, 8, x + 10, y + 488, footer);
}

OldUiTitle(string key)
{
    string title = OldShopItemTitle(key);
    if(strlen(title) > 34) { title[32] = 0; title = title + "..."; }
    return title;
}

'''
    text = _once(text, 'OldInventoryCreatePanel()\n{', frame + 'OldInventoryCreatePanel()\n{')
    for function in ('OldInventoryCreatePanel', 'OldDevelopmentCreatePanel', 'OldShopCreatePanel'):
        match = re.search(function + r'\(\)\n\{\n.*?\n\}', text, re.S)
        block = match[0]
        title = re.search(r'OldShopText\(1, 4, ScreenX\(\)/2, y, ("[^"]*"), BEH_CENTER_X\);', block)[1]
        help_text = re.search(r'OldShopText\(28, 8, x \+ 10, y \+ 470, ("[^"]*")\);', block)[1]
        footer = re.search(r'OldShopText\(29, 8, x \+ 10, y \+ 488, ("[^"]*")\);', block)[1]
        block = re.sub(r'    OldShopPanel\[0\] = MenuCreate\([^\n]*\);\n',
                       '    OldUiFrame(' + title + ',\n        ' + help_text + ',\n        ' + footer + ');\n', block)
        block = re.sub(r'    OldShopText\((?:1|2|27|28|29), [^\n]*\);\n', '', block)
        if function != 'OldDevelopmentCreatePanel':
            block = block.replace('5 + row, 8, x + 10', '5 + row, 8, x + 50')
            block = block.replace('13 + row, 8, x + 380', '13 + row, 8, x + 420')
        # Match each title's native button font and keep labels inside the hit area.
        block = block.replace('OldShopText(23, 4', 'OldShopText(23, 5')
        block = block.replace('OldShopText(24, 4', 'OldShopText(24, 5')
        block = block.replace('OldShopText(26, 4', 'OldShopText(26, 5')
        text = text[:match.start()] + block + text[match.end():]
    for key in ('key', 'key_buy', 'key_sell'):
        text = text.replace('            title = OldShopItemTitle(' + key + ')',
                            '            title = OldUiTitle(' + key + ')')
    # Selection has a graphic highlight now; remove textual arrows in item/skill rows.
    text = re.sub(r'^        +if\((?:i == OldShop(?:Sell|Buy)Row|row == OldDevelopmentRow)\) title = "> " \+ title;\n',
                  '', text, flags=re.M)
    text = _once(text, '    int edge = key && key != OldShopLastUIKey;',
                 '    OldUiPanelSkin(army, mode);\n    int edge = key && key != OldShopLastUIKey;')
    # Suppress disabled mouse actions before enqueue; native shared validation remains authoritative.
    for condition, button in (
        ('x >= 50 && x < 360', 0), ('x >= 0 && x < 180', 0),
        ('x >= 190 && x < 350', 1), ('x >= 360 && x < 560', 2),
        ('x >= 0 && x < 170', 0), ('x >= 300 && x < 450', 1), ('x >= 450 && x < 575', 2),
    ):
        text = _once(text, 'if(' + condition + ')', 'if(' + condition + f' && OldUiAllowed[{button}])')
    return text


def patch(source):
    """Return HUD-enabled shop text and exact metadata; unknown predecessors fail."""
    text = _text(source)
    if _sha(text) != INPUT_SHA256:
        raise ValueError('Expected exact campaign shop/inventory/development helper')
    before = len(text.encode('cp1251'))
    text, names_before, names_after = _compact_names(text)
    text = _skin_panels(text)
    text = _once(text, 'OldShopLocalPanel()\n{', HUD.strip() + '\n\nOldShopLocalPanel()\n{')
    text = _once(text, '    if(OldDevelopmentOpen[army]) mode = 3;',
                 '    if(OldDevelopmentOpen[army]) mode = 3;\n'
                 '    int hud_action = OldHudTact(army, mode);\n'
                 '    if(hud_action == 5) inventory_edge = 1;\n'
                 '    if(hud_action == 9) development_edge = 1;')
    text = _once(text, '            if(SendCommandA(army, 329, IM_LBUTTONDOWN) || key == VK_ESCAPE || key == VK_RETURN',
                 '            if(OldHudHover || SendCommandA(army, 329, IM_LBUTTONDOWN) || key == VK_ESCAPE || key == VK_RETURN')
    return text, {
        'feature': FEATURE, 'helper': HELPER_NAME,
        'input_sha256': INPUT_SHA256, 'output_sha256': _sha(text),
        'protocol_version_required': 5, 'weapon_slots': [1, 2, 3, 4, 5],
        'weapon_controls': 'Original synchronized 1..5, Q/E, mouse wheel.',
        'weapon_strip_clickable': False, 'weapon_setter_added': False,
        'inventory_character_buttons': 'Existing I/C edges -> OldShopQueue(5/9).',
        'presentation': {'text_handle_limit': 11, 'army': 'NET_N_LOCAL_PLAYER',
                         'fields': ['health', 'max_health', 'current_ammo', 'shared_money', 'current_weapon_class'],
                         'buttons': ['inventory', 'character', 'controls'],
                         'cached_text_updates': True, 'hidden_during_panels_and_menus': True,
                         'native_art_vids': [730, 732, 736, 2222, 2228],
                         'hud_art_handle_limit': 12, 'panel_art_handle_limit': 24,
                         'minimum_resolution': [800, 600], 'alignment': 'bottom-center HUD / centered personal panels',
                         'personal_item_icons': sum(bool(vid) for vid, direction in ICON_PAIRS),
                         'passive_visuals_only': True, 'native_menu_handlers_enabled': False,
                         'button_hover_and_disabled_tint': True, 'selection_background': True,
                         'help_closed_with_panels_and_menus': True, 'help_hover_captures_world_input': True,
                         'clear_function': 'OldHudClear()'},
        'names': {'count': NAME_COUNT, 'translations_unchanged': True,
                  'unknown_key_fallback_unchanged': True, 'bounded_lookup': True,
                  'source_bytes_before': names_before, 'source_bytes_after': names_after},
        'source_bytes_before': before, 'source_bytes_after': len(text.encode('cp1251')),
        'help_controls': ['WASD', 'arrows', 'LMB', 'RMB', '1..5', 'Q/E', 'wheel', 'R', 'F', 'I', 'C', 'Esc'],
        'native_bytecode_limit': 256000, 'native_bytecode_size_verified': False,
        'local_world_mutators_added': False, 'items_money_quests_hp_setters_added': False,
        'runtime_compiled': False, 'runtime_visual_tested': False,
    }
