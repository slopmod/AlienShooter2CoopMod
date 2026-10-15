"""Completion latch for the original Level05 server passage door.

The map's door closes at the server trigger and reopens only while Action12
equals 4. ACT79 is an equality wait (OLD 44D348..44D35B); another original
actor advances the phase to 5. The shared final quest 76 is a durable proof
that this scene has completed, even if a door missed its transient phase.

Do not manufacture a quest, remove a door, or toggle an already open door.
The only recovery is the same ANI_DEATH command used by the stock map.
The caller's Level05 map SHA guard also pins these exact SPR/SPRD records.
"""
from old_native_interaction_schema import MapCommand, SpriteIdentity


PASSAGE = SpriteIdentity(0x696B0, 0x186CB780, 2506, (10465, 4091, 0))
COMMANDS = (
    MapCommand(0xAA288, (43, 11225, 3613, 150)),
    MapCommand(0xAA278, (15, 0, 0, 0)),
    MapCommand(0xAA268, (79, 12, 4, 0)),
    MapCommand(0xAA258, (40, 800, 0, 0)),
    MapCommand(0xAA248, (15, 0, 0, 0)),
)

HELPER = r'''
static int OldLevel05ExitPassageDone = 0;

OldLevel05ExitPassageTact()
{
    if(OldLevel05ExitPassageDone) return;
    int quest = SendCommand(EXT_GETQUESTSSTATE, 0, 76, 1);
    if(quest != QS_BEGUN && quest != (QS_BEGUN | QS_NOTACTUAL)) return;

    // There is another open door only nine units away. Match the scripted
    // passage exactly, including height; never change the adjacent object.
    int door = FindNearestSprite(GETSPRITE_VID(2505), 10465, 4091, 3);
    if(!door) door = FindNearestSprite(GETSPRITE_VID(2506), 10465, 4091, 3);
    if(!door || GetX(door) != 10465 || GetY(door) != 4091 || GetZ(door) != 0)
        return;
    // Let a stock opening/closing animation finish before deciding its state.
    if(GetAnimation(door) == ANI_DEATH || GetAnimation(door) == ANI_DEATH2)
        return;
    // This scene is finished. Its old equality wait or a late arrival at the
    // closing trigger must not toggle the passage after this one-time latch.
    Action(door, ACT_CLEAR_STACK, 0);
    OldLevel05ExitPassageDone = 1;
    if(GetVid(door) == 2505)
    {
        Action(door, ANI_DEATH);
        Log2("Coop Level05: completed server passage reopening");
    }
}
'''


def adapt(source):
    from old_native_campaign_progression import once
    source = once(source, 'main()\n{', HELPER + '\nmain()\n{')
    return once(source, '  if(!OldCampaignReady) return;\n',
                '  if(!OldCampaignReady) return;\n'
                '  OldLevel05ExitPassageTact();\n')
