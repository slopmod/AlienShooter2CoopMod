"""Pure guarded composition of campaign shop, inventory and development panels.

Input scripts are cp1251 bytes or Unicode text. Map/levels/name resources are
exact original bytes. Returns (level02, common, helper, metadata); writes no
files and starts no processes. Native backend300..317/330..331 and transport320..329
must be installed by the caller. The transport owns synchronized execution.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import struct

from old_native_level02_patch import MAP_SHA256, SHOP_GUARD
from old_native_quest_observer import SOURCE_SHA256 as LEVELS_SHA256

FEATURE = 'old-native-campaign-shop-scripts-v6'
LEVEL_INPUT_SHA256 = '12e2d17766d52d80d15c9d9f294d23f94f43b079b1c7dd70389352e0b758a16c'
COMMON_INPUT_SHA256 = '88d1dba25900cc1e26ae86586a907ed71869f1b4abb2b51c83c2e016106a1f89'
LEVEL01_INPUT_SHA256 = {
    'f419441874981c3033bfa64516e6f8a24a11fe44b0d74a95169ec7bb7a49bf24': 'campaign',
    '3e50af4d69a4c14931a141ed3276248c543fa24d5bba69940a165894113ad1a0': 'campaign+rat',
    '550b13ada5f71902a783ecf9d74ca5b3dcd822e1b5263fc9c1080d988f392a6e': 'campaign+transition',
    '533da82871f4dd40ab8b0c7bcdde061b00aed48be3adf6d259a53bf5c791aa78': 'campaign+transition+rat',
}
NAMES_SHA256 = '26cd4a181666d28611b8ea0267872f135c4512446462e884c3ddb74156a0240c'
HELPER_NAME = 'Maps/old_campaign_shop.lgc'
TRANSPORT_NAME = 'Maps/old_campaign_shop_transport.lgc'
OPEN_RADIUS, USE_RADIUS, REARM_RADIUS = 55, 90, 110
ROWS = 8


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _text(source):
    if isinstance(source, bytes):
        source = source.decode('cp1251')
    if not isinstance(source, str):
        raise TypeError('Expected cp1251 bytes or script text')
    return source.replace('\r\n', '\n')


def _script_hash(source):
    return _sha(_text(source).replace('\n', '\r\n').encode('cp1251'))


def _replace(text, marker, replacement):
    if text.count(marker) != 1:
        raise ValueError('Shop script anchor changed: ' + repr(marker[:100]))
    return text.replace(marker, replacement)


def _guard(data, expected, name):
    if not isinstance(data, bytes):
        raise TypeError('Expected original bytes: ' + name)
    if _sha(data) != expected:
        raise ValueError('Unsupported shop source: ' + name)


def _names(source):
    """First printable heading from each original Weapon text block."""
    result, key = {}, None
    for line in source.decode('cp1251').splitlines():
        line = line.strip()
        if line.startswith('<') and line.endswith('>'):
            candidate = line[1:-1]
            if '=' not in candidate:
                key = candidate
            continue
        if key and line:
            if key in result:
                raise ValueError('Duplicate native item text key: ' + key)
            result[key] = line.replace('"', "'").replace('\\', '/')[:54]
            key = None
    if not result or 'Ammo_pistol' not in result:
        raise ValueError('Native item names not found')
    return result


def _name_script(names):
    lines = ['OldShopItemTitle(string key)', '{']
    for key, title in sorted(names.items()):
        if any(c in key for c in ('"', '\\', '\n', '\r')):
            raise ValueError('Unsupported native item text key')
        lines.append(f'    if(key == "{key}") return "{title}";')
    lines += ['    return key;', '}', '']
    return '\n'.join(lines)


HELPER = r'''#ifndef OLD_CAMPAIGN_SHOP_H
#define OLD_CAMPAIGN_SHOP_H 1

// Shared fields. No presentation handle is consulted by these decisions.
static int OldLevel02ShopBlockedRequests = 0;
static int OldShopInitialized = 0;
static int OldShopInitResult = 0;
static int OldShopFault = 0;
static int OldInventoryInitResult = 0;
static int OldInventoryFault = 0;
static int OldShopOpen[4];
static int OldInventoryOpen[4];
static int OldDevelopmentOpen[4];
static int OldShopArmed[4];
static int OldShopRequests[4];
static int OldShopAccepted[4];
static int OldShopLastOp[4];
static int OldShopLastResult[4];
static int OldShopLastTime[4];

// Presentation-only state: each process displays only its own panel.
static int OldShopVisible = 0;
static int OldShopPanel[40];
static int OldShopBuyPage = 0;
static int OldShopSellPage = 0;
static int OldShopBuyRow = 0;
static int OldShopSellRow = 0;
static int OldShopSelectionSide = 0;
static int OldShopLastUIKey = 0;
static int OldShopLastUIClick = 0;
static int OldShopLocalQueueResult = 0;
static int OldShopFaultNotice = 0;
static int OldShopLastInventoryInput = 0;
static int OldInventoryLastQueuedOp = 0;
static int OldShopLastDevelopmentInput = 0;
static int OldDevelopmentRow = 0;
static int OldDevelopmentSkills[] = {2, 3, 5, 6, 1, 4, 7, 8, 9, 10, 11};
static string OldDevelopmentNames[] = {"Здоровье", "Сила", "Скорость", "Точность", "Интеллект",
    "Броня", "Пистолеты", "Дробовики", "Пулеметы", "Ракетницы", "Энерг. оружие"};

@@ITEM_NAMES@@

OldShopPartyArmy(int army)
{
    return army == 0 || army == 3;
}

OldShopStoryReady()
{
    // Guarded levels.cfg: IDs1_1_39/40 occupy insertion indices35/36.
    return (SendCommand(EXT_GETQUESTSSTATE, 0, 35) & QS_BEGUN)
        && (SendCommand(EXT_GETQUESTSSTATE, 0, 36) & QS_BEGUN);
}

OldInventoryMapChanging()
{
    // Stock Options uses these two local pseudo-loads without changing maps.
    // They must never close another hero's shared panel on only one peer.
    return StartNextMap && NextMapName != "options" && NextMapName != "game";
}

OldInventoryCanUse(int army)
{
    if(!OldShopPartyArmy(army) || !OldCampaignReady
        || giMapType != MAP_TYPE_LEVEL
        || GameState != GAME_NORMAL || OldInventoryMapChanging()
        || !NetProperty(NET_IS_CONNECT) || NetProperty(NET_NO_PLAYERS) != 2)
        return 0;
    string map = ToLower(GetMapName());
    if(!((giCurLevCmpgnReal == 1 && map == "maps\\level_01.map")
        || (giCurLevCmpgnReal == 2 && map == "maps\\level_02.map"))) return 0;
    int unit = Flagman(army);
    if(!unit || !IsCharacter(unit) || Action(unit, ACT_GET_HP) <= 0)
        return 0;
    return 1;
}

OldShopCanUse(int army, int radius)
{
    if(!OldInventoryCanUse(army) || giCurLevCmpgnReal != 2 || !OldShopStoryReady()) return 0;
    int unit = Flagman(army);
    if(Abs(GetZ(unit) - GetGroundZ(3665, 8506)) > 48)
        return 0;
    return SizeTo(unit, 3665, 8506) < radius;
}

OldShopClose(int army)
{
    if(!OldShopPartyArmy(army) || (!OldShopOpen[army] && !OldInventoryOpen[army] && !OldDevelopmentOpen[army])) return;
    OldShopOpen[army] = 0;
    OldInventoryOpen[army] = 0;
    OldDevelopmentOpen[army] = 0;
    // Never alter the other hero or invoke native shop/menu map-type changes.
    SetPlayerControl(army, PLAYERCONTROL_NORMAL);
}

OldCampaignShopApply(int army, int op, int a, int b, int c)
{
    if(!OldShopPartyArmy(army)) return -20;
    OldShopRequests[army]++;
    OldShopLastOp[army] = op;
    OldShopLastTime[army] = GetTime();
    int result = -20;
    if(op == 4)
    {
        // Closing is always safe, including after a lost range/death guard.
        OldShopClose(army);
        result = 1;
    }
    else if(op == 5)
    {
        if(OldInventoryFault || !OldInventoryCanUse(army)) result = -21;
        else if(OldShopOpen[army] || OldDevelopmentOpen[army]) result = -23;
        else
        {
            OldInventoryOpen[army] = 1;
            Action(Flagman(army), ACT_STOP, 1, 1);
            SetPlayerControl(army, PLAYERCONTROL_NONE);
            result = 1;
        }
    }
    else if(op >= 6 && op <= 8)
    {
        if(!OldInventoryOpen[army] || OldInventoryFault || !OldInventoryCanUse(army)) result = -21;
        else if(op == 6) result = SendCommandA(army, 315, a, b, c);
        else if(op == 7) result = SendCommandA(army, 316, a, b, c);
        else if(op == 8) result = SendCommandA(army, 317, a, b, c);
    }
    else if(op == 9)
    {
        if(OldInventoryFault || !OldInventoryCanUse(army)) result = -21;
        else if(OldShopOpen[army] || OldInventoryOpen[army]) result = -23;
        else
        {
            OldDevelopmentOpen[army] = 1;
            Action(Flagman(army), ACT_STOP, 1, 1);
            SetPlayerControl(army, PLAYERCONTROL_NONE);
            result = 1;
        }
    }
    else if(op == 10)
    {
        if(!OldDevelopmentOpen[army] || OldInventoryFault || !OldInventoryCanUse(army)) result = -21;
        else result = SendCommandA(army, 331, a, b, c);
    }
    else if(op == 11)
    {
        int access = (OldInventoryOpen[army] || OldDevelopmentOpen[army]) && OldInventoryCanUse(army);
        if(OldShopOpen[army] && OldShopCanUse(army, @@USE_RADIUS@@)) access = 1;
        if(!access || OldInventoryFault) result = -21;
        else result = SendCommandA(army, 339, a, b, c);
        if(result == -24) OldInventoryFault = 1;
    }
    else if(!OldShopOpen[army] || !OldShopCanUse(army, @@USE_RADIUS@@))
        result = -21;
    else if(OldShopFault || SendCommandA(0, 204) != 1)
        result = -22;
    else if(op == 1)
        result = SendCommandA(army, 304, a, b, c);
    else if(op == 2)
        result = SendCommandA(army, 313, a, b, c);
    else if(op == 3)
        result = SendCommandA(army, 314, a, b, c);
    else if(op == 12)
    {
        if(OldInventoryFault) result = -21;
        else result = SendCommandA(army, 342, a, b, c);
        if(result == -24) { OldInventoryFault = 1; OldShopFault = 1; }
    }
    OldShopLastResult[army] = result;
    // Buy returns an inventory bitmask; sell returns quantity sold.
    if(result > 0 && (op != 1 || (result & 1))) OldShopAccepted[army]++;
    return result;
}

// The transport resolves the complete shared callback above before UI callers.
#include "maps\old_campaign_shop_transport.lgc"

OldShopText(int index, int font, int x, int y, string text, int behavior = 0)
{
    OldShopPanel[index] = CreateText(font, x, y + 4000, 4000, text, behavior);
}

OldShopSetText(int index, string text)
{
    if(OldShopPanel[index]) Action(OldShopPanel[index], ACT_SET_TEXT, &text);
}

OldShopClearPanel()
{
    for(int i = 0; i < 40; i++)
    {
        if(OldShopPanel[i]) Destroy(OldShopPanel[i]);
        OldShopPanel[i] = 0;
    }
    OldShopVisible = 0;
}

OldInventoryCreatePanel()
{
    int x = ScreenX()/2 - 360;
    int y = ScreenY()/2 - 235;
    OldShopPanel[0] = MenuCreate(2221, 0, ScreenX()/2, ScreenY()/2, 3900);
    OldShopText(1, 4, ScreenX()/2, y, "ИНВЕНТАРЬ", BEH_CENTER_X);
    OldShopText(2, 3, x + 10, y + 30, "");
    OldShopText(3, 5, x + 10, y + 60, "ВАШИ ВЕЩИ");
    OldShopText(4, 5, x + 420, y + 60, "ВЫБРАННАЯ ВЕЩЬ");
    for(int row = 0; row < 8; row++)
        OldShopText(5 + row, 8, x + 10, y + 92 + row*34, "");
    OldShopText(13, 8, x + 420, y + 92, "");
    OldShopText(14, 8, x + 420, y + 132, "");
    OldShopText(15, 8, x + 420, y + 164, "");
    OldShopText(16, 8, x + 420, y + 208, "");
    OldShopText(17, 8, x + 420, y + 240, "");
    OldShopText(18, 8, x + 420, y + 272, "");
    OldShopText(21, 5, x + 10, y + 376, "< Назад       Далее >");
    OldShopText(23, 5, x + 85, y + 412, "Экипировать [E]", BEH_CENTER_X);
    OldShopText(24, 5, x + 270, y + 412, "Снять [R]", BEH_CENTER_X);
    OldShopText(25, 5, x + 460, y + 412, "Использовать [U]", BEH_CENTER_X);
    OldShopText(26, 5, x + 660, y + 412, "Закрыть [I]", BEH_CENTER_X);
    OldShopText(27, 3, x + 10, y + 446, "");
    OldShopText(28, 8, x + 10, y + 470, "Стрелки — выбор, PgUp/PgDn — страницы. I или Esc — закрыть.");
    OldShopText(29, 8, x + 10, y + 488, "Игра продолжается. Аптечки: U; развитие героя: C после закрытия.");
    OldShopVisible = 2;
}

OldDevelopmentCreatePanel()
{
    int x = ScreenX()/2 - 360;
    int y = ScreenY()/2 - 235;
    OldShopPanel[0] = MenuCreate(2221, 0, ScreenX()/2, ScreenY()/2, 3900);
    OldShopText(1, 4, ScreenX()/2, y, "РАЗВИТИЕ", BEH_CENTER_X);
    OldShopText(2, 3, x + 10, y + 30, "");
    OldShopText(3, 5, x + 10, y + 60, "ХАРАКТЕРИСТИКА");
    OldShopText(4, 5, x + 430, y + 60, "БАЗА / ИТОГ");
    for(int row = 0; row < 11; row++)
    {
        OldShopText(5 + row, 8, x + 10, y + 92 + row*26, "");
        OldShopText(16 + row, 8, x + 440, y + 92 + row*26, "");
    }
    OldShopText(32, 8, x + 10, y + 376, "");
    OldShopText(30, 5, x + 190, y + 412, "Повысить [Enter]", BEH_CENTER_X);
    OldShopText(31, 5, x + 630, y + 412, "Закрыть [C]", BEH_CENTER_X);
    OldShopText(27, 3, x + 10, y + 446, "");
    OldShopText(28, 8, x + 10, y + 470, "Стрелки — выбор, Enter — одно повышение. C или Esc — закрыть.");
    OldShopText(29, 8, x + 10, y + 488, "Очки тратятся сразу. Закрытие не отменяет повышение.");
    OldShopVisible = 3;
}

OldShopCreatePanel()
{
    int x = ScreenX()/2 - 360;
    int y = ScreenY()/2 - 235;
    // Original shop background art only; no native inventory/shop anchors.
    OldShopPanel[0] = MenuCreate(2221, 0, ScreenX()/2, ScreenY()/2, 3900);
    OldShopText(1, 4, ScreenX()/2, y, "МАГАЗИН", BEH_CENTER_X);
    OldShopText(2, 3, x + 10, y + 30, "");
    OldShopText(3, 5, x + 10, y + 60, "ТОВАРЫ");
    OldShopText(4, 5, x + 380, y + 60, "ВАШИ ВЕЩИ");
    for(int row = 0; row < 8; row++)
    {
        OldShopText(5 + row, 8, x + 10, y + 92 + row*34, "");
        OldShopText(13 + row, 8, x + 380, y + 92 + row*34, "");
    }
    OldShopText(21, 5, x + 10, y + 376, "< Назад       Далее >");
    OldShopText(22, 5, x + 380, y + 376, "< Назад       Далее >");
    OldShopText(23, 4, x + 80, y + 412, "Купить", BEH_CENTER_X);
    OldShopText(24, 4, x + 380, y + 412, "Продать", BEH_CENTER_X);
    OldShopText(25, 5, x + 510, y + 412, "Продать всё", BEH_CENTER_X);
    OldShopText(26, 4, x + 650, y + 412, "Закрыть", BEH_CENTER_X);
    OldShopText(27, 3, x + 10, y + 446, "");
    OldShopText(28, 8, x + 10, y + 470, "Tab — список, PgUp/PgDn — страницы, Enter — сделка, Esc — закрыть.");
    OldShopText(29, 8, x + 10, y + 488, "Импланты, ремонт и выкуп проданных вещей пока недоступны.");
    OldShopVisible = 1;
}

OldShopQueueBuy(int army)
{
    int row = OldShopBuyPage*8 + OldShopBuyRow;
    int count = SendCommandA(0, 301);
    if(row < 0 || row >= count) return;
    int base = SendCommandA(0, 302, row);
    int unit = SendCommandA(0, 303, base, 2);
    int price = SendCommandA(0, 303, base, 1);
    if(base <= 0 || unit <= 0 || price <= 0) return;
    OldShopLocalQueueResult = OldShopQueue(1, base, unit, price);
}

OldShopQueueSell(int army, int all)
{
    int row = OldShopSellPage*8 + OldShopSellRow;
    int count = SendCommandA(army, 310);
    if(row < 0 || row >= count) return;
    int locator = SendCommandA(army, 311, row);
    if(locator < 0 || SendCommandA(army, 312, locator, 11) != 1) return;
    int base = SendCommandA(army, 312, locator, 0);
    int quantity = SendCommandA(army, 312, locator, 3);
    if(base <= 0 || quantity <= 0) return;
    OldShopLocalQueueResult = OldShopQueue(2 + all, locator, base, quantity);
}

OldInventoryQueue(int army, int op)
{
    if(op < 6 || op > 8) return;
    int row = OldShopSellPage*8 + OldShopSellRow;
    int count = SendCommandA(army, 310);
    if(row < 0 || row >= count) return;
    int locator = SendCommandA(army, 311, row);
    int base = SendCommandA(army, 312, locator, 0);
    int quantity = SendCommandA(army, 312, locator, 3);
    OldInventoryLastQueuedOp = op;
    if(locator < 0 || base <= 0 || quantity <= 0)
    {
        OldShopLocalQueueResult = -5;
        return;
    }
    if(SendCommandA(army, 312, locator, op + 6) != 1)
    {
        OldShopLocalQueueResult = -6;
        return;
    }
    OldShopLocalQueueResult = OldShopQueue(op, locator, base, quantity);
}

OldShopRefusalText(int op)
{
    if(op == 10) return "Повышение недоступно: нет очков или достигнут предел.";
    if(op == 8) return "Аптечка не использована: здоровье полное или лечение недоступно.";
    if(op == 6) return "Не удалось экипировать: проверьте требования и свободное место.";
    if(op == 7) return "Не удалось снять: проверьте свободное место в рюкзаке.";
    return "Операция отклонена: проверьте деньги и место в рюкзаке.";
}

OldDevelopmentQueue(int army)
{
    if(OldDevelopmentRow < 0 || OldDevelopmentRow >= 11) return;
    int skill = OldDevelopmentSkills[OldDevelopmentRow];
    int base = SendCommandA(army, 330, skill, 0);
    int points = SendCommandA(army, 330, skill, 2);
    if(base < 0 || points < 0)
    {
        OldShopLocalQueueResult = -5;
        return;
    }
    // A visible limit/empty balance may still be requested once: the shared
    // native predicate explains refusal without spending or staging locally.
    OldShopLocalQueueResult = OldShopQueue(10, skill, base, points);
}

OldDevelopmentDraw(int army)
{
    if(OldDevelopmentRow < 0 || OldDevelopmentRow >= 11) OldDevelopmentRow = 0;
    for(int row = 0; row < 11; row++)
    {
        int skill = OldDevelopmentSkills[row];
        int base = SendCommandA(army, 330, skill, 0);
        int effective = SendCommandA(army, 330, skill, 1);
        string title = OldDevelopmentNames[row];
        if(row == OldDevelopmentRow) title = "> " + title;
        OldShopSetText(5 + row, title);
        if(base < 0 || effective < 0) OldShopSetText(16 + row, "Недоступно");
        else OldShopSetText(16 + row, itoa(base) + " / " + itoa(effective));
    }
    int selected = OldDevelopmentSkills[OldDevelopmentRow];
    int points = SendCommandA(army, 330, selected, 2);
    int cost = SendCommandA(army, 330, selected, 3);
    int available = SendCommandA(army, 330, selected, 4);
    int increment = SendCommandA(army, 330, selected, 5);
    int limit = SendCommandA(army, 330, selected, 6);
    if(points < 0) OldShopSetText(2, "Очки развития недоступны");
    else OldShopSetText(2, "Свободные очки: " + itoa(points));
    string detail = "Повышение недоступно";
    if(cost >= 0 && increment >= 0 && limit >= 0)
    {
        detail = "Прибавка: " + itoa(increment) + "   Стоимость: " + itoa(cost) + "   Предел: " + itoa(limit);
        if(available != 1) detail = detail + "   Недоступно";
    }
    OldShopSetText(32, detail);
    string message = "Выберите характеристику. Итог учитывает действующие бонусы.";
    if(OldShopLastTime[army] && OldShopLastOp[army] == 10)
    {
        int result = OldShopLastResult[army];
        if(result > 0) message = "Характеристика повышена.";
        else if(result == 0) message = OldShopRefusalText(10);
        else if(result == -7) message = "Значение или очки изменились. Повторите запрос.";
        else message = "Повышение отклонено (" + itoa(result) + ").";
    }
    if(OldShopLocalQueueResult == -5) message = "Данные героя недоступны. Повторите позже.";
    if(SendCommandA(army, 326)) message = "Ожидание подтверждения...";
    if(SendCommandA(0, 327)) message = "Нет подтверждения сетевой операции.";
    OldShopSetText(27, message);
}

OldInventoryDrawList(int army)
{
    int count = SendCommandA(army, 310);
    if(OldShopSellPage*8 >= count) OldShopSellPage = 0;
    if(OldShopSellPage*8 + OldShopSellRow >= count) OldShopSellRow = 0;
    int row, locator, quantity, slot;
    string title;
    for(int i = 0; i < 8; i++)
    {
        title = "";
        row = OldShopSellPage*8 + i;
        if(row < count)
        {
            locator = SendCommandA(army, 311, row);
            string key = SendCommandA(army, 312, locator, 7);
            quantity = SendCommandA(army, 312, locator, 3);
            slot = SendCommandA(army, 312, locator, 8);
            title = OldShopItemTitle(key) + " x" + itoa(quantity);
            if(slot) title = title + "\nЭкипировано";
            else title = title + "\nВ рюкзаке";
            if(i == OldShopSellRow) title = "> " + title;
        }
        OldShopSetText(5 + i, title);
    }
    for(int field = 13; field <= 18; field++) OldShopSetText(field, "");
    row = OldShopSellPage*8 + OldShopSellRow;
    if(row < count)
    {
        locator = SendCommandA(army, 311, row);
        string selected_key = SendCommandA(army, 312, locator, 7);
        OldShopSetText(13, OldShopItemTitle(selected_key));
        slot = SendCommandA(army, 312, locator, 8);
        if(slot) OldShopSetText(14, "Экипировано");
        else OldShopSetText(14, "В рюкзаке");
        OldShopSetText(15, "Количество: " + itoa(SendCommandA(army, 312, locator, 3)));
        OldShopSetText(16, "Экипировать: недоступно");
        OldShopSetText(17, "Снять: недоступно");
        OldShopSetText(18, "Использовать: недоступно");
        if(SendCommandA(army, 312, locator, 12) == 1) OldShopSetText(16, "Экипировать: E");
        if(SendCommandA(army, 312, locator, 13) == 1) OldShopSetText(17, "Снять: R");
        if(SendCommandA(army, 312, locator, 14) == 1) OldShopSetText(18, "Использовать: U");
    }
    int hero = SendCommandA(army, EXT_GETHEROID);
    OldShopSetText(2, "Общая касса: " + itoa(SendCommand(EXT_GETSKILL, hero, RPGHERO_MONEY)) + " $");
    string message = "Выберите вещь и действие. Магазин доступен только у прилавка.";
    if(OldShopLastTime[army] && OldShopLastOp[army] >= 6)
    {
        int result = OldShopLastResult[army];
        if(result > 0) message = "Готово.";
        else if(result == 0) message = OldShopRefusalText(OldShopLastOp[army]);
        else if(result == -7 || result == -5) message = "Вещь изменилась. Выберите её снова.";
        else if(result == -6) message = "Для этой вещи действие пока недоступно.";
        else message = "Действие отклонено (" + itoa(result) + ").";
    }
    if(OldShopLocalQueueResult == -6) message = "Для этой вещи действие пока недоступно.";
    else if(OldShopLocalQueueResult == -5) message = "Вещь больше недоступна. Выберите другую.";
    if(SendCommandA(army, 326)) message = "Ожидание подтверждения...";
    if(SendCommandA(0, 327)) message = "Нет подтверждения сетевой операции.";
    OldShopSetText(27, message);
}

OldShopSaleQuote(int price, int quantity, int unit, int all)
{
    if(price < 0 || quantity <= 0 || unit <= 0) return -1;
    int removed = quantity;
    if(!all && removed > unit) removed = unit;
    // Native sale credits the integer package price scaled by actual removal.
    return price*removed/unit;
}

OldShopDrawLists(int army)
{
    if(!OldShopSelectionSide)
    {
        OldShopSetText(3, "> ТОВАРЫ");
        OldShopSetText(4, "ВАШИ ВЕЩИ");
    }
    else
    {
        OldShopSetText(3, "ТОВАРЫ");
        OldShopSetText(4, "> ВАШИ ВЕЩИ");
    }
    int count_buy = SendCommandA(0, 301);
    int count_sell = SendCommandA(army, 310);
    if(OldShopBuyPage*8 >= count_buy) OldShopBuyPage = 0;
    if(OldShopSellPage*8 >= count_sell) OldShopSellPage = 0;
    if(OldShopBuyPage*8 + OldShopBuyRow >= count_buy) OldShopBuyRow = 0;
    if(OldShopSellPage*8 + OldShopSellRow >= count_sell) OldShopSellRow = 0;
    string title;
    int base, locator, quantity, price, row;
    for(int i = 0; i < 8; i++)
    {
        title = "";
        row = OldShopBuyPage*8 + i;
        if(row < count_buy)
        {
            base = SendCommandA(0, 302, row);
            string key_buy = SendCommandA(0, 303, base, 7);
            quantity = SendCommandA(0, 303, base, 2);
            price = SendCommandA(0, 303, base, 1);
            int stock = SendCommandA(0, 303, base, 3);
            title = OldShopItemTitle(key_buy) + "\n" + itoa(quantity)
                + " шт. / " + itoa(price) + " $   В наличии: " + itoa(stock);
            if(i == OldShopBuyRow) title = "> " + title;
        }
        OldShopSetText(5 + i, title);
        title = "";
        row = OldShopSellPage*8 + i;
        if(row < count_sell)
        {
            locator = SendCommandA(army, 311, row);
            string key_sell = SendCommandA(army, 312, locator, 7);
            quantity = SendCommandA(army, 312, locator, 3);
            price = SendCommandA(army, 312, locator, 4);
            int sell_unit = SendCommandA(army, 312, locator, 2);
            int slot = SendCommandA(army, 312, locator, 8);
            title = OldShopItemTitle(key_sell) + " x" + itoa(quantity);
            if(slot) title = title + " [экипировано]";
            if(SendCommandA(army, 312, locator, 11) == 1)
                title = title + "\nПродать: " + itoa(OldShopSaleQuote(price, quantity, sell_unit, 0))
                    + " $ / всё: " + itoa(OldShopSaleQuote(price, quantity, sell_unit, 1)) + " $";
            else title = title + "\nНе продаётся";
            if(i == OldShopSellRow) title = "> " + title;
        }
        OldShopSetText(13 + i, title);
    }
    int hero = SendCommandA(army, EXT_GETHEROID);
    int cash = SendCommand(EXT_GETSKILL, hero, RPGHERO_MONEY);
    OldShopSetText(2, "Общая касса: " + itoa(cash) + " $");
    string message = "Выберите товар или свою вещь.";
    if(OldShopLastTime[army])
    {
        int result = OldShopLastResult[army];
        if(result > 0 && (OldShopLastOp[army] != 1 || (result & 1))) message = "Готово.";
        else if(result == 0) message = OldShopRefusalText(OldShopLastOp[army]);
        else if(result == -21) message = "Подойдите к магазину живым героем.";
        else if(result == -22) message = "Общая касса недоступна.";
        else if(result == -7) message = "Цена или вещь изменились. Выберите её снова.";
        else if(result == -8) message = "Этот товар закончился.";
        else if(result == -5) message = "Вещь больше недоступна. Обновите выбор.";
        else if(result == -6) message = "Эта операция для вещи пока недоступна.";
        else message = "Операция отклонена (" + itoa(result) + "). Обновите выбор.";
    }
    if(SendCommandA(army, 326)) message = "Ожидание подтверждения...";
    if(SendCommandA(0, 327)) message = "Нет подтверждения сетевой операции.";
    OldShopSetText(27, message);
}

OldShopLocalPanel()
{
    int army = NetProperty(NET_N_LOCAL_PLAYER);
    if(!OldShopPartyArmy(army)) return;
    int transport_fault = SendCommandA(0, 327);
    if(!transport_fault) transport_fault = OldShopTransportError;
    if(transport_fault)
    {
        // A negative raw-input result is not a held key. Keep the transport
        // failed closed; release presentation only so Escape still works.
        OldShopLocalOpening = 0;
        OldShopLocalCapture = 0;
        SendCommandA(army, 328, 0);
        if(OldShopVisible) OldShopClearPanel();
        OldShopTransportReport(transport_fault);
        string failure = "Ошибка сети (" + itoa(transport_fault)
            + "). Esc — меню; перезапустите сессию.";
        if(!OldShopFaultNotice)
            OldShopFaultNotice = CreateText(3, ScreenX()/2, ScreenY() - 100 + 4000,
                4000, failure, BEH_CENTER_X);
        else Action(OldShopFaultNotice, ACT_SET_TEXT, &failure);
        return;
    }
    // The mapped action supports the configured binding; raw I supports the
    // ordinary key path as well, including deterministic input fixtures.
    int key = SendCommandA(army, 329, IA_KEY);
    int click = SendCommandA(army, 329, IM_LBUTTONCLICK);
    int inventory_input = SendCommandA(army, 329, IA_SHOW_INVENTORY) || key == 73 || key == 105;
    int inventory_edge = inventory_input && !OldShopLastInventoryInput;
    OldShopLastInventoryInput = inventory_input;
    int development_input = SendCommandA(army, 329, IA_SHOW_CHARSCREEN) || key == 67 || key == 99;
    int development_edge = development_input && !OldShopLastDevelopmentInput;
    OldShopLastDevelopmentInput = development_input;
    int mode = OldShopOpen[army];
    if(OldInventoryOpen[army]) mode = 2;
    if(OldDevelopmentOpen[army]) mode = 3;
    if(mode || !SendCommandA(army, 326)) OldShopLocalOpening = 0;
    string notice = "";
    if(OldShopFault && OldShopCanUse(army, @@OPEN_RADIUS@@))
        notice = "Магазин недоступен: ошибка подготовки товаров (" + itoa(OldShopInitResult) + ").";
    if(!mode && (OldShopLastOp[army] == 5 || OldShopLastOp[army] == 9) && OldShopLastResult[army] < 0
        && GetTime() - OldShopLastTime[army] < 3000)
        notice = "Панель недоступна: герой ещё не готов (" + itoa(OldShopLastResult[army]) + ").";
    if(notice != "")
    {
        if(!OldShopFaultNotice)
            OldShopFaultNotice = CreateText(3, ScreenX()/2, ScreenY() - 100 + 4000,
                4000, notice, BEH_CENTER_X);
        else Action(OldShopFaultNotice, ACT_SET_TEXT, &notice);
    }
    else if(OldShopFaultNotice)
    {
        Destroy(OldShopFaultNotice);
        OldShopFaultNotice = 0;
    }
    if(!mode)
    {
        if(inventory_edge && giMenuState == MT_NOMENU && OldInventoryCanUse(army))
        {
            OldShopLocalQueueResult = OldShopQueue(5, 0, 0, 0);
            if(OldShopLocalQueueResult > 0) OldShopLocalOpening = 1;
        }
        else if(development_edge && giMenuState == MT_NOMENU && OldInventoryCanUse(army))
        {
            OldShopLocalQueueResult = OldShopQueue(9, 0, 0, 0);
            if(OldShopLocalQueueResult > 0) OldShopLocalOpening = 1;
        }
        if(OldShopVisible) OldShopClearPanel();
        if(OldShopLocalCapture)
        {
            // Do not turn the close click or held Escape into a world action.
            if(SendCommandA(army, 329, IM_LBUTTONDOWN) || key == VK_ESCAPE || key == VK_RETURN
                || inventory_input || development_input || key == 69 || key == 101 || key == 82 || key == 114
                || key == 85 || key == 117) return;
            SendCommandA(army, 328, 0);
            OldShopLocalCapture = 0;
            SetCursor(CURSOR_ATTACK);
        }
        OldShopLastUIKey = key;
        OldShopLastUIClick = click;
        return;
    }
    // Let an already-open options window close normally before showing ours.
    if(giMenuState != MT_NOMENU) return;
    if(!OldShopLocalCapture)
    {
        SendCommandA(army, 328, 1);
        OldShopLocalCapture = 1;
        OldShopLastUIKey = key;
        OldShopLastUIClick = click;
        inventory_edge = 0;
        development_edge = 0;
        SetCursor(CURSOR_NORMAL);
    }
    if(OldShopVisible && OldShopVisible != mode) OldShopClearPanel();
    if(!OldShopVisible)
    {
        if(mode == 3)
        {
            OldDevelopmentRow = 0;
            OldShopLocalQueueResult = 0;
            OldDevelopmentCreatePanel();
        }
        else if(mode == 2)
        {
            OldShopSelectionSide = 1;
            OldShopSellPage = 0;
            OldShopSellRow = 0;
            OldShopLocalQueueResult = 0;
            OldInventoryCreatePanel();
        }
        else
        {
            OldShopSelectionSide = 0;
            OldShopCreatePanel();
        }
    }
    int edge = key && key != OldShopLastUIKey;
    int mouse_edge = click && !OldShopLastUIClick;
    OldShopLastUIKey = key;
    OldShopLastUIClick = click;
    if(inventory_edge || development_edge || (edge && key == VK_ESCAPE))
        OldShopLocalQueueResult = OldShopQueue(4, 0, 0, 0);
    else if(mode == 3 && edge && key == VK_RETURN) OldDevelopmentQueue(army);
    else if(mode == 3 && edge && (key == VK_UP || key == VK_DOWN))
    {
        int development_delta = 1;
        if(key == VK_UP) development_delta = -1;
        OldDevelopmentRow = (OldDevelopmentRow + development_delta + 11) % 11;
    }
    else if(mode == 2 && edge && (key == 69 || key == 101)) OldInventoryQueue(army, 6);
    else if(mode == 2 && edge && (key == 82 || key == 114)) OldInventoryQueue(army, 7);
    else if(mode == 2 && edge && (key == 85 || key == 117)) OldInventoryQueue(army, 8);
    else if(mode == 1 && edge && key == VK_RETURN)
    {
        if(!OldShopSelectionSide) OldShopQueueBuy(army);
        else OldShopQueueSell(army, 0);
    }
    else if(mode == 1 && edge && key == VK_TAB)
        OldShopSelectionSide = 1 - OldShopSelectionSide;
    else if(mode != 3 && edge && (key == VK_PRIOR || key == VK_NEXT))
    {
        if(mode == 1 && !OldShopSelectionSide)
        {
            if(key == VK_PRIOR && OldShopBuyPage) OldShopBuyPage--;
            if(key == VK_NEXT && (OldShopBuyPage + 1)*8 < SendCommandA(0, 301)) OldShopBuyPage++;
            OldShopBuyRow = 0;
        }
        else
        {
            if(key == VK_PRIOR && OldShopSellPage) OldShopSellPage--;
            if(key == VK_NEXT && (OldShopSellPage + 1)*8 < SendCommandA(army, 310)) OldShopSellPage++;
            OldShopSellRow = 0;
        }
    }
    else if(edge && (key == VK_UP || key == VK_DOWN))
    {
        int delta = 1;
        if(key == VK_UP) delta = -1;
        if(mode == 1 && !OldShopSelectionSide) OldShopBuyRow = (OldShopBuyRow + delta + 8) % 8;
        else OldShopSellRow = (OldShopSellRow + delta + 8) % 8;
    }
    if(mouse_edge)
    {
        int x = SendCommandA(army, 329, IA_SCREEN_MOUSE_X) - (ScreenX()/2 - 360);
        int y = SendCommandA(army, 329, IA_SCREEN_MOUSE_Y) - (ScreenY()/2 - 235);
        if(mode == 3)
        {
            if(y >= 85 && y < 85 + 11*26 && x >= 0 && x < 730)
                OldDevelopmentRow = (y - 85)/26;
            else if(y >= 400 && y < 440)
            {
                if(x >= 50 && x < 360) OldDevelopmentQueue(army);
                else if(x >= 545 && x < 730) OldShopLocalQueueResult = OldShopQueue(4, 0, 0, 0);
            }
        }
        else if(mode == 2)
        {
            if(y >= 85 && y < 85 + 8*34 && x >= 0 && x < 400)
                OldShopSellRow = (y - 85)/34;
            else if(y >= 366 && y < 399)
            {
                if(x >= 0 && x < 95 && OldShopSellPage) OldShopSellPage--;
                else if(x >= 95 && x < 240 && (OldShopSellPage + 1)*8 < SendCommandA(army, 310)) OldShopSellPage++;
            }
            else if(y >= 400 && y < 440)
            {
                if(x >= 0 && x < 180) OldInventoryQueue(army, 6);
                else if(x >= 190 && x < 350) OldInventoryQueue(army, 7);
                else if(x >= 360 && x < 560) OldInventoryQueue(army, 8);
                else if(x >= 585 && x < 730) OldShopLocalQueueResult = OldShopQueue(4, 0, 0, 0);
            }
        }
        else if(y >= 85 && y < 85 + 8*34)
        {
            int row = (y - 85)/34;
            if(x >= 0 && x < 350) { OldShopBuyRow = row; OldShopSelectionSide = 0; }
            if(x >= 370 && x < 730) { OldShopSellRow = row; OldShopSelectionSide = 1; }
        }
        else if(y >= 366 && y < 399)
        {
            if(x >= 0 && x < 95 && OldShopBuyPage) OldShopBuyPage--;
            else if(x >= 95 && x < 240 && (OldShopBuyPage + 1)*8 < SendCommandA(0, 301)) OldShopBuyPage++;
            else if(x >= 370 && x < 465 && OldShopSellPage) OldShopSellPage--;
            else if(x >= 465 && x < 620 && (OldShopSellPage + 1)*8 < SendCommandA(army, 310)) OldShopSellPage++;
        }
        else if(y >= 400 && y < 440)
        {
            if(x >= 0 && x < 170) OldShopQueueBuy(army);
            else if(x >= 300 && x < 450) OldShopQueueSell(army, 0);
            else if(x >= 450 && x < 575) OldShopQueueSell(army, 1);
            else if(x >= 585 && x < 730) OldShopLocalQueueResult = OldShopQueue(4, 0, 0, 0);
        }
    }
    if(mode == 3) OldDevelopmentDraw(army);
    else if(mode == 2) OldInventoryDrawList(army);
    else OldShopDrawLists(army);
}

OldCampaignShopTact()
{
    if(!OldShopInitialized)
    {
        OldShopInitialized = 1;
        OldShopArmed[0] = 1;
        OldShopArmed[3] = 1;
        OldShopTransportBegin(OldShopTransportEpoch());
        OldInventoryInitResult = SendCommandA(0, 305);
        if(OldInventoryInitResult != 1) OldInventoryFault = 1;
        // One shared construction; getters and local drawing never refresh stock.
        if(giCurLevCmpgnReal == 2)
        {
            OldShopInitResult = SendCommandA(0, 300);
            if(OldShopInitResult <= 0 || SendCommandA(0, 301) <= 0) OldShopFault = 1;
        }
    }
    for(int army = 0; army <= 3; army = army + 3)
    {
        if(OldShopOpen[army] && !OldShopCanUse(army, @@USE_RADIUS@@)) OldShopClose(army);
        if(OldInventoryOpen[army] && !OldInventoryCanUse(army)) OldShopClose(army);
        if(OldDevelopmentOpen[army] && !OldInventoryCanUse(army)) OldShopClose(army);
        int unit = Flagman(army);
        if(unit && SizeTo(unit, 3665, 8506) >= @@REARM_RADIUS@@) OldShopArmed[army] = 1;
        if(!OldShopOpen[army] && !OldInventoryOpen[army] && !OldDevelopmentOpen[army]
            && OldShopArmed[army] && !OldShopFault
            && OldShopCanUse(army, @@OPEN_RADIUS@@))
        {
            OldShopOpen[army] = 1;
            OldShopArmed[army] = 0;
            // NONE alone leaves a previous native movement command active.
            Action(unit, ACT_STOP, 1, 1);
            SetPlayerControl(army, PLAYERCONTROL_NONE);
        }
    }
    OldShopTransportTact();
    OldShopLocalPanel();
}
#endif
'''


def patch(map_source: bytes, generated_level02: str | bytes,
          shared_common_source: str | bytes, levels_cfg: bytes,
          weapon_text: bytes) -> tuple[str, str, str, dict]:
    """Return (Level_02.lgc, COMMON.LGC, helper, metadata); no side effects."""
    _guard(map_source, MAP_SHA256, 'Maps/Level_02.map')
    _guard(levels_cfg, LEVELS_SHA256, 'levels.cfg')
    _guard(weapon_text, NAMES_SHA256, 'Text/Weapon.txt')
    level, common = _text(generated_level02), _text(shared_common_source)
    if _script_hash(level) != LEVEL_INPUT_SHA256:
        raise ValueError('Expected exact generated normal Level02 entry')
    if _script_hash(common) != COMMON_INPUT_SHA256:
        raise ValueError('Expected exact shared-wallet COMMON source')
    for at, values in ((0xD729C, (43, 3665, 8506, 25)),
                       (0xD728C, (131, 6, 1, 0)),
                       (0xD6B5D, (78, 1, 39, 0)),
                       (0xD6D7C, (78, 1, 40, 0))):
        if struct.unpack_from('<4i', map_source, at) != values:
            raise ValueError('Original earned-shop trigger changed')
    quests = re.findall(r'^\s*Quest\s*=\s*(1_1_\d+)', levels_cfg.decode('cp1251'), re.M)
    if len(quests) != 97 or quests.index('1_1_39') != 35 or quests.index('1_1_40') != 36:
        raise ValueError('Earned-shop quest insertion order changed')
    names = _names(weapon_text)
    helper = HELPER.replace('@@ITEM_NAMES@@', _name_script(names))
    for key, value in (('OPEN_RADIUS', OPEN_RADIUS), ('USE_RADIUS', USE_RADIUS),
                       ('REARM_RADIUS', REARM_RADIUS)):
        helper = helper.replace('@@' + key + '@@', str(value))
    level = _replace(level, '#define OLD_LEVEL02_SHOP_GUARD 1',
                     '#define OLD_LEVEL02_SHOP_GUARD 1\n#define OLD_CAMPAIGN_SHOP_UI 1')
    level = _replace(level, SHOP_GUARD, '#include "maps\\old_campaign_shop.lgc"\n')
    level = _replace(level, '  // OLD_LEVEL02_TRANSITION_TACT_HOOK',
                     '  OldCampaignShopTact();\n  // OLD_LEVEL02_TRANSITION_TACT_HOOK')
    level = _replace(level, '  OldLevel02ShopGuard();',
                     '  // Original single-player Action6 must not open its local mutating UI.\n'
                     '  if(Action6 != -1) Action6 = -1;')
    common = ('#ifdef OLD_CAMPAIGN_SHOP_UI\nstatic int OldShopLocalCapture = 0;\n'
              'static int OldShopLocalOpening = 0;\n#endif\n' + common)
    menu_handlers = '''        InventoryTact();
        CharScreenTact();
        ControlShop();'''
    common = _replace(common, menu_handlers,
                      '#ifdef OLD_CAMPAIGN_SHOP_UI\n'
                      '        // Options stay available; local item/stat handlers stay disabled.\n'
                      '#else\n' + menu_handlers + '\n#endif')
    anchor = '''        bool bCanProcessEscape = true;
if(!bMenuPause )
        if( GameState == GAME_MISSION_FAILED || GlobalQuestFailed )
        	bCanProcessEscape = false;
		else
			bCanProcessEscape = InventoryTact();
        bool bCanProcessEscape2 = true;
if(!bMenuPause )
        bCanProcessEscape2 = CharScreenTact();'''
    replacement = '''        bool bCanProcessEscape = true;
        // Original inventory/character tacts open mutating local handlers.
        bool bOldShopCapture = OldShopLocalCapture != 0 || OldShopLocalOpening != 0
            || GetInputAction(IA_SHOW_INVENTORY) || GetInputAction(IA_SHOW_CHARSCREEN);
        if(GameState == GAME_MISSION_FAILED || GlobalQuestFailed) bCanProcessEscape = false;
        bool bCanProcessEscape2 = true;
        if(bOldShopCapture) { bCanProcessEscape = false; bCanProcessEscape2 = false; }'''
    common = _replace(common, anchor, '#ifdef OLD_CAMPAIGN_SHOP_UI\n' + replacement
                      + '\n#else\n' + anchor + '\n#endif')
    metadata = {
        'feature': FEATURE, 'physical_map': 'maps/level_02.map', 'personal_maps': [1, 2], 'armies': [0, 3],
        'source_sha256': {'Maps/Level_02.map': MAP_SHA256, 'generated_Level_02.lgc': LEVEL_INPUT_SHA256,
                          'shared_COMMON.LGC': COMMON_INPUT_SHA256, 'levels.cfg': LEVELS_SHA256,
                          'Text/Weapon.txt': NAMES_SHA256},
        'output_sha256': {'Maps/Level_02.lgc': _script_hash(level), 'Maps/COMMON.LGC': _script_hash(common),
                          HELPER_NAME: _script_hash(helper)},
        'helper': HELPER_NAME, 'transport_include': TRANSPORT_NAME,
        'native_backend_commands': list(range(300, 306)) + list(range(310, 318)) + [330, 331],
        'transport_commands': list(range(320, 330)),
        'apply': 'OldCampaignShopApply(army,op,a,b,c)', 'queue': 'OldShopQueue(op,a,b,c)',
        'ops': {'buy': 1, 'sell_unit': 2, 'sell_all': 3, 'close': 4,
                'open_inventory': 5, 'equip': 6, 'unequip': 7, 'use': 8,
                'open_development': 9, 'increase_skill': 10, 'move_item': 11, 'buy_at': 12},
        'shop_center': [3665, 8506], 'original_open_radius': 25,
        'party_open_radius': OPEN_RADIUS, 'use_radius': USE_RADIUS, 'rearm_radius': REARM_RADIUS,
        'same_floor_max_difference': 48, 'quest_indices': {'1_1_39': 35, '1_1_40': 36},
        'stock_init_policy': 'Shared EXT305 on both maps, EXT300 only Level02; never from a local getter/render path',
        'transport_epoch_policy': 'Shared physical-map ordinal before personal/stock initialization and first drain',
        'presentation': {'original_background_vid': 2221, 'fonts': [3, 4, 5, 8],
                         'rows_per_page': ROWS, 'localized_item_names': len(names),
                         'reference_resolution': [800, 600], 'mouse': True,
                         'keys': ['I', 'C', 'E', 'R', 'U', 'Tab', 'PgUp', 'PgDn', 'Up', 'Down', 'Enter', 'Esc'],
                         'inventory_mapped_input': 18, 'development_mapped_input': 19,
                         'development_rows': 11, 'browser': False},
        'control_policy': 'Shared NONE on open, NORMAL on close; local raw-input capture before sync',
        'open_movement_policy': 'Shared ACT_STOP(1,1) before NONE clears the previous native command',
        'sale_quote_policy': 'Integer native unit sale price * actual removed quantity / package unit',
        'map_type_pause_camera_changes': False, 'quest_grants_or_setters': False,
        'local_menu_pseudoloads_ignored_by_shared_access': ['options', 'game'],
        'item_grants_or_wallet_setters': False, 'local_click_mutates_shared_state': False,
        'equipment_use_support': 'Guarded EXT315/316/317; native props12/13/14 advertise supported actions',
        'development_skill_ids': [2, 3, 5, 6, 1, 4, 7, 8, 9, 10, 11],
        'development_properties': {'base': 0, 'effective': 1, 'unspent': 2, 'cost': 3,
                                   'can_increase': 4, 'increment': 5, 'limit': 6},
        'development_commit_policy': 'One native EXT331 increase immediately; expected base and points; no local drafts/rollback',
        'perk_development_supported': False,
        'random_implants_supported': False,
        'stock_inventory_handlers_disabled': True,
        'stock_character_handlers_disabled': True,
        'runtime_compile_tested': False, 'runtime_visual_tested': False,
    }
    return level, common, helper, metadata


def patch_level01(source: str | bytes) -> tuple[str, dict]:
    """Add the shared personal panel to one exact generated Level01 variant."""
    text = _text(source)
    before = _script_hash(text)
    if before not in LEVEL01_INPUT_SHA256:
        raise ValueError('Expected exact generated Level01 campaign script before personal panel')
    text = '#define OLD_CAMPAIGN_SHOP_UI 1\n' + text
    marker = '#include "maps\\old_campaign_finish.lgc"'
    text = _replace(text, marker, marker + '\n#include "maps\\old_campaign_shop.lgc"')
    marker = '  if(OldFinishTact()) return;'
    text = _replace(text, marker, marker + '\n  OldCampaignShopTact();\n  // OLD_LEVEL01_ITEMS_TACT_HOOK')
    return text, {'feature': FEATURE, 'physical_map': 'maps/level_01.map',
                  'input_variant': LEVEL01_INPUT_SHA256[before], 'input_sha256': before,
                  'output_sha256': _script_hash(text), 'helper': HELPER_NAME,
                  'tact_order': 'After Ready and OldFinishTact guard, before GameTact',
                  'optional_tact_marker': '// OLD_LEVEL01_ITEMS_TACT_HOOK',
                  'stock_shop_enabled': False, 'personal_inventory_enabled': True,
                  'personal_development_enabled': True}


def prepare(old_root: Path, generated_level02: str | bytes,
            shared_common_source: str | bytes):
    """Read only the pinned original resources, then compose with patch()."""
    old_root = Path(old_root)
    return patch((old_root / 'Maps/Level_02.map').read_bytes(), generated_level02,
                 shared_common_source, (old_root / 'levels.cfg').read_bytes(),
                 (old_root / 'Text/Weapon.txt').read_bytes())
