"""Adapt the verified original teleport script for two campaign players.

Pure transformation: the caller alone writes the isolated runtime copy. The
stock script remains the default outside campaign builds. One transit remains
active at a time; native platform callbacks choose army 0 then army 3.
"""
import hashlib
from pathlib import Path


SOURCE_SHA256 = 'd74b7d51eb81580701fb711d71524722f0407cd43ded81748d7f392674b6a050'
FEATURE = 'old-campaign-teleports-v1'


def patch(source: bytes) -> tuple[str, dict]:
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported original util_teleport.lgc')
    text = source.decode('cp1251').replace('\r\n', '\n')
    changes = []

    def replace(before, after, count=1):
        nonlocal text
        if text.count(before) != count:
            raise ValueError('Teleport source guard failed: ' + repr(before))
        text = text.replace(before, after)
        changes.append({'source': before, 'count': count})

    replace('static int giTeleportTime = 0;', '''static int giTeleportTime = 0;
// The active army and hero are identical on both native simulations.
static int OldTeleportArmy = 0;
static int OldTeleportHero = 0;
static int OldTeleportNextUnit = 0;

// ChangeLight also creates a flashlight, so it cannot run on just one peer.
// Keep visual gamma local and apply the world change for the same army twice.
OldTeleportChangeLight(int gamma)
{
    if(OldTeleportArmy == giCurArmy)
    {
        SetGamma(gamma);
        CurrentGamma = gamma;
    }
    if(GetGammaIntensive(gamma) > FLASH_ON_INTENSIVE)
        SpotLightOn(OldTeleportArmy);
}''')
    replace('BeginTeleporting2(int unit, int iNextVid, int iHeroAnimZ, int bMoveTeleport, int iTeleportTime)\n{',
            '''BeginTeleporting2(int unit, int iNextVid, int iHeroAnimZ, int bMoveTeleport, int iTeleportTime, int nArmy = 0)
{
    if(gCurrentTeleport || (nArmy != 0 && nArmy != 3) || !unit)
        return false;
    int hero = Flagman(nArmy);
    if(!hero || Action(hero, ACT_GET_HP) <= 0 || !Action(unit, ACT_GET_GOAL))
        return false;
    OldTeleportArmy = nArmy;
    OldTeleportHero = hero;
    OldTeleportNextUnit = 0;''')
    replace('''		if( goal && SizeTo( Flagman(0), GetX(unit), GetY(unit) ) <= TELEPORT_RADIUS )
			return BeginTeleporting2(unit, iNextVid, iHeroAnimZ, bMoveTeleport, iTeleportTime);''',
            '''        for(int army = 0; army <= 3; army = army + 3)
        {
            int hero = Flagman(army);
            if(hero && Action(hero, ACT_GET_HP) > 0
                && SizeTo(hero, GetX(unit), GetY(unit)) <= TELEPORT_RADIUS)
                return BeginTeleporting2(unit, iNextVid, iHeroAnimZ,
                    bMoveTeleport, iTeleportTime, army);
        }''')
    # All remaining Flagman(0) uses belong to the active transit, including the
    # explicit scripted default leader start. No local-identity world mutation.
    replace('Flagman(0)', 'Flagman(OldTeleportArmy)', 16)
    replace('SendCommandA( 0, EXT_DISABLEFLAGMANCONTROL,',
            'SendCommandA( OldTeleportArmy, EXT_DISABLEFLAGMANCONTROL,', 2)
    replace('AddInvuln( 0, 0, false );', 'AddInvuln( OldTeleportArmy, 0, false );')
    replace('DelInvuln( 0, false );', 'DelInvuln( OldTeleportArmy, false );')
    replace('MoveDroneToHero(0);', 'MoveDroneToHero(OldTeleportArmy);', 4)
    replace('\tEffect( EFF_FADE, 0, 0, iTeleportTime );',
            '\tif(OldTeleportArmy == giCurArmy)\n\t\tEffect( EFF_FADE, 0, 0, iTeleportTime );')
    # Add braces to preserve the original else binding on nonmoving teleports.
    replace('''			if( !bMoveTeleport )
				SetPosition( -ToScreenX(0) + ScreenX()/2, -ToScreenY( 0, 0 ) + ScreenY()/2 + PrevZ - z );
			else''',
            '''			if( !bMoveTeleport )
            {
                if(OldTeleportArmy == giCurArmy)
				    SetPosition( -ToScreenX(0) + ScreenX()/2, -ToScreenY( 0, 0 ) + ScreenY()/2 + PrevZ - z );
            }
			else''')
    replace('''		if( !bMoveTeleport )
		{
			SetPosition( -ToScreenX(0) + ScreenX()/2, -ToScreenY( 0, 0 ) + ScreenY()/2 + PrevZ - z );''',
            '''		if( !bMoveTeleport )
		{
            if(OldTeleportArmy == giCurArmy)
			    SetPosition( -ToScreenX(0) + ScreenX()/2, -ToScreenY( 0, 0 ) + ScreenY()/2 + PrevZ - z );''')
    replace('''		ChangeCurScrollBox();
		SetPosition( GetX( goal ), GetY( goal ) - iHeroAnimZ );''',
            '''        if(OldTeleportArmy == giCurArmy)
        {
		    ChangeCurScrollBox();
		    SetPosition( GetX( goal ), GetY( goal ) - iHeroAnimZ );
        }''')
    replace('ChangeLight(item);', 'OldTeleportChangeLight(item);')
    replace('\tstatic int iNextUnit = 0;',
            '''    // Death/removal cannot leave the shared platform and control lock stuck.
    if(!Flagman(OldTeleportArmy) || Flagman(OldTeleportArmy) != OldTeleportHero
        || Action(OldTeleportHero, ACT_GET_HP) <= 0)
    {
        if(OldTeleportNextUnit)
        {
            Action(OldTeleportNextUnit, ACT_CHANGE_COOR,
                GetX(OldTeleportNextUnit), GetY(OldTeleportNextUnit), OldTeleportZ);
            Action(OldTeleportNextUnit, ACT_SET_TIMER, 1000);
        }
        else if(bMoveTeleport)
            Action(unit, ACT_CHANGE_COOR, GetX(unit), GetY(unit), OldTeleportZ);
        FinishTeleporting(unit);
        return;
    }''')
    # This local was static in the original. Make it visible to start/cleanup.
    import re
    text, count = re.subn(r'\biNextUnit\b', 'OldTeleportNextUnit', text)
    if count != 25:
        raise ValueError('Unexpected original teleport destination references: ' + str(count))
    changes.append({'source': 'iNextUnit', 'count': count})
    replace('\tgCurrentTeleport = 0;\n\t//',
            '\tgCurrentTeleport = 0;\n    OldTeleportHero = 0;\n    OldTeleportNextUnit = 0;\n\t//')
    # Propagate guarded BeginTeleporting2 failure to scripted callers.
    replace('''	BeginTeleporting2( unit, 0, 0, false, TELEPORT_TIME_SCRIPT );
	return true;''',
            '\treturn BeginTeleporting2( unit, 0, 0, false, TELEPORT_TIME_SCRIPT );')
    encoded = text.replace('\n', '\r\n').encode('cp1251')
    return text, {
        'feature': FEATURE,
        'source_sha256': SOURCE_SHA256,
        'output_sha256': hashlib.sha256(encoded).hexdigest(),
        'active_army_variable': 'OldTeleportArmy',
        'army_order': [0, 3],
        'single_active_transit': True,
        'script_event_default_army': 0,
        'manual_death_tested': False,
        'changes': changes,
    }


def prepare(old_root: Path) -> tuple[str, dict]:
    return patch((Path(old_root) / 'Maps' / 'util_teleport.lgc').read_bytes())
