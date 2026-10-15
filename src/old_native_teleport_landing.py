"""Guard both native teleport commits against a living party member.

Keep the original destination, platform animation and one-shot event lifetime.
A busy landing waits at its current phase; it never moves the other player or
searches across walls. All placement decisions use shared world state only.
"""

HELPER = r'''
static int OldTeleportLandingWaiting = 0;
static int OldTeleportLandingWaitText = 0;

OldTeleportLandingClear(int army, int x, int y, int z)
{
    int other = Flagman(3 - army);
    if(!other || Action(other, ACT_GET_HP) <= 0) return true;
    if(GetZ(other) < z - 48 || GetZ(other) > z + 48) return true;
    return SizeTo(other, x, y) >= 96;
}

OldTeleportLandingWait(int waiting)
{
    if(OldTeleportLandingWaiting == waiting) return;
    OldTeleportLandingWaiting = waiting;
    Destroy(OldTeleportLandingWaitText);
    OldTeleportLandingWaitText = 0;
    if(waiting)
        OldTeleportLandingWaitText = CreateText(13, ScreenX()/2, ScreenY()/2+95, 0,
            "Выход занят. Напарнику нужно отойти от точки прибытия.", BEH_CENTER);
}
'''

COMMIT_GUARD = r'''
    // Check immediately before either coordinate commit, not just before fade.
    // Do not reject BeginTeleporting2: one-shot script events may not retry.
    if(timer <= iTeleportTime / 2
        || (timer > iTeleportTime && timer <= iTeleportTime * 3 / 2))
    {
        int landingX = GetX(goal);
        int landingY = GetY(goal);
        int landingZ = GetZ(goal);
        int landingPlatform = OldTeleportNextUnit;
        if(!landingPlatform && iNextVid && timer > iTeleportTime)
            landingPlatform = FindNearestSprite(GETSPRITE_VID(iNextVid), landingX, landingY, 200);
        if(landingPlatform)
        {
            landingX = GetX(landingPlatform);
            landingY = GetY(landingPlatform);
            if(OldTeleportNextUnit) landingZ = OldTeleportZ;
            else landingZ = GetZ(landingPlatform);
        }
        if(!OldTeleportLandingClear(OldTeleportArmy, landingX, landingY, landingZ))
        {
            if(timer <= iTeleportTime / 2)
                Action(unit, ACT_SET_TIMER, iTeleportTime / 2);
            else Action(unit, ACT_SET_TIMER, iTeleportTime * 3 / 2);
            OldTeleportLandingWait(1);
            return;
        }
        OldTeleportLandingWait(0);
    }
'''


def apply(source):
    def once(before, after):
        nonlocal source
        if source.count(before) != 1:
            raise ValueError('Teleport landing source guard: ' + repr(before))
        source = source.replace(before, after)

    once('static int OldTeleportNextUnit = 0;',
         'static int OldTeleportNextUnit = 0;\n' + HELPER)
    once('FinishTeleporting( int unit )\n{',
         'FinishTeleporting( int unit )\n{\n    OldTeleportLandingWait(0);')
    once('\tint timer = Action( unit, ACT_GET_TIMER );\n\tint goal = Action( unit, ACT_GET_GOAL );',
         '\tint timer = Action( unit, ACT_GET_TIMER );\n\tint goal = Action( unit, ACT_GET_GOAL );\n'
         + COMMIT_GUARD)
    return source
