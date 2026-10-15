"""Small reviewed exceptions after the common mission lifecycle composition.

Inputs are hash-guarded by campaign_entries; world changes depend exclusively
on shared quest/time/hero state. Local input and fade state never move heroes.
"""


def adapt(source, number):
    from old_native_campaign_progression import once
    if number == 4:
        source = once(source, '        Action(Flagman(0), ACT_SET_IMPULSE_SPEED, 300, -300, 0);',
            '        for(int army = 0; army <= 3; army = army + 3)\n'
            '            if(Flagman(army))\n'
            '                Action(Flagman(army), ACT_SET_IMPULSE_SPEED, 300, -300, 0);')
        # Retain the original water bounds, period and visual effect per hero.
        start = source.index('    if ( WaterZ >= 85 && Flagman(0) )')
        end = source.index('    //iff( SizeTo', start)
        waves = source[start:end].replace('Flagman(0)', 'Flagman(army)')
        waves = waves.replace('            static int old_time = 0;\n', '')
        waves = waves.replace('old_time', 'OldWaterWaveTime[army]')
        source = source[:start] + ('    for(int army = 0; army <= 3; army = army + 3)\n    {\n'
                                  + waves + '    }\n\n') + source[end:]
        source = once(source, 'static int WaterZ = 114;',
                       'static int WaterZ = 114;\nstatic int OldWaterWaveTime[8];')
    elif number == 5:
        from old_native_level05_exit import adapt as adapt_exit_passage
        source = adapt_exit_passage(source)
    elif number == 6:
        # Stock Space/fade shortcut teleports only army0 and is driven by local
        # input. Keep the original quest-gated ScriptEvent13 route instead;
        # the common controller queues each hero independently at that exit.
        start = source.index('    if ( EndQuest )\n')
        source = source[:start] + '}\n'
        source = once(source, '        CreateWinText();',
            '        CreateText(14, ScreenX()/2, MISSION_FAILURE_COUNTER_Y, 0,\n'
            '            "Задание выполнено. Идите к выходу вместе.", BEH_CENTER);')
    elif number == 7:
        # The map supplies a single driveable car. Its stock per-army boarding
        # logic can serve both heroes once a second safely placed car exists.
        source = once(source, '#include "maps\\old_campaign_shop.lgc"',
            '#include "maps\\old_campaign_shop.lgc"\n'
            '#include "maps\\old_campaign_party_vehicle.lgc"')
        source = once(source, '    OldCampaignInit();',
            '    OldCampaignInit();\n'
            '    if(OldCampaignReady) OldCampaignPartyVehicleInit(3000, 2062, 11702, 5);')
    elif number == 11:
        from old_native_level11_specials import adapt as adapt_robot
        source = adapt_robot(source)
    elif number == 12:
        from old_native_level12_carrier import adapt as adapt_carrier
        source = adapt_carrier(source)
    elif number == 14:
        from old_native_level14_specials import adapt as adapt_finale
        source = adapt_finale(source)
    elif number == 15:
        from old_native_level15_specials import adapt as adapt_finale
        source = adapt_finale(source)
    return source
