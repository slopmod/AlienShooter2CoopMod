"""Generate a guarded Level_01 -> Level_02 native session transition.

prepare(root) reads the original sources through prepare_finish and returns
script text plus metadata. patch(text) transforms only the pinned generated
finish helper. Neither function writes files or touches a running process.

The shared 120-call dwell is not a network-ready barrier. The host sends one
native NET_GAME_START; the existing engine owns the map load and input sync.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from old_native_finish_patch import prepare as prepare_finish, SOURCES


FEATURE = 'old-campaign-level02-transition-v1'
FINISH_FEATURE = 'old-campaign-finish-v1'
FINISH_HELPER_SHA256 = 'f5d5b68f0367e5bf84976e2272089a101254c8f79dc039cb39b8e2373828f8d1'
DWELL_CALLS = 120
TARGET_MAP = r'maps\Level_02.map'

GLOBALS = '''
#include "maps\\old_campaign_checkpoint.lgc"
// Shared counters are independent of observer frames and UI/input timing.
static int OldTransitionStage = 0; // 0=playing, 1=dwell, 2=requested, 90=fault
static int OldTransitionFault = 0; // 1=session, 2=party, 3=progression
static int OldTransitionTactCount = 0;
static int OldTransitionCommitTact = -1;
static int OldTransitionCommitTime = -1;
static int OldTransitionFirstCompletedTact = -1;
static int OldTransitionFirstCompletedTime = -1;
static int OldTransitionDwellCalls = 0;
static int OldTransitionRequests = 0; // Shared decision count, both peers.
static int OldTransitionRequestTact = -1;
static int OldTransitionRequestTime = -1;
static int OldTransitionHostCalls = 0; // Local diagnostic, exclude peer equality.
static int OldFinishWaitingText = 0;
static string OldFinishWaitingValue = "";
'''

TRANSITION = r'''
OldFinishWaiting()
{
    string text = "";
    if(OldFinishStage == 1 && (OldFinishHeroReady(0) || OldFinishHeroReady(3)) &&
       (!OldFinishHeroReady(0) || !OldFinishHeroReady(3)))
    {
        text = "Для перехода соберитесь вдвоём внутри лифта.";
        if(!Flagman(0) || !Flagman(3) || Action(Flagman(0), ACT_GET_HP) <= 0 ||
           Action(Flagman(3), ACT_GET_HP) <= 0)
            text = "Переход невозможен: один из героев погиб. Возрождение пока недоступно.";
    }
    if(text == "")
    {
        if(OldFinishWaitingText) Destroy(OldFinishWaitingText);
        OldFinishWaitingText = 0;
    }
    else if(!OldFinishWaitingText)
        OldFinishWaitingText = CreateText(8, ScreenX()/2, ScreenY()-140+4000,
            4000, text, BEH_CENTER_X);
    else if(text != OldFinishWaitingValue)
        Action(OldFinishWaitingText, ACT_SET_TEXT, &text);
    OldFinishWaitingValue = text;
}

OldTransitionSessionValid()
{
    if(!NetProperty(NET_IS_CONNECT) || NetProperty(NET_NO_PLAYERS) != 2)
        return false;
    for(int army = 0; army < 8; army++)
    {
        int exists = NetProperty(NET_IS_PLAYER_EXIST + army) != 0;
        if(exists != (army == 0 || army == 3))
            return false;
    }
    int local = NetProperty(NET_N_LOCAL_PLAYER);
    if(local != 0 && local != 3)
        return false;
    if(NetProperty(NET_IS_HOST) && local != 0
        || !NetProperty(NET_IS_HOST) && local != 3)
        return false;
    return true;
}

OldTransitionFail(int fault)
{
    if(!OldTransitionFault)
    {
        OldTransitionFault = fault;
        OldTransitionStage = 90;
        OldFinishFault = 3;
        // Local presentation is never read by a shared transition decision.
        Destroy(OldFinishText2);
        OldFinishText2 = CreateText(13, ScreenX() / 2,
            ScreenY() - MISSION_STATE_Y + 20, 0,
            "Переход остановлен: состояние группы изменилось.", BEH_CENTER);
    }
    return true;
}

OldTransitionTact()
{
    if(OldTransitionFault || OldTransitionStage == 90)
        return true;
    // The native callback may now begin unloading sprites. Never validate
    // stale outgoing-map handles again or retry the native start request.
    if(OldTransitionStage == 2)
    {
        OldCheckpointTact();
        return true;
    }
    if(!OldTransitionSessionValid())
        return OldTransitionFail(1);
    if(!OldFinishHeroReady(0) || !OldFinishHeroReady(3))
        return OldTransitionFail(2);
    if(OldTransitionStage != 1 || OldFinishCompletions != 1
        || giCurLevCmpgn != 2 || giCurLevCmpgnReal != 1
        || OldFinishLevelAfter != 2
        || ToLower(NextMapName) != "maps\\level_02.map")
        return OldTransitionFail(3);

    if(OldTransitionFirstCompletedTact == -1)
    {
        OldTransitionFirstCompletedTact = OldTransitionTactCount;
        OldTransitionFirstCompletedTime = GetTime();
    }
    OldTransitionDwellCalls = OldTransitionDwellCalls + 1;
    if(OldTransitionDwellCalls < 120)
        return true;
    // Set shared state first, identically on both peers. This is a dwell,
    // not an acknowledgement that the other computer has loaded Level_02.
    OldTransitionStage = 2;
    OldTransitionRequests = OldTransitionRequests + 1;
    OldTransitionRequestTact = OldTransitionTactCount;
    OldTransitionRequestTime = GetTime();
    if(NetProperty(NET_IS_HOST))
    {
        OldTransitionHostCalls = OldTransitionHostCalls + 1;
        // Void native API. Client waits for tag0x86; it must not call Load.
        OldCheckpointBegin(giCurLevCmpgn, "maps\\Level_02.map");
    }
    return true;
}
'''


def _script_bytes(text: str) -> bytes:
    return text.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1251')


def patch(source: str) -> tuple[str, dict]:
    """Transform exactly the generated old-campaign-finish-v1 helper."""
    if not isinstance(source, str):
        raise TypeError('Expected generated finish helper text')
    source = source.replace('\r\n', '\n')
    if hashlib.sha256(_script_bytes(source)).hexdigest() != FINISH_HELPER_SHA256:
        raise ValueError('Unsupported generated finish helper for Level_02 transition')
    changes = (
        ('    if(OldFinishStage != 1)\n', '    OldFinishWaiting();\n    if(OldFinishStage != 1)\n'),
        ('static int OldFinishText3 = 0;\n', 'static int OldFinishText3 = 0;\n' + GLOBALS),
        ('OldFinishTact()\n{', TRANSITION + '\nOldFinishTact()\n{'),
        ('"Продолжение кампании пока недоступно."', '"Переход ко второй миссии..."'),
        ('    if(OldFinishFault || OldFinishStage == 2)\n        return true;\n',
         '    OldTransitionTactCount = OldTransitionTactCount + 1;\n'
         '    if(OldFinishFault)\n        return true;\n'
         '    if(OldFinishStage == 2)\n        return OldTransitionTact();\n'),
        ('    if(!NetProperty(NET_IS_CONNECT) || NetProperty(NET_NO_PLAYERS) != 2\n'
         '        || giCurLevCmpgn != 1 || giCurLevCmpgnReal != 1)\n',
         '    if(!OldTransitionSessionValid()\n'
         '        || giCurLevCmpgn != 1 || giCurLevCmpgnReal != 1)\n'),
        ('    OldFinishShowText();\n    Pause(1);\n    return true;\n',
         '    OldFinishShowText();\n'
         '    OldTransitionStage = 1;\n'
         '    OldTransitionCommitTact = OldTransitionTactCount;\n'
         '    OldTransitionCommitTime = GetTime();\n'
         '    // Keep native input synchronization ticking during the dwell.\n'
         '    // Controls stay NONE; Level_02 initialization must restore them.\n'
         '    Pause(0);\n'
         '    return true;\n'),
    )
    output = source
    for before, after in changes:
        if output.count(before) != 1:
            raise ValueError('Finish transition source anchor changed: ' + repr(before[:80]))
        output = output.replace(before, after)
    return output, {
        'feature': FEATURE,
        'requires_finish_feature': FINISH_FEATURE,
        'input_sha256': FINISH_HELPER_SHA256,
        'output_sha256': hashlib.sha256(_script_bytes(output)).hexdigest(),
        'source_sha256': dict(SOURCES),
        'helper_file': 'Maps/old_campaign_finish.lgc',
        'scope': 'Original Level_01 completed party to native Level_02 load request',
        'target_map': TARGET_MAP,
        'dwell_calls': DWELL_CALLS,
        'dwell_counter': 'Incremented only by the 120 subsequent OldFinishTact calls in completed stage; commit call is not counted.',
        'observer_order': 'Observer runs before helper: first completed sample C+1, native request after observer C+120; 101 stable frames fit before request.',
        'shared_request_count': 'OldTransitionRequests records one decision on both peers, not a confirmed native load.',
        'local_only_fields': ['OldTransitionHostCalls'],
        'native_api': 'Host calls NetProperty(NET_GAME_START, target) once; client waits for native notification.',
        'progression': 'Retain original guarded completion/rewards; current level becomes2 while physical level/giCurLevCmpgnReal stay1 until native load.',
        'pause': 'Pause(0) after commit; control NONE and ACT_STOP remain in place. No global world freeze is claimed.',
        'error_policy': 'Invalid session/party/progression stops the transition with fault state and skips GameTact; no retry or disconnect.',
        'original_finish_guards_retained': True,
        'original_level01_map_guard': SOURCES['Maps/Level_01.map'],
        'new_state_setters': ['transition bookkeeping', 'Pause(0)', 'one host NET_GAME_START'],
        'rng_calls_added': 0,
        'network_ready_barrier': False,
        'rpg_preservation_proven': False,
        'level02_initialization_required': True,
        'durable_save_proven': False,
        'runtime_tested': False,
    }


def prepare(old_root: Path) -> tuple[str, dict]:
    """Read hash-guarded original inputs; return transition helper, never write."""
    finish_text, finish_metadata = prepare_finish(Path(old_root))
    if finish_metadata.get('feature') != FINISH_FEATURE:
        raise ValueError('Unexpected generated finish feature')
    output, metadata = patch(finish_text)
    metadata['original_finish'] = finish_metadata
    return output, metadata
