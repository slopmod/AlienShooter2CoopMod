"""Shared boundary autosave and pre-game checkpoint transfer, no live world load."""
from old_native_checkpoints import CHUNK, MAX_CHUNKS
from old_native_campaign_missions import MISSIONS

HELPER_PATH = 'Maps/old_campaign_checkpoint.lgc'
HELPER = r'''
#ifndef OLD_CAMPAIGN_CHECKPOINT_H
#define OLD_CAMPAIGN_CHECKPOINT_H
static int OldCheckpointStage = 0;
static int OldCheckpointTime = 0;
static int OldCheckpointText = 0;
static string OldCheckpointMap = "";

OldCheckpointNotice(string message)
{
    Destroy(OldCheckpointText);
    OldCheckpointText = CreateText(13, ScreenX()/2, ScreenY()/2+95, 0, message, BEH_CENTER);
}

OldCheckpointBegin(int mission, string map)
{
    if(!NetProperty(NET_IS_HOST) || OldCheckpointStage) return;
    OldCheckpointStage = 1;
    OldCheckpointTime = GetTime();
    OldCheckpointMap = map;
    Log2("CoopCheckpoint: begin mission=" + itoa(mission) + " map=" + map);
    OldCheckpointNotice("Автосохранение кампании...");
    int status = FCreate("coop-save-status.txt");
    if(!status) { Log2("CoopCheckpoint: cannot reset receipt"); OldCheckpointStage = 90; return; }
    FWrite(status, "WAIT"); FClose(status);
    if(SendCommandA(0, 350, 0) != 1)
    { Log2("CoopCheckpoint: native export failed"); OldCheckpointStage = 90; return; }
    int file = FCreate("coop-save.pending.txt");
    if(!file) { Log2("CoopCheckpoint: cannot write request"); OldCheckpointStage = 90; return; }
    FWrite(file, "AS2CHECKPOINT1"); FWrite(file, itoa(mission));
    FWrite(file, GetReg(GetDefaultRegPath(), "CoopTestHealthActive", 0));
    FWrite(file, "END"); FClose(file);
    Log2("CoopCheckpoint: waiting for durable save map=" + map);
}

OldCheckpointTact()
{
    if(!NetProperty(NET_IS_HOST) || !OldCheckpointStage || OldCheckpointStage == 2) return;
    if(OldCheckpointStage == 1)
    {
        int file = FOpen("coop-save-status.txt");
        string state = "";
        if(file) { state = FRead(file); FClose(file); }
        if(state == "SAVED")
        {
            OldCheckpointStage = 2;
            Destroy(OldCheckpointText);
            Log2("CoopCheckpoint: SAVED, loading " + OldCheckpointMap);
            NetProperty(NET_GAME_START, OldCheckpointMap);
            return;
        }
        if(state == "ERROR" || GetTime() - OldCheckpointTime > 15000)
        {
            Log2("CoopCheckpoint: stopped map=" + OldCheckpointMap + " receipt=" + state);
            OldCheckpointStage = 90;
        }
    }
    if(OldCheckpointStage == 90)
    {
        OldCheckpointNotice("Не удалось сохранить кампанию. Проверьте журнал лаунчера. Переход остановлен.");
        OldCheckpointStage = 91;
    }
}
#endif
'''

DECLARATIONS = r'''
#include "maps\old_campaign_checkpoint.lgc"
static int OldResumeMode = -1;
static int OldResumeMission = 1;
static int OldResumeCount = 0;
static int OldResumeIndex = 0;
static int OldResumeAck = -1;
static int OldResumeInput = 0;
static int OldResumeOutput = 0;
static int OldResumeLoaded = 0;
static int OldResumeTime = 0;
static string OldResumeHeader = "";
static string OldResumeHash = "";
static string OldResumeChunk = "";
static int OldResumeChar[2];
static int OldResumeColor[2];
OldResumeTact();
OldResumeReceive();
OldResumePublish();
OldResumeSignature();
OldResumeWaiting();
OldResumeMap();
OldMissionLabel(int mission);
'''

SCRIPT = ('OldMissionLabel(int mission)\n{\n' + ''.join(
    f'    if(mission == {m.number}) return "{m.label}";\n' for m in MISSIONS)
    + '    return itoa(mission);\n}\nOldResumeMap()\n{\n' + ''.join(
    f'    if(OldResumeMission == {mission.number}) return "{mission.path.replace("/", chr(92) * 2)}";\n'
    for mission in MISSIONS) + '    return "";\n}\n' + r'''
OldResumeHeaderSet(string message)
{
    if(OldResumeHeader != "")
    {
        if(message != OldResumeHeader) OldGameStage = 94;
        return;
    }
    OldResumeHeader = message;
    string mode = StrBefore(message, ":");
    message = StrAfter(message, ":");
    if(mode == "N1")
    {
        if(message != "0" && message != "1") { OldGameStage = 94; return; }
        OldCreateHealth = message; OldResumeMode = 0; return;
    }
    if(mode != "S1") { OldGameStage = 94; return; }
    OldResumeMission = StrBefore(message, ":"); message = StrAfter(message, ":");
    for(int i = 0; i < 2; i++)
    {
        OldResumeChar[i] = StrBefore(message, ":"); message = StrAfter(message, ":");
        OldResumeColor[i] = StrBefore(message, ":"); message = StrAfter(message, ":");
        if(OldResumeChar[i] < 1 || OldResumeChar[i] > 8 || OldResumeColor[i] < 0 || OldResumeColor[i] > 7)
        { OldGameStage = 94; return; }
    }
    OldResumeCount = StrBefore(message, ":"); message = StrAfter(message, ":");
    OldResumeHash = StrBefore(message, ":"); message = StrAfter(message, ":");
    if(OldResumeMap() == "" || OldResumeCount < 1 || OldResumeCount > 2048
        || strlen(OldResumeHash) != 64 || (message != "0" && message != "1"))
    { OldGameStage = 94; return; }
    OldCreateHealth = message;
    OldResumeMode = 1;
    OldCreateStage = 3;
    OldMenuReady = 1; OldMenuStartRequested = 1;
    // Base/color messages may still be in flight; the save owns both heroes now.
    OldCreateApplied[0] = "saved"; OldCreateApplied[3] = "saved";
    if(OLD_GAME_HOST)
    {
        int status = FCreate("coop-resume-state.txt");
        if(!status) { OldGameStage = 94; return; }
        FWrite(status, "WAIT"); FClose(status);
        int request = FCreate("coop-resume-request.txt");
        if(!request) { OldGameStage = 94; return; }
        FWrite(request, OldResumeHash); FWrite(request, "END"); FClose(request);
        OldResumeInput = FOpen("coop-resume-wire.txt");
        if(!OldResumeInput) { OldGameStage = 94; return; }
        OldResumeChunk = FRead(OldResumeInput);
    }
    else
    {
        OldResumeOutput = FCreate("coop-incoming.txt");
        if(!OldResumeOutput) { OldGameStage = 94; return; }
        FWrite(OldResumeOutput, OldResumeHash);
    }
}

OldResumePublish()
{
    if(OLD_GAME_HOST && OldResumeHeader != "") NetSend(18, OldResumeHeader);
    if(OldResumeMode != 1) return;
    if(OLD_GAME_HOST && OldResumeIndex < OldResumeCount)
        NetSend(19, itoa(OldResumeIndex) + ":" + OldResumeChunk);
    if(!OLD_GAME_HOST) NetSend(19, "A:" + itoa(OldResumeAck));
}

OldResumeReceive()
{
    string message;
    if(!OLD_GAME_HOST && (message = NetReceive(18, 0)) != "") OldResumeHeaderSet(message);
    if(OldResumeMode != 1 || OldGameStage >= 90) return;
    if(OLD_GAME_HOST)
    {
        message = NetReceive(19, 3);
        if(StrBefore(message, ":") == "A" && OldResumeIndex < OldResumeCount)
        {
            int ack = StrAfter(message, ":");
            if(ack == OldResumeIndex)
            {
                OldResumeIndex++;
                if(OldResumeIndex < OldResumeCount) OldResumeChunk = FRead(OldResumeInput);
                else { FClose(OldResumeInput); OldResumeInput = 0; }
            }
        }
    }
    else
    {
        message = NetReceive(19, 0);
        if(message == "") return;
        int index = StrBefore(message, ":");
        string chunk = StrAfter(message, ":");
        if(index != OldResumeIndex || index >= OldResumeCount) return;
        if(strlen(chunk) < 2 || strlen(chunk) > 240) { OldGameStage = 94; return; }
        FWrite(OldResumeOutput, chunk);
        OldResumeAck = OldResumeIndex; OldResumeIndex++;
        if(OldResumeIndex == OldResumeCount)
        {
            FWrite(OldResumeOutput, "END"); FClose(OldResumeOutput); OldResumeOutput = 0;
        }
    }
    OldResumePublish();
}

OldResumeTact()
{
    if(OLD_GAME_HOST && OldResumeMode < 0)
    {
        int file = FOpen("coop-resume-mode.txt");
        if(!file) { OldGameStage = 94; return; }
        string mode = FRead(file); FClose(file);
        if(mode == "NEW") mode = "N1:" + itoa(GetReg(GetDefaultRegPath(), "CoopTestHealthRequested", 0) == 1);
        OldResumeHeaderSet(mode);
        OldResumePublish();
    }
    if(OldResumeMode != 1) return;
    if(OldGamePlayers != 2) return;
    if(!OldResumeTime) OldResumeTime = GetTime();
    if(GetTime() - OldResumeTime > 120000) { OldGameStage = 98; return; }
    if(OldResumeLoaded || (!OLD_GAME_HOST && OldResumeIndex != OldResumeCount)) return;
    int file = FOpen("coop-resume-state.txt");
    string state = "";
    if(file) { state = FRead(file); FClose(file); }
    if(state == "ERROR") { OldGameStage = 94; return; }
    if(state != "READY:" + OldResumeHash) return;
    for(int i = 0; i < 2; i++)
    {
        int army = i * 3;
        SendCommandA(army, EXT_SetPlayerMenuType, 0);
        int base = SendCommandC(EXT_GetIdByName, "Char" + itoa(OldResumeChar[i]));
        SendCommand(EXT_SetHeroPDId, army, base, true);
        SendCommand(EXT_SetHeroPDClr, army, OldResumeColor[i]);
        if(SendCommandA(army, 351) != 1) { OldGameStage = 94; return; }
        OldGameHeroSeen[army] = 1; OldGameColorSeen[army] = 1;
    }
    if(SendCommandA(0, 352) != 1 || SendCommandA(0, 350, 1) != 1) { OldGameStage = 94; return; }
    int proof = FCreate("coop-resume-proof.txt");
    if(!proof) { OldGameStage = 94; return; }
    FWrite(proof, OldResumeHash); FWrite(proof, "END"); FClose(proof);
    OldMenuClearResult = SendCommandA(0, 345);
    // A fresh process has no active shared purse. Bind the restored owners
    // before map load; later entries retain and validate these same identities.
    if(SendCommandA(0, 203, 0, 0, 0) != 1) { OldGameStage = 94; return; }
    OldResumeLoaded = 1;
}

OldResumeSignature()
{
    if(!OldResumeLoaded) return "";
    int file = FOpen("coop-resume-state.txt");
    string state = "";
    if(file) { state = FRead(file); FClose(file); }
    if(state == "ERROR") { OldGameStage = 94; return ""; }
    if(state != "OK:" + OldResumeHash) return "";
    return "/S1/" + OldResumeHash;
}

OldResumeWaiting()
{
    OldBrowserWaiting("Продолжение");
    OldBrowserText("ListHeading", "Миссия " + OldMissionLabel(OldResumeMission));
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
            OldMenuRow(row + 2, "Герой из сохранения");
        }
        else OldMenuRow(row + 2, "Ожидание подключения");
    }
    string detail = "Ожидание напарника.\n\nОба героя и инвентарь\nбудут восстановлены.\n\nСоздавать персонажей\nзаново не нужно.";
    if(OldGamePlayers == 2)
    {
        detail = "Загрузка сохранения...\n\nВосстановление героев\nи прогресса кампании.";
        if(OldResumeCount > 0)
        {
            int percent = OldResumeIndex * 100 / OldResumeCount;
            if(percent < 0) percent = 0;
            if(percent > 100) percent = 100;
            detail += "\n\nПередано: " + itoa(percent) + "%";
        }
    }
    if(OldGameStage >= 4)
        detail = "Сохранение загружено.\n\nЗапуск миссии " + OldMissionLabel(OldResumeMission) + "...\n\nПодождите немного.";
    if(OldCreateHealth == 1) OldMenuRow(12, "Тест: бесконечное здоровье");
    Action(OldMenuDetails, ACT_SET_TEXT, &detail);
}
''')


def compose(source):
    from old_native_campaign_menu import _once
    assert CHUNK == 240 and MAX_CHUNKS == 2048
    source = _once(source, 'static int OldMenuHost = 0;', DECLARATIONS + '\nstatic int OldMenuHost = 0;')
    source = _once(source, 'OldMenuSessionMatches(string label)', SCRIPT + '\nOldMenuSessionMatches(string label)')
    source = _once(source, 'OldCreateTact()\n{', 'OldCreateTact()\n{\n    OldResumeTact();\n    if(OldResumeMode != 0 || OldGameStage >= 90) return;')
    source = _once(source, 'OldCreateSignature()\n{', 'OldCreateSignature()\n{\n    if(OldResumeMode == 1) return OldResumeSignature();')
    source = _once(source, 'OldCreateWaiting()\n{', 'OldCreateWaiting()\n{\n    if(OldResumeMode == 1) { OldResumeWaiting(); return; }')
    source = _once(source, '    if(OLD_GAME_HOST) NetSend(18, OldCreateHealth);', '    OldResumePublish();\n    if(OldResumeMode != 0) return;')
    start = source.index('    if(!OLD_GAME_HOST && (message = NetReceive(18, 0)) != "")')
    end = source.index('    for(int army', start)
    source = source[:start] + '    OldResumeReceive();\n    if(OldResumeMode != 0) return;\n' + source[end:]
    source = _once(source, '    if(OldGameStage == 7) return;\n    CommonTact();',
                   '    if(OldGameStage == 7) { OldCheckpointTact(); return; }\n    CommonTact();')
    source = _once(source, '    NetProperty(NET_GAME_START, OLD_GAME_MAP);',
        '    string target = OldResumeMap();\n'
        '    if(OldResumeMode == 1) NetProperty(NET_GAME_START, target);\n'
        '    else OldCheckpointBegin(1, target);')
    source = _once(source, '    OldMenuHost = host;',
        '    OldMenuHost = host;\n    OldResumeMode = -1; OldResumeHeader = "";')
    source = _once(source, 'OldMenuLeave(int mainMenu)\n{',
        'OldMenuLeave(int mainMenu)\n{\n'
        '    if(OldResumeInput) { FClose(OldResumeInput); OldResumeInput = 0; }\n'
        '    if(OldResumeOutput) { FClose(OldResumeOutput); OldResumeOutput = 0; }')
    source = _once(source, '        if(OldGameStage == 96) detail = ',
        '        if(OldGameStage == 94 && OldResumeMode == 1) detail = "Ошибка загрузки сохранения.\\nПроверьте журнал\\nлаунчера. Нажмите Отмена.";\n'
        '        if(OldGameStage == 96) detail = ')
    source = _once(source, '    OldGameValue(file, "creation_stage", OldCreateStage);',
        '    OldGameValue(file, "resume_mode", OldResumeMode);\n'
        '    OldGameValue(file, "resume_mission", OldResumeMission);\n'
        '    OldGameValue(file, "resume_index", OldResumeIndex);\n'
        '    OldGameValue(file, "resume_loaded", OldResumeLoaded);\n'
        '    OldGameValue(file, "creation_stage", OldCreateStage);')
    return source
