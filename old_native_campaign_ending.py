"""Shared ending commit followed by independent, original slide presentation.

All character mutations happen once before any local input/effect state is
read. Slides never load a map in an active session. Leaving after completion
explicitly disconnects, just like the LAN menu. The view itself does not
require an active session. No synthetic reward/onward checkpoint is created.
"""

NAME = 'Maps/old_campaign_ending.lgc'


def adapt_script(source, *, picture_vid, text_prefix, original_body_sha256):
    """Reuse the original scene while separating shared completion from UI.

    Entry composition pins the complete stock script. This additional body
    guard prevents an upstream transform from silently losing finale logic.
    The map-specific quest condition and original slide constants stay intact.
    """
    import hashlib
    from old_native_campaign_progression import once

    anchor = '    if ( StartQuest )\n'
    if source.count(anchor) != 1:
        raise ValueError('Original campaign ending body changed')
    start = source.index(anchor)
    original_body = source[start:]
    if hashlib.sha256(original_body.encode('cp1251')).hexdigest() != original_body_sha256:
        raise ValueError('Unreviewed original campaign ending body')
    view = f'OldCampaignEndingView({picture_vid}, "{text_prefix}");'
    source = source[:start] + '''    if(StartQuest && GetTime()-StartQuest > 2000)
    {
        OldCampaignEndingCommit();
        @@VIEW@@
    }
}
'''.replace('@@VIEW@@', view)
    source = once(source, 'static int StartQuest = 0;',
                  '#include "maps\\old_campaign_ending.lgc"\n\nstatic int StartQuest = 0;')
    return once(source, 'main()\n{',
                'main()\n{\n    if(OldEndingCommitted)\n    { ' + view + ' return; }')


HELPER = r'''
static int OldEndingCommitted = 0;
static int OldEndingSlide = 0;
static int OldEndingFadeTime = 0;
static int OldEndingText = 0;
static int OldEndingTextCount = 0;
static int OldEndingSlideTime = 0;
static int OldEndingDone = 0;
static int OldEndingKeyDown = 0;

OldCampaignEndingCommit()
{
    if(OldEndingCommitted) return;
    OldEndingCommitted = 1;
    // Original ending only awards the aggregate rank. It is separate from
    // the ordinary Action9 exit and must not grant CurLevelMoney a second time.
    if(MustAddRank())
    {
        SendCommandA(0, EXT_ADDSKILL, RPGHERO_RANK, 1);
        SendCommandA(3, EXT_ADDSKILL, RPGHERO_RANK, 1);
    }
    for(int army = 0; army <= 3; army = army + 3)
    {
        OldShopClose(army);
        SendCommandA(army, EXT_DISABLEFLAGMANCONTROL, 1);
        if(Flagman(army)) Action(Flagman(army), ACT_STOP, 1, 1);
        SetPlayerControl(army, PLAYERCONTROL_NONE);
    }
    StartNextMap = 0;
    GameState = GAME_WIN;
    SetScrollType(SCROLL_NONE);
    SetCursor(CURSOR_NORMAL);
    Pause(1);
    Log2("Coop ending: shared completion committed");
    // Presentation below this point does not mutate the shared campaign.
    Effect(EFF_FADE, 0, 0, FADE_SLIDE_TIME);
    OldEndingFadeTime = GetTime();
    PlayMusicFile(MUSIC_SLIDE);
}

OldCampaignEndingView(int pictureVid, string textPrefix)
{
    int key = GetInputAction(IA_ANY_KEY) || GetKey() == VK_ESCAPE;
    int pressed = key && !OldEndingKeyDown;
    OldEndingKeyDown = key;
    if(OldEndingDone)
    {
        if(pressed && GetKey() == VK_ESCAPE)
        {
            NetProperty(NET_DISCONNECT);
            NetProperty(NET_NETWORK_OFF);
            MenuRelease();
            Load("maps\\mainmenu.map");
        }
        return;
    }
    if(OldEndingFadeTime && GetEffectState(EFF_FADE) > 45)
    {
        OldEndingFadeTime = 0;
        MenuRelease();
        if(OldEndingSlide >= NO_SLIDE)
        {
            OldEndingDone = 1;
            CreateText(14, ScreenX()/2, ScreenY()/2-20, 1001,
                "Кампания завершена", BEH_CENTER);
            CreateText(13, ScreenX()/2, ScreenY()/2+20, 1001,
                "Esc — главное меню", BEH_CENTER);
            return;
        }
        OldEndingTextCount = 0;
        OldEndingSlideTime = GetTime();
        int pict = MenuCreate(pictureVid, OldEndingSlide, ScreenX()/2, ScreenY()/2, 1000);
        if(ScreenX() == 800)
            Action(pict, ACT_SET_SCALE, 800000/1024+20, 800000/1024+20, 1000);
        OldEndingText = CreateTextFromFile(20, ScreenX()/2-360, ScreenY()+940, 1001,
            textPrefix + itoa(OldEndingSlide++) + ".txt", BEH_LEFT+BEH_BOTTOM);
        Action(OldEndingText, ACT_SET_TEXT_COUNT, 0);
    }
    if(OldEndingFadeTime) return;
    if(pressed && GetKey() == VK_ESCAPE)
    {
        // Keep the original final slide even when the earlier story is skipped.
        if(OldEndingSlide < NO_SLIDE) OldEndingSlide = NO_SLIDE - 1;
        Effect(EFF_FADE, 0, 0, FADE_SLIDE_TIME);
        OldEndingFadeTime = GetTime();
    }
    else if(pressed || GetTime()-OldEndingSlideTime > TIME_FOR_ONE_SLIDE)
    {
        if(OldEndingTextCount)
        {
            Effect(EFF_FADE, 0, 0, FADE_SLIDE_TIME);
            OldEndingFadeTime = GetTime();
        }
        else
        {
            OldEndingTextCount = 10000;
            Action(OldEndingText, ACT_SET_TEXT_COUNT, OldEndingTextCount);
            OldEndingSlideTime = GetTime()-TIME_FOR_ONE_SLIDE+TIME_AFTER_KEY;
        }
    }
    else if(!OldEndingTextCount && Action(OldEndingText, ACT_SET_TEXT_COUNT, -1))
    {
        OldEndingTextCount = 10000;
        OldEndingSlideTime = GetTime()-TIME_FOR_ONE_SLIDE+TIME_FOR_AFTER_TEXT;
    }
}
'''
