"""Original inventory presentation over the campaign's acknowledged commands.

The shipped .men and native container renderer own layout, icons and quantities.
Only local input translation is new. Never enter the single-player menu/pause,
PD draft or native drag handlers. The common shop is still a separate adapter.
"""
from __future__ import annotations

import json
from pathlib import Path

from old_native_campaign_stock_ui import sha, once
from old_native_campaign_hud import _sha, _text
from old_native_campaign_drag import SCRIPT as DRAG_SCRIPT

FEATURE = 'old-native-campaign-stock-inventory-v4'
INVENTORY_SHA = '97dced6b072041c475ee6c82ea719416e36d382224c6fea737aaae11a3afc0b0'

SCRIPT = r'''
// Native containers draw the real local inventory. Selection is a locator,
// never a native item pointer or a pending native drag operation.
static int OldStockInventoryShown = 0;
static int OldStockInventoryResult = 0;
static int OldStockInventoryLocator = -1;
static int OldStockInventoryBase = 0;
static int OldStockInventoryQuantity = 0;
static int OldStockInventoryClickTime = 0;
static int OldStockInventorySeenRequests = -1;
static int OldStockInventoryRefreshAt = 0;
static int OldStockInfoKind = 0;
static int OldStockInfoItem = -1;
static int OldStockInfoSince = 0;
static int OldStockInfoRefresh = 0;
static int OldStockInfoVisible = 0;
static int OldStockInfoResult = 0;
OldInventoryDragCancel();
OldInventoryDragReset(int army);

OldStockInventoryRefresh(int army)
{
    // Requests advances at the acknowledged apply, never at mouse release.
    // Also refresh occasionally for world pickups/ammo/condition changes.
    if(OldStockInventorySeenRequests == OldShopRequests[army] &&
       GetTime()-OldStockInventoryRefreshAt < 250) return;
    OldStockInventorySeenRequests = OldShopRequests[army];
    OldStockInventoryRefreshAt = GetTime();
    SendCommandA(army, 318, 2);
}

OldStockItemInfoClear(int army)
{
    if(OldStockInfoVisible) SendCommandA(army, 338);
    OldStockInfoKind = 0;
    OldStockInfoItem = -1;
    OldStockInfoVisible = 0;
    OldStockInfoRefresh = 0;
}

// Shared by native owned grids and the shared shop catalog. The native window
// supplies every label, requirement, condition and value; no copied stat table.
// kind 1 = stable owned locator, kind 2 = catalog base ID.
OldStockItemInfo(int army, int kind, int item, int x, int y)
{
    if(item < 0 || !kind || SendCommandA(army, 326))
    {
        OldStockItemInfoClear(army);
        return;
    }
    if(kind != OldStockInfoKind || item != OldStockInfoItem)
    {
        OldStockItemInfoClear(army);
        OldStockInfoKind = kind;
        OldStockInfoItem = item;
        OldStockInfoSince = GetTime();
    }
    // Original hover delay is 1500 ms. Limit native text rebuilding while the
    // world continues to run and item condition/ammunition can change.
    if(GetTime() - OldStockInfoSince < 1500) return;
    if(OldStockInfoRefresh && GetTime() - OldStockInfoRefresh < 250) return;
    OldStockInfoRefresh = GetTime();
    if(kind == 1) OldStockInfoResult = SendCommandA(army, 336, item, x, y);
    else OldStockInfoResult = SendCommandA(army, 337, item, x, y);
    if(OldStockInfoResult == 1) OldStockInfoVisible = 1;
    else OldStockItemInfoClear(army);
}

OldStockInventoryClose()
{
    if(!OldStockInventoryShown) return;
    OldInventoryDragCancel();
    int army = NetProperty(NET_N_LOCAL_PLAYER);
    OldStockItemInfoClear(army);
    SendCommandA(army, 318, 0);
    MenuRelease("maps\\inventory.men");
    Genocide(2230);
    OldStockInventoryShown = 0;
    OldStockInventoryLocator = -1;
    OldStockInventoryBase = 0;
}

OldStockInventoryCreate(int army, int mode)
{
    OldInventoryDragReset(army);
    MenuLoad("maps\\inventory.men");
    // Ground pickup and the journal/options/shop tabs need their own adapters.
    // Do not present active controls that still have single-player handlers.
    int spr = MenuFindNamed("INV_GRND");
    if(spr) Destroy(spr);
    spr = MenuFind(2224, 999999);
    if(spr) Action(spr, ACT_SET_INVISIBLE, 1);
    spr = MenuFindNamed("MT_LOGSMENU");
    if(spr) Action(spr, ACT_SET_INVISIBLE, 1);
    spr = MenuFindNamed("MT_SHOPMENU");
    if(spr) Action(spr, ACT_SET_INVISIBLE, 1);
    spr = MenuFindNamed("MT_PAUSEMENU");
    if(spr) Action(spr, ACT_SET_INVISIBLE, 1);
    AllignInventory();
    // Only presentation routines; ControlCharScreen would also process PD drafts.
    SearchForSkillLines();
    SearchForSkillScrolls();
    SearchForTexts();
    ControlHeroFace();
    int perk = SendCommandA(army, EXT_GETPERKSKILL) - RPGHERO_PERK_HEALING;
    MenuAction(713, 999999, ACT_CHANGE_DIRECTION, SendCommand(EXT_GETABSDIR, 713, perk));
    OldStockInventoryResult = SendCommandA(army, 318, 1);
    OldStockInventorySeenRequests = OldShopRequests[army];
    OldStockInventoryRefreshAt = GetTime();
    OldStockInventoryShown = 1;
    OldStockInventoryLocator = -1;
    OldStockInventoryBase = 0;
    OldShopVisible = mode;
    OldShopLocalQueueResult = 0;
    OldShopText(27, 8, ScreenX()/2, ScreenY()/2 + 258, "", BEH_CENTER_X);
    OldShopText(28, 8, ScreenX()/2, ScreenY()/2 + 278,
        "Перетаскивание — перенос. Двойной щелчок — надеть/снять. E / R / U. Esc — отмена/выход.", BEH_CENTER_X);
}

OldStockInventorySelect(int army, int locator)
{
    OldStockInventoryLocator = locator;
    OldStockInventoryBase = SendCommandA(army, 312, locator, 0);
    OldStockInventoryQuantity = SendCommandA(army, 312, locator, 3);
}

OldStockInventoryQueue(int army, int op)
{
    if(SendCommandA(army, 326)) return;
    int locator = OldStockInventoryLocator;
    if(locator < 0 || OldStockInventoryBase <= 0 || OldStockInventoryQuantity <= 0) return;
    // Keep the selection's original quote. Another action cannot silently turn
    // a stale selection into an operation on the next item occupying that cell.
    if(SendCommandA(army, 312, locator, 0) != OldStockInventoryBase ||
       SendCommandA(army, 312, locator, 3) != OldStockInventoryQuantity)
    {
        OldShopLocalQueueResult = -7;
        OldStockInventoryLocator = -1;
        return;
    }
    if(SendCommandA(army, 312, locator, op + 6) != 1)
    {
        OldShopLocalQueueResult = -6;
        return;
    }
    OldShopLocalQueueResult = OldShopQueue(op, locator, OldStockInventoryBase, OldStockInventoryQuantity);
}

@@DRAG_SCRIPT@@

OldStockInventoryTact(int army, int mode, int key, int click, int inv_edge, int dev_edge)
{
    if(!OldShopVisible) OldStockInventoryCreate(army, mode);
    OldStockInventoryRefresh(army);
    int edge = key && key != OldShopLastUIKey;
    int mouse_edge = click && !OldShopLastUIClick;
    OldShopLastUIKey = key;
    OldShopLastUIClick = click;
    int x = SendCommandA(army, 329, IA_SCREEN_MOUSE_X);
    int y = SendCommandA(army, 329, IA_SCREEN_MOUSE_Y);
    if(inv_edge || dev_edge || (edge && key == VK_ESCAPE))
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
    int close = MenuFindNamed("INV_BTN_CLOSE");
    int close_x = ToScreenX(GetX(close));
    int close_y = ToScreenY(GetY(close), GetZ(close));
    if(mouse_edge && close &&
       x >= close_x - 60 && x <= close_x + 60 &&
       y >= close_y - 16 && y <= close_y + 16)
    {
        if(OldInventoryDragArmed)
        {
            OldInventoryDragCancel();
            OldStockInventoryClickTime = 0;
            return;
        }
        OldInventoryDragCancel();
        OldShopLocalQueueResult = OldShopQueue(4, 0, 0, 0);
        return;
    }
    int hovered = SendCommandA(army, 319, x, y);
    int was_dragging = OldInventoryDragArmed;
    OldInventoryDragTact(army, SendCommandA(army, 329, IM_LBUTTONDOWN), hovered, x, y);
    if(was_dragging) mouse_edge = 0;
    if(!OldInventoryDragArmed) OldStockItemInfo(army, 1, hovered, x, y);
    if(!OldInventoryDragArmed && edge)
    {
        if(key == 69 || key == 101) OldStockInventoryQueue(army, 6);
        if(key == 82 || key == 114) OldStockInventoryQueue(army, 7);
        if(key == 85 || key == 117) OldStockInventoryQueue(army, 8);
    }
    // The original plus/minus art indicates only immediately available increases.
    // A minus never creates a local draft or refunds already committed points.
    for(int i = 0; i < CS_TEXTSCNT; i++)
    {
        int btn = SkillScrolls[i];
        if(btn)
        {
            int skill = GetSkillFromBtnNum(i);
            int enabled = 0;
            if(skill >= 1 && skill <= 11)
                enabled = SendCommandA(army, 330, skill, 4) == 1;
            Action(btn, ACT_CHANGE_DIRECTION, SendCommand(EXT_GETABSDIR, 719, enabled));
            int bx = ToScreenX(GetX(btn));
            int by = ToScreenY(GetY(btn), GetZ(btn));
            if(!OldInventoryDragArmed && mouse_edge && enabled && x > bx && x <= bx + 17 && y >= by - 8 && y <= by + 8
                && !SendCommandA(army, 326))
            {
                int base = SendCommandA(army, 330, skill, 0);
                int points = SendCommandA(army, 330, skill, 2);
                OldShopLocalQueueResult = OldShopQueue(10, skill, base, points);
            }
        }
    }
    ControlSkillLines();
    ControlTexts();
    string message = "Игра продолжается. Повышение характеристики применяется сразу.";
    int selected = OldStockInventoryLocator;
    if(hovered >= 0) selected = hovered;
    if(selected >= 0)
    {
        int base = SendCommandA(army, 312, selected, 0);
        int quantity = SendCommandA(army, 312, selected, 3);
        if(base > 0 && quantity > 0)
        {
            string item_key = SendCommandA(army, 312, selected, 7);
            message = OldShopItemTitle(item_key) + " x" + itoa(quantity);
        }
    }
    if(OldShopLocalQueueResult == -7) message = "Предмет изменился. Выберите его снова.";
    if(OldShopLocalQueueResult == -6) message = "Это действие для выбранной вещи недоступно.";
    if(OldInventoryDragActive)
    {
        message = "Сюда перенести нельзя. Esc — отменить.";
        if(OldInventoryDragAllowed) message = "Отпустите кнопку для переноса. Esc — отменить.";
    }
    if(OldShopLastTime[army] && GetTime() - OldShopLastTime[army] < 2500 && OldShopLastOp[army] >= 6)
    {
        if(OldShopLastResult[army] == 0)
        {
            message = OldShopRefusalText(OldShopLastOp[army]);
            if(OldShopLastOp[army] == 11) message = "Перенос отклонён: проверьте место и требования вещи.";
        }
        if(OldShopLastResult[army] < 0) message = "Операция отклонена (" + itoa(OldShopLastResult[army]) + "). Выберите вещь снова.";
    }
    if(SendCommandA(army, 326)) message = "Ожидание подтверждения...";
    if(SendCommandA(0, 327)) message = "Нет подтверждения сетевой операции.";
    if(OldStockInventoryResult != 1) message = "Ошибка открытия инвентаря (" + itoa(OldStockInventoryResult) + "). Закройте панель.";
    OldShopSetText(27, message);
}
'''.replace('@@DRAG_SCRIPT@@', DRAG_SCRIPT.strip())


def prepare(old_root: Path, helper: str, previous: dict,
            files: dict[str, bytes]) -> tuple[str, dict[str, bytes], dict]:
    helper = _text(helper)
    if _sha(helper) != previous['helper_output_sha256']:
        raise ValueError('Expected exact original HUD predecessor')
    raw = (Path(old_root) / 'Maps/inventory.men').read_bytes()
    if sha(raw) != INVENTORY_SHA:
        raise ValueError('Unsupported original inventory resource')
    helper = once(helper, 'OldShopClearPanel()\n{',
                  'OldStockInventoryClose();\n\nOldShopClearPanel()\n{\n    OldStockInventoryClose();')
    helper = once(helper, 'OldShopLocalPanel()\n{', SCRIPT.strip() + '\n\nOldShopLocalPanel()\n{')
    marker = '    if(OldShopVisible && OldShopVisible != mode) OldShopClearPanel();'
    helper = once(helper, marker, marker + '\n'
        '    if(mode == 2 || mode == 3)\n    {\n'
        '        OldStockInventoryTact(army, mode, key, click, inventory_edge, development_edge);\n'
        '        return;\n    }')
    # Original inventory integrates both groups of controls in a single screen.
    # Either synchronized personal mode authorizes the same guarded operations.
    for name, alternate in (('OldInventoryOpen', 'OldDevelopmentOpen'),
                            ('OldDevelopmentOpen', 'OldInventoryOpen')):
        helper = once(helper,
            f'if(!{name}[army] || OldInventoryFault || !OldInventoryCanUse(army)) result = -21;',
            f'if((!{name}[army] && !{alternate}[army]) || OldInventoryFault || !OldInventoryCanUse(army)) result = -21;')
    output_files = dict(files)
    output_files['Maps/inventory.men'] = raw
    hashes = {path: sha(data) for path, data in sorted(output_files.items())}
    helper_hash = _sha(helper)
    combined = sha(json.dumps(dict(helper=helper_hash, assets=hashes), sort_keys=True).encode())
    metadata = dict(previous, feature=FEATURE, hud_feature=previous['feature'],
        input_sha256=previous['output_sha256'], output_sha256=combined,
        helper_output_sha256=helper_hash, files=hashes,
        source_hashes=dict(previous['source_hashes'], **{'Maps/inventory.men': INVENTORY_SHA}),
        original_inventory_layout_unchanged=True, original_inventory_renderer=True,
        inventory_presentation_commands=[318, 319, 336, 337, 338, 340, 341],
        inventory_move_command=339, inventory_move_opcode=11,
        original_item_tooltips=True,
        live_grid_refresh='After acknowledged local commands and every 250 simulation ms for pickups/ammo/condition; native presentation only, no panel reopen.',
        native_inventory_handlers_enabled=False,
        controls='I/C original inventory and character; drag, swap and merge backpack items or compatible equipment; double click equip/unequip; E/R/U item actions; + commits one increase; Esc cancels drag/closes.',
        panel_status='Original inventory and character presentation; synchronized immediate transactions. Shop still uses the previous panel.',
        pending=['shop drag/drop', 'journal/menu tabs', 'skill drafts/refunds'],
        runtime_compiled=False, runtime_visual_tested=False)
    return helper, output_files, metadata
