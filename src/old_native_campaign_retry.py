"""Connected checkpoint retry: reuse the production save transfer and barrier.

The host stages a durable save before NET_GAME_START enters this empty menu map.
Both existing DirectPlay peers remain connected. Only this map permits clearing
old world command/shop ownership; normal checkpoint imports remain fail closed.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping

from old_native_campaign_menu import _encode, _once, _replace_function, _text

FEATURE = 'old-native-campaign-retry-v1'
SCRIPT_PATH = 'Maps/old_campaign_retry.lgc'
MAP_PATH = 'Maps/old_campaign_retry.map'

DECLARATIONS = r'''
static string OldRetryNonce = "";
static string OldRetryExpectedHash = "";
static int OldRetryExpectedMission = 0;
OldRetrySend(int channel, string payload);
OldRetryReceive(int channel, int army);
OldGameRefresh();
OldMenuCheckRoster();
'''

SCRIPT = r'''
OldRetryReadReceipt()
{
    int file = FOpen("coop-retry-status.txt");
    if(!file) return false;
    string nonce = FRead(file);
    string state = FRead(file);
    string hash = FRead(file);
    int mission = FRead(file);
    string end = FRead(file);
    FClose(file);
    if(state != "READY" || end != "END" || nonce == ""
        || strlen(nonce) > 10 || strlen(hash) != 64 || mission < 1) return false;
    // Simulation time can repeat after loading the same checkpoint. The
    // service's attempt counter stays monotonic while this connection lives.
    file = FOpen("coop-retry-attempt.txt");
    if(!file) return false;
    string request = FRead(file);
    string attempt = FRead(file);
    string selected = FRead(file);
    end = FRead(file);
    FClose(file);
    if(request != nonce || selected != hash || end != "END"
        || attempt == "" || strlen(attempt) > 10) return false;
    OldRetryNonce = attempt;
    OldRetryExpectedHash = hash;
    OldRetryExpectedMission = mission;
    return true;
}

OldRetrySend(int channel, string payload)
{
    if(OldRetryNonce == "") return;
    // All save chunks and launch acknowledgements belong to this retry. An
    // earlier lobby's tail cannot satisfy the new restore/launch barrier.
    if(channel >= 16)
        payload = "R1:" + OldRetryNonce + ":" + payload;
    OldLobbySend(channel, payload);
}

OldRetryReceive(int channel, int army)
{
    string message = OldLobbyReceive(channel, army);
    if(channel < 16 || message == "") return message;
    if(StrBefore(message, ":") != "R1") return "";
    message = StrAfter(message, ":");
    string nonce = StrBefore(message, ":");
    message = StrAfter(message, ":");
    if(nonce == "" || strlen(nonce) > 10) return "";
    if(OldRetryNonce == "" && channel == 18 && army == 0
        && !OLD_GAME_HOST && StrBefore(message, ":") == "S1")
        OldRetryNonce = nonce;
    if(nonce != OldRetryNonce) return "";
    return message;
}

OldRetryAttach()
{
    OldMenuInitialized = 1;
    OldMenuHost = NetProperty(NET_IS_HOST) != 0;
    // A native map transition has discarded the dead world. Switch to the
    // same non-gameplay map type as the ordinary checkpoint/creation lobby.
    SetMapTypeEx(MAP_TYPE_PLAYERMENU, "");
    SetCursor(CURSOR_NORMAL);
    SetScrollType(SCROLL_NONE);
    GameType = 1;
    OldGameRefresh();
    OldMenuConnectTime = GetTime();
    OldMenuConnectionSeen = 1;
    OldGameStage = 3;
    OldCreateStage = 3;
    OldCreateApplied[0] = "saved";
    OldCreateApplied[3] = "saved";
    OldMenuReady = 1;
    OldMenuStartRequested = 1;
    OldGamePrevArmy = OldGameLocalArmy;
    MenuRelease();
    MenuLoad("maps\\old_campaign_browser.men");
    OldBrowserBind();
    OldBrowserWaiting("Загрузка сохранения");
    OldMenuDetails = MenuFindNamed("BrowserDetails");
    OldMenuClearResult = SendCommandA(0, 345);
    if(!OldGameConnected || OldGamePlayers != 2
        || OldGameLocalArmy != 3 * (1 - OLD_GAME_HOST))
    { OldLobbyFail("retry_party"); return; }
    // Drain the bounded shared script ring before publishing the new nonce.
    // Native input (tag zero) is never read or discarded by the script.
    OldLobbyReceiveBudget = 0;
    for(int pass = 0; pass < 8; pass++)
    {
        int before = OldLobbyReceiveBudget;
        for(int channel = 1; channel < 20; channel++)
            if(channel <= 7 || channel >= 16) OldLobbyReceive(channel, -1);
        if(before == OldLobbyReceiveBudget || OldLobbyReceiveBudget >= 64) break;
    }
    // These native APIs are authorized exclusively by this exact empty map.
    // Reset BEFORE recreating descriptors, reading save chunks or sending ACKs.
    if(SendCommandA(0, 353) != 1 || SendCommandA(0, 354) != 1)
    { OldLobbyFail("retry_reset"); return; }
    if(OLD_GAME_HOST)
    {
        if(!OldRetryReadReceipt()) { OldLobbyFail("retry_receipt"); return; }
        for(int setting = 0; setting < 5; setting++) OldGameSettings[setting] = 1;
    }
    OldMenuCheckRoster();
    Effect(EFF_FADE_OUT, 0, 0, FADE_GAME_TIME);
}
'''

MAIN = r'''
main()
{
    OldGameFrame++;
    if(!OldMenuInitialized) OldRetryAttach();
    OldLobbyTick();
    if(OldGameStage == 7) return;
    CommonTact();
    int clicked = MenuLClick();
    if(GetKey() == VK_ESCAPE || (clicked && (clicked == MenuFindNamed("ExitButton")
        || clicked == MenuFindNamed("SearchButton"))))
    { OldMenuLeave(1); return; }
    OldGameRefresh();
    if(OldGameStage >= 3 && OldGameStage <= 6 && OldMenuConnectionReady())
    {
        if((OLD_GAME_HOST && !NetProperty(NET_IS_HOST))
            || (!OLD_GAME_HOST && NetProperty(NET_IS_HOST))) OldGameStage = 93;
        OldMenuCheckRoster();
        if(OldGameStage < 90)
        {
            OldLobbyDrainLocal();
            for(int pass = 0; pass < 4; pass++)
            {
                int before = OldLobbyReceiveBudget;
                OldGameReceive();
                if(OldGameStage >= 90) break;
                OldResumeReceive();
                if(OldGameStage >= 90 || before == OldLobbyReceiveBudget) break;
            }
            if(OldGameStage < 90) OldResumeTact();
            if(OldGameStage < 90)
            {
                OldGamePublish();
                OldResumePublish();
                OldGameBarrier();
            }
        }
    }
    if(OldGameStage == 7) return;
    if(clicked || OldGameFrame % 8 == 0) OldMenuWaiting();
    if(GetTime() - OldLobbyLastStateTime >= 1000)
    { OldLobbyLastStateTime = GetTime(); OldGameWriteState(); }
}
'''


def prepare(menu_files: Mapping[str, bytes]) -> tuple[dict[str, bytes], dict]:
    """Derive only the connected retry files from the final guarded menu files."""
    source = _text(menu_files['Maps/old_campaign_lobby.lgc'])
    if '#define OLD_GAME_HOST OldMenuHost' not in source:
        raise ValueError('Retry requires the production role-independent campaign menu')
    source = _replace_function(source, 'main', MAIN.strip())
    source = _replace_function(source, 'OldMenuConnect',
        'OldMenuConnect(int host)\n{ OldLobbyFail("retry_connect_forbidden"); }')
    source = _replace_function(source, 'OldGameLocalHero',
        'OldGameLocalHero()\n{ OldGamePrevArmy = OldGameLocalArmy; }')
    source = _replace_function(source, 'OldCreateTact',
        'OldCreateTact()\n{ OldResumeTact(); }')
    source = _once(source, 'static int OldGameFrame = 0;', DECLARATIONS + '\nstatic int OldGameFrame = 0;')
    # Wrap protocol callers, not the rate-limiter definitions or its actual
    # native primitives. Local echo drain deliberately consumes raw envelopes.
    from old_native_campaign_menu import _function
    for name in ('OldGamePublish', 'OldGameReceive', 'OldGameBarrier',
                 'OldResumePublish', 'OldResumeReceive'):
        start, end = _function(source, name)
        body = source[start:end].replace('OldLobbySend(', 'OldRetrySend(').replace(
            'OldLobbyReceive(', 'OldRetryReceive(')
        source = source[:start] + body + source[end:]
    source = _once(source, '    OldCreateHealth = message;\n    OldResumeMode = 1;',
        '    if(OLD_GAME_HOST && (OldResumeHash != OldRetryExpectedHash\n'
        '        || OldResumeMission != OldRetryExpectedMission))\n'
        '    { OldLobbyFail("retry_save_changed"); return; }\n'
        '    OldCreateHealth = message;\n    OldResumeMode = 1;')
    source = _once(source, '    if(mode == "N1")',
        '    if(mode != "S1") { OldLobbyFail("retry_requires_save"); return; }\n'
        '    if(mode == "N1")')
    source = _once(source, '    return "/S1/" + OldResumeHash;',
        '    return "/S1/" + OldResumeHash + "/R1/" + OldRetryNonce;')
    source = _once(source, 'OldGameRefresh()\n{', SCRIPT + '\nOldGameRefresh()\n{')
    source = _once(source, '    OldGameValue(file, "resume_mode", OldResumeMode);',
        '    FWrite(file, "retry_nonce=" + OldRetryNonce);\n'
        '    OldGameValue(file, "resume_mode", OldResumeMode);')
    source = source.replace('old-game-lobby-state.txt', 'old-game-retry-state.txt')
    files = {SCRIPT_PATH: _encode(source), MAP_PATH: menu_files['Maps/old_campaign_lobby.map']}
    return files, {'feature': FEATURE, 'entry_map': 'maps\\old_campaign_retry.map',
        'connected_peers_preserved': True, 'character_creation': False,
        'checkpoint_protocol': 'existing S1 transfer, native proof and prepare/ACK barrier',
        'retry_nonce_channels': [16, 17, 18, 19], 'native_reset_commands': [353, 354],
        'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw)}
                  for name, raw in files.items()}}
