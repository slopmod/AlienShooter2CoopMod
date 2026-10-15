"""Bounded lobby-only traffic over the original reliable, loopback transport.

The native 64-slot ring is shared by script and gameplay packets. These helpers
never change native input transport or discard a remote creation/save operation.
Apply last, after character creation, checkpoint and browser composition.
"""
from __future__ import annotations

import re

FEATURE = 'old-native-lobby-transport-v1'
RETRY_MS = 500
BARRIER_RETRY_MS = 250
DRAIN_PASSES = 4

DECLARATIONS = r'''
static string OldLobbyLastSent[20];
static int OldLobbySentTime[20];
static int OldLobbySentSeen[20];
static int OldLobbySentCount = 0;
static int OldLobbyReceivedCount = 0;
static int OldLobbyDrainedCount = 0;
static int OldLobbyReceiveBudget = 0;
static int OldLobbyLastChannel = -1;
static int OldLobbyLastSender = -1;
static int OldLobbyLastReceiveSize = 0;
static int OldLobbyLastStateTime = 0;
static string OldLobbyError = "";
OldLobbySend(int channel, string payload);
OldLobbyReceive(int channel, int army);
OldLobbyTick();
OldLobbyDrainLocal();
OldLobbyFail(string reason);
OldGameWriteState();
'''

SCRIPT = r'''
OldLobbySend(int channel, string payload)
{
    // No catch-up bursts after a slow frame. New save chunks/ACKs go at once;
    // identical retries are bounded by elapsed menu time, independent of FPS.
    if(channel < 1 || channel >= 20 || OldGamePlayers < 2
        || OldGameStage == 7 || OldGameStage >= 90) return;
    int now = GetTime();
    int retry = 500;
    if(channel == 16 || channel == 17) retry = 250;
    if(OldLobbySentSeen[channel] && OldLobbyLastSent[channel] == payload
        && now - OldLobbySentTime[channel] < retry) return;
    OldLobbyLastSent[channel] = payload;
    OldLobbySentTime[channel] = now;
    OldLobbySentSeen[channel] = 1;
    OldLobbySentCount++;
    NetSend(channel, payload);
}

OldLobbyReceive(int channel, int army)
{
    if(OldLobbyReceiveBudget >= 64) return "";
    string message = NetReceive(channel, army);
    if(message != "")
    {
        OldLobbyReceiveBudget++;
        OldLobbyReceivedCount++;
        OldLobbyLastChannel = channel;
        OldLobbyLastSender = army;
        OldLobbyLastReceiveSize = strlen(message);
    }
    return message;
}

OldLobbyDrainLocal()
{
    if(OldGameLocalArmy < 0 || OldGameLocalArmy > 7) return;
    // DirectPlay includes the sender. Header handling reads only host->guest;
    // save transfer reads only the opposite army. Consume their local echoes.
    // Channel19 character drafts still go through OldCreateReceive unchanged.
    for(int pass = 0; pass < 8; pass++)
    {
        int before = OldLobbyReceiveBudget;
        if(OLD_GAME_HOST && OldLobbyReceive(18, OldGameLocalArmy) != "") OldLobbyDrainedCount++;
        if(OldResumeMode == 1 && OldLobbyReceive(19, OldGameLocalArmy) != "") OldLobbyDrainedCount++;
        if(before == OldLobbyReceiveBudget) return;
    }
}

OldLobbyTick()
{
    OldLobbyReceiveBudget = 0;
    // Error screens used to stop receiving while the other peer kept sending.
    // The host also waits here for durable autosave after the prepare/ACK.
    // Drain only lobby script channels; never the native tag-zero input queue.
    if(OldGameStage != 7 && OldGameStage < 90) return;
    for(int pass = 0; pass < 8; pass++)
    {
        int before = OldLobbyReceiveBudget;
        for(int channel = 1; channel < 20; channel++)
            if(channel <= 7 || channel >= 16)
                if(OldLobbyReceive(channel, -1) != "") OldLobbyDrainedCount++;
        if(before == OldLobbyReceiveBudget || OldLobbyReceiveBudget >= 64) return;
    }
}

OldLobbyFail(string reason)
{
    OldGameStage = 94;
    if(OldLobbyError != "") return;
    OldLobbyError = reason;
    Log2("CoopLobby: failure=" + reason + " channel=" + itoa(OldLobbyLastChannel)
        + " sender=" + itoa(OldLobbyLastSender) + " size=" + itoa(OldLobbyLastReceiveSize));
    OldGameWriteState();
}
'''


def compose(source: str) -> str:
    from old_native_campaign_menu import _function, _once, _replace_function

    # Preserve a precise first failure even if a later disconnect changes stage.
    # Function/site labels refer to the composed source, not a guessed cause.
    functions = re.findall(r'^(\w+)\([^\n]*\)\s*\n\{', source, re.M)
    for name in functions:
        start, end = _function(source, name)
        body = source[start:end]
        for site in range(1, body.count('OldGameStage = 94;') + 1):
            body = body.replace('OldGameStage = 94;', f'OldLobbyFail("{name}:{site}");', 1)
        source = _replace_function(source, name, body)

    # NetSend's VM wrapper converts integers; use explicit text for user-script
    # function arguments rather than depending on that native-only coercion.
    for channel, value in ((1, 'OldGameTimeLimit'), (2, 'OldGameFragLimit'),
                           (3, '2'), (4, '1'), (7, 'OldGameRespawnWeapon'),
                           (5, 'SendCommand(EXT_GetHeroPDClr, OldGameLocalArmy)'),
                           (6, 'SendCommand(EXT_GetHeroPDId, OldGameLocalArmy)')):
        source = _once(source, f'NetSend({channel}, {value});',
                       f'NetSend({channel}, itoa({value}));')
    source = source.replace('NetSend(', 'OldLobbySend(')
    source = re.sub(r'NetReceive\((\d+)\)', r'OldLobbyReceive(\1, -1)', source)
    source = source.replace('NetReceive(', 'OldLobbyReceive(')
    # Only the old periodic *network* gates use 20 frames. Polling every tick
    # lets the wrapper send changed payloads immediately and retry by time.
    if source.count('if(OldGameFrame % 20 == 0)') != 4:
        raise ValueError('Expected four original lobby publish/barrier gates')
    source = source.replace('if(OldGameFrame % 20 == 0)', 'if(OldGameStage < 90)')

    source = _once(source, '    OldGameFrame++;', '    OldGameFrame++;\n    OldLobbyTick();')
    # Move the creator's once-per-frame receive into the bounded shared drain.
    source = _once(source, '\n                    OldCreateReceive();\n', '\n')
    source = _once(source, '                    OldGameReceive();',
        '                    OldLobbyDrainLocal();\n'
        '                    for(int receivePass = 0; receivePass < 4; receivePass++)\n'
        '                    {\n'
        '                        int receivedBefore = OldLobbyReceiveBudget;\n'
        '                        OldGameReceive();\n'
        '                        if(OldGameStage >= 90) break;\n'
        '                        OldCreateReceive();\n'
        '                        if(OldGameStage >= 90 || receivedBefore == OldLobbyReceiveBudget) break;\n'
        '                    }')
    source = _once(source, '        OldMenuRoster = roster;',
        '        for(int channel = 1; channel < 20; channel++) OldLobbySentSeen[channel] = 0;\n'
        '        OldMenuRoster = roster;')
    source = _once(source, '                    OldGameBarrier();',
        '                    if(OldGameStage < 90) OldGameBarrier();')
    source = _once(source, '    if(OldGameFrame % 60 == 0) OldGameWriteState();',
        '    if(GetTime() - OldLobbyLastStateTime >= 1000)\n'
        '    { OldLobbyLastStateTime = GetTime(); OldGameWriteState(); }')
    source = _once(source, '    OldGameValue(file, "end_frame", OldGameFrame);',
        '    FWrite(file, "lobby_error=" + OldLobbyError);\n'
        '    OldGameValue(file, "lobby_sent", OldLobbySentCount);\n'
        '    OldGameValue(file, "lobby_received", OldLobbyReceivedCount);\n'
        '    OldGameValue(file, "lobby_drained", OldLobbyDrainedCount);\n'
        '    OldGameValue(file, "lobby_last_channel", OldLobbyLastChannel);\n'
        '    OldGameValue(file, "lobby_last_sender", OldLobbyLastSender);\n'
        '    OldGameValue(file, "lobby_last_size", OldLobbyLastReceiveSize);\n'
        '    OldGameValue(file, "end_frame", OldGameFrame);')
    source = _once(source,
        'detail = "Несовместимые настройки.\\nОбоим игрокам нужна\\nодна версия мода.\\nНажмите Отмена.";',
        'detail = "Ошибка согласования\\nкампании.\\nКод: " + OldLobbyError + "\\nНажмите Отмена.";')
    source = _once(source,
        'detail = "Ошибка загрузки сохранения.\\nПроверьте журнал\\nлаунчера. Нажмите Отмена.";',
        'detail = "Ошибка загрузки\\nсохранения.\\nКод: " + OldLobbyError + "\\nПроверьте журнал лаунчера.";')
    source = _once(source, 'static int OldGameFrame = 0;', DECLARATIONS + '\nstatic int OldGameFrame = 0;')
    source = _once(source, 'OldGameRefresh()\n{', SCRIPT + '\nOldGameRefresh()\n{')
    return source


def metadata() -> dict:
    return {'feature': FEATURE, 'unchanged_retry_ms': RETRY_MS,
            'barrier_retry_ms': BARRIER_RETRY_MS, 'receive_passes': DRAIN_PASSES,
            'receive_budget_per_tick': 64, 'sender_echo_drain_channels': [18, 19],
            'changed_payload_immediate': True, 'native_gameplay_transport_unchanged': True,
            'first_failure_site_in_state_and_log': True}
