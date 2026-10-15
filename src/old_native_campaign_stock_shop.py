"""Stock shop layout with a read-only view of the shared campaign catalog.

Native inventory renders owned items; catalog sprites are presentation only.
Never construct native inventory items or invoke the single-player shop input.
"""
from __future__ import annotations

import json
from pathlib import Path

from old_native_campaign_stock_ui import sha, once
from old_native_campaign_hud import _sha, _text
from old_native_ui_resources import MenuResource

FEATURE = 'old-native-campaign-stock-shop-v3'
SHOP_SHA = '48aad3869f4692a5c2f94dea7a86215d1e31ac184cdcf8103d28ca8f95b122ac'
MENU = 'Maps/old_campaign_stock_shop.men'


def named_layout(raw: bytes) -> bytes:
    """Give stock controls stable names; every non-name byte remains intact."""
    if sha(raw) != SHOP_SHA:
        raise ValueError('Unsupported original shop menu')
    resource = MenuResource.read(raw)
    description = resource.describe()
    if description['format_version'] != 19:
        raise ValueError('Expected v19 shop resource')
    rows = description['sprites']
    names = {}
    for vid, prefix, count in ((721, 'OSC_CAT', 9), (723, 'OSC_ACTION', 2),
                               (2210, 'OSC_ARROW', 2), (2201, 'OSC_SCROLL', 1)):
        indices = sorted((i for i, row in enumerate(rows) if row['vid'] == vid),
                         key=lambda i: (rows[i]['centered_xy'][1], rows[i]['centered_xy'][0]))
        if len(indices) != count:
            raise ValueError('Original shop control count changed')
        names.update({i: prefix + str(n) for n, i in enumerate(indices)})
    for caption, name in (('BuyWeapon', 'OSC_LABEL0'), ('BuyAmmo', 'OSC_LABEL1'),
                          ('Price_Weapon', 'OSC_PRICE0'), ('Price_Ammo', 'OSC_PRICE1')):
        indices = [i for i, row in enumerate(rows) if row['strings'] == [caption]]
        if len(indices) != 1:
            raise ValueError('Original shop caption changed')
        names[indices[0]] = name
    records = list(resource.records)
    for index, name in names.items():
        prefix, tail = records[index][:60], records[index][60:]
        old_name, rest = tail.split(b'\0', 1)
        if old_name:
            raise ValueError('Will not replace an existing native anchor')
        records[index] = prefix + name.encode('ascii') + b'\0' + rest
    return MenuResource(resource.header, resource.sprite_header, tuple(records)).encode()


SCRIPT = r'''
static int OldStockShopShown = 0;
static int OldStockShopResult = 0;
static int OldStockShopCategory = 0;
static int OldStockShopPage = 0;
static int OldStockShopPages = 1;
static int OldStockShopCount = 0;
static int OldStockShopIds[256];
static int OldStockShopWidths[256];
static int OldStockShopHeights[256];
static int OldStockShopCells[256];
static int OldStockShopItemPages[256];
static int OldStockShopOccupied[42];
static int OldStockShopX = 0;
static int OldStockShopY = 0;
static int OldStockShopAmmoX = 0;
static int OldStockShopAmmoY = 0;
static int OldStockShopCellsArt[48];
static int OldStockShopIcons[48];
static int OldStockShopCounts[48];
static int OldStockShopVisibleIds[48];
static int OldStockShopLeft[48];
static int OldStockShopTop[48];
static int OldStockShopRight[48];
static int OldStockShopBottom[48];
static int OldStockShopVisibleCount = 0;
static int OldStockShopSelected[2];
static int OldStockShopUnits[2];
static int OldStockShopPrices[2];
static int OldStockShopOwned = 0;
static int OldStockShopActiveButton = 0;
static int OldStockShopScrollDrag = 0;
static int OldStockShopRefreshAt = 0;
static int OldStockShopSeenHostRequests = -1;
static int OldStockShopSeenClientRequests = -1;
static int OldStockShopScrollY = 0;
static int OldStockShopScrollScale = 0;

OldInventoryDragShopArea(int x, int y)
{
    if(OldShopVisible != 1 || !OldStockShopShown) return 0;
    return (x >= OldStockShopX && x < OldStockShopX+222 && y >= OldStockShopY && y < OldStockShopY+259) ||
        (x >= OldStockShopAmmoX && x < OldStockShopAmmoX+222 && y >= OldStockShopAmmoY && y < OldStockShopAmmoY+37);
}

OldStockShopSetText(string name, string text)
{
    int spr = MenuFindNamed(name);
    if(!spr) return;
    // Stock prices/captions use BEH_SCRIPT_UPDATED. Our value is literal;
    // otherwise the renderer searches for a variable named "Buy" / "100 $"
    // on the next frame and clears it. Retain the original centered layout.
    Action(spr, ACT_SET_BEHAVE, Action(spr, ACT_GET_BEHAVE) & ~BEH_LOAD_FROM);
    Action(spr, ACT_SET_TEXT, &text);
}

OldStockShopButtonState(int spr, int enabled, int hovered, int pressed)
{
    if(!spr) return;
    int animation = ANI_MENUSTAND;
    if(!enabled) animation = ANI_MENUDISABLE;
    else if(hovered)
    {
        animation = ANI_MENUSELECTDOWN;
        if(pressed) animation = ANI_MENUPRESSDOWN;
    }
    if(GetAnimation(spr) != animation) Action(spr, ACT_CHANGE_ANIMATION, animation);
    // VID 723 has its own stock normal/selected/disabled art. Do not darken
    // those frames again with the generic catalog-item gamma tint.
    Action(spr, ACT_SET_GAMMA, 0);
}

OldStockShopHit(string name, int x, int y, int rx, int ry)
{
    int spr = MenuFindNamed(name);
    if(!spr) return 0;
    int sx = ToScreenX(GetX(spr));
    int sy = ToScreenY(GetY(spr), GetZ(spr));
    return x >= sx-rx && x <= sx+rx && y >= sy-ry && y <= sy+ry;
}

OldStockShopHitCatalog(int x, int y)
{
    for(int i = 0; i < OldStockShopVisibleCount; i++)
        if(x >= OldStockShopLeft[i] && x < OldStockShopRight[i] &&
           y >= OldStockShopTop[i] && y < OldStockShopBottom[i]) return i;
    return -1;
}

OldStockShopClearGrid()
{
    for(int i = 0; i < 48; i++)
    {
        if(OldStockShopCellsArt[i]) Destroy(OldStockShopCellsArt[i]);
        if(OldStockShopIcons[i]) Destroy(OldStockShopIcons[i]);
        if(OldStockShopCounts[i]) Destroy(OldStockShopCounts[i]);
        OldStockShopCellsArt[i] = 0;
        OldStockShopIcons[i] = 0;
        OldStockShopCounts[i] = 0;
    }
    OldStockShopVisibleCount = 0;
}

OldStockShopClose()
{
    if(!OldStockShopShown) return;
    OldInventoryDragCancel();
    int army = NetProperty(NET_N_LOCAL_PLAYER);
    OldStockItemInfoClear(army);
    SendCommandA(army, 318, 0);
    OldStockShopClearGrid();
    MenuRelease("maps\\old_campaign_stock_shop.men");
    Genocide(2230);
    OldStockShopShown = 0;
    OldStockShopOwned = 0;
    OldStockShopScrollDrag = 0;
}

OldStockShopSelect(int base, int ammo)
{
    OldStockShopSelected[ammo] = base;
    OldStockShopUnits[ammo] = SendCommandA(0, 303, base, 2);
    OldStockShopPrices[ammo] = SendCommandA(0, 303, base, 1);
    OldStockShopOwned = 0;
}

OldStockShopAddCatalog(int base)
{
    int j, x, y, cell;
    int type = SendCommandA(0, 303, base, 5);
    int cls = SendCommandA(0, 303, base, 6);
    int matches = OldStockShopCategory < 5 && type == 2 && cls == OldStockShopCategory+1;
    if(OldStockShopCategory == 5 && type == 4) matches = 1;
    if(OldStockShopCategory == 7 && type == 6) matches = 1;
    if(OldStockShopCategory == 8 && type == 3) matches = 1;
    if(!matches) return;
    int w = SendCommandA(0, 303, base, 16);
    int h = SendCommandA(0, 303, base, 17);
    if(w < 1 || w > 6 || h < 1 || h > 7) return;
    int found = -1;
    // Bounded first-fit packing. The original cell pitch is 37 pixels.
    for(int attempt = 0; attempt < 2 && found < 0; attempt++)
    {
        for(cell = 0; cell < 42 && found < 0; cell++)
        {
            int fits = cell%6+w <= 6 && cell/6+h <= 7;
            if(fits)
                for(y = 0; y < h; y++)
                    for(x = 0; x < w; x++)
                        if(OldStockShopOccupied[cell+y*6+x]) fits = 0;
            if(fits) found = cell;
        }
        if(found < 0)
        {
            OldStockShopPages++;
            for(j = 0; j < 42; j++) OldStockShopOccupied[j] = 0;
        }
    }
    if(found < 0) return;
    for(y = 0; y < h; y++)
        for(x = 0; x < w; x++) OldStockShopOccupied[found+y*6+x] = 1;
    j = OldStockShopCount;
    OldStockShopIds[j] = base;
    OldStockShopWidths[j] = w;
    OldStockShopHeights[j] = h;
    OldStockShopCells[j] = found;
    OldStockShopItemPages[j] = OldStockShopPages-1;
    OldStockShopCount++;
}

OldStockShopBuildCatalog()
{
    OldStockShopCount = 0;
    OldStockShopPage = 0;
    OldStockShopPages = 1;
    OldStockShopActiveButton = 0;
    for(int i = 0; i < 42; i++) OldStockShopOccupied[i] = 0;
    int count = SendCommandA(0, 301);
    if(count >= 0 && count <= 256)
        for(i = 0; i < count; i++) OldStockShopAddCatalog(SendCommandA(0, 302, i));
    OldStockShopSelected[0] = 0;
    OldStockShopSelected[1] = 0;
    OldStockShopOwned = 0;
    if(OldStockShopCount) OldStockShopSelect(OldStockShopIds[0], 0);
}

OldStockShopAddIcon(int army, int base, int x, int y, int w, int h)
{
    int i = OldStockShopVisibleCount;
    if(i >= 48) return;
    int vid = SendCommandA(army, EXT_GETITEMVIDBYID, base, 1);
    int dir = SendCommandA(army, EXT_GETITEMVIDBYID, base, 2);
    if(vid <= 0 || dir < 0) return;
    OldStockShopVisibleIds[i] = base;
    OldStockShopLeft[i] = x;
    OldStockShopTop[i] = y;
    OldStockShopRight[i] = x+w*37;
    OldStockShopBottom[i] = y+h*37;
    OldStockShopIcons[i] = OldUiVisual(vid, SendCommand(EXT_GETABSDIR, vid, dir),
        x+w*37/2, y+h*37/2, 1000, 1000, 3950);
    OldStockShopCounts[i] = CreateText(8, x+w*37-13, y+h*37-8+4000, 4000, "", BEH_CENTER_X);
    OldStockShopVisibleCount++;
}

OldStockShopDrawGrid(int army)
{
    OldStockItemInfoClear(army);
    OldStockShopClearGrid();
    for(int i = 0; i < 42; i++)
        OldStockShopCellsArt[i] = OldUiVisual(720, 0,
            OldStockShopX+i%6*37+19, OldStockShopY+i/6*37+18, 1000, 1000, 3900);
    int first = 0;
    int selected_visible = 0;
    for(i = 0; i < OldStockShopCount; i++)
    {
        if(OldStockShopItemPages[i] == OldStockShopPage)
        {
            if(!first) first = OldStockShopIds[i];
            if(OldStockShopIds[i] == OldStockShopSelected[0]) selected_visible = 1;
            int cell = OldStockShopCells[i];
            OldStockShopAddIcon(army, OldStockShopIds[i], OldStockShopX+cell%6*37,
                OldStockShopY+cell/6*37, OldStockShopWidths[i], OldStockShopHeights[i]);
        }
    }
    if(!selected_visible)
    {
        OldStockShopSelected[0] = 0;
        if(first) OldStockShopSelect(first, 0);
    }
    // The original lower tray holds ammunition for the current weapon class.
    int count = SendCommandA(0, 301);
    int ammo_cell = 0;
    if(OldStockShopCategory < 5)
        for(i = 0; i < count && ammo_cell < 6; i++)
        {
            int base = SendCommandA(0, 302, i);
            if(SendCommandA(0, 303, base, 5) == 3 &&
               SendCommandA(0, 303, base, 6) == OldStockShopCategory+1)
            {
                int w = SendCommandA(0, 303, base, 16);
                int h = SendCommandA(0, 303, base, 17);
                if(w >= 1 && ammo_cell+w <= 6 && h == 1)
                {
                    OldStockShopAddIcon(army, base, OldStockShopAmmoX+ammo_cell*37, OldStockShopAmmoY, w, h);
                    if(!OldStockShopSelected[1]) OldStockShopSelect(base, 1);
                    ammo_cell = ammo_cell+w;
                }
            }
        }
    for(i = 0; i < 6; i++)
        OldStockShopCellsArt[42+i] = OldUiVisual(720, 0,
            OldStockShopAmmoX+i*37+19, OldStockShopAmmoY+18, 1000, 1000, 3900);
    OldStockShopRefreshAt = 0;
    OldStockShopSeenHostRequests = OldShopRequests[0];
    OldStockShopSeenClientRequests = OldShopRequests[3];
}

OldStockShopRefreshCatalog(int army)
{
    if(!OldStockShopShown || OldInventoryDragArmed || SendCommandA(army, 326)) return;
    if(OldStockShopSeenHostRequests == OldShopRequests[0] &&
       OldStockShopSeenClientRequests == OldShopRequests[3]) return;
    // Refresh after acknowledged transactions from EITHER shopper. Keep the
    // same page, base IDs and finite stock; never reinitialize the catalog.
    int owned = OldStockShopOwned;
    OldStockShopDrawGrid(army);
    OldStockShopOwned = owned;
    if(owned)
    {
        int loc = OldStockInventoryLocator;
        int quantity = SendCommandA(army, 312, loc, 3);
        if(loc >= 0 && quantity > 0 &&
           SendCommandA(army, 312, loc, 0) == OldStockInventoryBase)
            OldStockInventoryQuantity = quantity;
        else
        {
            OldStockShopOwned = 0;
            OldStockInventoryLocator = -1;
        }
    }
}

OldStockShopCreate(int army)
{
    OldInventoryDragReset(army);
    MenuLoad("maps\\old_campaign_stock_shop.men");
    int anchor = MenuFindNamed("INV_SHOP");
    OldStockShopX = ToScreenX(GetX(anchor))-19;
    OldStockShopY = ToScreenY(GetY(anchor), GetZ(anchor))-18;
    Destroy(anchor);
    anchor = MenuFindNamed("INV_AMMO");
    OldStockShopAmmoX = ToScreenX(GetX(anchor))-19;
    OldStockShopAmmoY = ToScreenY(GetY(anchor), GetZ(anchor))-18;
    Destroy(anchor);
    // Missing catalog anchors move native containers 20/21 offscreen. Only
    // genuine owned containers are rendered; catalog sprites never own items.
    AllignInventory();
    SearchForTexts();
    int perk = SendCommandA(army, EXT_GETPERKSKILL)-RPGHERO_PERK_HEALING;
    MenuAction(713, 999999, ACT_CHANGE_DIRECTION, SendCommand(EXT_GETABSDIR, 713, perk));
    anchor = MenuFindNamed("OSC_SCROLL0");
    OldStockShopScrollY = GetY(anchor);
    OldStockShopScrollScale = Action(anchor, ACT_GET_SCALE, 1);
    for(int i = 0; i < 3; i++)
    {
        string name = "MT_INVMENU";
        if(i == 1) name = "MT_LOGSMENU";
        if(i == 2) name = "MT_PAUSEMENU";
        anchor = MenuFindNamed(name);
        if(anchor) Action(anchor, ACT_SET_INVISIBLE, 1);
    }
    OldStockShopResult = SendCommandA(army, 318, 1);
    OldStockInventorySeenRequests = OldShopRequests[army];
    OldStockInventoryRefreshAt = GetTime();
    OldStockShopShown = 1;
    OldShopVisible = 1;
    OldShopLocalQueueResult = 0;
    OldStockShopCategory = 0;
    OldStockInventoryLocator = -1;
    OldStockShopBuildCatalog();
    OldStockShopDrawGrid(army);
    OldShopText(27, 8, ScreenX()/2, ScreenY()/2+258, "", BEH_CENTER_X);
    OldShopText(28, 8, ScreenX()/2, ScreenY()/2+278,
        "Перенос: купить / продать стопку / переместить. Enter — действие. Esc — отмена / выход.", BEH_CENTER_X);
}

OldStockShopCanAct(int army, int button)
{
    if(SendCommandA(army, 326) || SendCommandA(0, 327)) return 0;
    if(OldStockShopOwned)
    {
        int loc = OldStockInventoryLocator;
        if(loc < 0 || SendCommandA(army, 312, loc, 0) != OldStockInventoryBase ||
           SendCommandA(army, 312, loc, 3) != OldStockInventoryQuantity) return 0;
        return SendCommandA(army, 312, loc, 11) == 1;
    }
    int base = OldStockShopSelected[button];
    if(base <= 0 || OldStockShopUnits[button] <= 0 || OldStockShopPrices[button] <= 0) return 0;
    if(SendCommandA(0, 303, base, 2) != OldStockShopUnits[button] ||
       SendCommandA(0, 303, base, 1) != OldStockShopPrices[button]) return 0;
    int hero = SendCommandA(army, EXT_GETHEROID);
    return SendCommandA(0, 303, base, 3) >= OldStockShopUnits[button] &&
        SendCommand(EXT_GETSKILL, hero, RPGHERO_MONEY) >= OldStockShopPrices[button];
}

OldStockShopQueueAction(int army, int button)
{
    if(!OldStockShopCanAct(army, button)) return;
    if(OldStockShopOwned)
        OldShopLocalQueueResult = OldShopQueue(2+button, OldStockInventoryLocator,
            OldStockInventoryBase, OldStockInventoryQuantity);
    else
        OldShopLocalQueueResult = OldShopQueue(1, OldStockShopSelected[button],
            OldStockShopUnits[button], OldStockShopPrices[button]);
}

OldStockShopTact(int army, int key, int click, int inv_edge, int dev_edge)
{
    if(!OldShopVisible) OldStockShopCreate(army);
    OldStockInventoryRefresh(army);
    OldStockShopRefreshCatalog(army);
    int edge = key && key != OldShopLastUIKey;
    int mouse_edge = click && !OldShopLastUIClick;
    OldShopLastUIKey = key;
    OldShopLastUIClick = click;
    int x = SendCommandA(army, 329, IA_SCREEN_MOUSE_X);
    int y = SendCommandA(army, 329, IA_SCREEN_MOUSE_Y);
    int down = SendCommandA(army, 329, IM_LBUTTONDOWN);
    int pressed = down && !OldInventoryDragLastDown;
    if(inv_edge || dev_edge || (edge && key == VK_ESCAPE) ||
       (mouse_edge && OldStockShopHit("INV_BTN_CLOSE", x, y, 60, 16)))
    {
        if(OldInventoryDragArmed)
        {
            OldInventoryDragCancel();
            OldStockInventoryClickTime = 0;
            return;
        }
        OldShopLocalQueueResult = OldShopQueue(4, 0, 0, 0);
        return;
    }
    int owned = SendCommandA(army, 319, x, y);
    int hovered = OldStockShopHitCatalog(x, y);
    int i;
    if(pressed && owned >= 0 && !SendCommandA(army, 326))
    {
        OldStockInventorySelect(army, owned);
        OldStockShopOwned = 1;
        OldStockShopActiveButton = 0;
        OldShopLocalQueueResult = 0;
    }
    if(pressed && hovered >= 0 && !SendCommandA(army, 326))
    {
        int ammo = OldStockShopTop[hovered] == OldStockShopAmmoY;
        OldStockShopSelect(OldStockShopVisibleIds[hovered], ammo);
        OldStockShopActiveButton = ammo;
        OldShopLocalQueueResult = 0;
        OldInventoryDragCatalogStart(army, OldStockShopVisibleIds[hovered], x, y,
            OldStockShopLeft[hovered], OldStockShopTop[hovered]);
    }
    int was_dragging = OldInventoryDragArmed;
    OldInventoryDragTact(army, down, owned, x, y);
    int block_controls = was_dragging || OldInventoryDragArmed;
    if(block_controls) { mouse_edge = 0; edge = 0; }
    if(!OldInventoryDragArmed)
    {
        if(owned >= 0) OldStockItemInfo(army, 1, owned, x, y);
        else if(hovered >= 0) OldStockItemInfo(army, 2, OldStockShopVisibleIds[hovered], x, y);
        else OldStockItemInfoClear(army);
    }
    for(i = 0; i < 9; i++)
    {
        string name = "OSC_CAT"+itoa(i);
        int over = OldStockShopHit(name, x, y, 20, 11);
        int spr = MenuFindNamed(name);
        OldUiTone(spr, i != 6, OldStockShopCategory == i || over);
        if(mouse_edge && over && i != 6 && i != OldStockShopCategory)
        {
            OldStockShopCategory = i;
            OldStockShopBuildCatalog();
            OldStockShopDrawGrid(army);
            hovered = -1;
        }
    }
    int page = OldStockShopPage;
    if(!block_controls && ((edge && key == VK_PRIOR) || SendCommandA(army, 329, IM_MOUSEWHEELUP) ||
       (mouse_edge && OldStockShopHit("OSC_ARROW0", x, y, 12, 12)))) page--;
    if(!block_controls && ((edge && key == VK_NEXT) || SendCommandA(army, 329, IM_MOUSEWHEELDOWN) ||
       (mouse_edge && OldStockShopHit("OSC_ARROW1", x, y, 12, 12)))) page++;
    int scroll = MenuFindNamed("OSC_SCROLL0");
    int track_x = ToScreenX(GetX(scroll));
    int track_y = ToScreenY(OldStockShopScrollY, GetZ(scroll))-117;
    if(mouse_edge && x >= track_x-10 && x <= track_x+10 && y >= track_y && y < track_y+235)
        OldStockShopScrollDrag = 1;
    if(!down || block_controls) OldStockShopScrollDrag = 0;
    if(OldStockShopScrollDrag) page = (y-track_y)*OldStockShopPages/235;
    if(page < 0) page = 0;
    if(page >= OldStockShopPages) page = OldStockShopPages-1;
    if(page != OldStockShopPage)
    {
        OldStockShopPage = page;
        OldStockShopDrawGrid(army);
        hovered = -1;
    }
    int height = 235/OldStockShopPages;
    int scroll_y = OldStockShopScrollY-(235-height)/2;
    if(OldStockShopPages > 1) scroll_y = scroll_y+(235-height)*OldStockShopPage/(OldStockShopPages-1);
    Action(scroll, ACT_SET_SCALE, 1000, OldStockShopScrollScale/OldStockShopPages, 1000);
    Action(scroll, ACT_CHANGE_COOR, GetX(scroll), scroll_y, GetZ(scroll));
    ControlTexts();
    for(i = 0; i < 2; i++)
    {
        int enabled = OldStockShopCanAct(army, i);
        string name = "OSC_ACTION"+itoa(i);
        int over = OldStockShopHit(name, x, y, 61, 19);
        OldStockShopButtonState(MenuFindNamed(name), enabled, over, down && !block_controls);
        int price = OldStockShopPrices[i];
        string label = "Купить";
        if(i == 1) label = "Купить патроны";
        if(!OldStockShopSelected[i]) price = -1;
        if(OldStockShopOwned)
        {
            label = "Продать";
            if(i == 1) label = "Продать всё";
            int loc = OldStockInventoryLocator;
            price = OldShopSaleQuote(SendCommandA(army, 312, loc, 4),
                OldStockInventoryQuantity, SendCommandA(army, 312, loc, 2), i);
        }
        string value = "—";
        if(price >= 0) value = itoa(price)+" $";
        OldStockShopSetText("OSC_LABEL"+itoa(i), label);
        OldStockShopSetText("OSC_PRICE"+itoa(i), value);
        if(mouse_edge && over && enabled) OldStockShopQueueAction(army, i);
    }
    if(edge && key == VK_RETURN) OldStockShopQueueAction(army, OldStockShopActiveButton);
    string message = "Деньги и запас магазина общие. Вещи остаются личными.";
    if(!OldStockShopCount) message = "В этой категории пока нет товаров.";
    if(OldStockShopOwned)
    {
        int loc = OldStockInventoryLocator;
        if(SendCommandA(army, 312, loc, 0) == OldStockInventoryBase &&
           SendCommandA(army, 312, loc, 3) == OldStockInventoryQuantity)
        {
            string title = SendCommandA(army, 312, loc, 7);
            message = OldShopItemTitle(title)+"  x"+itoa(OldStockInventoryQuantity)+" — выбрано для продажи";
        }
        else message = "Состав инвентаря изменился. Выберите вещь снова.";
    }
    if(hovered >= 0)
    {
        int base = OldStockShopVisibleIds[hovered];
        string title = SendCommandA(0, 303, base, 7);
        message = OldShopItemTitle(title)+"  В наличии: "+itoa(SendCommandA(0, 303, base, 3));
    }
    if(OldStockShopHit("OSC_CAT6", x, y, 20, 11)) message = "Покупка имплантов пока недоступна.";
    if(OldShopLastTime[army] && GetTime()-OldShopLastTime[army] < 2500)
    {
        if(OldShopLastResult[army] > 0 && OldShopLastOp[army] <= 3) message = "Операция выполнена.";
        if(OldShopLastResult[army] == 0) message = OldShopRefusalText(OldShopLastOp[army]);
        if(OldShopLastResult[army] < 0) message = "Операция отклонена. Выберите вещь снова.";
    }
    if(OldShopLocalQueueResult == -6) message = "Перенос отклонён: проверьте место, требования и деньги.";
    if(OldShopLocalQueueResult == -7) message = "Предмет или цена изменились. Выберите снова.";
    if(OldInventoryDragActive)
    {
        message = "Сюда перенести нельзя. Esc — отменить.";
        if(OldInventoryDragAllowed)
        {
            message = "Отпустите кнопку для переноса.";
            if(OldInventoryDragKind == 2) message = "Купить за "+itoa(OldInventoryDragPrice)+" $ — отпустите кнопку.";
            else if(OldInventoryDragTarget == 2097152)
            {
                int loc = OldStockInventoryLocator;
                int price = OldShopSaleQuote(SendCommandA(army,312,loc,4), OldStockInventoryQuantity, SendCommandA(army,312,loc,2), 1);
                message = "Продать всю стопку за "+itoa(price)+" $ — отпустите кнопку.";
            }
        }
    }
    if(SendCommandA(army, 326)) message = "Ожидание подтверждения...";
    if(SendCommandA(0, 327)) message = "Нет подтверждения сетевой операции.";
    if(OldStockShopResult != 1) message = "Не удалось открыть магазин. Закройте панель.";
    OldShopSetText(27, message);
    if(!OldStockShopRefreshAt || GetTime()-OldStockShopRefreshAt >= 250)
    {
        OldStockShopRefreshAt = GetTime();
        for(i = 0; i < OldStockShopVisibleCount; i++)
        {
            int base = OldStockShopVisibleIds[i];
            int stock = SendCommandA(0, 303, base, 3);
            int selected = !OldStockShopOwned && (base == OldStockShopSelected[0] || base == OldStockShopSelected[1]);
            OldUiTone(OldStockShopIcons[i], stock > 0, selected);
            string quantity = itoa(stock);
            Action(OldStockShopCounts[i], ACT_SET_TEXT, &quantity);
        }
    }
}
'''


def prepare(old_root: Path, helper: str, previous: dict,
            files: dict[str, bytes]) -> tuple[str, dict[str, bytes], dict]:
    helper = _text(helper)
    if _sha(helper) != previous['helper_output_sha256']:
        raise ValueError('Expected exact original inventory predecessor')
    raw = (Path(old_root) / 'Maps/inventory_shop.men').read_bytes()
    layout = named_layout(raw)
    helper = once(helper, 'OldInventoryDragShopArea(int x, int y) { return 0; }', '')
    helper = once(helper, 'OldShopClearPanel()\n{',
                  'OldStockShopClose();\n\nOldShopClearPanel()\n{\n    OldStockShopClose();')
    helper = once(helper, 'OldShopLocalPanel()\n{', SCRIPT.strip()+'\n\nOldShopLocalPanel()\n{')
    marker = '    if(OldShopVisible && OldShopVisible != mode) OldShopClearPanel();'
    helper = once(helper, marker, marker+'\n    if(mode == 1)\n    {\n'
                  '        OldStockShopTact(army, key, click, inventory_edge, development_edge);\n'
                  '        return;\n    }')
    output_files = dict(files)
    output_files[MENU] = layout
    hashes = {path: sha(data) for path, data in sorted(output_files.items())}
    helper_hash = _sha(helper)
    combined = sha(json.dumps(dict(helper=helper_hash, assets=hashes), sort_keys=True).encode())
    metadata = dict(previous, feature=FEATURE, inventory_feature=previous['feature'],
        input_sha256=previous['output_sha256'], output_sha256=combined,
        helper_output_sha256=helper_hash, files=hashes,
        source_hashes=dict(previous['source_hashes'], **{'Maps/inventory_shop.men': SHOP_SHA}),
        original_shop_geometry_unchanged=True, original_shop_control_names_added=True,
        shop_catalog_presentation='Read-only native menu VID/direction and Size; 6x7 grid, original anchors, 37px cells, matching ammo tray.',
        native_shop_handlers_enabled=False, shop_drag_drop=True,
        shop_buy_destination='Chosen backpack cell/stack or empty/mergeable compatible equipment slot',
        shop_drag_sale='Whole selected stack through opcode3; unit-sale button unchanged',
        catalog_refresh='Redraw after either peer ACK; preserve page, selection and finite stock; defer during a drag/pending request',
        catalog_hit_test='Same visible base-ID rectangles for clicks, tooltips and drag quotes',
        action_captions='Literal text without stock script-variable binding; original button animation states',
        panel_status='Original inventory, character and shop layouts with synchronized transactions.',
        pending=['purchase over unrelated occupied equipment', 'stack splitting', 'ground drops', 'tooltip paging', 'journal/menu tabs', 'skill drafts/refunds',
                 'implants/repair/buyback'],
        runtime_compiled=False, runtime_visual_tested=False)
    return helper, output_files, metadata
