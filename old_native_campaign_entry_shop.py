"""One shared preparation-shop visit per hero, triggered by stock Action6.

Entry shops have no world-space vendor. Missions opt in explicitly; normal
shops retain their distance/rearm policy and all operations use the existing
native inventory, shared money, command transport and original shop UI.
"""


FEATURE = 'old-campaign-entry-shop-v1'


def adapt_shop(source):
    from old_native_campaign_missions import MISSIONS
    from old_native_campaign_progression import once

    missions = tuple(m for m in MISSIONS if getattr(m, 'entry_shop', False))
    if not missions:
        return source
    # Admission is pinned to full original maps with reviewed Action6 sources.
    from old_native_level14_interactions import LEVEL14
    from old_native_level15_interactions import LEVEL15
    admitted = {identity.path: identity.sha256 for identity in (LEVEL14, LEVEL15)}
    for mission in missions:
        if admitted.get(mission.path) != mission.map_sha256:
            raise ValueError('Entry shop requires reviewed Action6 source evidence')
        if mission.shop is not None:
            raise ValueError('Entry preparation shop cannot also be a proximity vendor')
    scope = ' || '.join(
        f'(giCurLevCmpgnReal == {m.native} && map == "{m.path.lower().replace("/", chr(92) * 2)}")'
        for m in missions)
    helper = '''static int OldEntryShopStarted = 0;
static int OldEntryShopDone[4];

OldEntryShopMap()
{
    string map = ToLower(GetMapName());
    return @@SCOPE@@;
}

'''.replace('@@SCOPE@@', scope)
    source = once(source, 'OldShopCanUse(int army, int radius)\n{',
                  helper + 'OldShopCanUse(int army, int radius)\n{')
    source = once(source,
        '    if(!OldInventoryCanUse(army) || !OldShopMissionAvailable() || !OldShopStoryReady()) return 0;\n',
        '    if(!OldInventoryCanUse(army) || !OldShopMissionAvailable() || !OldShopStoryReady()) return 0;\n'
        '    if(OldEntryShopMap()) return OldEntryShopStarted && !OldEntryShopDone[army];\n')
    source = once(source,
        '    if(!OldShopPartyArmy(army) || (!OldShopOpen[army] && !OldInventoryOpen[army] && !OldDevelopmentOpen[army])) return;\n',
        '    if(!OldShopPartyArmy(army) || (!OldShopOpen[army] && !OldInventoryOpen[army] && !OldDevelopmentOpen[army])) return;\n'
        '    if(OldEntryShopMap() && OldShopOpen[army]) OldEntryShopDone[army] = 1;\n')
    source = once(source, 'OldCampaignShopTact()\n{', '''OldCampaignShopTact()
{
    // Latch the shared map event before the level script clears Action6.
    // Initial arming alone must never open a preparation shop.
    if(OldEntryShopMap() && Action6 == 1)
    {
        OldEntryShopStarted = 1;
        Action6 = -1;
    }''')
    rearm = '        if(unit && SizeTo(unit, OldShopLocationX(army), OldShopLocationY(army)) >= '
    source = once(source, rearm,
                  '        if(!OldEntryShopMap() && unit && SizeTo(unit, OldShopLocationX(army), OldShopLocationY(army)) >= ')
    return source
