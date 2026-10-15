"""Audited original Level01 interaction data; no runtime handlers or I/O."""
from old_native_interaction_schema import (
    LogicalPortal, MapCommand, MapIdentity, PartyTrigger, PortalPolicy, SpriteIdentity,
)

LEVEL01 = MapIdentity('level01', 'Maps/Level_01.map', '5bdc5f4ff57e06feeb7b02d36c09d76e01ef5d258b05e3c45c4e47523df694ec')

LEVEL01_PARTY_TRIGGERS = (
    PartyTrigger('dynamite_plant', 'level01', SpriteIdentity(0x6CCE0, 0x189B34E8, 922, (6446.0, 2600.0, 10.0)), (6554, 2606, 70), (0xA3B50, 0xA3BC4)),
    PartyTrigger('elevator_inspect', 'level01', SpriteIdentity(0x6A850, 0x189A7F70, 922, (3184.0, 5852.0, 90.0)), (3204, 5833, 110), (0xA1E44,)),
    PartyTrigger('elevator_unlock', 'level01', SpriteIdentity(0x6A880, 0x189A8008, 922, (3089.0, 5880.0, 90.0)), (3204, 5833, 110), (0xA1EF9,)),
)

# Keep the historical three-entry patch profile above immutable. The opening
# panel was still falling back to army0; only its proximity selector changes.
# Original sound, quest, gate request, delay, effect and radio stay in the map.
LEVEL01_OPENING_TRIGGERS = (
    PartyTrigger('opening_gate_panel', 'level01',
        SpriteIdentity(0x6CBC0, 0x189B2CD0, 922, (5213.0, 3165.0, 1.0)),
        (5201, 3156, 50), (0xA3A00,), (
            MapCommand(0xA39F0, (135, 78, 0, 0)),
            MapCommand(0xA39E0, (78, 1, 3, 0)),
            MapCommand(0xA39D0, (131, 10, 1, 0)),
            MapCommand(0xA39C0, (40, 500, 0, 0)),
            MapCommand(0xA39B0, (15, 661, 5653, 3265)),
            MapCommand(0xA39A0, (116, 110, 0, 0)),
        )),
)

# These native stacks include delays/door sounds. Admit either hero but leave
# their sequence and the original quest prerequisites in the map itself.
LEVEL01_INTERIOR_TRIGGERS = (
    PartyTrigger('bunker_stair_roof', 'level01',
        SpriteIdentity(0x6A6A0, 0x189A2F08, 922, (2291.0, 6200.0, 90.0)),
        (2173, 6070, 140), (0xA1A93,), (
            MapCommand(0xA1A83, (40, 300, 0, 0)),
            MapCommand(0xA1A73, (131, 5, 4, 0)),
        )),
    PartyTrigger('bunker_lower_door', 'level01',
        SpriteIdentity(0x6AA30, 0x189A8920, 1786, (1697.0, 5756.0, 0.0)),
        (1702, 5775, 230), (0xA2133,), (
            MapCommand(0xA2123, (40, 200, 8, 0)),
            MapCommand(0xA2113, (131, 5, 8, 0)),
        )),
    PartyTrigger('bunker_side_door', 'level01',
        SpriteIdentity(0x6AF10, 0x189AA140, 1785, (1328.0, 5123.0, 0.0)),
        (1326, 5103, 220), (0xA250F,), (
            MapCommand(0xA24FF, (15, 0, 0, 0)),
            MapCommand(0xA24EF, (40, 200, 8, 0)),
            MapCommand(0xA24DF, (131, 5, 9, 0)),
        )),
    PartyTrigger('elevator_open', 'level01',
        SpriteIdentity(0x6AAF0, 0x189A8CA0, 1136, (3712.0, 5415.0, 8.0)),
        (3700, 5458, 180), (0xA2209,), (
            MapCommand(0xA21F9, (135, 76, 0, 0)),
            MapCommand(0xA21E9, (40, 2000, 0, 0)),
            MapCommand(0xA21D9, (6, 0, 0, 0)),
            MapCommand(0xA21C9, (10, 0, 0, 0)),
        )),
    PartyTrigger('elevator_enter', 'level01',
        SpriteIdentity(0x6AAF0, 0x189A8CA0, 1136, (3712.0, 5415.0, 8.0)),
        (3831, 5334, 120), (0xA21B9,), (
            MapCommand(0xA21A9, (131, 9, 1, 0)),
        )),
)

BUNKER_PORTALS = (
    LogicalPortal('entry', 'level01', SpriteIdentity(0x6D910, 0x189B6CB0, 922, (7325.0, 1948.0, 0.0)),
                  (7471, 1945, 130), 0xA42A2, (2061, 6625, 90), 0xA4282, 0xA4272,
                  PortalPolicy('level01_bunker', 'leader_pending', True, 40, False, None, (90, 90), True)),
    LogicalPortal('exit', 'level01', SpriteIdentity(0x6A1C0, 0x189A5378, 922, (2036.0, 6686.0, 90.0)),
                  (1891, 6716, 123), 0xA12FC, (7260, 2059, 0), 0xA12DC, 0xA12CC,
                  PortalPolicy('level01_bunker', 'leader_pending', True, 40, False, None, (0, 0), True)),
)
