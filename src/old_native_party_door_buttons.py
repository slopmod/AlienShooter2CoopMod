"""Either living hero can operate stock VID1210 sliding-door buttons.

These are animation callbacks, not ACT43 map commands. The original quest
animation waits, linked door stack and paired button animation are retained.
"""
import hashlib
from pathlib import Path

from old_native_interaction_schema import SpriteIdentity
from old_native_level01_interactions import LEVEL01
from old_native_level04_interactions import LEVEL04


NAME = 'Maps/common_event.lgc'
SOURCE_SHA256 = 'e93ed7073667956caa6a8d6ebe81094d10f24d1cabd5100412900e370ed764d9'
BUTTONS = (
    (LEVEL01, (
        SpriteIdentity(0x6A040, 0x189A49D8, 1210, (2885, 6516, 90)),
        SpriteIdentity(0x6A190, 0x189A5208, 1210, (2170, 6692, 90)),
        SpriteIdentity(0x6A610, 0x189A70B8, 1210, (2342, 6130, 90)),
        SpriteIdentity(0x6A8B0, 0x189A80A0, 1210, (3263, 5926, 90)),
        SpriteIdentity(0x6A9D0, 0x189A86D0, 1210, (1812, 5743, 0)),
        SpriteIdentity(0x6AFA0, 0x189AA428, 1210, (1369, 5221, -8)),
    )),
    (LEVEL04, (
        SpriteIdentity(0x5DA70, 0x1860D660, 1210, (3339, 2589, 90)),
        SpriteIdentity(0x5DAA0, 0x1860D818, 1210, (3088, 2410, 90)),
        SpriteIdentity(0x5DAD0, 0x1860D9D0, 1210, (3267, 2537, 90)),
        SpriteIdentity(0x5DB00, 0x1860DB40, 1210, (3156, 2461, 90)),
        SpriteIdentity(0x5E580, 0x18611C78, 1210, (7507, 2298, 90)),
        SpriteIdentity(0x5E610, 0x18612048, 1210, (7433, 2236, 90)),
        SpriteIdentity(0x5E790, 0x18612A50, 1210, (7064, 2296, 90)),
        SpriteIdentity(0x5E820, 0x18612E50, 1210, (6973, 2327, 84)),
        SpriteIdentity(0x60BC0, 0x0C289740, 1210, (2260, 1812, 89)),
        SpriteIdentity(0x60BF0, 0x0C2898B0, 1210, (2078, 1695, 90)),
        SpriteIdentity(0x60C20, 0x0C289A20, 1210, (2185, 1765, 90)),
        SpriteIdentity(0x60CB0, 0x0C289E00, 1210, (2010, 1633, 90)),
    )),
)


HELPER = r'''
OldPartyDoorButtonNear(int button)
{
#ifdef COOP_CAMPAIGN
    string map = ToLower(GetMapName());
    if(NetProperty(NET_IS_CONNECT) && NetProperty(NET_NO_PLAYERS) == 2
        && ((giCurLevCmpgnReal == 1 && map == "maps\\level_01.map")
            || (giCurLevCmpgnReal == 4 && map == "maps\\level_04.map")))
    {
        for(int army = 0; army <= 3; army = army + 3)
        {
            int hero = Flagman(army);
            if(hero && Action(hero, ACT_GET_HP) > 0
                && SizeTo(hero, GetX(button), GetY(button)) < 40) return true;
        }
        return false;
    }
#endif
    return SizeTo(Flagman(0), GetX(button), GetY(button)) < 40;
}
'''


def prepare(root):
    from old_native_campaign_progression import once, digest
    root = Path(root)
    original = (root / NAME).read_bytes()
    if hashlib.sha256(original).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported original door-event script')
    for identity, buttons in BUTTONS:
        data = (root / identity.path).read_bytes()
        if hashlib.sha256(data).hexdigest() != identity.sha256:
            raise ValueError('Unsupported door-button map: ' + identity.path)
        for button in buttons:
            if data[button.offset:button.offset + 20] != button.packed():
                raise ValueError('Changed door-button source sprite')
    source = original.decode('cp1251').replace('\r\n', '\n')
    source = once(source, 'F1210_0(int button)\n{', HELPER + '\nF1210_0(int button)\n{')
    source = once(source, '  if( SizeTo(Flagman(0),GetX(button),GetY(button)) < 40 )',
                  '  if(OldPartyDoorButtonNear(button))')
    return {NAME: source}, {
        'feature': 'old-campaign-party-door-buttons-v1',
        'source_sha256': SOURCE_SHA256, 'output_sha256': digest(source),
        'map_sha256': {m.path: m.sha256 for m, _ in BUTTONS},
        'button_counts': {m.path: len(buttons) for m, buttons in BUTTONS},
        'original_radius': 40, 'quest_animation_gates_preserved': True,
        'original_door_and_paired_button_stacks_preserved': True,
        'native_runtime_tested': False,
    }
