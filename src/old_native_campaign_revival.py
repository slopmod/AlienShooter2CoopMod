"""Shared death receipts and five-second assistance for every campaign map.

Only native hero death callbacks admit a casualty. Presentation and the host's
retry request never decide a resurrection; both peers use simulation time,
the same party positions and a fixed collision-free placement order.
"""
from pathlib import Path
import hashlib

FEATURE = 'old-campaign-revival-v1'
HELPER_PATH = 'Maps/old_campaign_revival.lgc'
NETWORK_PATH = 'Maps/common_network.lgc'
NETWORK_SHA256 = 'cbcbbf725e43451ec6a31241b459fd012fd3a5671adbbaf602cd8acaec0c6462'
RADIUS = 120
DURATION_MS = 5000

HELPER = r'''
#ifndef OLD_CAMPAIGN_REVIVAL_H
#define OLD_CAMPAIGN_REVIVAL_H 1
static int OldReviveDead[8];
static int OldReviveActor[8];
static int OldReviveBirth[8];
static int OldReviveDeathActor[8];
static int OldReviveDeathBirth[8];
static int OldReviveX[8];
static int OldReviveY[8];
static int OldReviveZ[8];
static int OldReviveSince[8];
static int OldReviveCount[8];
static int OldReviveBlocked[8];
static int OldReviveMarker[8];
static int OldReviveText = 0;
static string OldReviveMessage = "";
static int OldReviveWipe = 0;
static int OldReviveRetryStage = 0;
static int OldReviveRetryNonce = 0;
static int OldReviveRetryTime = 0;
static int OldReviveRightReleased = 0;
static int OldReviveSpawnX = 0, OldReviveSpawnY = 0, OldReviveSpawnZ = 0;

OldCampaignReviveRemember()
{
    for(int army = 0; army <= 3; army += 3)
    {
        int unit = Flagman(army);
        if(unit && GetVid(unit) == GetFlagmanVid(army) && !OldReviveDead[army])
        {
            OldReviveActor[army] = unit;
            OldReviveBirth[army] = Action(unit, ACT_GET_BIRTH_TIME);
        }
    }
}

OldCampaignReviveDeath(int unit)
{
    int army = Action(unit, ACT_GET_ARMY);
    if((army != 0 && army != 3) || OldReviveDead[army]) return;
    if(GetVid(unit) != GetFlagmanVid(army)) return;
    // Flagman may already be cleared by the native death path. Never confuse
    // a saved corpse handle with a later allocation or a vehicle transition.
    int birth = Action(unit, ACT_GET_BIRTH_TIME);
    if(unit == OldReviveDeathActor[army] && birth == OldReviveDeathBirth[army]) return;
    // Escaping a vehicle may create a replacement hero later in GameTact,
    // before the next sampler. Accept that native binding as well.
    if(unit != Flagman(army) && unit != OldHeroes[army]
        && (unit != OldReviveActor[army] || birth != OldReviveBirth[army])) return;
    OldReviveDeathActor[army] = unit; OldReviveDeathBirth[army] = birth;
    OldReviveDead[army] = 1;
    OldReviveX[army] = GetX(unit); OldReviveY[army] = GetY(unit); OldReviveZ[army] = GetZ(unit);
    OldReviveSince[army] = 0;
    Log2("CoopRevive: death army=" + itoa(army));
}

OldReviveNear(int army)
{
    int rescuer = 3 - army;
    int unit = Flagman(rescuer);
    if(OldReviveDead[rescuer] || !unit || GetVid(unit) != GetFlagmanVid(rescuer)) return false;
    if(Action(unit, ACT_GET_HP) <= 0 || GetAnimation(unit) == 15 || GetAnimation(unit) == 16) return false;
    if(SizeTo(unit, OldReviveX[army], OldReviveY[army]) > @@RADIUS@@
        || Abs(GetZ(unit) - OldReviveZ[army]) > 48) return false;
    // Assistance cannot cross an intervening floor/terrain wall.
    return !IsLineUnderGround(GetX(unit), GetY(unit), GetZ(unit) + 24,
        OldReviveX[army], OldReviveY[army], OldReviveZ[army] + 24);
}

OldRevivePositionFree(int army, int x, int y)
{
    if(x < 32 || y < 32 || x >= MapSizeX()-32 || y >= MapSizeY()-32) return false;
    int z = GetGroundZ(x, y);
    if(Abs(z - OldReviveZ[army]) > 48 || SizeTo(Flagman(3-army), x, y) < 96) return false;
    if(IsLineUnderGround(OldReviveX[army], OldReviveY[army], OldReviveZ[army]+24, x, y, z+24)) return false;
    if(CanPlace(GetFlagmanVid(army), x, y, z)) return false;
    OldReviveSpawnX = x; OldReviveSpawnY = y; OldReviveSpawnZ = z;
    return true;
}

OldReviveFindPosition(int army)
{
    for(int radius = 0; radius <= 120; radius += 40)
        for(int direction = 0; direction < 256; direction += 32)
        if(radius || !direction)
        {
            int x = OldReviveX[army] + Cos(direction) * radius / 1024;
            int y = OldReviveY[army] + Sin(direction) * radius / 1024;
            if(OldRevivePositionFree(army, x, y)) return true;
        }
    return false;
}

OldReviveRestore(int army)
{
    // Wait for native death/vehicle cleanup to release the old flagman.
    // Do not destroy corpses, occupants or scenery to make a spawn possible.
    if(Flagman(army) || !OldReviveFindPosition(army)) return false;
    SendCommandA(army, EXT_RESETHEROHP);
    int unit = CreateSprite(GetFlagmanVid(army), OldReviveSpawnX, OldReviveSpawnY, OldReviveSpawnZ);
    if(!unit) return false;
    Action(unit, ACT_SET_ARMY, army);
    SetFlagman(army, unit);
    SetPlayerControl(army, PLAYERCONTROL_NORMAL);
    SendCommandA(army, EXT_DISABLEFLAGMANCONTROL, 0);
    OldReviveDead[army] = 0; OldReviveSince[army] = 0;
    OldReviveBlocked[army] = 0; OldReviveCount[army]++;
    OldCampaignReviveRemember();
    Hero_IsDirty[army] = true;
    Log2("CoopRevive: restored army=" + itoa(army));
    return true;
}

OldReviveNotice(string message)
{
    if(message == "")
    {
        Destroy(OldReviveText); OldReviveText = 0; OldReviveMessage = "";
        return;
    }
    if(!OldReviveText)
        OldReviveText = CreateText(3, ScreenX()/2, 80+4000, 4000, message, BEH_CENTER_X);
    else if(message != OldReviveMessage) Action(OldReviveText, ACT_SET_TEXT, &message);
    OldReviveMessage = message;
}

OldReviveClosePanels()
{
    for(int army = 0; army <= 3; army += 3)
        if(OldReviveDead[army]) OldShopClose(army);
    int local = NetProperty(NET_N_LOCAL_PLAYER);
    if((local == 0 || local == 3) && OldReviveDead[local])
    {
        if(OldShopVisible) OldShopClearPanel();
        OldShopLocalCapture = 0; OldShopLocalOpening = 0;
        SendCommandA(local, 328, 0);
    }
}

OldReviveRequestRetry()
{
    if(!OldReviveWipe || !NetProperty(NET_IS_HOST) || OldReviveRetryStage == 1 || OldReviveRetryStage == 2) return;
    OldReviveRetryNonce++;
    int file = FCreate("coop-retry-status.txt");
    if(!file) { OldReviveRetryStage = 90; return; }
    FWrite(file, "WAIT"); FClose(file);
    file = FCreate("coop-retry-request.txt");
    if(!file) { OldReviveRetryStage = 90; return; }
    FWrite(file, "AS2RETRY1"); FWrite(file, itoa(OldReviveRetryNonce)); FWrite(file, "END"); FClose(file);
    OldReviveRetryTime = GetTime(); OldReviveRetryStage = 1;
}

OldReviveRetryTact()
{
    if(!NetProperty(NET_IS_HOST))
    {
        OldReviveNotice("Оба героя погибли.\nОжидание: хост может загрузить последнее сохранение.");
        return;
    }
    int down = SendCommandA(0, 329, IM_RBUTTONDOWN);
    if(down == 0) OldReviveRightReleased = 1;
    if(down > 0 && OldReviveRightReleased)
    {
        OldReviveRightReleased = 0;
        OldReviveRequestRetry();
    }
    if(OldReviveRetryStage == 1)
    {
        int file = FOpen("coop-retry-status.txt");
        string nonce = "", status = "", hash = "", mission = "", end = "";
        if(file)
        {
            nonce = FRead(file); status = FRead(file); hash = FRead(file);
            mission = FRead(file); end = FRead(file); FClose(file);
        }
        if(nonce == itoa(OldReviveRetryNonce) && status == "READY" && strlen(hash) == 64 && end == "END")
        {
            OldReviveRetryStage = 2;
            Log2("CoopRevive: retry checkpoint=" + hash);
            NetProperty(NET_GAME_START, "maps\\old_campaign_retry.map");
        }
        else if(nonce == itoa(OldReviveRetryNonce) && status == "ERROR") OldReviveRetryStage = 90;
        else if(GetTime() - OldReviveRetryTime > 15000) OldReviveRetryStage = 90;
    }
    if(OldReviveRetryStage == 1 || OldReviveRetryStage == 2)
        OldReviveNotice("Оба героя погибли.\nЗагрузка последнего сохранения...");
    else if(OldReviveRetryStage >= 90)
        OldReviveNotice("Не удалось подготовить сохранение.\nПКМ — повторить. Esc — главное меню.");
    else OldReviveNotice("Оба героя погибли.\nХост: нажмите ПКМ, чтобы загрузить последнее сохранение.\nEsc — главное меню.");
}

OldCampaignReviveTact()
{
    if(OldReviveWipe && StartNextMap) { GoToNextMap(); return true; }
    OldCampaignReviveRemember();
    OldReviveClosePanels();
    if(OldReviveDead[0] && OldReviveDead[3])
    {
        if(!OldReviveWipe)
        {
            OldReviveWipe = 1;
            OldReviveSince[0] = 0; OldReviveSince[3] = 0;
            HideOptionsMenu();
            Log2("CoopRevive: party defeated");
        }
        // Keep the native command FIFO acknowledged; reject transactions with
        // the ordinary dead-hero guards. Do not clear pending commands in-world.
        OldShopTransportTact();
        OldReviveRetryTact();
        if(GetKey() == VK_ESCAPE) { GoToMainMenu(); GoToNextMap(); }
        return true;
    }
    string message = "";
    for(int army = 0; army <= 3; army += 3)
    {
        if(OldReviveDead[army])
        {
            if(!OldReviveNear(army))
            {
                OldReviveSince[army] = 0;
                OldReviveBlocked[army] = 0;
            }
            else
            {
                if(!OldReviveSince[army]) OldReviveSince[army] = GetTime();
                if(GetTime() - OldReviveSince[army] >= @@DURATION@@)
                    OldReviveBlocked[army] = !OldReviveRestore(army);
            }
        }
        if(OldReviveDead[army])
        {
            message = "Подойдите к погибшему союзнику и оставайтесь рядом 5 секунд.";
            if(army == NetProperty(NET_N_LOCAL_PLAYER)) message = "Вы погибли. Союзник может воскресить вас, постояв рядом 5 секунд.";
            if(OldReviveSince[army])
            {
                int left = (@@DURATION@@ - (GetTime()-OldReviveSince[army]) + 999) / 1000;
                if(left < 0) left = 0;
                message = "Воскрешение: " + itoa(left) + " сек. Не отходите от союзника.";
            }
            if(OldReviveBlocked[army]) message = "Воскрешение готово. Освободите место рядом с союзником.";
            string marker = "+ ВОСКРЕСИТЬ";
            // Same world-space font and placement as native network names.
            if(!OldReviveMarker[army]) OldReviveMarker[army] = CreateText(6,
                OldReviveX[army], OldReviveY[army], OldReviveZ[army]+85, marker, BEH_CENTER);
        }
        else if(OldReviveMarker[army])
        {
            Destroy(OldReviveMarker[army]); OldReviveMarker[army] = 0;
        }
    }
    OldReviveNotice(message);
    return false;
}
#endif
'''.replace('@@RADIUS@@', str(RADIUS)).replace('@@DURATION@@', str(DURATION_MS))


def prepare(root):
    from old_native_campaign_progression import once
    data = (Path(root) / NETWORK_PATH).read_bytes()
    if hashlib.sha256(data).hexdigest() != NETWORK_SHA256:
        raise ValueError('Unsupported native hero death callbacks')
    text = data.decode('cp1251').replace('\r\n', '\n')
    text = once(text, 'F250_15(int unit)\n{',
        '#ifdef OLD_CAMPAIGN_REVIVAL\nOldCampaignReviveDeath(int unit);\n#endif\n'
        'F250_15(int unit)\n{\n#ifdef OLD_CAMPAIGN_REVIVAL\n    OldCampaignReviveDeath(unit);\n#endif')
    return {NETWORK_PATH: text, HELPER_PATH: HELPER}


def adapt_level(source):
    from old_native_campaign_progression import once
    source = once(source, '#define COOP_CAMPAIGN 1', '#define COOP_CAMPAIGN 1\n#define OLD_CAMPAIGN_REVIVAL 1')
    source = once(source, '#include "maps\\old_campaign_shop.lgc"',
        '#include "maps\\old_campaign_shop.lgc"\n#include "maps\\old_campaign_revival.lgc"')
    return once(source, 'if(!OldCampaignReady) return;',
        'if(!OldCampaignReady) return;\n  if(OldCampaignReviveTact()) return;')


def adapt_init(source):
    from old_native_campaign_progression import once
    source = 'OldCampaignReviveRemember();\n' + source
    return once(source, '    OldCampaignReady = 1;',
        '    OldCampaignReady = 1;\n    OldCampaignReviveRemember();')
