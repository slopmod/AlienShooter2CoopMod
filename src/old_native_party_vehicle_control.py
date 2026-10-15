"""Shared explicit-actor boarding and safe release using native vehicle state.

The stock remote-console callback finds the nearest hero to the vehicle,
which need not be the hero who used its console. Callers may now specify an
army without copying the native light/body/descriptor/scroll bookkeeping.
Existing callers retain the original four-argument behavior.
"""


RELEASE_HELPER = r'''
#ifdef COOP_CAMPAIGN
OldPartyVehicleRelease(int army, int vid)
{
    int vehicle = Flagman(army);
    if(!vehicle || GetVid(vehicle) != vid) return true;
    TryEscapeFromCar(army, true, true);
    // Escape can fail if the body/landing is unavailable. The caller retries;
    // never start a death timer while the player still controls this vehicle.
    int hero = Flagman(army);
    return hero && hero != vehicle && IsCharacter(hero);
}
#endif
'''


def adapt_vehicle(source):
    from old_native_campaign_progression import once
    source = once(source,
        'TryBecomeAFlagman( int this, int iRadius, bool bStationaryGun, int iHeroDir = 0 )',
        'TryBecomeAFlagman( int this, int iRadius, bool bStationaryGun, int iHeroDir = 0, int requiredArmy = -1 )')
    source = once(source,
        '\tint NearFlagman = FindNearestFlagman( GetX(this), GetY(this), iRadius );',
        '\tint NearFlagman = 0;\n'
        '\tif(requiredArmy < 0)\n'
        '\t\tNearFlagman = FindNearestFlagman(GetX(this), GetY(this), iRadius);\n'
        '\telse\n'
        '\t{\n'
        '\t\tif(requiredArmy != 0 && requiredArmy != 3) return false;\n'
        '\t\tif(this == Flagman(0) || this == Flagman(3)) return false;\n'
        '\t\tNearFlagman = Flagman(requiredArmy);\n'
        '\t\tif(!NearFlagman || !IsCharacter(NearFlagman)\n'
        '\t\t\t|| Action(NearFlagman, ACT_GET_HP) <= 0\n'
        '\t\t\t|| Action(this, ACT_GET_HP) <= 0\n'
        '\t\t\t|| (iRadius && SizeTo(NearFlagman, GetX(this), GetY(this)) > iRadius))\n'
        '\t\t\treturn false;\n'
        '\t}\n')
    source = once(source, 'ScriptEvent15( int unit, int iVidGun, int iHeroDir )\n{',
                  RELEASE_HELPER + '\nScriptEvent15( int unit, int iVidGun, int iHeroDir )\n{')
    from old_native_party_vehicle_consoles import adapt_vehicle as adapt_consoles
    return adapt_consoles(source)
