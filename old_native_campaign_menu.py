"""Guarded in-game LAN campaign menus; no launch, process access or file writes.

The existing native lobby still owns hero exchange and its prepare/ack barrier.
This frontend adds human role selection and readiness in a separate menu map.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import struct
from old_native_campaign_creation import STOCK_HASHES as CREATION_HASHES


FEATURE = 'old-native-campaign-menu-v11-connected-retry'
LOBBY_PATH = 'Maps/old_campaign_lobby.lgc'
MAP_PATH = 'Maps/old_campaign_lobby.map'
MAIN_PATH = 'Maps/mainmenu.lgc'
MENU_PATH = 'Maps/mainmenu.men'
BASE_LOBBY_SHA256 = 'e3c13991bb7a085202b1911688b31a4378e77d2debc6c4cddd672023c99f4a2d'
STOCK_HASHES = {
    **CREATION_HASHES,
    MAIN_PATH: '235408606e11710fec2662406201987449cfb56ccf170636a51877cd282b83fc',
    'Maps/mainmenu.men': '5705f36427522c242c49a46ddfb342638c40cb52c681b0c552fc0b931ffc3b1c',
    'Maps/netmenu.lgc': '22cc243cd7a163de0366136058bf9d51bb1fd57ba521a5f70f8af0c00d46ce4a',
    'Maps/netselectgame.men': 'eb4c9853658d9d3cda6964a0256564bb9c7a7ea1e401b4296ccca127d412dcf3',
    'Maps/shop.map': '8e157cc6c8fbe2c71644b71e8d32d8c3047c92422fc771fff5c5e0ef2ea09b87',
}


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _text(value: bytes | str) -> str:
    if isinstance(value, bytes):
        value = value.decode('cp1251')
    if not isinstance(value, str):
        raise TypeError('Expected campaign lobby text or immutable script bytes')
    return value.replace('\r\n', '\n')


def _encode(value: str) -> bytes:
    return value.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251')


def _once(source: str, before: str, after: str) -> str:
    if source.count(before) != 1:
        raise ValueError('Campaign menu source guard differs: ' + before[:80])
    return source.replace(before, after, 1)


def _function(source: str, name: str) -> tuple[int, int]:
    """Find a complete stock function, ignoring braces in comments/strings."""
    match = re.search(r'^' + re.escape(name) + r'\([^\n]*\)\s*\n\{', source, re.M)
    if match is None:
        raise ValueError('Missing guarded lobby function: ' + name)
    token = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[{}]', re.S)
    depth = 0
    for item in token.finditer(source, match.end() - 1):
        if item.group() == '{':
            depth += 1
        elif item.group() == '}':
            depth -= 1
            if depth == 0:
                return match.start(), item.end()
    raise ValueError('Unterminated guarded lobby function: ' + name)


def _replace_function(source: str, name: str, replacement: str) -> str:
    start, end = _function(source, name)
    return source[:start] + replacement + source[end:]


CAPTION = r'''
OldCampaignCaption(int button, int font, string label)
{
    if(!button) return;
    int text = MenuFind(font, 999999, ToScreenX(GetX(button)),
        ToScreenY(GetY(button), GetZ(button)));
    if(text) Action(text, ACT_SET_TEXT, &label);
}
'''

DECLARATIONS = r'''
static int OldMenuHost = 0;
static int OldMenuInitialized = 0;
static int OldMenuReady = 0;
static int OldMenuStartRequested = 0;
static int OldMenuRoster = -1;
static int OldMenuSelection = -1;
static int OldMenuSessionCount = 0;
static int OldMenuSessionIndex[14];
static int OldMenuNextSearch = 0;
static int OldMenuSearchTime = 0;
static int OldMenuPaintedSelection = -2;
static int OldMenuConnectTime = 0;
static int OldMenuConnectionSeen = 0;
static int OldMenuStatus = 0;
static int OldMenuDetails = 0;
static int OldMenuClearResult = -999;
static string OldMenuAddress = "";
static string OldMenuSelectedHost = "";
static string OldMenuReadySignature = "";
static string OldMenuHumanReady[8];
static int OldMenuButtonStates[3];
static string OldMenuButtonLabels[3];
'''

UI = r'''
OldMenuSessionMatches(string label)
{
    // NET_GAME_LIST is hostname/session + "  <ping>ms <players>/6",
    // not the raw session name. Keep an exact match after removing decoration.
    return StrBefore(StrAfter(label, "/"), "  ") == OLD_GAME_SESSION;
}

OldMenuRow(int row, string label)
{
    int sprite = MenuFind(5, 999001 + row);
    Action(sprite, ACT_SET_BEHAVE, Action(sprite, ACT_GET_BEHAVE) & ~BEH_LOAD_FROM);
    Action(sprite, ACT_SET_TEXT, &label);
}

OldMenuButton(int slot, string name, int enabled, string label)
{
    int button = MenuFindNamed(name);
    if(!button) return;
    // Captions have stable names, including mutually exclusive primary buttons
    // at the same position. Nearest-font lookup can bind the other caption.
    int caption = MenuFindNamed(name + "Text");
    // Restart the native sprite stack only when availability changes.
    // Otherwise its normal hover/press animation must run uninterrupted.
    if(OldMenuButtonStates[slot] != enabled + 1)
    {
        OldMenuButtonStates[slot] = enabled + 1;
        if(enabled)
        {
            Action(button, ANI_MENUSTAND);
            Action(button, ACT_SET_GAMMA, 0);
            Action(caption, ACT_SET_GAMMA, 0);
        }
        else
        {
            Action(button, ANI_MENUDISABLE);
            // Original netselectgame.men disabled Join button/text gamma.
            Action(button, ACT_SET_GAMMA, 130);
            Action(caption, ACT_SET_GAMMA, 0x323232);
        }
    }
    if(OldMenuButtonLabels[slot] != label)
    {
        OldMenuButtonLabels[slot] = label;
        if(caption) Action(caption, ACT_SET_BEHAVE, Action(caption, ACT_GET_BEHAVE) & ~BEH_LOAD_FROM);
        Action(caption, ACT_SET_TEXT, &label);
    }
}

OldMenuLeave(int mainMenu)
{
    NetProperty(NET_DISCONNECT);
    NetProperty(NET_NETWORK_OFF);
    MenuRelease();
    if(mainMenu) Load("maps\\mainmenu.map");
    else Load("maps\\old_campaign_lobby.map");
}

OldMenuSearch()
{
    if(GetTime() < OldMenuNextSearch) return;
    NetProperty(NET_GAME_FIND_HOSTS, OldMenuAddress);
    OldGameSearchCount++;
    OldMenuSelection = -1;
    OldMenuSelectedHost = "";
    OldMenuSessionCount = 0;
    OldMenuStatus = 1;
    OldMenuSearchTime = GetTime();
    OldMenuNextSearch = OldMenuSearchTime + 1000;
}

OldMenuList()
{
    int count = NetProperty(NET_NO_GAME);
    if(count > 128) count = 128;
    OldMenuSessionCount = 0;
    OldMenuSelection = -1;
    string label;
    for(int index = 0; index < count && OldMenuSessionCount < 14; index++)
        if(OldMenuSessionMatches(NetProperty(NET_GAME_LIST, itoa(index))))
        {
            label = NetProperty(NET_GAME_LIST, itoa(index));
            OldMenuSessionIndex[OldMenuSessionCount] = index;
            OldMenuRow(OldMenuSessionCount, StrBefore(label, "/"));
            if(OldMenuSelectedHost != "" && StrBefore(label, "  ") == OldMenuSelectedHost)
                OldMenuSelection = OldMenuSessionCount;
            OldMenuSessionCount++;
        }
    for(int row = OldMenuSessionCount; row < 14; row++) OldMenuRow(row, "");
    if(OldMenuPaintedSelection != OldMenuSelection)
    {
        OldMenuPaintedSelection = OldMenuSelection;
        MenuAction(98, 999999, ANI_STAND);
        if(OldMenuSelection >= 0)
            MenuAction(98, 999000 + OldMenuSelection, ANI_MENUSTANDUP);
    }
    if(OldMenuStatus == 1 && GetTime() - OldMenuSearchTime >= 3000) OldMenuStatus = 2;
    string detail = "Выберите игру\nв списке слева.";
    if(OldMenuSelection >= 0)
    {
        detail = "Игроки в кампании\n\n" + NetProperty(NET_PLAYER_LIST_IN_HOST,
            itoa(OldMenuSessionIndex[OldMenuSelection])) + "\n\nНажмите Подключиться,\nчтобы присоединиться.";
    }
    else if(OldMenuStatus == 1 && !OldMenuSessionCount)
        detail = "Поиск по локальной сети.\n\nПодождите несколько\nсекунд.";
    else if(!OldMenuSessionCount)
        detail = "ИГРЫ НЕ НАЙДЕНЫ\n\nНапарник должен\nсоздать кампанию.\nЗатем повторите поиск.\n\nМожно указать адрес IP\nего компьютера.";
    else
        detail = "Найдено игр: " + itoa(OldMenuSessionCount) + "\n\nВыберите кампанию\nв списке слева.";
    Action(OldMenuDetails, ACT_SET_TEXT, &detail);
    OldMenuButton(0, "StartButton", 1, "Создать");
    OldMenuButton(1, "JoinButton", OldMenuSelection >= 0, "Подключиться");
    string search = "Поиск";
    if(OldMenuStatus == 1) search = "Поиск...";
    OldMenuButton(2, "SearchButton", GetTime() >= OldMenuNextSearch, search);
}

OldMenuConnect(int host)
{
    if(!host && (OldMenuSelection < 0 || OldMenuSelection >= OldMenuSessionCount)) return;
    if(!host && !OldMenuSessionMatches(NetProperty(NET_GAME_LIST,
        itoa(OldMenuSessionIndex[OldMenuSelection]))))
    {
        OldMenuSelection = -1;
        return;
    }
    if(!host && StrBefore(NetProperty(NET_GAME_LIST,
        itoa(OldMenuSessionIndex[OldMenuSelection])), "  ") != OldMenuSelectedHost)
    {
        OldMenuSelection = -1;
        return;
    }
    OldMenuHost = host;
    SendCommand(EXT_ReloadDB);
    SendCommand(EXT_ResetAllQuests);
    SendCommandA(-1, EXT_SetPlayerMenuType, 0);
    OldGameHeroBase = SendCommandC(EXT_GetIdByName, "Char1");
    OldGameColor = 1 - OLD_GAME_HOST;
    if(OldGameHeroBase <= 0) { OldGameStage = 95; return; }
    if(host)
    {
        for(int setting = 0; setting < 5; setting++) OldGameSettings[setting] = 1;
        OldGameCreateRet = NetProperty(NET_CREATE, OLD_GAME_SESSION);
        if(OldGameCreateRet) { OldGameStage = 90; return; }
    }
    else
    {
        OldGameJoinRet = NetProperty(NET_JOIN, itoa(OldMenuSessionIndex[OldMenuSelection]));
        if(OldGameJoinRet) { OldGameStage = 92; return; }
    }
    NetProperty(NET_SET_PLAYER_NAME, PlayerName);
    OldMenuConnectTime = GetTime();
    OldMenuConnectionSeen = 0;
    OldGameStage = 3;
    OldMenuSelection = -1;
    MenuAction(98, 999999, ANI_MENUDISABLE);
    MenuAction(718, 999064, ANI_MENUDISABLE);
    string address = "Сетевая кампания";
    Action(MenuFindNamed("HostAddr"), ACT_SET_TEXT, &address);
}

OldMenuConnectionReady()
{
    if(OldGameConnected && OldGamePlayers > 0
        && OldGameLocalArmy >= 0 && OldGameLocalArmy < 8)
    {
        OldMenuConnectionSeen = 1;
        return true;
    }
    if(OldMenuConnectionSeen) OldGameStage = 96;
    else if(GetTime() - OldMenuConnectTime >= 15000) OldGameStage = 97;
    return false;
}

OldMenuCheckRoster()
{
    int roster = 0;
    int army;
    for(army = 0; army < 8; army++)
        if(NetProperty(NET_IS_PLAYER_EXIST + army)) roster = roster | (1 << army);
    if(roster != OldMenuRoster)
    {
        OldMenuRoster = roster;
        OldMenuReady = 0;
        OldMenuStartRequested = 0;
        OldMenuReadySignature = "";
        OldGamePrepare = "";
        OldGamePrepareTime = 0;
        for(army = 0; army < 8; army++)
        {
            OldMenuHumanReady[army] = "";
            OldGameReady[army] = "";
            OldGameAck[army] = "";
            OldGameHeroSeen[army] = army == OldGameLocalArmy;
            OldGameColorSeen[army] = army == OldGameLocalArmy;
        }
    }
    if((roster & ~9) || (OLD_GAME_HOST && OldGameLocalArmy != 0)
        || (!OLD_GAME_HOST && OldGameLocalArmy != 3)) OldGameStage = 93;
}

OldMenuBothReady()
{
    return OldMenuReady && OldGameSignature != ""
        && OldMenuReadySignature == OldGameSignature
        && OldMenuHumanReady[0] == OldGameSignature
        && OldMenuHumanReady[3] == OldGameSignature;
}

OldMenuPlayerState(int army)
{
    if(!NetProperty(NET_IS_PLAYER_EXIST + army)) return "Ожидание подключения";
    return "Подключение...";
}

OldMenuWaiting()
{
    for(int row = 0; row < 14; row++) OldMenuRow(row, "");
    string hostName = NetProperty(NET_PLAYER_NAME);
    OldBrowserWaiting("Подключение");
    string guestName = NetProperty(NET_PLAYER_NAME + 3);
    if(OLD_GAME_HOST) hostName = hostName + " (вы)";
    else guestName = guestName + " (вы)";
    OldMenuRow(1, "ХОСТ");
    OldMenuRow(2, hostName);
    OldMenuRow(3, OldMenuPlayerState(0));
    OldMenuRow(6, "НАПАРНИК");
    if(NetProperty(NET_IS_PLAYER_EXIST + 3))
        OldMenuRow(7, guestName);
    OldMenuRow(8, OldMenuPlayerState(3));
    OldMenuRow(11, "Игроков: " + itoa(OldGamePlayers) + " / 2");
    string detail = "Ожидание напарника.\n\nВторой игрок выбирает\nвашу кампанию в сети\nи подключается.";
    if(!OldMenuConnectionSeen) detail = "ПОДКЛЮЧЕНИЕ...\n\nПодождите немного.\nОтмена — вернуться\nк списку кампаний.";
    if(OldGamePlayers == 2)
    {
        detail = "ПОДГОТОВКА ИГРЫ...\n\nПодождите немного.";
        if(OldMenuStartRequested || (OldGameSignature != "" && OldGamePrepare == OldGameSignature))
            detail = "ЗАПУСК КАМПАНИИ...\n\nЗагрузка начнется\nу обоих игроков.";
    }
    if(OldGameStage >= 90)
    {
        OldBrowserHeading("Ошибка соединения");
        detail = "Не удалось подключиться.\nНажмите Отмена\nи повторите поиск.";
        if(OldGameStage == 90) detail = "Не удалось создать игру.\nНажмите Отмена\nи попробуйте снова.";
        if(OldGameStage == 93) detail = "Состав сессии изменился.\nКампания рассчитана\nровно на двух игроков.\nНажмите Отмена.";
        if(OldGameStage == 94) detail = "Несовместимые настройки.\nОбоим игрокам нужна\nодна версия мода.\nНажмите Отмена.";
        if(OldGameStage == 96) detail = "Соединение разорвано.\nНажмите Отмена\nдля нового подключения.";
        if(OldGameStage == 97) detail = "Хост не ответил вовремя.\nНажмите Отмена\nи повторите подключение.";
        if(OldGameStage == 98) detail = "Не удалось согласовать\nперсонажей.\nНажмите Отмена\nи создайте игру снова.";
    }
    Action(OldMenuDetails, ACT_SET_TEXT, &detail);
}

main()
{
    OldGameFrame++;
    if(!OldMenuInitialized)
    {
        OldMenuInitialized = 1;
        SetMapTypeEx(MAP_TYPE_PLAYERMENU, "");
        SetCursor(CURSOR_NORMAL);
        SetScrollType(SCROLL_NONE);
        GetUserName();
        GameType = 1;
        NetProperty(NET_NETWORK_ON);
        MenuLoad("maps\\netselectgame.men");
        OldMenuClearResult = SendCommandA(0, 345); // Native windows outside .men.
        Effect(EFF_FADE_OUT, 0, 0, FADE_GAME_TIME);
        int title = MenuFind(8);
        OldMenuDetails = MenuFind(3, 999999, ToScreenX(GetX(title)), ToScreenY(GetY(title), GetZ(title)));
        string heading = "Кампания по LAN";
        Action(title, ACT_SET_TEXT, &heading);
        OldMenuSearch();
        OldMenuList();
    }
    if(OldGameStage == 7) return;
    CommonTact();
    if(EditStringFlag)
    {
        if(EditStringTact())
        {
            OldMenuAddress = EditString;
            OldMenuNextSearch = 0;
            OldMenuSearch();
        }
        return;
    }
    int clicked = MenuLClick();
    if(GetKey() == VK_ESCAPE || (clicked && clicked == MenuFindNamed("ExitButton")))
    { OldMenuLeave(1); return; }
    if(OldGameStage == 0)
    {
        if(clicked && clicked == MenuFindNamed("SearchButton")) OldMenuSearch();
        else if(clicked && clicked == MenuFindNamed("StartButton")) OldMenuConnect(1);
        else if(clicked && clicked == MenuFindNamed("JoinButton")) OldMenuConnect(0);
        else if(clicked && GetVid(clicked) == 718 && GetDirection(clicked) == 64)
            EditStringStart(OldMenuAddress, 63, MenuFindNamed("HostAddr"));
        else if(clicked && GetVid(clicked) == 98 && GetDirection(clicked) < OldMenuSessionCount)
        {
            OldMenuSelection = GetDirection(clicked);
            OldMenuSelectedHost = StrBefore(NetProperty(NET_GAME_LIST,
                itoa(OldMenuSessionIndex[OldMenuSelection])), "  ");
        }
        if(OldGameStage == 0 && (clicked || OldGameFrame % 8 == 0)) OldMenuList();
    }
    else
    {
        if(clicked && clicked == MenuFindNamed("SearchButton"))
        { OldMenuLeave(0); return; }
        OldGameRefresh();
        if(OldGameStage >= 3 && OldGameStage <= 6)
        {
            if(OldMenuConnectionReady())
            {
                if((OLD_GAME_HOST && !NetProperty(NET_IS_HOST))
                    || (!OLD_GAME_HOST && NetProperty(NET_IS_HOST)))
                { OldGameStage = 93; OldMenuWaiting(); return; }
                OldGameLocalHero();
                OldMenuCheckRoster();
                if(OldGameStage < 90)
                {
                    OldGameReceive();
                    if(OldGameStage >= 90) { OldMenuWaiting(); return; }
                    OldGameSignature = OldGameMakeSignature();
                    if(OldMenuReady && OldMenuReadySignature != OldGameSignature)
                    {
                        OldMenuReady = 0;
                        OldMenuStartRequested = 0;
                    }
                    int preparing = OldMenuStartRequested || (OldGameSignature != "" && OldGamePrepare == OldGameSignature);
                    if(clicked && clicked == MenuFindNamed("StartButton")
                        && OldGameSignature != "" && !preparing)
                    {
                        OldMenuReady = !OldMenuReady;
                        OldMenuReadySignature = OldGameSignature;
                        if(OldMenuReady) OldMenuHumanReady[OldGameLocalArmy] = OldGameSignature;
                        else OldMenuHumanReady[OldGameLocalArmy] = "0";
                        NetSend(18, OldMenuHumanReady[OldGameLocalArmy]);
                    }
                    if(clicked && clicked == MenuFindNamed("JoinButton")
                        && OLD_GAME_HOST && OldMenuBothReady() && !preparing)
                        OldMenuStartRequested = 1;
                    if(OldGameFrame % 20 == 0)
                    {
                        OldGamePublish();
                        if(OldMenuReady) NetSend(18, OldGameSignature);
                        else NetSend(18, "0");
                    }
                    OldGameBarrier();
                }
            }
        }
        if(OldGameStage == 7) return;
        if(clicked || OldGameFrame % 8 == 0) OldMenuWaiting();
    }
    if(OldGameFrame % 60 == 0) OldGameWriteState();
}
'''


def _mainmenu(source: str) -> str:
    source = _once(source, 'MainMenuBaseLoad()\n{', CAPTION + '\nMainMenuBaseLoad()\n{')
    source = _once(source, '    MenuLoad("maps\\\\mainmenu.men");',
                   '    MenuLoad("maps\\\\mainmenu.men");\n'
                   '    SendCommandA(0, 345); // Native item windows have their own lifetime.\n'
                   '    OldCampaignCaption(MenuFindNamed("GOTO_MULTIPLAYER"), 3, "Сетевая кампания");')
    source = _once(source, '            ret = MENU_PERKSCREEN;', '            ret = -1; // Single-player starts are unavailable in this campaign copy.')
    source = _once(source, '            ret = MENU_SURVIVE;', '            ret = -1; // Use the original game for survival.')
    source = _once(source, 'bool bShowMenCont = GetReg( GetDefaultRegPath(), "bShowMenContOnMainMenu", 0 );',
                   'bool bShowMenCont = false; // No unsupported single-player resume in this copy.')
    source = _once(source, 'Load( "maps\\\\netmenu.map" );', 'Load( "maps\\\\old_campaign_lobby.map" );')
    return source


def _mainmenu_layout(source: bytes) -> bytes:
    """Keep stock graphics and handlers, with five supported menu actions.

    Each caption moves by its button's delta, retaining its original offset,
    font, depth and alignment. Profile name and background records are intact.
    """
    if _sha(source) != STOCK_HASHES[MENU_PATH]:
        raise ValueError('Unsupported original main menu layout')
    if source[:4] != b'RES ' or source[8:12] != b'MENU':
        raise ValueError('Main menu container differs')
    cursor = 12
    chunks = []
    while cursor < len(source):
        size = struct.unpack_from('<I', source, cursor + 4)[0]
        end = cursor + 8 + size
        if end > len(source):
            raise ValueError('Main menu chunk exceeds file')
        chunks.append((source[cursor:cursor + 4], source[cursor + 8:end]))
        cursor = end
    if [tag for tag, _ in chunks] != [b'HEAD', b'SPR ']:
        raise ValueError('Main menu chunks differ')
    payload = chunks[1][1]
    marker, flags, count = struct.unpack_from('<III', payload)
    if (marker, flags, count) != (0x80000000, 0, 20):
        raise ValueError('Main menu sprite layout differs')
    cursor = 12
    records = []
    for _ in range(count):
        size = struct.unpack_from('<I', payload, cursor)[0]
        cursor += 4
        record = payload[cursor:cursor + size]
        if len(record) != size:
            raise ValueError('Main menu sprite exceeds block')
        records.append(record)
        cursor += size
    if cursor != len(payload) or records[-1] != b'\xff\xff\xff\xff':
        raise ValueError('Main menu sprite terminator differs')

    def key(record):
        if len(record) <= 60:
            return None
        parts = record[60:].split(b'\0')
        if parts[0]:
            return parts[0].decode('ascii')
        if len(parts) > 1 and parts[1]:
            return '$' + parts[1].decode('ascii')
        return None

    index = {key(record): record for record in records if key(record)}
    removed = {'GOTO_CAMPAIGN', '$Play', 'GOTO_SURVIVE', '$Survive',
               'GOTO_HALLOFFAME', '$FameHall'}
    rows = (('GOTO_MULTIPLAYER', '$Network', 410), ('GOTO_OPTIONS', '$Options', 445),
            ('GOTO_PROFSEL', '$EditLogName', 480), ('GOTO_CREDITS', '$Credits', 515),
            ('GOTO_EXIT', '$Exit', 550))
    required = removed | {name for button, caption, _ in rows for name in (button, caption)}
    if not required <= index.keys():
        raise ValueError('Main menu buttons or captions differ')
    moves = {}
    for button, caption, row in rows:
        if struct.unpack_from('<I', index[button], 4)[0] != 705:
            raise ValueError('Main menu button graphic differs')
        if struct.unpack_from('<I', index[caption], 4)[0] != 3:
            raise ValueError('Main menu caption font differs')
        y, z = struct.unpack_from('<ff', index[button], 12)
        moves[button] = moves[caption] = row - (y - z)
    result = []
    for record in records:
        name = key(record)
        if name in removed:
            continue
        if name in moves:
            record = bytearray(record)
            y = struct.unpack_from('<f', record, 12)[0]
            struct.pack_into('<f', record, 12, y + moves[name])
            record = bytes(record)
        result.append(record)
    payload = struct.pack('<III', marker, flags, len(result))
    payload += b''.join(struct.pack('<I', len(record)) + record for record in result)
    body = b'MENU' + b'HEAD' + struct.pack('<I', len(chunks[0][1])) + chunks[0][1]
    body += b'SPR ' + struct.pack('<I', len(payload)) + payload
    return b'RES ' + struct.pack('<I', len(body)) + body


def _lobby(source: str, session_name: str, stock_netmenu: str) -> str:
    source = re.sub(r'^#define OLD_GAME_HOST [01]$', '#define OLD_GAME_HOST OldMenuHost', source, count=1, flags=re.M)
    source = source.replace(session_name, session_name + '_CREATE2')
    source = _once(source, 'static int OldGameFrame = 0;', DECLARATIONS + '\nstatic int OldGameFrame = 0;')
    source = _once(source, '    OldGameValue(file, "end_frame", OldGameFrame);',
                   '    OldGameValue(file, "discovered_games", NetProperty(NET_NO_GAME));\n'
                   '    OldGameValue(file, "compatible_games", OldMenuSessionCount);\n'
                   '    OldGameValue(file, "search_attempts", OldGameSearchCount);\n'
                   '    FWrite(file, "search_address=" + OldMenuAddress);\n'
                   '    FWrite(file, "first_discovery_label=" + NetProperty(NET_GAME_LIST, "0"));\n'
                   '    OldGameValue(file, "end_frame", OldGameFrame);')
    source = _replace_function(source, 'OldGameFind', '')
    source = _replace_function(source, 'OldGameDiscover', '')
    source = _once(source, '        if((message = NetReceive(16, army)) != "")',
                   '        if((message = NetReceive(18, army)) != "")\n'
                   '            OldMenuHumanReady[army] = message;\n'
                   '        if((message = NetReceive(16, army)) != "")')
    source = _once(source, '    if(OldGamePlayers != 2 || NetPlCnt != 2)',
                   '    if(!NetProperty(NET_IS_PLAYER_EXIST) || !NetProperty(NET_IS_PLAYER_EXIST + 3)) return "";\n'
                   '    if(OldGamePlayers != 2 || NetPlCnt != 2)')
    source = _once(source, '    OldGameStage = 4;\n    if(OldGameFrame % 20 == 0)',
                   '    if(!OldMenuReady || OldMenuReadySignature != OldGameSignature) return;\n'
                   '    OldGameStage = 4;\n    if(OldGameFrame % 20 == 0)')
    source = _once(source, '    int army;\n    for(army = 0; army < 8; army++)',
                   '    if(!OldMenuStartRequested) return;\n'
                   '    if(OldMenuHumanReady[0] != OldGameSignature || OldMenuHumanReady[3] != OldGameSignature) return;\n'
                   '    int army;\n    for(army = 0; army < 8; army++)')
    declarations = ('int EditStringFlag = 0;\nint EditStringSprite;\nint EditStringLength;\n'
                    'string EditStringOldName;\nstring EditString;\n')
    editing = []
    for name in ('EditStringStart', 'EditStringTact'):
        start, end = _function(stock_netmenu, name)
        editing.append(stock_netmenu[start:end])
    source = _replace_function(source, 'main', declarations + '\n' + '\n\n'.join(editing) + CAPTION + UI)
    from old_native_campaign_creation import compose
    from old_native_campaign_checkpoint import compose as checkpoint_compose
    from old_native_campaign_browser import compose as browser_compose
    from old_native_lobby_transport import compose as transport_compose
    return transport_compose(browser_compose(checkpoint_compose(compose(source)))).replace('_CREATE2', '_SAVE1')


def prepare(old_root: Path, campaign_lobby_source: bytes | str, session_name: str) -> tuple[dict[str, bytes], dict]:
    """Return composed scripts/menu assets plus hashes; never mutate the old game."""
    if not isinstance(session_name, str) or not re.fullmatch(r'AS2_CAMPAIGN_[0-9a-f]{12}', session_name):
        raise ValueError('Expected the resolved production campaign session identity')
    old_root = Path(old_root)
    assets = {}
    for path, digest in STOCK_HASHES.items():
        raw = (old_root / path).read_bytes()
        if _sha(raw) != digest:
            raise ValueError('Unsupported original campaign menu asset: ' + path)
        assets[path] = raw
    base = (Path(__file__).parent / 'templates/old_game_lobby.lgc').read_bytes()
    if _sha(base) != BASE_LOBBY_SHA256:
        raise ValueError('Unsupported original native lobby/barrier source')
    source = _text(campaign_lobby_source)
    role = re.findall(r'^#define OLD_GAME_HOST ([01])$', source, re.M)
    if len(role) != 1:
        raise ValueError('Expected one original auto-lobby role definition')
    expected = _text(base).replace('#define OLD_GAME_HOST 1', '#define OLD_GAME_HOST ' + role[0])
    expected = expected.replace('maps\\\\cooperative\\\\cooperative.map', 'maps\\\\Level_01.map')
    expected = expected.replace('"CharSurv1"', '"Char1"').replace('EXT_SetPlayerMenuType, 1', 'EXT_SetPlayerMenuType, 0')
    expected = expected.replace('AS2_OLD_GAME_PROBE', session_name)
    expected = expected.replace('SendCommand(EXT_ReloadDB);', 'SendCommand(EXT_ReloadDB);\n        SendCommand(EXT_ResetAllQuests);')
    if source != expected:
        raise ValueError('Campaign lobby differs from the guarded production composition')
    files = {
        MAIN_PATH: _encode(_mainmenu(_text(assets[MAIN_PATH]))),
        MENU_PATH: _mainmenu_layout(assets[MENU_PATH]),
        MAP_PATH: assets['Maps/shop.map'],
        LOBBY_PATH: _encode(_lobby(source, session_name, _text(assets['Maps/netmenu.lgc']))),
    }
    from old_native_campaign_checkpoint import HELPER_PATH, HELPER
    files[HELPER_PATH] = _encode(HELPER)
    from old_native_campaign_menu_layout import prepare as browser_layout
    files['Maps/old_campaign_browser.men'] = browser_layout(old_root)
    from old_native_campaign_creation import charscreen, invulnerability, starting_inventory
    files['Maps/common_charscreen.lgc'] = _encode(charscreen(_text(assets['Maps/common_charscreen.lgc'])))
    files['Maps/util_invuln.lgc'] = _encode(invulnerability(_text(assets['Maps/util_invuln.lgc'])))
    files['Weapon.cfg'] = _encode(starting_inventory(_text(assets['Weapon.cfg'])))
    from old_native_campaign_retry import prepare as prepare_retry
    retry_files, retry_metadata = prepare_retry(files)
    files.update(retry_files)
    from old_native_lobby_transport import metadata as transport_metadata
    metadata = {
        'feature': FEATURE, 'session_name': session_name,
        'effective_session_name': session_name + '_SAVE1',
        'entry_map': 'maps\\mainmenu.map', 'lobby_map': 'maps\\old_campaign_lobby.map',
        'input_lobby_sha256': _sha(_encode(source)), 'base_lobby_sha256': BASE_LOBBY_SHA256,
        'original_assets': dict(STOCK_HASHES),
        'files': {name: {'sha256': _sha(value), 'size': len(value)} for name, value in files.items()},
        'armies': [0, 3], 'players': 2, 'manual_role_selection': True,
        'existing_barrier_channels': [16, 17],
        'lobby_transport': transport_metadata(),
        'connected_retry': retry_metadata,
        'manual_host_start_required': False, 'native_directplay_unchanged': True,
        'character_creation': {'stock_screens': ['perk.men', 'createplayer.men'],
                               'confirmed_draft_channel': 19, 'host_test_health_channel': 18,
                               'duplicates_allowed': True, 'auto_start_when_both_confirmed': True,
                               'starting_implant_seeds': {'Char4': 10004, 'Char5': 10005, 'Char7': 10007},
                               'native_pd_replay_and_result_barrier': True},
        'creation_perk_scope': 'Per-player native descriptor, no registry-wide mutation during replay',
        'native_menu_item_cleanup': 'Release independent parameter-menu item windows and hide native inventory on menu entry/confirmation',
        'creation_agreement_timeout_ms': 20000,
        'discovery_label_format': 'hostname/session  <ping>ms <players>/6[ err]',
        'discovery_match': 'exact session name extracted from the native display label',
        'join_target': 'selected native discovery index, rechecked before joining',
        'connection_wait_ms': 15000,
        'button_states': 'native hover/press, transition-only enable/disable, dimmed unavailable captions',
        'per_player_ready_status': True, 'host_only_start_caption': False,
        'search_feedback_ms': 3000, 'search_retry_cooldown_ms': 1000,
        'selection_identity': 'hostname/session retained across native discovery index reorder',
        'stock_menu_binary_unchanged': False, 'stock_lan_menu_binary_unchanged': True,
        'stock_profile_creation_preserved': True,
        'mainmenu_layout': {'actions': ['network_campaign', 'options', 'profile', 'credits', 'exit'],
                            'rows_at_800x600': [410, 445, 480, 515, 550],
                            'removed': ['singleplayer', 'survival', 'hall_of_fame'],
                            'original_graphics_and_caption_offsets_preserved': True},
        'unsupported_singleplayer_starts_disabled': True, 'save_resume_or_level_selection': True,
        'checkpoints': 'In-game host selection, native heroes/quests, channel18 mode and channel19 transfer, autosave before onward load',
        'browser': {'views': ['new', 'saves', 'join'], 'save_page_size': 8,
                    'native_assets': True, 'selection_receipt_required': True,
                    'named_captions': True, 'context_primary_action': True,
                    'frame_scale': [1.25, 1], 'native_font_scale': 1,
                    'automatic_waiting_view': True},
        'build_role_does_not_select_ui_role': True, 'native_validation': 'pending',
    }
    return files, metadata
