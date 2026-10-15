"""Native campaign browser: new game, paged checkpoints and LAN discovery.

The launcher validates save files. The menu selects catalog UUIDs through a
nonce-acknowledged local bridge before creating any native network session.
"""

DECLARATIONS = r'''
static int OldBrowserView = 0; // 0=new, 1=saves, 2=join
static int OldBrowserPage = 0;
static int OldBrowserCount = 0;
static int OldBrowserUnavailable = 0;
static int OldBrowserRows = 0;
static int OldBrowserSelected = -1;
static int OldBrowserNonce = 0;
static int OldBrowserPending = 0; // 1=refresh, 2=host selection
static int OldBrowserRequestTime = 0;
static int OldBrowserCatalogReady = 0;
static int OldBrowserInitial = 1;
static int OldBrowserRowCount = -1;
static int OldBrowserAddressEnabled = -1;
static int OldBrowserChromeMode = -2;
static int OldBrowserTabSelection = -1;
static string OldBrowserWanted = "";
static string OldBrowserError = "";
static string OldBrowserIds[8];
static string OldBrowserDates[8];
static string OldBrowserHosts[8];
static string OldBrowserGuests[8];
static int OldBrowserMissions[8];
static int OldBrowserHealth[8];
OldBrowserBind();
OldBrowserPaint();
OldBrowserReadCatalog();
OldBrowserTabs(int enabled);
OldBrowserPaging(int visible);
OldBrowserRowsMode(int count);
OldBrowserText(string name, string label);
OldBrowserWaiting(string title);
OldMenuConnect(int host);
OldMenuList();
OldMenuSearch();
'''

SCRIPT = r'''
OldBrowserBind()
{
    for(int slot = 0; slot < 8; slot++)
    { OldMenuButtonStates[slot] = 0; OldMenuButtonLabels[slot] = ""; }
    OldMenuDetails = MenuFindNamed("BrowserDetails");
    Action(OldMenuDetails, ACT_SET_BEHAVE, Action(OldMenuDetails, ACT_GET_BEHAVE) & ~BEH_LOAD_FROM);
    OldMenuPaintedSelection = -2;
    OldBrowserRowCount = -1;
    OldBrowserAddressEnabled = -1;
    OldBrowserChromeMode = -2;
    OldBrowserTabSelection = -1;
    OldBrowserText("CampaignHeading", "СЕТЕВАЯ КАМПАНИЯ");
    OldBrowserText("ExitButtonText", "Главное меню");
    // Stock B_FRAME selected/disabled state: the accent remains lit without
    // taking input or resetting the neighbouring tab's hover animation.
    Action(MenuFindNamed("NewTabMark"), ANI_MENUDISABLEUP);
    Action(MenuFindNamed("SavesTabMark"), ANI_MENUDISABLEUP);
    Action(MenuFindNamed("JoinTabMark"), ANI_MENUDISABLEUP);
    OldBrowserTabs(0);
    OldBrowserPaging(0);
}

OldBrowserHeading(string label)
{
    OldBrowserText("BrowserTitle", label);
}

OldBrowserText(string name, string label)
{
    int sprite = MenuFindNamed(name);
    if(!sprite) return;
    Action(sprite, ACT_SET_BEHAVE, Action(sprite, ACT_GET_BEHAVE) & ~BEH_LOAD_FROM);
    Action(sprite, ACT_SET_TEXT, &label);
}

OldBrowserControl(string name, int visible)
{
    Action(MenuFindNamed(name), ACT_SET_INVISIBLE, !visible);
    int caption = MenuFindNamed(name + "Text");
    if(caption) Action(caption, ACT_SET_INVISIBLE, !visible);
}

OldBrowserChrome(int mode)
{
    if(mode == OldBrowserChromeMode) return;
    OldBrowserChromeMode = mode;
    OldBrowserControl("StartButton", mode == 0 || mode == 1);
    OldBrowserControl("JoinButton", mode == 2);
    OldBrowserControl("SearchButton", mode != 0);
    OldBrowserControl("NewTab", mode >= 0);
    OldBrowserControl("SavesTab", mode >= 0);
    OldBrowserControl("JoinTab", mode >= 0);
    OldBrowserControl("AddressInput", mode == 2);
    OldBrowserControl("HostAddr", mode == 2);
    OldBrowserControl("AddressHint", mode == 2);
    if(mode < 0)
    {
        OldBrowserControl("NewTabMark", 0);
        OldBrowserControl("SavesTabMark", 0);
        OldBrowserControl("JoinTabMark", 0);
        OldBrowserTabSelection = -1;
    }
    // Hidden controls must also stop accepting mouse input.
    if(mode == 2) MenuAction(718, 999064, ANI_MENUSTAND);
    else MenuAction(718, 999064, ANI_MENUDISABLE);
    OldBrowserAddressEnabled = mode == 2;
}

OldBrowserWaiting(string title)
{
    OldBrowserTabs(0);
    OldBrowserChrome(-1);
    OldBrowserPaging(0);
    OldBrowserRowsMode(0);
    for(int row = 0; row < 14; row++) OldMenuRow(row, "");
    OldBrowserHeading(title);
    OldBrowserText("ListHeading", "Игроки кампании");
    OldMenuButton(0, "StartButton", 0, "Создать игру");
    OldMenuButton(1, "JoinButton", 0, "Подключиться");
    OldMenuButton(2, "SearchButton", 1, "Отмена");
    OldMenuButton(6, "PrevPage", 0, "");
    OldMenuButton(7, "NextPage", 0, "");
}

OldBrowserHighlight(int selected)
{
    if(OldMenuPaintedSelection == selected) return;
    OldMenuPaintedSelection = selected;
    for(int row = 0; row < OldBrowserRowCount; row++)
        MenuAction(98, 999000 + row, ANI_STAND);
    if(selected >= 0 && selected < OldBrowserRowCount)
        MenuAction(98, 999000 + selected, ANI_MENUSTANDUP);
}

OldBrowserReadCatalog()
{
    // Two sequential passes only when a refreshed sort moves the selected UUID.
    for(int pass = 0; pass < 2; pass++)
    {
        int file = FOpen("coop-menu-catalog.txt");
        if(!file) { OldBrowserCatalogReady = 0; return; }
        string magic = FRead(file);
        int nonce = FRead(file);
        string active = FRead(file);
        int count = FRead(file);
        int unavailable = FRead(file);
        if(magic != "AS2CATALOG1" || count < 0 || count > 4096 || nonce < 0)
        { FClose(file); OldBrowserCatalogReady = 0; return; }
        if(nonce > OldBrowserNonce) OldBrowserNonce = nonce;
        if(OldBrowserInitial && active != "NEW")
        { OldBrowserWanted = active; OldBrowserView = 1; }
        OldBrowserInitial = 0;
        OldBrowserCount = count;
        OldBrowserUnavailable = unavailable;
        if(OldBrowserPage * 8 >= count) OldBrowserPage = 0;
        OldBrowserRows = 0;
        OldBrowserSelected = -1;
        int found = -1;
        for(int index = 0; index < count; index++)
        {
            string id = FRead(file);
            int mission = FRead(file);
            string date = FRead(file);
            string host = FRead(file);
            string guest = FRead(file);
            int health = FRead(file);
            if(id == OldBrowserWanted) found = index;
            if(index >= OldBrowserPage * 8 && index < OldBrowserPage * 8 + 8)
            {
                int row = OldBrowserRows++;
                OldBrowserIds[row] = id; OldBrowserMissions[row] = mission;
                OldBrowserDates[row] = date; OldBrowserHosts[row] = host;
                OldBrowserGuests[row] = guest; OldBrowserHealth[row] = health;
                if(id == OldBrowserWanted) OldBrowserSelected = row;
            }
        }
        string end = FRead(file); FClose(file);
        if(end != "END") { OldBrowserCatalogReady = 0; return; }
        if(found >= 0 && found / 8 != OldBrowserPage && pass == 0)
            OldBrowserPage = found / 8;
        else
        {
            if(OldBrowserSelected < 0 && OldBrowserRows > 0) OldBrowserSelected = 0;
            if(OldBrowserSelected >= 0) OldBrowserWanted = OldBrowserIds[OldBrowserSelected];
            else OldBrowserWanted = "";
            OldBrowserCatalogReady = 1;
            return;
        }
    }
}

OldBrowserRequest(int operation)
{
    if(OldBrowserPending) return;
    OldBrowserReadCatalog();
    if(operation == 2 && OldBrowserView == 1 &&
       (!OldBrowserCatalogReady || OldBrowserSelected < 0)) return;
    OldBrowserNonce++;
    string selected = "NEW";
    if(operation == 2 && OldBrowserView == 1) selected = OldBrowserIds[OldBrowserSelected];
    int file = FCreate("coop-menu-request.txt");
    if(!file) { OldBrowserError = "Не удалось открыть список.\nПерезапустите лаунчер."; return; }
    FWrite(file, "AS2MENU1"); FWrite(file, itoa(OldBrowserNonce));
    if(operation == 1) FWrite(file, "REFRESH");
    else FWrite(file, "SELECT");
    FWrite(file, selected); FWrite(file, "END"); FClose(file);
    OldBrowserPending = operation;
    OldBrowserRequestTime = GetTime();
    OldBrowserError = "";
}

OldBrowserPoll()
{
    if(!OldBrowserPending) return;
    int file = FOpen("coop-menu-status.txt");
    int nonce = -1;
    string result = "";
    string selected = "";
    if(file)
    {
        nonce = FRead(file); result = FRead(file); selected = FRead(file);
        FClose(file);
    }
    if(nonce == OldBrowserNonce && (result == "OK" || result == "ERROR"))
    {
        int operation = OldBrowserPending;
        OldBrowserPending = 0;
        if(result == "ERROR")
        {
            OldBrowserError = "Сохранение недоступно.\nОбновите список\nи выберите другое.";
            OldBrowserReadCatalog(); return;
        }
        if(operation == 2)
        {
            string expected = "NEW";
            if(OldBrowserView == 1) expected = OldBrowserWanted;
            if(selected != expected)
            { OldBrowserError = "Выбор изменился.\nПовторите создание игры."; return; }
            OldMenuConnect(1);
        }
        else OldBrowserReadCatalog();
    }
    else if(GetTime() - OldBrowserRequestTime > 10000)
    {
        OldBrowserPending = 0;
        OldBrowserError = "Лаунчер не отвечает.\nЗапустите игру через\nлаунчер мода.";
    }
}

OldBrowserTabs(int enabled)
{
    OldMenuButton(3, "NewTab", enabled, "Новая игра");
    OldMenuButton(4, "SavesTab", enabled, "Сохранения");
    OldMenuButton(5, "JoinTab", enabled, "Подключение");
    int selected = OldBrowserView;
    if(OldBrowserChromeMode < 0) selected = -1;
    if(OldBrowserTabSelection == selected) return;
    OldBrowserTabSelection = selected;
    OldBrowserControl("NewTabMark", selected == 0);
    OldBrowserControl("SavesTabMark", selected == 1);
    OldBrowserControl("JoinTabMark", selected == 2);
}

OldBrowserPaging(int visible)
{
    Action(MenuFindNamed("PrevPage"), ACT_SET_INVISIBLE, !visible);
    Action(MenuFindNamed("NextPage"), ACT_SET_INVISIBLE, !visible);
    Action(MenuFindNamed("PageLabel"), ACT_SET_INVISIBLE, !visible);
}

OldBrowserRowsMode(int count)
{
    if(count == OldBrowserRowCount) return;
    OldBrowserRowCount = count; OldMenuPaintedSelection = -2;
    for(int row = 0; row < 14; row++)
    {
        int sprite = MenuFind(98, 999000 + row);
        if(row < count) Action(sprite, ANI_STAND);
        else Action(sprite, ANI_MENUDISABLE);
        Action(sprite, ACT_SET_INVISIBLE, row >= count);
    }
}

OldBrowserHero(string value)
{
    return "Герой " + StrBefore(StrAfter(value, "Char"), " ") + ", опыт " + StrAfter(value, "XP ");
}

OldBrowserPaint()
{
    OldBrowserChrome(OldBrowserView);
    OldBrowserTabs(!OldBrowserPending);
    OldBrowserPaging(OldBrowserView == 1 && OldBrowserCount > 8);
    for(int row = 0; row < 14; row++) OldMenuRow(row, "");
    OldMenuButton(6, "PrevPage", !OldBrowserPending && OldBrowserView == 1 && OldBrowserPage > 0, "Назад");
    OldMenuButton(7, "NextPage", !OldBrowserPending && OldBrowserView == 1 && (OldBrowserPage + 1) * 8 < OldBrowserCount, "Далее");
    string page = "";
    string detail = "";
    OldBrowserHeading("Новая кампания");
    if(OldBrowserView == 0)
    {
        OldMenuButton(0, "StartButton", !OldBrowserPending, "Создать игру");
        OldMenuButton(1, "JoinButton", 0, "Войти");
        OldMenuButton(2, "SearchButton", 0, "Обновить");
        OldBrowserRowsMode(0);
        OldBrowserHighlight(-1);
        OldBrowserText("ListHeading", "Кампания для двух игроков");
        OldMenuRow(0, "С НАЧАЛА ИСТОРИИ");
        OldMenuRow(1, "Первая миссия кампании");
        OldMenuRow(3, "ВАШИ ПЕРСОНАЖИ");
        OldMenuRow(4, "Свой герой, навыки и инвентарь");
        OldMenuRow(6, "ОБЩЕЕ ПРОХОЖДЕНИЕ");
        OldMenuRow(7, "Задания и деньги для всей команды");
        OldMenuRow(9, "АВТОСОХРАНЕНИЕ");
        OldMenuRow(10, "Прогресс сохраняется между миссиями");
        detail = "Создайте игру и\nпригласите напарника\nиз локальной сети.\n\nКаждый выберет героя\nи распределит очки\nхарактеристик.\n\nМиссия начнётся,\nкогда оба подтвердят\nсвоих персонажей.";
        if(GetReg(GetDefaultRegPath(), "CoopTestHealthRequested", 0) == 1)
            OldMenuRow(12, "Тест: бесконечное здоровье");
    }
    else if(OldBrowserView == 1)
    {
        OldMenuButton(1, "JoinButton", 0, "Войти");
        OldBrowserHeading("Сохранение");
        OldBrowserText("ListHeading", "Сохранённые кампании");
        OldMenuButton(0, "StartButton", !OldBrowserPending && OldBrowserCatalogReady && OldBrowserSelected >= 0, "Продолжить");
        OldMenuButton(2, "SearchButton", !OldBrowserPending, "Обновить");
        for(int saved = 0; saved < OldBrowserRows; saved++)
            OldMenuRow(saved, "Миссия " + OldMissionLabel(OldBrowserMissions[saved]) + "   " + OldBrowserDates[saved]);
        OldBrowserRowsMode(OldBrowserRows);
        OldBrowserHighlight(OldBrowserSelected);
        page = itoa(OldBrowserPage + 1) + " / " + itoa((OldBrowserCount + 7) / 8);
        if(!OldBrowserCount) page = "Нет сохранений";
        detail = "Сохранений пока нет.\n\nНачните новую игру.\nПрогресс сохранится\nавтоматически при\nпереходе между миссиями.";
        if(!OldBrowserCount) OldMenuRow(2, "Здесь появятся ваши сохранения");
        if(!OldBrowserCatalogReady) detail = "Список недоступен.\n\nНажмите Обновить.\nИгра должна быть\nзапущена через\nлаунчер мода.";
        if(OldBrowserSelected >= 0)
        {
            int selectedRow = OldBrowserSelected;
            detail = "Миссия " + OldMissionLabel(OldBrowserMissions[selectedRow]) + "\n" + OldBrowserDates[selectedRow]
                + "\n\nХозяин игры\n" + OldBrowserHero(OldBrowserHosts[selectedRow])
                + "\nНапарник\n" + OldBrowserHero(OldBrowserGuests[selectedRow])
                + "\n\nГерои и инвентарь\nбудут восстановлены.\nВыбор персонажей\nне потребуется.";
            if(OldBrowserHealth[selectedRow]) OldMenuRow(10, "Тест: бесконечное здоровье");
        }
        if(OldBrowserUnavailable) OldMenuRow(12, "Недоступно файлов: " + itoa(OldBrowserUnavailable));
    }
    else
    {
        OldBrowserHeading("Подключение");
        OldBrowserText("ListHeading", "Игры в локальной сети");
        OldMenuList();
        OldBrowserRowsMode(OldMenuSessionCount);
        OldBrowserHighlight(OldMenuSelection);
        OldMenuButton(0, "StartButton", 0, "Создать");
        if(!OldMenuSessionCount)
        {
            if(OldMenuStatus == 1) OldMenuRow(2, "Поиск кампаний...");
            else OldMenuRow(2, "Нет доступных игр");
        }
        OldBrowserText("PageLabel", "");
        OldBrowserText("HostAddr", OldMenuAddress);
        string hint = "Адрес хоста (пусто — вся сеть)";
        if(EditStringFlag) hint = "Enter — поиск; Esc — отмена";
        OldBrowserText("AddressHint", hint);
        return;
    }
    if(OldBrowserPending) detail = "Подготовка кампании...\n\nПодождите немного.";
    else if(OldBrowserError != "") detail = OldBrowserError;
    Action(OldMenuDetails, ACT_SET_TEXT, &detail);
    OldBrowserText("PageLabel", page);
}

OldBrowserSwitch(int view)
{
    if(OldBrowserPending) return;
    OldBrowserView = view; OldBrowserError = ""; OldMenuPaintedSelection = -2;
    if(view == 1) { OldBrowserReadCatalog(); OldBrowserRequest(1); }
    if(view == 2) { OldMenuNextSearch = 0; OldMenuSearch(); }
    OldBrowserPaint();
}

OldBrowserInput(int clicked)
{
    OldBrowserPoll();
    if(OldGameStage != 0) return;
    if(!OldBrowserPending && clicked)
    {
        if(clicked == MenuFindNamed("NewTab")) OldBrowserSwitch(0);
        else if(clicked == MenuFindNamed("SavesTab")) OldBrowserSwitch(1);
        else if(clicked == MenuFindNamed("JoinTab")) OldBrowserSwitch(2);
        else if(OldBrowserView != 2 && clicked == MenuFindNamed("StartButton")) OldBrowserRequest(2);
        else if(OldBrowserView == 2 && clicked == MenuFindNamed("JoinButton")) OldMenuConnect(0);
        else if(clicked == MenuFindNamed("SearchButton"))
        { if(OldBrowserView == 1) OldBrowserRequest(1); else if(OldBrowserView == 2) OldMenuSearch(); }
        else if(OldBrowserView == 1 && (clicked == MenuFindNamed("PrevPage") || clicked == MenuFindNamed("NextPage")))
        {
            if(clicked == MenuFindNamed("PrevPage") && OldBrowserPage > 0) OldBrowserPage--;
            else if(clicked == MenuFindNamed("NextPage") && (OldBrowserPage + 1) * 8 < OldBrowserCount) OldBrowserPage++;
            OldBrowserWanted = ""; OldBrowserReadCatalog();
        }
        else if(OldBrowserView == 2 && GetVid(clicked) == 718 && GetDirection(clicked) == 64)
            EditStringStart(OldMenuAddress, 63, MenuFindNamed("HostAddr"));
        else if(GetVid(clicked) == 98)
        {
            int row = GetDirection(clicked);
            if(OldBrowserView == 1 && row >= 0 && row < OldBrowserRows)
            { OldBrowserSelected = row; OldBrowserWanted = OldBrowserIds[row]; }
            if(OldBrowserView == 2 && row >= 0 && row < OldMenuSessionCount)
            {
                OldMenuSelection = row;
                OldMenuSelectedHost = StrBefore(NetProperty(NET_GAME_LIST, itoa(OldMenuSessionIndex[row])), "  ");
            }
        }
    }
    if(OldGameStage == 0 && (clicked || OldGameFrame % 8 == 0)) OldBrowserPaint();
}
'''


def compose(source):
    from old_native_campaign_menu import _once, _function
    source = _once(source, 'static int OldMenuHost = 0;', DECLARATIONS + '\nstatic int OldMenuHost = 0;')
    source = source.replace('OldMenuButtonStates[3]', 'OldMenuButtonStates[8]').replace(
        'OldMenuButtonLabels[3]', 'OldMenuButtonLabels[8]')
    for command in ('Action(caption, ACT_SET_GAMMA, 0);',
                    'Action(caption, ACT_SET_GAMMA, 0x323232);',
                    'Action(caption, ACT_SET_TEXT, &label);'):
        source = source.replace(command, 'if(caption) ' + command)
    source = _once(source, '    // Restart the native sprite stack only when availability changes.',
        '    if(name == "PrevPage" || name == "NextPage") caption = 0;\n'
        '    // Restart the native sprite stack only when availability changes.')
    source = _once(source, '    OldMenuButton(0, "StartButton", 1, "Создать");',
                   '    OldMenuButton(0, "StartButton", 0, "Создать");')
    source = _once(source, 'OldMenuSessionMatches(string label)', SCRIPT + '\nOldMenuSessionMatches(string label)')
    source = _once(source, '''    if(OldMenuPaintedSelection != OldMenuSelection)
    {
        OldMenuPaintedSelection = OldMenuSelection;
        MenuAction(98, 999999, ANI_STAND);
        if(OldMenuSelection >= 0)
            MenuAction(98, 999000 + OldMenuSelection, ANI_MENUSTANDUP);
    }''', '''    OldBrowserRowsMode(OldMenuSessionCount);
    OldBrowserHighlight(OldMenuSelection);''')
    source = source.replace('MenuLoad("maps\\\\netselectgame.men");',
                            'MenuLoad("maps\\\\old_campaign_browser.men");\n    OldBrowserBind();')
    # All three return paths (initial menu, character confirmation and failure)
    # bind the same named widgets. Geometry no longer determines ownership.
    source = source.replace('int title = MenuFind(8);',
                            'int title = MenuFindNamed("BrowserTitle");')
    source = source.replace('OldMenuDetails = MenuFind(3, 999999, ToScreenX(GetX(title)), ToScreenY(GetY(title), GetZ(title)));',
                            'OldMenuDetails = MenuFindNamed("BrowserDetails");')
    source = _once(source, '        OldMenuSearch();\n        OldMenuList();',
                   '        OldBrowserReadCatalog();\n        OldBrowserRequest(1);\n        OldBrowserPaint();')
    start, end = _function(source, 'main')
    main = source[start:end]
    first = main.index('    if(OldGameStage == 0)\n    {')
    last = main.index('    else\n    {\n        if(clicked && clicked == MenuFindNamed("SearchButton"))', first)
    main = main[:first] + '    if(OldGameStage == 0)\n    {\n        OldBrowserInput(clicked);\n    }\n' + main[last:]
    source = source[:start] + main + source[end:]
    source = _once(source, '    OldMenuHost = host;',
        '    OldBrowserTabs(0);\n'
        '    OldBrowserPaging(0);\n'
        '    OldMenuButton(6, "PrevPage", 0, "Назад");\n'
        '    OldMenuButton(7, "NextPage", 0, "Далее");\n'
        '    string page = ""; Action(MenuFindNamed("PageLabel"), ACT_SET_TEXT, &page);\n'
        '    OldMenuHost = host;')
    # Connected views retain the existing creation/restore logic, but every
    # menu reload resets animation caches and disables browser navigation.
    source = _once(source, '    OldCreateStage = 3;\n    OldMenuReady = 1;\n    OldMenuStartRequested = 1;\n    OldCreatePublish();',
        '    OldBrowserTabs(0);\n'
        '    OldMenuButton(6, "PrevPage", 0, "Назад");\n'
        '    OldMenuButton(7, "NextPage", 0, "Далее");\n'
        '    OldCreateStage = 3;\n    OldMenuReady = 1;\n    OldMenuStartRequested = 1;\n    OldCreatePublish();')
    source = _once(source, '    OldGameValue(file, "resume_mode", OldResumeMode);',
        '    OldGameValue(file, "browser_view", OldBrowserView);\n'
        '    OldGameValue(file, "browser_saves", OldBrowserCount);\n'
        '    OldGameValue(file, "browser_pending", OldBrowserPending);\n'
        '    FWrite(file, "browser_selected=" + OldBrowserWanted);\n'
        '    OldGameValue(file, "resume_mode", OldResumeMode);')
    return source
