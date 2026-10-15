"""Audited original ScriptEvent13 routes; activation still belongs to map stacks."""
from old_native_interaction_schema import LogicalPortal, PortalPolicy, SpriteIdentity

CAMPAIGN_PORTALS = (
    LogicalPortal(
        'level03_route_186748e8', 'level03', SpriteIdentity(503168, 409422056, 1144, (6506.0, 5218.0, 2.0)),
        (6409, 5101, 200), 0xbeb32,
        (4543, 4493, 90), 0xbeb22, 0xbeb12,
        PortalPolicy('level03_route_186748e8', 'eligible_order', True, 40, True,
                     None, (90, 90), False, consume_invalid_event=True)),
    LogicalPortal(
        'level05_route_1858b898', 'level05', SpriteIdentity(402224, 408467608, 1144, (1716.0, 10587.0, 0.0)),
        (1678, 10643, 100), 0x9b91a,
        (13949, 11646, 0), 0x9b90a, 0x9b8fa,
        PortalPolicy('level05_route_1858b898', 'eligible_order', True, 40, True,
                     None, (0, 0), False, consume_invalid_event=True, closed_by_quest=(1, 76))),
    LogicalPortal(
        'level06_route_187adf80', 'level06', SpriteIdentity(641696, 410705792, 1144, (11147.0, 11944.0, 107.0)),
        (11064, 12007, 170), 0xf6dde,
        (3469, 11054, 0), 0xf6dce, 0xf6dbe,
        PortalPolicy('level06_route_187adf80', 'eligible_order', True, 40, True,
                     None, (0, 0), False, consume_invalid_event=True)),
    LogicalPortal(
        'level06_route_187bcbe0', 'level06', SpriteIdentity(651200, 410766304, 1144, (3549.998046875, 11001.0, 1.0)),
        (3615, 10924, 120), 0xf8718,
        (11254, 11848, 90), 0xf8708, 0xf86f8,
        PortalPolicy('level06_route_187bcbe0', 'eligible_order', True, 40, True,
                     None, (90, 90), False, consume_invalid_event=True)),
    LogicalPortal(
        'level06_route_187eab60', 'level06', SpriteIdentity(680288, 410954592, 922, (4826.0, 7838.0, 25.0)),
        (4826, 7821, 30), 0xfc331,
        (4242, 3869, 8), 0xfc311, 0xfc301,
        PortalPolicy('level06_route_187eab60', 'eligible_order', True, 40, True,
                     None, (8, 8), False, consume_invalid_event=True)),
    LogicalPortal(
        'level06_route_187f08b0', 'level06', SpriteIdentity(682352, 410978480, 922, (6479.0, 6804.0, 29.0)),
        (6475, 6785, 30), 0xfcfca,
        (9510, 5729, 9), 0xfcfaa, 0xfcf9a,
        PortalPolicy('level06_route_187f08b0', 'eligible_order', True, 40, True,
                     None, (9, 9), False, consume_invalid_event=True)),
    LogicalPortal(
        'level06_route_187f9f78', 'level06', SpriteIdentity(686432, 411017080, 922, (9511.0, 5727.0, 5.0)),
        (9508, 5726, 30), 0xfdf97,
        (6476, 6783, 8), 0xfdf77, 0xfdf67,
        PortalPolicy('level06_route_187f9f78', 'eligible_order', True, 40, True,
                     None, (8, 8), False, consume_invalid_event=True)),
    LogicalPortal(
        'level06_route_18807300', 'level06', SpriteIdentity(694160, 411071232, 922, (4242.0, 3871.939697265625, 4.0)),
        (4237, 3869, 30), 0xff271,
        (4826, 7822, 8), 0xff251, 0xff241,
        PortalPolicy('level06_route_18807300', 'eligible_order', True, 40, True,
                     None, (8, 8), False, consume_invalid_event=True)),
    LogicalPortal(
        'level06_route_188359f0', 'level06', SpriteIdentity(717728, 411261424, 1712, (11276.0, 11845.0, 90.0)),
        (11271, 11910, 220), 0x103c2a,
        (15699, 1797, 0), 0x103c1a, 0x103c0a,
        PortalPolicy('level06_route_188359f0', 'eligible_order', True, 40, True,
                     None, (0, 0), False, consume_invalid_event=True)),
)
