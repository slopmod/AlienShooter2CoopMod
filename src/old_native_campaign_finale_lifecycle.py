"""No synthetic Action9/reward for maps completed by an original ending quest."""


def helper(number):
    return '''// Ending owns completion; native map has no Action9 exit.
static int OldLevel@@N@@FinishStage = 0;
static int OldLevel@@N@@FinishFault = 0;
OldLevel@@N@@FinishNarrative()
{
    if(!Action8 && GameState != GAME_PREWIN) return;
    Action8 = 0;
    if(GameState == GAME_PREWIN) GameState = GAME_NORMAL;
    Destroy(WinText1); WinText1 = 0;
    Destroy(WinText2); WinText2 = 0;
    WinTextCreated = false;
}
OldLevel@@N@@FinishTact()
{
    OldLevel@@N@@FinishNarrative();
    // Never accept an unreviewed ordinary exit on an ending-only map.
    if(Action9 == 1) OldLevel@@N@@FinishFault = 1;
    return OldLevel@@N@@FinishFault != 0;
}
'''.replace('@@N@@', f'{number:02d}')
