"""Level12 extraction cart policy over the shared party-carrier mechanism."""
from pathlib import Path

from old_native_interaction_schema import MapCommand, SpriteIdentity
from old_native_level12_interactions import LEVEL12
from old_native_party_carriers import PartyCarrier, helper, patch_map


ROUTE = PartyCarrier(
    prefix='OldLevel12Carrier', map=LEVEL12,
    sprite=SpriteIdentity(0x862A0, 0x183D7488, 2695, (529, 1224, 10)),
    commands=(
        MapCommand(0xC8B3F, (33, 2574, -214, 10)),
        MapCommand(0xC8B4F, (131, 2, 50000, 0)),
        MapCommand(0xC8B5F, (131, 12, 1, 0)),
        MapCommand(0xC8B6F, (43, 538, 1294, 50)),
        MapCommand(0xC8B7F, (77, 1, 65, 0)),
    ),
    proximity=MapCommand(0xC8B6F, (43, 538, 1294, 50)),
    quest=(1, 65), gathering_radius=180, height_tolerance=48,
    # Y separation leaves both final seats within ACT43(2341,-120,310).
    # X separation would leave the far seat outside the original exit gate.
    seats=((0, -55, 40), (0, 55, 40)),
    # No original Level12 stack or included script reads/writes Action13.
    # Hold it until map teardown, so ACT79 cannot miss a transient pulse.
    latch=(13, 1202695),
)


def prepare(root):
    data, metadata = patch_map((Path(root) / LEVEL12.path).read_bytes(), ROUTE)
    return {LEVEL12.path: data}, metadata


def adapt(source):
    from old_native_campaign_progression import once
    before = '    Action(Flagman(0), ACT_CHANGE_COOR, GetX(unit), GetY(unit), GetZ(unit) + 40);'
    source = once(source, before, '    OldLevel12CarrierCarry(unit);')
    source = once(source, 'F2695_2(int unit)', helper(ROUTE) + '\nF2695_2(int unit)')
    return once(source, '  if(!OldCampaignReady) return;\n',
                '  if(!OldCampaignReady) return;\n  OldLevel12CarrierTact();\n')
