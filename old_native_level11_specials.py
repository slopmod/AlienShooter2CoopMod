"""Two independently controlled robots, preserving Level11's quest sequence.

The stock robot is controlled remotely: TryBecomeAFlagman(stationary=true)
retains the hero body at the terminal. The controller admits each actual
terminal user, never the hero nearest the robot, and releases every operator
after the original quest60 + four-second delay. Robot loss before quest60
still fails the mission. No quest/reward/state counters are manufactured.
"""


HELPER = r'''
#ifdef COOP_CAMPAIGN
static int OldLevel11Robot[2];
static int OldLevel11RobotRetired[2];
static int OldLevel11RobotReady = 0;
static int OldLevel11ConsoleEnabled = 0;
static int OldLevel11ConsoleUnit = 0;
static int OldLevel11ConsoleClaimed = 0;
static int OldLevel11RobotPhase = 0;
static int OldLevel11RobotOperator[8];
static int OldLevel11ConsoleArmed[8] = {1, 0, 0, 1, 0, 0, 0, 0};

OldLevel11RobotScope()
{
    return giCurLevCmpgn == 11 && giCurLevCmpgnReal == 11
        && NetProperty(NET_IS_CONNECT) && NetProperty(NET_NO_PLAYERS) == 2
        && ToLower(GetMapName()) == "maps\\level_11.map";
}

OldLevel11RobotPhaseEnded()
{
    int state = SendCommand(EXT_GETQUESTSSTATE, 0, 60, 1);
    return (state & QS_BEGUN) != 0;
}

OldLevel11ConsoleNear(int army, int margin)
{
    int hero = Flagman(army);
    return hero && IsCharacter(hero) && Action(hero, ACT_GET_HP) > 0
        && abs(GetZ(hero)) <= 32 && SizeTo(hero, 10530, 8545) < 40 + margin;
}

OldLevel11RobotAdmit()
{
    if(!OldLevel11RobotReady || !OldLevel11ConsoleEnabled
        || OldLevel11RobotPhaseEnded()) return;
    for(int army = 0; army <= 3; army = army + 3)
    {
        int hero = Flagman(army);
        // Remote-control exit restores the body inside the console. Require
        // a step off before re-entry, independently for the two operators.
        if(hero && IsCharacter(hero) && !OldLevel11ConsoleNear(army, 40))
            OldLevel11ConsoleArmed[army] = 1;
        if(OldLevel11ConsoleArmed[army] && OldLevel11ConsoleNear(army, 0))
        {
            for(int index = 0; index < 2; index++)
            {
                int robot = OldLevel11Robot[index];
                if(robot && robot != Flagman(0) && robot != Flagman(3)
                    && Action(robot, ACT_GET_HP) > 0
                    && TryBecomeAFlagman(robot, 100000, true, 224, army))
                {
                    if(!OldLevel11RobotPhase)
                    {
                        OldLevel11RobotOperator[0] = 0;
                        OldLevel11RobotOperator[3] = 0;
                    }
                    OldLevel11RobotOperator[army] = 1;
                    OldLevel11RobotPhase = 1;
                    Action10 = 1;
                    OldLevel11ConsoleArmed[army] = 0;
                    Log("Coop Level11 robot: army=" + itoa(army) + " slot=" + itoa(index));
                    break;
                }
            }
        }
    }
}

OldLevel11RobotBoardTact()
{
    if(!OldLevel11RobotReady || !OldLevel11ConsoleEnabled
        || OldLevel11RobotPhaseEnded()) return;
    // Claim only stack0 on the main tact, outside its ScriptEvent callback.
    // ACT_CLEAR_STACK's first argument indexes one of four native stacks;
    // stack1 retains the original quest60 + 3000..4000ms console cleanup.
    if(!OldLevel11ConsoleClaimed && OldLevel11ConsoleUnit)
    {
        Action(OldLevel11ConsoleUnit, ACT_CLEAR_STACK, 0);
        OldLevel11ConsoleClaimed = 1;
    }
    OldLevel11RobotAdmit();
    if(OldLevel11RobotPhase)
    {
        int returned = 1;
        for(int army = 0; army <= 3; army = army + 3)
        {
            if(OldLevel11RobotOperator[army])
            {
                int controlled = Flagman(army);
                // Preserve the exact source return circle and strict radius.
                // An on-foot partner who never operated cannot end this phase.
                if(!controlled || SizeTo(controlled, 10695, 8714) >= 190)
                    returned = 0;
            }
        }
        Action10 = 1;
        if(returned)
        {
            Action10 = 2;
            OldLevel11RobotPhase = 0;
        }
    }
}

OldLevel11RobotEvent(int unit, int vid, int direction)
{
    if(!OldLevel11RobotScope() || vid != 3040) return false;
    // Consume malformed calls in this map rather than falling through to
    // the stock global nearest-hero/first-robot search.
    if(!unit || GetVid(unit) != 922 || direction != 224
        || GetX(unit) < 10522 || GetX(unit) > 10523
        || GetY(unit) < 8574 || GetY(unit) > 8575 || GetZ(unit) != 0)
        return true;
    if(!OldLevel11RobotPhaseEnded()
        && (OldLevel11ConsoleNear(0, 0) || OldLevel11ConsoleNear(3, 0)))
    {
        // This permission originates only from the reviewed map event.
        // A second operator may arrive while the first robot is in use.
        OldLevel11ConsoleEnabled = 1;
        OldLevel11ConsoleUnit = unit;
        OldLevel11RobotAdmit();
    }
    return true;
}

OldLevel11RobotRetireTact()
{
    for(int army = 0; army <= 3; army = army + 3)
        OldPartyVehicleRelease(army, 3040);
    for(int index = 0; index < 2; index++)
    {
        int robot = OldLevel11Robot[index];
        if(!OldLevel11RobotRetired[index] && robot
            && robot != Flagman(0) && robot != Flagman(3))
        {
            OldLevel11RobotRetired[index] = 1;
            Action(robot, ACT_SET_DEATH_TIMER, 1000);
        }
    }
}
#endif
'''


INITIALIZE = r'''
OldLevel11RobotInit()
{
    if(OldLevel11RobotReady || !OldCampaignReady) return;
    OldLevel11RobotReady = 1;
    int original = FindNearestSprite(GETSPRITE_VID(3040), 11300, 9177, 3);
    if(!original || GetX(original) != 11300 || GetY(original) != 9177 || GetZ(original) != 0)
    {
        Log("Coop Level11 robot: original source missing");
        return;
    }
    OldLevel11Robot[0] = original;
    if(OldCampaignPartyVehicleInit(3040, 11300, 9177, 0))
    {
        OldLevel11Robot[1] = OldPartyVehicle;
        BecomeNeutral(OldPartyVehicle, true, -1);
    }
}
'''


def adapt_vehicle(source):
    """Compose after the common hash-guarded util_car corrections."""
    from old_native_campaign_progression import once
    from old_native_party_vehicle_control import adapt_vehicle as explicit_actor
    source = explicit_actor(source)
    return once(source, 'ScriptEvent15( int unit, int iVidGun, int iHeroDir )\n{',
        HELPER + '\nScriptEvent15( int unit, int iVidGun, int iHeroDir )\n{\n'
        '#ifdef COOP_CAMPAIGN\n'
        '    if(OldLevel11RobotEvent(unit, iVidGun, iHeroDir)) return;\n#endif')


def adapt(source):
    """Compose only the reviewed Level11 entry after common lifecycle hooks."""
    from old_native_campaign_progression import once
    source = once(source, '#include "maps\\old_campaign_shop.lgc"',
        '#include "maps\\old_campaign_shop.lgc"\n'
        '#include "maps\\old_campaign_party_vehicle.lgc"')
    source = once(source, 'main()\n{', INITIALIZE + '\nmain()\n{')
    source = once(source, '    OldCampaignInit();',
        '    OldCampaignInit();\n    OldLevel11RobotInit();')
    source = once(source, '  if(!OldCampaignReady) return;\n',
        '  if(!OldCampaignReady) return;\n  OldLevel11RobotBoardTact();\n')
    # Keep the native quest60 latch and >4000 timing. An ordinary if retries
    # a failed release; per-robot retirement flags keep each timer one-shot.
    source = once(source,
        '    iff( StartQuest60 && (GetTime() - StartQuest60) > 4000 )\n'
        '    {\n'
        '        Action(Flagman(0), ACT_SET_DEATH_TIMER, 1000);// убиваем робота через секунду\n'
        '        TryEscapeFromCar(0, true, true);// высаживаемся из робота\n'
        '    }',
        '    if( StartQuest60 && (GetTime() - StartQuest60) > 4000 )\n'
        '        OldLevel11RobotRetireTact();')
    return once(source,
        '    if( SendCommand( EXT_GETQUESTSSTATE, 0, 60, 1 ) == QS_NOTBEGUN )\n'
        '        FailCurQuest();',
        '    if( SendCommand( EXT_GETQUESTSSTATE, 0, 60, 1 ) == QS_NOTBEGUN )\n'
        '        FailCurQuest();\n'
        '    else CommonCarDeath(unit);')
