"""Stock character creation in the connected pre-game lobby.

Only confirmed drafts are exchanged. Both peers replay the same bounded native
PD operations, then include the resulting character values in prepare/ack.
No raw stat grants, uniqueness restrictions, or gameplay input are involved.
"""
from __future__ import annotations

STOCK_HASHES = {
    'Weapon.cfg': 'ce0975fa9229d3c787fd5161f385b0c595c7f8dda7cb1626da11405c9d3dfcd0',
    'Maps/common_charscreen.lgc': '06f4f3ed5935193b5da2f3badac67bd603f490c4750042c7656c003c7931651e',
    'Maps/util_charselect.lgc': '9fc354f04b95c3a4e54b3dd75197b4f0eedfa2c1478bcccdc70694214fd13c4d',
    'Maps/createplayer.men': '30059815cd165fab3c229c0db0a4f95b1e046f34bf24a2934c425eddec7e4e33',
    'Maps/perk.men': '3bc0ab0b35d7a53aed214ae60845923ab4cdd3b0971cf12ee08363dc939861e6',
    'Maps/util_invuln.lgc': 'c7ef853c4cd70d86996a48da87c209d08a43d747e13743a5a6e011bea1832ec1',
}

DECLARATIONS = r'''
static int OldCreateStage = 0;
static int OldCreateSteps[13];
static int OldCreateSkills[] = {2,3,4,5,6,22,1,7,8,9,10,11,18};
static string OldCreateDraft[8];
static string OldCreateApplied[8];
static string OldCreateProof[8];
static int OldCreateValues[16];
static int OldCreateHealth = -1;
static int OldCreateMoneyMerged = 0;
static int OldCreateReplayStarted = 0;
static int OldCreateAgreeTime = 0;
OldCreateTact();
OldCreateReceive();
OldCreatePublish();
OldCreateSignature();
OldCreateWaiting();
OldMenuRow(int row, string label);
OldMenuButton(int slot, string name, int enabled, string label);
'''

SCRIPT = r'''
OldCreateSkillInput()
{
    if(OldCreateStage != 2) return;
    int row = GetClickedButtonNum();
    if(row < 0 || row >= 13) return;
    int skill = GetSkillFromBtnNum(row);
    int step = -1;
    if(ToScreenX(GetX(SkillScrolls[row])) < GetInputAction(IA_SCREEN_MOUSE_X)) step = 1;
    if(step > 0 && !SendCommandA(-1, EXT_PDCANINCSKILL, skill)) return;
    if(step < 0 && !SendCommandA(-1, EXT_PDCANDECSKILL, skill)) return;
    SendCommandA(-1, EXT_PDADDSKILL, skill, step);
    OldCreateSteps[row] += step;
    ResetSkillScrolls();
    iPlusShowTime = 0;
    Genocide(2230);
}

OldCreateClearSteps()
{
    SendCommandA(-1, EXT_PDREMOVESKILLINCREASE);
    for(int row = 0; row < 13; row++) OldCreateSteps[row] = 0;
}

OldCreatePerkScreen()
{
    DeleteHeroSprite();
    g_iCharScrCurType = CS_NONE; // Hiding the stock screen would send arena channel 16.
    MenuRelease();
    MenuLoad("maps\\perk.men");
    SetMapTypeEx(MAP_TYPE_PERKSELECT, "");
    OldCreateStage = 1;
}

OldCreateCharacterScreen()
{
    MenuRelease();
    MenuLoad("maps\\createplayer.men");
    SetMapTypeEx(MAP_TYPE_PLAYERMENU, "");
    ShowCharScreen(CS_CHARSELECT, 1);
    FindCharSelectBtn();
    GetUserName();
    CreateHeroSprite(-120, -140);
    for(int sprite = FirstSprite(); sprite; sprite = NextSprite())
        if(GetVid(sprite) == 718 && ToScreenX(GetX(sprite)) > ScreenX()/2)
            OldCampaignCaption(sprite, 4, "Начать");
    OldCreateStage = 2;
}

OldCreateEncode()
{
    string draft = itoa(SendCommand(EXT_GetHeroPDId, OldGameLocalArmy)) + ":"
        + itoa(SendCommand(EXT_GetHeroPDClr, OldGameLocalArmy)) + ":"
        + itoa(SendCommandA(-1, EXT_GETPERKSKILL));
    for(int row = 0; row < 13; row++) draft += ":" + itoa(OldCreateSteps[row]);
    return draft;
}

OldCreateDecode(string draft)
{
    // Canonical bounded integers only; no partial or extra fields accepted.
    if(strlen(draft) > 160) return false;
    for(int field = 0; field < 16; field++)
    {
        string part = draft;
        if(field < 15) part = StrBefore(draft, ":");
        int value = part;
        if(part != itoa(value)) return false;
        OldCreateValues[field] = value;
        if(field < 15) draft = StrAfter(draft, ":");
    }
    int validHero = 0;
    for(int hero = 1; hero <= 8; hero++)
        if(OldCreateValues[0] == SendCommandC(EXT_GetIdByName, "Char" + itoa(hero))) validHero = 1;
    if(!validHero || OldCreateValues[1] < 0 || OldCreateValues[1] > 7
        || OldCreateValues[2] < 22 || OldCreateValues[2] > 32) return false;
    int steps = 0;
    for(int row = 3; row < 16; row++)
    {
        int count = OldCreateValues[row];
        if(count < -20 || count > 20) return false;
        if(count < 0) steps -= count;
        else steps += count;
    }
    return steps <= 64;
}

OldCreateApply(int army)
{
    if(OldCreateDraft[army] == "" || OldCreateApplied[army] == OldCreateDraft[army]) return;
    if(!OldCreateDecode(OldCreateDraft[army])) { OldGameStage = 94; return; }
    SendCommandA(army, EXT_PDREMOVESKILLINCREASE);
    SendCommandA(army, EXT_SetPlayerMenuType, 0);
    SendCommand(EXT_SetHeroPDId, army, OldCreateValues[0], true);
    SendCommand(EXT_SetHeroPDClr, army, OldCreateValues[1]);
    // EXT199 mutates the whole preset registry. EXT344 calls the same native
    // perk setter on this player's descriptor only, restricted to this lobby.
    if(SendCommandA(army, 344, OldCreateValues[2]) != 1) { OldGameStage = 94; return; }
    SendCommandA(army, EXT_PDREMOVESKILLINCREASE);
    // Decreases first: the original menu can reclaim points before spending.
    for(int pass = 0; pass < 2; pass++)
        for(int row = 0; row < 13; row++)
        {
            int count = OldCreateValues[row+3];
            int step = 1;
            int check = EXT_PDCANINCSKILL;
            if(count < 0) { step = -1; count = -count; check = EXT_PDCANDECSKILL; }
            if((pass == 0 && step > 0) || (pass == 1 && step < 0)) count = 0;
            int skill = OldCreateSkills[row];
            if(row == 5) skill = OldCreateValues[2];
            for(int n = 0; n < count; n++)
            {
                if(!SendCommandA(army, check, skill)) { OldGameStage = 94; return; }
                SendCommandA(army, EXT_PDADDSKILL, skill, step);
            }
        }
    SendCommandA(army, EXT_PDASSIGNSKILLS);
    OldCreateApplied[army] = OldCreateDraft[army];
    // Compare actual native result as well as input before loading the map.
    int id = SendCommandA(army, EXT_GETHEROID);
    string proof = OldCreateApplied[army];
    for(int skillNum = 1; skillNum <= 43; skillNum++)
        proof += ":" + itoa(SendCommand(EXT_GETSKILLBASE, id, skillNum));
    // Starting implants affect effective skills without changing base values.
    for(int effective = 1; effective <= 11; effective++)
        proof += ":" + itoa(SendCommand(EXT_GETSKILL, id, effective));
    OldCreateProof[army] = proof;
    OldGameHeroSeen[army] = 1;
    OldGameColorSeen[army] = 1;
}

OldCreatePublish()
{
    if(OLD_GAME_HOST) NetSend(18, OldCreateHealth);
    if(OldCreateStage == 3) NetSend(19, OldCreateDraft[OldGameLocalArmy]);
}

OldCreateReceive()
{
    string message;
    if(!OLD_GAME_HOST && (message = NetReceive(18, 0)) != "")
    {
        if(message != "0" && message != "1") { OldGameStage = 94; return; }
        OldCreateHealth = message;
    }
    for(int army = 0; army < 8; army++)
        if((message = NetReceive(19, army)) != "" && army != OldGameLocalArmy)
        {
            if((army != 0 && army != 3) || !OldCreateDecode(message)) { OldGameStage = 94; return; }
            // A confirmed character is immutable for this connection.
            if(OldCreateDraft[army] != "" && OldCreateDraft[army] != message) { OldGameStage = 94; return; }
            OldCreateDraft[army] = message;
        }
}

OldCreateSignature()
{
    if(OldCreateStage != 3 || OldCreateHealth < 0) return "";
    if(OldCreateDraft[0] == "" || OldCreateDraft[3] == "") return "";
    if(!OldCreateReplayStarted)
    {
        SendCommandA(0, EXT_PDREMOVESKILLINCREASE);
        SendCommandA(3, EXT_PDREMOVESKILLINCREASE);
        SendCommandA(0, EXT_SETPERKSKILL, -1);
        OldCreateReplayStarted = 1;
        OldCreateAgreeTime = GetTime();
    }
    OldCreateApply(0);
    OldCreateApply(3);
    if(OldGameStage >= 90) return "";
    if(!OldCreateMoneyMerged)
    {
        // Keep one normal starting purse. Add only the guest's paid creation
        // bonus, so money points chosen by either player reach the shared purse.
        int guest = SendCommandA(3, EXT_GETHEROID);
        int base = SendCommand(EXT_GetHeroPDId, 3);
        int extra = SendCommand(EXT_GETSKILLBASE, guest, RPGHERO_MONEY)
            - SendCommand(EXT_GETSKILLBASE, base, RPGHERO_MONEY);
        if(extra) SendCommandA(0, EXT_ADDSKILL, RPGHERO_MONEY, extra);
        OldCreateMoneyMerged = 1;
        OldCreateProof[0] += ":M" + itoa(SendCommand(EXT_GETSKILLBASE, SendCommandA(0, EXT_GETHEROID), RPGHERO_MONEY));
        OldMenuClearResult = SendCommandA(0, 345);
    }
    return "/C1/" + itoa(OldCreateHealth) + "/" + OldCreateProof[0] + "/" + OldCreateProof[3];
}

OldCreateConfirm()
{
    if(OldCreateStage != 2) return;
    OldCreateDraft[OldGameLocalArmy] = OldCreateEncode();
    if(!OldCreateDecode(OldCreateDraft[OldGameLocalArmy])) { OldGameStage = 94; return; }
    DeleteHeroSprite();
    g_iCharScrCurType = CS_NONE;
    MenuRelease();
    MenuLoad("maps\\netselectgame.men");
    OldMenuClearResult = SendCommandA(0, 345);
    int title = MenuFind(8);
    OldMenuDetails = MenuFind(3, 999999, ToScreenX(GetX(title)), ToScreenY(GetY(title), GetZ(title)));
    string heading = "Ожидание напарника";
    Action(title, ACT_SET_TEXT, &heading);
    for(int button = 0; button < 3; button++)
    { OldMenuButtonStates[button] = 0; OldMenuButtonLabels[button] = ""; }
    OldCreateStage = 3;
    OldMenuReady = 1;
    OldMenuStartRequested = 1;
    OldCreatePublish();
}

OldCreateConnectionError()
{
    // A disconnect can happen while either original editor is visible.
    // Rebind the lobby widgets before the connection-status view uses them.
    if(!OldCreateStage || OldCreateStage == 3) return;
    DeleteHeroSprite();
    g_iCharScrCurType = CS_NONE;
    MenuRelease();
    MenuLoad("maps\\netselectgame.men");
    int title = MenuFind(8);
    OldMenuDetails = MenuFind(3, 999999, ToScreenX(GetX(title)), ToScreenY(GetY(title), GetZ(title)));
    string heading = "Подключение прервано";
    OldMenuClearResult = SendCommandA(0, 345);
    Action(title, ACT_SET_TEXT, &heading);
    for(int button = 0; button < 3; button++)
    { OldMenuButtonStates[button] = 0; OldMenuButtonLabels[button] = ""; }
    OldCreateStage = 3;
}

OldCreateTact()
{
    if(!OldCreateStage)
    {
        if(OLD_GAME_HOST) OldCreateHealth = GetReg(GetDefaultRegPath(), "CoopTestHealthRequested", 0) == 1;
        SendCommandA(-1, EXT_SETPERKSKILL, RPGHERO_PERK_HEALING);
        OldCreatePerkScreen();
        return;
    }
    int clicked = MenuLClick();
    if(OldCreateStage == 1)
    {
        if((clicked && GetVid(clicked) == 718) || GetKey() == VK_RETURN || GetKey() == ' ')
            OldCreateCharacterScreen();
    }
    else if(OldCreateStage == 2)
    {
        HeroSpriteTact();
        CharScreenTact();
        int hero = SendCommand(EXT_GetHeroPDId, OldGameLocalArmy);
        if(clicked && (clicked == PrevNextBtn[0] || clicked == PrevNextBtn[1]
            || clicked == PrevNextBtn[2] || clicked == PrevNextBtn[3])) OldCreateClearSteps();
        ControlCharSelectBtn();
        if(hero != SendCommand(EXT_GetHeroPDId, OldGameLocalArmy)) OldCreateClearSteps();
        ControlWpns(1);
        DelTipIfNeed();
        if((clicked && GetVid(clicked) == 718 && ToScreenX(GetX(clicked)) > ScreenX()/2)
            || GetKey() == VK_RETURN) OldCreateConfirm();
        else if(clicked && GetVid(clicked) == 718)
        { OldCreateClearSteps(); OldCreatePerkScreen(); }
    }
}

OldCreateWaiting()
{
    OldBrowserWaiting("Ожидание");
    OldBrowserText("ListHeading", "Новая кампания");
    for(int army = 0; army <= 3; army += 3)
    {
        int row = 1;
        string role = "ХОСТ";
        if(army == 3) { row = 6; role = "НАПАРНИК"; }
        if(army == OldGameLocalArmy) role += " (ВЫ)";
        OldMenuRow(row, role);
        if(NetProperty(NET_IS_PLAYER_EXIST + army))
        {
            OldMenuRow(row + 1, NetProperty(NET_PLAYER_NAME + army));
            if(OldCreateDraft[army] != "") OldMenuRow(row + 2, "Персонаж готов");
            else OldMenuRow(row + 2, "Создаёт персонажа");
        }
        else OldMenuRow(row + 2, "Ожидание подключения");
    }
    int other = 3 - OldGameLocalArmy;
    string detail = "Ваш персонаж готов.\n\nНапарник завершает\nсоздание своего героя.\n\nКампания начнётся\nавтоматически.";
    if(!NetProperty(NET_IS_PLAYER_EXIST + other))
        detail = "Ваш персонаж готов.\n\nНапарник может найти\nигру в локальной сети\nи создать героя.\n\nКампания начнётся,\nкогда оба будут готовы.";
    if(OldCreateDraft[other] != "")
        detail = "Оба персонажа готовы.\n\nПодготовка кампании...\n\nМиссия 1 начнётся\nу обоих игроков.";
    if(OldCreateHealth == 1) OldMenuRow(12, "Тест: бесконечное здоровье");
    Action(OldMenuDetails, ACT_SET_TEXT, &detail);
}
'''


def compose(source: str) -> str:
    from old_native_campaign_menu import _once, _replace_function
    source = _once(source, '#include "maps\\common.lgc"',
        '#define OLD_CAMPAIGN_CREATOR 1\nOldCreateSkillInput();\n#include "maps\\common.lgc"\n'
        '#include "maps\\util_charselect.lgc"')
    source = _once(source, 'static int OldMenuHost = 0;', DECLARATIONS + '\nstatic int OldMenuHost = 0;')
    source = _once(source, '        if((message = NetReceive(18, army)) != "")\n'
                          '            OldMenuHumanReady[army] = message;\n', '')
    source = _once(source, 'OldMenuSessionMatches(string label)', SCRIPT + '\nOldMenuSessionMatches(string label)')
    # Do not let periodic base-ID updates erase a confirmed RPG descriptor.
    source = _once(source, '            SendCommand(EXT_SetHeroPDId, army, message);',
        '            if(army != OldGameLocalArmy && OldCreateApplied[army] == "")\n'
        '                SendCommand(EXT_SetHeroPDId, army, message);')
    source = _once(source, '            SendCommand(EXT_SetHeroPDClr, army, message);',
        '            if(army != OldGameLocalArmy && OldCreateApplied[army] == "")\n'
        '                SendCommand(EXT_SetHeroPDClr, army, message);')
    source = _once(source, '    string signature = ',
        '    string creation = OldCreateSignature();\n    if(creation == "") return "";\n    string signature = ')
    source = _once(source, '    return signature;', '    return signature + creation;')
    source = _once(source, '    if(!OldMenuReady || OldMenuReadySignature != OldGameSignature) return;',
        '    if(OldCreateStage != 3) return;')
    source = _once(source, '    if(OldMenuHumanReady[0] != OldGameSignature || OldMenuHumanReady[3] != OldGameSignature) return;', '')
    source = _once(source, '    // The harness must isolate RegPath in each disposable copy\'s cfg.',
        '    SetReg(GetDefaultRegPath(), "CoopTestHealthActive", OldCreateHealth);\n'
        '    // The harness must isolate RegPath in each disposable copy\'s cfg.')
    source = _once(source, '        OldMenuReady = 0;\n        OldMenuStartRequested = 0;',
        '        OldMenuReady = OldCreateStage == 3;\n        OldMenuStartRequested = OldCreateStage == 3;')
    source = _once(source, '        OldMenuRoster = roster;',
        '        if(OldMenuRoster == 9 && roster != 9) { OldGameStage = 96; return; }\n'
        '        OldMenuRoster = roster;')
    start = source.index('                    if(OldMenuReady && OldMenuReadySignature != OldGameSignature)')
    end = source.index('                    OldGameBarrier();', start)
    source = source[:start] + '''                    OldCreateReceive();
                    if(OldGameStage >= 90) { OldMenuWaiting(); return; }
                    OldCreateTact();
                    if(OldCreateAgreeTime && GetTime() - OldCreateAgreeTime > 20000)
                    { OldGameStage = 98; OldMenuWaiting(); OldGameWriteState(); return; }
                    if(OldGameFrame % 20 == 0)
                    {
                        OldGamePublish();
                        OldCreatePublish();
                    }
''' + source[end:]
    source = _once(source, '    for(int row = 0; row < 14; row++) OldMenuRow(row, "");\n    string hostName',
        '    if(OldCreateStage && OldGameStage < 90)\n'
        '    { if(OldCreateStage == 3) OldCreateWaiting(); return; }\n'
        '    if(OldGameStage >= 90) OldCreateConnectionError();\n'
        '    for(int row = 0; row < 14; row++) OldMenuRow(row, "");\n    string hostName')
    source = _once(source, '    OldGameValue(file, "end_frame", OldGameFrame);',
        '    OldGameValue(file, "creation_stage", OldCreateStage);\n'
        '    OldGameValue(file, "menu_clear_result", OldMenuClearResult);\n'
        '    OldGameValue(file, "test_health", OldCreateHealth);\n'
        '    FWrite(file, "creation_0=" + OldCreateDraft[0]);\n'
        '    FWrite(file, "creation_3=" + OldCreateDraft[3]);\n'
        '    OldGameValue(file, "end_frame", OldGameFrame);')
    return source


def charscreen(source: str) -> str:
    from old_native_campaign_menu import _function
    start, end = _function(source, 'ControlSkillScrolls')
    original = source[start:end]
    return source[:start] + ('#ifdef OLD_CAMPAIGN_CREATOR\nControlSkillScrolls()\n'
        '{ OldCreateSkillInput(); }\n#else\n' + original + '\n#endif') + source[end:]


def invulnerability(source: str) -> str:
    from old_native_campaign_menu import _once
    source = _once(source, 'static bool AdditionalInvuln[ MAX_PLAYER ];',
        'static bool AdditionalInvuln[ MAX_PLAYER ];\nstatic int OldTestHealth = 0;\n'
        'static int OldTestHealthHero[MAX_PLAYER];')
    source = _once(source, '    iff( 1 )\n    {', '    iff( 1 )\n    {\n'
        '#ifdef NET_GAME_RUN\n'
        '        OldTestHealth = GetReg(GetDefaultRegPath(), "CoopTestHealthActive", 0) == 1;\n'
        '#endif')
    source = _once(source, 'if( AdditionalInvuln[nArmy] == false && InvulnerableTime[nArmy] == 0 )',
        'if( !(OldTestHealth && (nArmy == 0 || nArmy == 3))\n'
        '        && AdditionalInvuln[nArmy] == false && InvulnerableTime[nArmy] == 0 )')
    source = _once(source, 'InvulnTact()\n{\n\tInitInvulnConst();',
        'InvulnTact()\n{\n\tInitInvulnConst();\n'
        '    if(OldTestHealth)\n'
        '        for(int army = 0; army <= 3; army += 3)\n'
        '            if(Flagman(army) && HeroID[army] > 0 && OldTestHealthHero[army] != HeroID[army])\n'
        '            {\n'
        '                SendCommand(EXT_SETINVULNERABLE, HeroID[army], 1);\n'
        '                OldTestHealthHero[army] = HeroID[army];\n'
        '            }')
    return source


def starting_inventory(source: str) -> str:
    """Use the engine's own saved-item (seed) syntax for three starting implants.

    Native 48F3B0 parses (seed), 48F084 sets RPG seed before clone, 48F0B1
    restores it; 48F7B0..48F7DD writes the same syntax in stock saves.
    Keep every item, its native generator, and all base character attributes.
    Only the roll is stable across copies and independent of menu timing.
    """
    import re
    count = 0

    def character(match):
        nonlocal count
        number, body = int(match[1]), match[2]
        def inventory(row):
            nonlocal count
            def implant(item):
                nonlocal count
                count += 1
                return item[0] + '(' + str(10000 + number) + ')'
            return re.sub(r'\bimplant_rnd[12]_1\b', implant, row[0])
        return match[0][:len(match[0])-len(body)] + re.sub(r'^Inv=.*$', inventory, body, flags=re.M)

    source = re.sub(r'^Character=Char([1-8])\b([^\r]*?)(?=^Character=|\Z)', character, source, flags=re.M|re.S)
    if count != 3:
        raise ValueError('Expected exactly three original campaign starting implants')
    return source
