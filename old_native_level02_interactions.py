"""Audited original Level02 interaction data; no runtime handlers or I/O."""
from old_native_interaction_schema import (
    LogicalPortal, MapCommand, MapIdentity, PartyTrigger, PortalPolicy, SpriteIdentity,
)

LEVEL02 = MapIdentity('level02', 'Maps/Level_02.map', 'e52d86951d508743ed625ef0b4910e7ba2c4ce633e3e94029c179a466186ff79')

ADMIN_ENTRY_SPRITE = SpriteIdentity(0x8A890, 0x186E0758, 922, (4015.0, 7872.0, 0.0))
LEVEL02_LEGACY_PARTY_TRIGGERS = (
    PartyTrigger('admin_door', 'level02', SpriteIdentity(0x8A830, 0x186E04C0, 1731, (4009.545166015625, 7829.154296875, 0.03293609619140625)), (3921, 7726, 400), (0xD76D1,)),
    PartyTrigger('admin_entry', 'level02', ADMIN_ENTRY_SPRITE, (3831, 7584, 300), (0xD779B,)),
    PartyTrigger('admin_arrival', 'level02', SpriteIdentity(0x8A920, 0x186E0E50, 922, (1917.0, 6722.0, 180.0)), (1920, 6720, 500), (0xD7ADA,), (MapCommand(0xD7ACA, (78, 1, 18, 1)),)),
)

ADMIN_PORTAL = LogicalPortal('admin_entry', 'level02', ADMIN_ENTRY_SPRITE,
                             (3831, 7584, 300), 0xD779B, (1977, 6760, 181), 0xD778B, 0xD777B,
                             PortalPolicy('level02_admin', 'eligible_order', False, 0, True, (-20, 20), (180, 181), False, consume_invalid_event=True))

# Execution order below is reversed from the original stored SPRD stacks.
# Extra commands pin the original effect as well as its proximity condition.
INTERIOR_STAIR_ENCOUNTERS = (
    PartyTrigger('interior_stair_monster_01', 'level02',
                 SpriteIdentity(0x8B010, 0x186E38C0, 1025, (2173.0, 5769.0, 90.0)),
                 (1590, 6088, 230), (0xD7ED4,), (
                     MapCommand(0xD7EC4, (95, 3, 6220, 0)),
                 )),
    PartyTrigger('interior_stair_monster_02', 'level02',
                 SpriteIdentity(0x8B670, 0x186E6258, 1025, (2058.0, 5681.0, 90.0)),
                 (1590, 6088, 230), (0xD8264,), (
                     MapCommand(0xD8254, (95, 3, 6220, 0)),
                 )),
    PartyTrigger('interior_stair_monster_03', 'level02',
                 SpriteIdentity(0x8B730, 0x186E66C0, 1025, (2004.0, 5636.0, 90.0)),
                 (1590, 6088, 230), (0xD82FC,), (
                     MapCommand(0xD82EC, (95, 3, 6220, 0)),
                 )),
)

INTERIOR_CORRIDOR_GENERATORS = (
    PartyTrigger('interior_corridor_generator_01', 'level02',
                 SpriteIdentity(0x8F060, 0x186FBDC0, 908, (2257.0, 4428.0, 0.0)),
                 (1844, 5545, 180), (0xDD83F,), (
                     MapCommand(0xDD82F, (35, 1025, -150, -120)),
                     MapCommand(0xDD81F, (35, 1025, -150, -120)),
                     MapCommand(0xDD80F, (35, 1025, -150, -120)),
                     MapCommand(0xDD7FF, (35, 1025, -150, -120)),
                     MapCommand(0xDD7EF, (35, 1025, -150, -120)),
                     MapCommand(0xDD7DF, (35, 1025, -150, -120)),
                     MapCommand(0xDD7CF, (35, 1025, -150, -120)),
                     MapCommand(0xDD7BF, (35, 1025, -150, -120)),
                     MapCommand(0xDD7AF, (35, 1025, -150, -120)),
                     MapCommand(0xDD79F, (35, 1025, -150, -120)),
                     MapCommand(0xDD78F, (35, 1025, -150, -120)),
                     MapCommand(0xDD77F, (35, 1025, -150, -120)),
                     MapCommand(0xDD76F, (35, 1025, -150, -120)),
                     MapCommand(0xDD75F, (35, 1025, -150, -120)),
                     MapCommand(0xDD74F, (73, 0, 0, 0)),
                     MapCommand(0xDD73F, (33, 2072, 4557, 0)),
                 )),
)

INTERIOR_LOWER_ENCOUNTERS = (
    PartyTrigger('interior_lower_monster_01', 'level02',
                 SpriteIdentity(0x8ED90, 0x186EB060, 1025, (2567.9462890625, 4482.60888671875, 0.0)),
                 (1534, 4977, 250), (0xDD314,), (
                     MapCommand(0xDD304, (33, 2019, 4635, 0)),
                     MapCommand(0xDD2F4, (95, 3, 4977, 0)),
                     MapCommand(0xDD2E4, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_02', 'level02',
                 SpriteIdentity(0x8EE80, 0x186FB480, 1025, (2318.44873046875, 4360.9482421875, 0.0)),
                 (1534, 4977, 250), (0xDD3CD,), (
                     MapCommand(0xDD3BD, (33, 2019, 4635, 0)),
                     MapCommand(0xDD3AD, (95, 3, 4977, 0)),
                     MapCommand(0xDD39D, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_03', 'level02',
                 SpriteIdentity(0x8EEB0, 0x186FB558, 1025, (2361.634765625, 4363.56494140625, 0.0)),
                 (1534, 4977, 250), (0xDD432,), (
                     MapCommand(0xDD422, (33, 2019, 4635, 0)),
                     MapCommand(0xDD412, (95, 3, 4977, 0)),
                     MapCommand(0xDD402, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_04', 'level02',
                 SpriteIdentity(0x8EEE0, 0x186FB630, 1025, (2391.752197265625, 4443.87451171875, 0.0)),
                 (1534, 4977, 250), (0xDD497,), (
                     MapCommand(0xDD487, (33, 2019, 4635, 0)),
                     MapCommand(0xDD477, (95, 3, 4977, 0)),
                     MapCommand(0xDD467, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_05', 'level02',
                 SpriteIdentity(0x8EF10, 0x186FB770, 1025, (2397.585205078125, 4488.84326171875, 0.0)),
                 (1534, 4977, 250), (0xDD4FC,), (
                     MapCommand(0xDD4EC, (33, 2019, 4635, 0)),
                     MapCommand(0xDD4DC, (95, 3, 4977, 0)),
                     MapCommand(0xDD4CC, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_06', 'level02',
                 SpriteIdentity(0x8EF40, 0x186FB848, 1025, (2508.509033203125, 4498.19921875, 0.0)),
                 (1534, 4977, 250), (0xDD561,), (
                     MapCommand(0xDD551, (33, 2019, 4635, 0)),
                     MapCommand(0xDD541, (95, 3, 4977, 0)),
                     MapCommand(0xDD531, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_07', 'level02',
                 SpriteIdentity(0x8EF70, 0x186FB920, 1025, (2456.419921875, 4545.59375, 0.0)),
                 (1534, 4977, 250), (0xDD5C6,), (
                     MapCommand(0xDD5B6, (33, 2019, 4635, 0)),
                     MapCommand(0xDD5A6, (95, 3, 4977, 0)),
                     MapCommand(0xDD596, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_08', 'level02',
                 SpriteIdentity(0x8EFA0, 0x186FBAA0, 1025, (2414.5869140625, 4581.857421875, 0.0)),
                 (1534, 4977, 250), (0xDD62B,), (
                     MapCommand(0xDD61B, (33, 2019, 4635, 0)),
                     MapCommand(0xDD60B, (95, 3, 4977, 0)),
                     MapCommand(0xDD5FB, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_09', 'level02',
                 SpriteIdentity(0x8EFD0, 0x186FBB78, 1025, (2372.779541015625, 4535.79541015625, 0.0)),
                 (1534, 4977, 250), (0xDD690,), (
                     MapCommand(0xDD680, (33, 2019, 4635, 0)),
                     MapCommand(0xDD670, (95, 3, 4977, 0)),
                     MapCommand(0xDD660, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_10', 'level02',
                 SpriteIdentity(0x8F000, 0x186FBC50, 1025, (2350.813720703125, 4420.1044921875, 0.0)),
                 (1534, 4977, 250), (0xDD6F5,), (
                     MapCommand(0xDD6E5, (33, 2019, 4635, 0)),
                     MapCommand(0xDD6D5, (95, 3, 4977, 0)),
                     MapCommand(0xDD6C5, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_11', 'level02',
                 SpriteIdentity(0x8F090, 0x186FBEB8, 1025, (2168.99560546875, 4381.18603515625, 0.0)),
                 (1534, 4977, 250), (0xDD8A4,), (
                     MapCommand(0xDD894, (33, 2019, 4635, 0)),
                     MapCommand(0xDD884, (95, 3, 4977, 0)),
                     MapCommand(0xDD874, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_12', 'level02',
                 SpriteIdentity(0x8F0C0, 0x186FBF90, 1025, (2119.956787109375, 4389.97705078125, 0.0)),
                 (1534, 4977, 250), (0xDD909,), (
                     MapCommand(0xDD8F9, (33, 2019, 4635, 0)),
                     MapCommand(0xDD8E9, (95, 3, 4977, 0)),
                     MapCommand(0xDD8D9, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_13', 'level02',
                 SpriteIdentity(0x8F0F0, 0x186FC068, 1025, (2174.787109375, 4423.0576171875, 0.0)),
                 (1534, 4977, 250), (0xDD96E,), (
                     MapCommand(0xDD95E, (33, 2019, 4635, 0)),
                     MapCommand(0xDD94E, (95, 3, 4977, 0)),
                     MapCommand(0xDD93E, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_14', 'level02',
                 SpriteIdentity(0x8F120, 0x186FC140, 1025, (2138.622314453125, 4463.728515625, 0.0)),
                 (1534, 4977, 250), (0xDD9D3,), (
                     MapCommand(0xDD9C3, (33, 2019, 4635, 0)),
                     MapCommand(0xDD9B3, (95, 3, 4977, 0)),
                     MapCommand(0xDD9A3, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_15', 'level02',
                 SpriteIdentity(0x8F150, 0x186FC218, 1025, (2193.3876953125, 4498.87841796875, 0.0)),
                 (1534, 4977, 250), (0xDDA38,), (
                     MapCommand(0xDDA28, (33, 2019, 4635, 0)),
                     MapCommand(0xDDA18, (95, 3, 4977, 0)),
                     MapCommand(0xDDA08, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_16', 'level02',
                 SpriteIdentity(0x8F180, 0x186FC3C0, 1025, (2257.20751953125, 4530.83544921875, 0.0)),
                 (1534, 4977, 250), (0xDDA9D,), (
                     MapCommand(0xDDA8D, (33, 2019, 4635, 0)),
                     MapCommand(0xDDA7D, (95, 3, 4977, 0)),
                     MapCommand(0xDDA6D, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_17', 'level02',
                 SpriteIdentity(0x8F1B0, 0x186FC498, 1025, (2172.444091796875, 4548.93896484375, 0.0)),
                 (1534, 4977, 250), (0xDDB02,), (
                     MapCommand(0xDDAF2, (33, 2019, 4635, 0)),
                     MapCommand(0xDDAE2, (95, 3, 4977, 0)),
                     MapCommand(0xDDAD2, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_18', 'level02',
                 SpriteIdentity(0x8F1E0, 0x186FC570, 1025, (2119.38671875, 4553.279296875, 0.0)),
                 (1534, 4977, 250), (0xDDB67,), (
                     MapCommand(0xDDB57, (33, 2019, 4635, 0)),
                     MapCommand(0xDDB47, (95, 3, 4977, 0)),
                     MapCommand(0xDDB37, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_19', 'level02',
                 SpriteIdentity(0x8F210, 0x186FC648, 1025, (2087.6669921875, 4501.48291015625, 0.0)),
                 (1534, 4977, 250), (0xDDBCC,), (
                     MapCommand(0xDDBBC, (33, 2019, 4635, 0)),
                     MapCommand(0xDDBAC, (95, 3, 4977, 0)),
                     MapCommand(0xDDB9C, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_20', 'level02',
                 SpriteIdentity(0x8FDB0, 0x187006D0, 1025, (2320.620361328125, 4309.8330078125, 0.0)),
                 (1534, 4977, 250), (0xDFB0B,), (
                     MapCommand(0xDFAFB, (33, 2019, 4635, 0)),
                     MapCommand(0xDFAEB, (95, 3, 4977, 0)),
                     MapCommand(0xDFADB, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_21', 'level02',
                 SpriteIdentity(0x8FF30, 0x18701010, 1025, (2222.237548828125, 4311.74462890625, 0.0)),
                 (1534, 4977, 250), (0xDFC53,), (
                     MapCommand(0xDFC43, (33, 2019, 4635, 0)),
                     MapCommand(0xDFC33, (95, 3, 4977, 0)),
                     MapCommand(0xDFC23, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_22', 'level02',
                 SpriteIdentity(0x8FF60, 0x187010E8, 1025, (2231.436767578125, 4263.28173828125, 0.0)),
                 (1534, 4977, 250), (0xDFCB8,), (
                     MapCommand(0xDFCA8, (33, 2019, 4635, 0)),
                     MapCommand(0xDFC98, (95, 3, 4977, 0)),
                     MapCommand(0xDFC88, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_23', 'level02',
                 SpriteIdentity(0x8FF90, 0x18701228, 1025, (2275.212890625, 4283.82373046875, 0.0)),
                 (1534, 4977, 250), (0xDFD1D,), (
                     MapCommand(0xDFD0D, (33, 2019, 4635, 0)),
                     MapCommand(0xDFCFD, (95, 3, 4977, 0)),
                     MapCommand(0xDFCED, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_24', 'level02',
                 SpriteIdentity(0x8FFC0, 0x18701300, 1025, (2265.863525390625, 4325.70849609375, 0.0)),
                 (1534, 4977, 250), (0xDFD82,), (
                     MapCommand(0xDFD72, (33, 2019, 4635, 0)),
                     MapCommand(0xDFD62, (95, 3, 4977, 0)),
                     MapCommand(0xDFD52, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_25', 'level02',
                 SpriteIdentity(0x8FFF0, 0x187013D8, 1025, (2179.726318359375, 4294.17578125, 0.0)),
                 (1534, 4977, 250), (0xDFDE7,), (
                     MapCommand(0xDFDD7, (33, 2019, 4635, 0)),
                     MapCommand(0xDFDC7, (95, 3, 4977, 0)),
                     MapCommand(0xDFDB7, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_26', 'level02',
                 SpriteIdentity(0x90020, 0x187014B0, 1025, (2143.373291015625, 4339.32470703125, 0.0)),
                 (1534, 4977, 250), (0xDFE4C,), (
                     MapCommand(0xDFE3C, (33, 2019, 4635, 0)),
                     MapCommand(0xDFE2C, (95, 3, 4977, 0)),
                     MapCommand(0xDFE1C, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
    PartyTrigger('interior_lower_monster_27', 'level02',
                 SpriteIdentity(0x90050, 0x18701630, 1025, (2280.8759765625, 4233.8857421875, 0.0)),
                 (1534, 4977, 250), (0xDFEB1,), (
                     MapCommand(0xDFEA1, (33, 2019, 4635, 0)),
                     MapCommand(0xDFE91, (95, 3, 4977, 0)),
                     MapCommand(0xDFE81, (33, 1853, 4731, 0)),
                 ), source_guard='map_vid_act43'),
)

LEVEL02_ENCOUNTER_TRIGGERS = (
    INTERIOR_STAIR_ENCOUNTERS + INTERIOR_CORRIDOR_GENERATORS + INTERIOR_LOWER_ENCOUNTERS
)

# Original wait-q42 commands precede ACT43 in execution. extra_commands guards
# the whole original stack, including that prerequisite; commands() enumerates
# guards, not an execution program. No quest setters or new door script exist.
Q42_DOORS = (
    PartyTrigger('personal_key_door_01', 'level02',
                 SpriteIdentity(0x8B8B0, 0x186E6EA0, 1777, (3577.0, 5133.0, 0.0)),
                 (3621, 5084, 120), (0xD84E4,), (
                     MapCommand(0xD84F4, (77, 1, 42, 0)),
                     MapCommand(0xD84D4, (131, 5, 11, 0)),
                     MapCommand(0xD84C4, (135, 75, 0, 0)),
                     MapCommand(0xD84B4, (40, 800, 0, 0)),
                     MapCommand(0xD84A4, (15, 0, 0, 0)),
                 )),
    PartyTrigger('personal_key_door_02', 'level02',
                 SpriteIdentity(0x8D5F0, 0x186F23B0, 1777, (3758.0, 4748.0, 0.0)),
                 (3776, 4760, 90), (0xDA2F8,), (
                     MapCommand(0xDA308, (77, 1, 42, 0)),
                     MapCommand(0xDA2E8, (131, 5, 11, 0)),
                     MapCommand(0xDA2D8, (135, 75, 0, 0)),
                     MapCommand(0xDA2C8, (40, 800, 0, 0)),
                     MapCommand(0xDA2B8, (15, 0, 0, 0)),
                 )),
    PartyTrigger('personal_key_door_03', 'level02',
                 SpriteIdentity(0x8DA70, 0x186F3CA8, 1777, (2948.0, 4685.0, 0.0)),
                 (2979, 4652, 110), (0xDB280,), (
                     MapCommand(0xDB290, (77, 1, 42, 0)),
                     MapCommand(0xDB270, (131, 5, 10, 0)),
                     MapCommand(0xDB260, (135, 75, 0, 0)),
                     MapCommand(0xDB250, (40, 800, 0, 0)),
                     MapCommand(0xDB240, (15, 0, 0, 0)),
                 )),
    PartyTrigger('personal_key_door_04', 'level02',
                 SpriteIdentity(0x8EB80, 0x186F9AE8, 1777, (3487.0, 4557.0, 0.0)),
                 (3464, 4519, 110), (0xDD07D,), (
                     MapCommand(0xDD08D, (77, 1, 42, 0)),
                     MapCommand(0xDD06D, (131, 5, 10, 0)),
                     MapCommand(0xDD05D, (135, 75, 0, 0)),
                     MapCommand(0xDD04D, (40, 800, 0, 0)),
                     MapCommand(0xDD03D, (15, 0, 0, 0)),
                 )),
)

# Pure proximity -> original shared roof group h1. This is distinct from the
# closed door without a stack, the destructible wall, or the personalkey item.
PERSONAL_KEY_ROOM_ROOF = PartyTrigger(
    'personal_key_room_roof', 'level02',
    SpriteIdentity(0x8FE40, 0x18700B68, 922, (2213.0, 4177.0, 0.0)),
    (2110, 4046, 120), (0xDFB9A,), (MapCommand(0xDFB8A, (131, 5, 1, 0)),),
)

LEVEL02_DOOR_ROOF_TRIGGERS = Q42_DOORS + (PERSONAL_KEY_ROOM_ROOF,)


# Remaining original ACT43 conditions for manual campaign play. Existing tuples
# above are intentionally unchanged: historical native profiles refer to them.
# These are source-byte guards, not replacement programs. Original quest waits,
# dialogue, delays, combat targets, generators, animation and loop commands stay
# in the map. Sources are declared once even when several stacks/conditions use
# them; each generated entry guards the complete original source command set.
def _remaining_source_triggers(name, sprite, stacks, runtime_vid=None):
    commands = tuple(command for stack in stacks for command in stack)
    conditions = {}
    for command in commands:
        if command.values[0] == 43:
            conditions.setdefault(command.values[1:], []).append(command.offset)
    return tuple(
        PartyTrigger(
            name if len(conditions) == 1 else f'{name}_{index:02d}',
            'level02', sprite, trigger, tuple(records),
            tuple(command for command in commands if command.offset not in records),
            source_guard='map_vid_act43', runtime_vid=runtime_vid,
        )
        for index, (trigger, records) in enumerate(conditions.items(), 1)
    )


# (stable name, exact original SPR identity, stacks in execution order,
#  optional effective VID at ACT43). Four NPCs change 1154 -> 1155 before their
#  conditions: retain original VID1154 in SpriteIdentity and guard ACT62 too.
_LEVEL02_REMAINING_SOURCES = (
    ('supplemental_logic_186dab10',
     SpriteIdentity(0x89ab0, 0x186dab10, 922, (2993.0, 9411.0, 90.0)), (
         (
             MapCommand(0xd6aa1, (43, 3166, 9316, 470)),
             MapCommand(0xd6a91, (135, 112, 0, 0)),
             MapCommand(0xd6a81, (35, 923, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_npc_186db0b0',
     SpriteIdentity(0x89b40, 0x186db0b0, 1160, (4602.0, 8976.0, 0.0)), (
         (
             MapCommand(0xd6bbd, (43, 4552, 9000, 380)),
             MapCommand(0xd6bad, (33, 4572, 8991, 0)),
             MapCommand(0xd6b9d, (41, 160, 0, 0)),
             MapCommand(0xd6b8d, (43, 4504, 9035, 70)),
             MapCommand(0xd6b7d, (115, 8, 0, 0)),
             MapCommand(0xd6b6d, (40, 500, 0, 0)),
             MapCommand(0xd6b5d, (78, 1, 39, 0)),
             MapCommand(0xd6b4d, (40, 17000, 0, 0)),
             MapCommand(0xd6b3d, (46, 4602, 8976, 2)),
             MapCommand(0xd6b2d, (95, 1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_door_186dc240',
     SpriteIdentity(0x89d80, 0x186dc240, 1731, (4138.544921875, 8871.154296875, 0.03293609619140625)), (
         (
             MapCommand(0xd6d16, (43, 4134, 8829, 190)),
             MapCommand(0xd6d06, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_door_186dc520',
     SpriteIdentity(0x89de0, 0x186dc520, 1731, (3721.545166015625, 8866.154296875, 0.03293609619140625)), (
         (
             MapCommand(0xd6d9c, (77, 1, 39, 0)),
             MapCommand(0xd6d8c, (43, 3720, 8838, 240)),
             MapCommand(0xd6d7c, (78, 1, 40, 0)),
             MapCommand(0xd6d6c, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_186dc6d8',
     SpriteIdentity(0x89e10, 0x186dc6d8, 922, (3733.999755859375, 8900.0, 0.0)), (
         (
             MapCommand(0xd6e01, (43, 3777, 8843, 120)),
             MapCommand(0xd6df1, (116, 125, 0, 0)),
             MapCommand(0xd6de1, (40, 3500, 0, 0)),
             MapCommand(0xd6dd1, (71, 3, 0, 0)),
         ),
         (
             MapCommand(0xd6e25, (77, 1, 39, 0)),
             MapCommand(0xd6e15, (134, -1, 0, 0)),
         ),
         (
             MapCommand(0xd6e49, (77, 1, 40, 0)),
             MapCommand(0xd6e39, (134, -1, 0, 0)),
         ),
         (
         ),
     ), None),
    ('supplemental_generator_186dc978',
     SpriteIdentity(0x89ea0, 0x186dc978, 908, (5376.0, 8448.0, 0.0)), (
         (
             MapCommand(0xd6fa0, (35, 1025, -10, -10)),
             MapCommand(0xd6f90, (35, 1030, -10, -10)),
             MapCommand(0xd6f80, (40, 300, 800, 0)),
             MapCommand(0xd6f70, (35, 1025, -10, -10)),
             MapCommand(0xd6f60, (35, 1025, -10, -10)),
             MapCommand(0xd6f50, (35, 1025, -10, -10)),
             MapCommand(0xd6f40, (40, 100, 800, 0)),
             MapCommand(0xd6f30, (35, 1037, -10, -10)),
             MapCommand(0xd6f20, (35, 1025, -10, -10)),
             MapCommand(0xd6f10, (35, 1025, -10, -10)),
             MapCommand(0xd6f00, (40, 300, 800, 0)),
             MapCommand(0xd6ef0, (71, 16, 0, 0)),
             MapCommand(0xd6ee0, (73, 0, 0, 0)),
             MapCommand(0xd6ed0, (33, 5193, 8551, 5)),
             MapCommand(0xd6ec0, (33, 5038, 8636, 0)),
             MapCommand(0xd6eb0, (33, 4787, 8828, 0)),
             MapCommand(0xd6ea0, (33, 4639, 8927, 0)),
         ),
         (
             MapCommand(0xd6fc4, (43, 1926, 6721, 500)),
             MapCommand(0xd6fb4, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_186dd238',
     SpriteIdentity(0x8a020, 0x186dd238, 922, (4764.544921875, 8543.154296875, 17.032936096191406)), (
         (
             MapCommand(0xd7108, (43, 8351, 8935, 80)),
             MapCommand(0xd70f8, (116, 51, 0, 48)),
             MapCommand(0xd70e8, (131, 15, 1, 0)),
             MapCommand(0xd70d8, (131, 2, 100, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_door_186ddf40',
     SpriteIdentity(0x8a1a0, 0x186ddf40, 1731, (3774.545166015625, 8617.154296875, 0.03293609619140625)), (
         (
             MapCommand(0xd71f2, (43, 3848, 8618, 190)),
             MapCommand(0xd71e2, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_186de148',
     SpriteIdentity(0x8a200, 0x186de148, 922, (3667.0, 8526.0, 29.516468048095703)), (
         (
             MapCommand(0xd729c, (43, 3665, 8506, 25)),
             MapCommand(0xd728c, (131, 6, 1, 0)),
             MapCommand(0xd727c, (43, 3743, 8600, 100)),
             MapCommand(0xd726c, (71, 3, 1, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('campaign_secondary_exit',
     SpriteIdentity(0x8a680, 0x186dfce0, 922, (3713.545166015625, 8032.154296875, 1.032938003540039)), (
         (
             MapCommand(0xd7564, (77, 1, 8, 1)),
             MapCommand(0xd7554, (43, 7230, 8409, 140)),
             MapCommand(0xd7544, (131, 9, 1, 0)),
         ),
         (
             MapCommand(0xd7578, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_npc_186e07f0',
     SpriteIdentity(0x8a8c0, 0x186e07f0, 1155, (76.0, 6753.0, 0.0)), (
         (
             MapCommand(0xd7800, (77, 1, 20, 0)),
             MapCommand(0xd77f0, (43, 4698, 3884, 500)),
             MapCommand(0xd77e0, (40, 18000, 0, 0)),
             MapCommand(0xd77d0, (115, 44, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_npc_186e0b10',
     SpriteIdentity(0x8a8f0, 0x186e0b10, 1182, (101.0, 6872.0, 0.0)), (
         (
             MapCommand(0xd7a85, (88, 0, 150, 0)),
             MapCommand(0xd7a75, (77, 1, 23, 0)),
             MapCommand(0xd7a65, (63, 3145, 4983, 2)),
             MapCommand(0xd7a55, (41, 38, 0, 0)),
             MapCommand(0xd7a45, (46, 3145, 4983, 2)),
             MapCommand(0xd7a35, (79, 11, 2, 0)),
             MapCommand(0xd7a25, (43, 3215, 4918, 250)),
             MapCommand(0xd7a15, (95, 0, 0, 0)),
             MapCommand(0xd7a05, (62, 1180, 0, 0)),
             MapCommand(0xd79f5, (41, 38, 0, 0)),
             MapCommand(0xd79e5, (46, 3145, 4983, 2)),
             MapCommand(0xd79d5, (115, 165, 0, 0)),
             MapCommand(0xd79c5, (40, 2500, 0, 0)),
             MapCommand(0xd79b5, (131, 10, 4, 0)),
             MapCommand(0xd79a5, (40, 6500, 0, 0)),
             MapCommand(0xd7995, (115, 166, 0, 0)),
             MapCommand(0xd7985, (40, 999999, 0, 1)),
             MapCommand(0xd7975, (131, 14, 1, 0)),
             MapCommand(0xd7965, (79, 14, 2, 0)),
             MapCommand(0xd7955, (40, 1500, 0, 0)),
             MapCommand(0xd7945, (62, 1182, 0, 0)),
             MapCommand(0xd7935, (95, 1, 0, 0)),
             MapCommand(0xd7925, (46, 3145, 4983, 2)),
             MapCommand(0xd7915, (115, 167, 0, 0)),
             MapCommand(0xd7905, (40, 2000, 0, 0)),
             MapCommand(0xd78f5, (131, 16, 1, 0)),
             MapCommand(0xd78e5, (33, 2521, 5428, 90)),
             MapCommand(0xd78d5, (46, 2521, 5428, 90)),
             MapCommand(0xd78c5, (77, 1, 25, 0)),
             MapCommand(0xd78b5, (40, 2000, 500, 0)),
             MapCommand(0xd78a5, (33, 2575, 5597, 90)),
             MapCommand(0xd7895, (33, 2641, 5672, 90)),
             MapCommand(0xd7885, (33, 2697, 5838, 90)),
             MapCommand(0xd7875, (33, 2568, 5979, 90)),
             MapCommand(0xd7865, (33, 2421, 5944, 90)),
             MapCommand(0xd7855, (33, 2238, 5852, 90)),
             MapCommand(0xd7845, (33, 1874, 5861, 90)),
             MapCommand(0xd7835, (63, 101, 6872, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_186e61c0',
     SpriteIdentity(0x8b640, 0x186e61c0, 922, (2225.0, 5520.0, 90.0)), (
         (
             MapCommand(0xd821f, (77, 1, 25, 0)),
             MapCommand(0xd820f, (43, 2187, 5495, 70)),
             MapCommand(0xd81ff, (116, 129, 0, 0)),
             MapCommand(0xd81ef, (131, 17, 1, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_generator_186e6c88',
     SpriteIdentity(0x8b850, 0x186e6c88, 908, (3617.0, 5324.0, 0.0)), (
         (
             MapCommand(0xd845a, (77, 1, 23, 0)),
             MapCommand(0xd844a, (43, 3902, 4211, 80)),
             MapCommand(0xd843a, (35, 1025, -20, -20)),
             MapCommand(0xd842a, (35, 1025, -20, -20)),
             MapCommand(0xd841a, (35, 1025, -20, -20)),
             MapCommand(0xd840a, (35, 1025, -20, -20)),
             MapCommand(0xd83fa, (35, 1025, -20, -20)),
             MapCommand(0xd83ea, (35, 1025, -20, -20)),
             MapCommand(0xd83da, (35, 1025, -20, -20)),
             MapCommand(0xd83ca, (35, 1025, -20, -20)),
             MapCommand(0xd83ba, (35, 1025, -20, -20)),
             MapCommand(0xd83aa, (73, 0, 0, 0)),
             MapCommand(0xd839a, (33, 3081, 4939, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_186e74d8',
     SpriteIdentity(0x8b970, 0x186e74d8, 922, (3544.0, 5157.0, 2.0)), (
         (
             MapCommand(0xd8598, (43, 3603, 5111, 80)),
             MapCommand(0xd8588, (116, 126, 0, 0)),
             MapCommand(0xd8578, (40, 3500, 0, 0)),
             MapCommand(0xd8568, (71, 3, 0, 0)),
         ),
         (
             MapCommand(0xd85bc, (77, 1, 42, 0)),
             MapCommand(0xd85ac, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186ec748',
     SpriteIdentity(0x8c600, 0x186ec748, 1025, (3293.0, 4876.0, 3.0)), (
         (
             MapCommand(0xd9292, (43, 2701, 4696, 250)),
             MapCommand(0xd9282, (33, 3112, 4995, 1)),
             MapCommand(0xd9272, (95, 3, 4635, 0)),
             MapCommand(0xd9262, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186ed118',
     SpriteIdentity(0x8c7b0, 0x186ed118, 1025, (3291.00390625, 4923.09521484375, 2.0)), (
         (
             MapCommand(0xd9450, (43, 2701, 4696, 250)),
             MapCommand(0xd9440, (33, 3112, 4995, 1)),
             MapCommand(0xd9430, (95, 3, 4635, 0)),
             MapCommand(0xd9420, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186ed1f0',
     SpriteIdentity(0x8c7e0, 0x186ed1f0, 1025, (3213.993408203125, 4884.3193359375, 3.0)), (
         (
             MapCommand(0xd94b5, (43, 2701, 4696, 250)),
             MapCommand(0xd94a5, (33, 3112, 4995, 1)),
             MapCommand(0xd9495, (95, 3, 4635, 0)),
             MapCommand(0xd9485, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f0ca0',
     SpriteIdentity(0x8d1a0, 0x186f0ca0, 1025, (4623.0, 4646.0, 0.0)), (
         (
             MapCommand(0xd9b02, (43, 3735, 4565, 300)),
             MapCommand(0xd9af2, (33, 4121, 4320, 1)),
             MapCommand(0xd9ae2, (95, 3, 4565, 0)),
             MapCommand(0xd9ad2, (33, 3923, 4406, 0)),
             MapCommand(0xd9ac2, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f0e08',
     SpriteIdentity(0x8d1d0, 0x186f0e08, 1025, (4663.0, 4646.0, 0.0)), (
         (
             MapCommand(0xd9b77, (43, 3735, 4565, 300)),
             MapCommand(0xd9b67, (33, 4121, 4320, 1)),
             MapCommand(0xd9b57, (95, 3, 4565, 0)),
             MapCommand(0xd9b47, (33, 3923, 4406, 0)),
             MapCommand(0xd9b37, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f0ee0',
     SpriteIdentity(0x8d200, 0x186f0ee0, 1025, (4623.0, 4686.0, 0.0)), (
         (
             MapCommand(0xd9bec, (43, 3735, 4565, 300)),
             MapCommand(0xd9bdc, (33, 4121, 4320, 1)),
             MapCommand(0xd9bcc, (95, 3, 4565, 0)),
             MapCommand(0xd9bbc, (33, 3923, 4406, 0)),
             MapCommand(0xd9bac, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f0fb8',
     SpriteIdentity(0x8d230, 0x186f0fb8, 1025, (4663.0, 4686.0, 0.0)), (
         (
             MapCommand(0xd9c61, (43, 3735, 4565, 300)),
             MapCommand(0xd9c51, (33, 4121, 4320, 1)),
             MapCommand(0xd9c41, (95, 3, 4565, 0)),
             MapCommand(0xd9c31, (33, 3923, 4406, 0)),
             MapCommand(0xd9c21, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f10f8',
     SpriteIdentity(0x8d260, 0x186f10f8, 1025, (4703.0, 4686.0, 0.0)), (
         (
             MapCommand(0xd9cd6, (43, 3735, 4565, 300)),
             MapCommand(0xd9cc6, (33, 4121, 4320, 1)),
             MapCommand(0xd9cb6, (95, 3, 4565, 0)),
             MapCommand(0xd9ca6, (33, 3923, 4406, 0)),
             MapCommand(0xd9c96, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f12a0',
     SpriteIdentity(0x8d290, 0x186f12a0, 1025, (4743.0, 4686.0, 0.0)), (
         (
             MapCommand(0xd9d4b, (43, 3735, 4565, 300)),
             MapCommand(0xd9d3b, (33, 4121, 4320, 1)),
             MapCommand(0xd9d2b, (95, 3, 4565, 0)),
             MapCommand(0xd9d1b, (33, 3923, 4406, 0)),
             MapCommand(0xd9d0b, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f1378',
     SpriteIdentity(0x8d2c0, 0x186f1378, 1025, (4623.0, 4726.0, 0.0)), (
         (
             MapCommand(0xd9dc0, (43, 3735, 4565, 300)),
             MapCommand(0xd9db0, (33, 4121, 4320, 1)),
             MapCommand(0xd9da0, (95, 3, 4565, 0)),
             MapCommand(0xd9d90, (33, 3923, 4406, 0)),
             MapCommand(0xd9d80, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186ecaa0',
     SpriteIdentity(0x8d2f0, 0x186ecaa0, 1025, (4663.0, 4726.0, 0.0)), (
         (
             MapCommand(0xd9e35, (43, 3735, 4565, 300)),
             MapCommand(0xd9e25, (33, 4121, 4320, 1)),
             MapCommand(0xd9e15, (95, 3, 4565, 0)),
             MapCommand(0xd9e05, (33, 3923, 4406, 0)),
             MapCommand(0xd9df5, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f1678',
     SpriteIdentity(0x8d320, 0x186f1678, 1025, (4703.0, 4726.0, 0.0)), (
         (
             MapCommand(0xd9eaa, (43, 3735, 4565, 300)),
             MapCommand(0xd9e9a, (33, 4121, 4320, 1)),
             MapCommand(0xd9e8a, (95, 3, 4565, 0)),
             MapCommand(0xd9e7a, (33, 3923, 4406, 0)),
             MapCommand(0xd9e6a, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f1750',
     SpriteIdentity(0x8d350, 0x186f1750, 1025, (4743.0, 4726.0, 0.0)), (
         (
             MapCommand(0xd9f1f, (43, 3735, 4565, 300)),
             MapCommand(0xd9f0f, (33, 4121, 4320, 1)),
             MapCommand(0xd9eff, (95, 3, 4565, 0)),
             MapCommand(0xd9eef, (33, 3923, 4406, 0)),
             MapCommand(0xd9edf, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f1828',
     SpriteIdentity(0x8d380, 0x186f1828, 1025, (4735.0, 4776.0, 0.0)), (
         (
             MapCommand(0xd9f94, (43, 3735, 4565, 300)),
             MapCommand(0xd9f84, (33, 4121, 4320, 1)),
             MapCommand(0xd9f74, (95, 3, 4565, 0)),
             MapCommand(0xd9f64, (33, 3923, 4406, 0)),
             MapCommand(0xd9f54, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f1aa0',
     SpriteIdentity(0x8d3e0, 0x186f1aa0, 1025, (4421.0, 4656.0, 3.0)), (
         (
             MapCommand(0xda14e, (43, 3735, 4565, 300)),
             MapCommand(0xda13e, (33, 4121, 4320, 1)),
             MapCommand(0xda12e, (33, 3923, 4406, 0)),
             MapCommand(0xda11e, (95, 3, 4565, 0)),
             MapCommand(0xda10e, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f1ca8',
     SpriteIdentity(0x8d470, 0x186f1ca8, 1025, (4354.0, 4616.0, 2.0)), (
         (
             MapCommand(0xda1ed, (43, 3735, 4565, 300)),
             MapCommand(0xda1dd, (33, 4121, 4320, 1)),
             MapCommand(0xda1cd, (95, 3, 4565, 0)),
             MapCommand(0xda1bd, (33, 3923, 4406, 0)),
             MapCommand(0xda1ad, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f2600',
     SpriteIdentity(0x8d620, 0x186f2600, 1025, (3351.0, 4845.0, 2.0)), (
         (
             MapCommand(0xda36d, (43, 2701, 4696, 250)),
             MapCommand(0xda35d, (33, 3112, 4995, 1)),
             MapCommand(0xda34d, (95, 3, 4635, 0)),
             MapCommand(0xda33d, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f2840',
     SpriteIdentity(0x8d680, 0x186f2840, 1025, (3445.0, 4809.0, 2.0)), (
         (
             MapCommand(0xda3e7, (43, 2701, 4696, 250)),
             MapCommand(0xda3d7, (33, 3112, 4995, 1)),
             MapCommand(0xda3c7, (95, 3, 4635, 0)),
             MapCommand(0xda3b7, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f2918',
     SpriteIdentity(0x8d6b0, 0x186f2918, 1025, (3564.0, 4743.0, 3.0)), (
         (
             MapCommand(0xda44c, (43, 2701, 4696, 250)),
             MapCommand(0xda43c, (33, 3112, 4995, 1)),
             MapCommand(0xda42c, (95, 3, 4635, 0)),
             MapCommand(0xda41c, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f29f0',
     SpriteIdentity(0x8d6e0, 0x186f29f0, 1025, (3453.0, 4762.0, 2.0)), (
         (
             MapCommand(0xda4b1, (43, 2701, 4696, 250)),
             MapCommand(0xda4a1, (33, 3112, 4995, 1)),
             MapCommand(0xda491, (95, 3, 4635, 0)),
             MapCommand(0xda481, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f2b98',
     SpriteIdentity(0x8d710, 0x186f2b98, 1025, (3447.0, 4695.0, 2.0)), (
         (
             MapCommand(0xda516, (43, 2701, 4696, 250)),
             MapCommand(0xda506, (33, 3112, 4995, 1)),
             MapCommand(0xda4f6, (95, 3, 4635, 0)),
             MapCommand(0xda4e6, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f2c70',
     SpriteIdentity(0x8d740, 0x186f2c70, 1025, (3481.0, 4648.0, 3.0)), (
         (
             MapCommand(0xda57b, (43, 2701, 4696, 250)),
             MapCommand(0xda56b, (33, 3112, 4995, 1)),
             MapCommand(0xda55b, (95, 3, 4635, 0)),
             MapCommand(0xda54b, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f2d48',
     SpriteIdentity(0x8d770, 0x186f2d48, 1025, (3573.0, 4649.0, 3.0)), (
         (
             MapCommand(0xda5e0, (43, 2701, 4696, 250)),
             MapCommand(0xda5d0, (33, 3112, 4995, 1)),
             MapCommand(0xda5c0, (95, 3, 4635, 0)),
             MapCommand(0xda5b0, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f2e20',
     SpriteIdentity(0x8d7a0, 0x186f2e20, 1025, (3560.0, 4696.0, 2.0)), (
         (
             MapCommand(0xda645, (43, 2701, 4696, 250)),
             MapCommand(0xda635, (33, 3112, 4995, 1)),
             MapCommand(0xda625, (95, 3, 4635, 0)),
             MapCommand(0xda615, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f2ef8',
     SpriteIdentity(0x8d7d0, 0x186f2ef8, 1025, (3519.0, 4792.0, 2.0)), (
         (
             MapCommand(0xda6aa, (43, 2701, 4696, 250)),
             MapCommand(0xda69a, (33, 3112, 4995, 1)),
             MapCommand(0xda68a, (95, 3, 4635, 0)),
             MapCommand(0xda67a, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f2fd0',
     SpriteIdentity(0x8d800, 0x186f2fd0, 1025, (3445.0, 4849.0, 1.0)), (
         (
             MapCommand(0xda70f, (43, 2701, 4696, 250)),
             MapCommand(0xda6ff, (33, 3112, 4995, 1)),
             MapCommand(0xda6ef, (95, 3, 4635, 0)),
             MapCommand(0xda6df, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f30a8',
     SpriteIdentity(0x8d830, 0x186f30a8, 1025, (3344.0, 4784.0, 3.0)), (
         (
             MapCommand(0xda774, (43, 2701, 4696, 250)),
             MapCommand(0xda764, (33, 3112, 4995, 1)),
             MapCommand(0xda754, (95, 3, 4635, 0)),
             MapCommand(0xda744, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f3180',
     SpriteIdentity(0x8d860, 0x186f3180, 1025, (3371.0, 4741.0, 3.0)), (
         (
             MapCommand(0xda7d9, (43, 2701, 4696, 250)),
             MapCommand(0xda7c9, (33, 3112, 4995, 1)),
             MapCommand(0xda7b9, (95, 3, 4635, 0)),
             MapCommand(0xda7a9, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f33a8',
     SpriteIdentity(0x8d890, 0x186f33a8, 1025, (3485.0, 4849.0, 1.0)), (
         (
             MapCommand(0xda83e, (43, 2701, 4696, 250)),
             MapCommand(0xda82e, (33, 3112, 4995, 1)),
             MapCommand(0xda81e, (95, 3, 4635, 0)),
             MapCommand(0xda80e, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f3740',
     SpriteIdentity(0x8d980, 0x186f3740, 1025, (3281.0, 4821.0, 2.0)), (
         (
             MapCommand(0xdb1b7, (43, 2701, 4696, 250)),
             MapCommand(0xdb1a7, (33, 3112, 4995, 1)),
             MapCommand(0xdb197, (95, 3, 4635, 0)),
             MapCommand(0xdb187, (33, 2703, 4698, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_186f3eb0',
     SpriteIdentity(0x8daa0, 0x186f3eb0, 922, (2934.0, 4696.0, 0.0)), (
         (
             MapCommand(0xdb2f5, (43, 2961, 4665, 80)),
             MapCommand(0xdb2e5, (116, 126, 0, 0)),
             MapCommand(0xdb2d5, (40, 3500, 0, 0)),
             MapCommand(0xdb2c5, (71, 3, 0, 0)),
         ),
         (
             MapCommand(0xdb319, (77, 1, 42, 0)),
             MapCommand(0xdb309, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_door_186f4168',
     SpriteIdentity(0x8db30, 0x186f4168, 1786, (2597.0, 4618.0, 0.0)), (
         (
             MapCommand(0xdb384, (43, 4049, 3481, 200)),
             MapCommand(0xdb374, (15, 0, 0, 0)),
         ),
         (
             MapCommand(0xdb3a8, (77, 1, 25, 0)),
             MapCommand(0xdb398, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_generator_186f4200',
     SpriteIdentity(0x8db60, 0x186f4200, 908, (2673.0, 4644.0, 0.0)), (
         (
             MapCommand(0xdb479, (77, 1, 23, 0)),
             MapCommand(0xdb469, (43, 3902, 4211, 80)),
             MapCommand(0xdb459, (35, 1025, -20, -20)),
             MapCommand(0xdb449, (35, 1025, -20, -20)),
             MapCommand(0xdb439, (35, 1025, -20, -20)),
             MapCommand(0xdb429, (35, 1025, -20, -20)),
             MapCommand(0xdb419, (35, 1025, -20, -20)),
             MapCommand(0xdb409, (35, 1025, -20, -20)),
             MapCommand(0xdb3f9, (35, 1025, -20, -20)),
             MapCommand(0xdb3e9, (73, 0, 0, 0)),
             MapCommand(0xdb3d9, (33, 3081, 4939, 2)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_186f5478',
     SpriteIdentity(0x8de90, 0x186f5478, 922, (5650.0, 4487.0, 0.0)), (
         (
             MapCommand(0xdbf74, (43, 5738, 4464, 45)),
             MapCommand(0xdbf64, (135, 75, 0, 0)),
             MapCommand(0xdbf54, (40, 300, 0, 0)),
             MapCommand(0xdbf44, (131, 12, 2, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_186f65b0',
     SpriteIdentity(0x8e1c0, 0x186f65b0, 922, (5385.0, 4535.0, 0.0)), (
         (
             MapCommand(0xdc129, (43, 5515, 4451, 450)),
             MapCommand(0xdc119, (131, 13, 1, 0)),
             MapCommand(0xdc109, (131, 1, 3, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f6f58',
     SpriteIdentity(0x8e400, 0x186f6f58, 1025, (4623.0, 4606.0, 0.0)), (
         (
             MapCommand(0xdc585, (43, 3735, 4565, 300)),
             MapCommand(0xdc575, (33, 4121, 4320, 1)),
             MapCommand(0xdc565, (95, 3, 4565, 0)),
             MapCommand(0xdc555, (33, 3923, 4406, 0)),
             MapCommand(0xdc545, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f7078',
     SpriteIdentity(0x8e430, 0x186f7078, 1025, (4663.0, 4606.0, 0.0)), (
         (
             MapCommand(0xdc5fa, (43, 3735, 4565, 300)),
             MapCommand(0xdc5ea, (33, 4121, 4320, 1)),
             MapCommand(0xdc5da, (95, 3, 4565, 0)),
             MapCommand(0xdc5ca, (33, 3923, 4406, 0)),
             MapCommand(0xdc5ba, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f73e8',
     SpriteIdentity(0x8e4f0, 0x186f73e8, 1025, (4679.0, 4564.0, 0.0)), (
         (
             MapCommand(0xdc6ae, (43, 3735, 4565, 300)),
             MapCommand(0xdc69e, (33, 4121, 4320, 1)),
             MapCommand(0xdc68e, (95, 3, 4565, 0)),
             MapCommand(0xdc67e, (33, 3923, 4406, 0)),
             MapCommand(0xdc66e, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f74c0',
     SpriteIdentity(0x8e520, 0x186f74c0, 1025, (4583.0, 4566.0, 2.0)), (
         (
             MapCommand(0xdc723, (43, 3735, 4565, 300)),
             MapCommand(0xdc713, (33, 4121, 4320, 1)),
             MapCommand(0xdc703, (95, 3, 4565, 0)),
             MapCommand(0xdc6f3, (33, 3923, 4406, 0)),
             MapCommand(0xdc6e3, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f76b8',
     SpriteIdentity(0x8e580, 0x186f76b8, 1025, (4543.0, 4606.0, 1.0)), (
         (
             MapCommand(0xdc7ad, (43, 3735, 4565, 300)),
             MapCommand(0xdc79d, (33, 4121, 4320, 1)),
             MapCommand(0xdc78d, (33, 3923, 4406, 0)),
             MapCommand(0xdc77d, (95, 3, 4565, 0)),
             MapCommand(0xdc76d, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f7790',
     SpriteIdentity(0x8e5b0, 0x186f7790, 1025, (4543.0, 4526.0, 2.0)), (
         (
             MapCommand(0xdc822, (43, 3735, 4565, 300)),
             MapCommand(0xdc812, (33, 4121, 4320, 1)),
             MapCommand(0xdc802, (33, 3923, 4406, 0)),
             MapCommand(0xdc7f2, (95, 3, 4565, 0)),
             MapCommand(0xdc7e2, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f7868',
     SpriteIdentity(0x8e5e0, 0x186f7868, 1025, (4543.0, 4566.0, 2.0)), (
         (
             MapCommand(0xdc897, (43, 3735, 4565, 300)),
             MapCommand(0xdc887, (33, 4121, 4320, 1)),
             MapCommand(0xdc877, (95, 3, 4565, 0)),
             MapCommand(0xdc867, (33, 3923, 4406, 0)),
             MapCommand(0xdc857, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f7a10',
     SpriteIdentity(0x8e610, 0x186f7a10, 1025, (4583.0, 4606.0, 1.0)), (
         (
             MapCommand(0xdc90c, (43, 3735, 4565, 300)),
             MapCommand(0xdc8fc, (33, 4121, 4320, 1)),
             MapCommand(0xdc8ec, (95, 3, 4565, 0)),
             MapCommand(0xdc8dc, (33, 3923, 4406, 0)),
             MapCommand(0xdc8cc, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_186f8140',
     SpriteIdentity(0x8e760, 0x186f8140, 1025, (4447.0, 4577.0, 2.0)), (
         (
             MapCommand(0xdcddf, (43, 3735, 4565, 300)),
             MapCommand(0xdcdcf, (33, 4121, 4320, 1)),
             MapCommand(0xdcdbf, (33, 3923, 4406, 0)),
             MapCommand(0xdcdaf, (95, 3, 4565, 0)),
             MapCommand(0xdcd9f, (33, 3709, 4586, 1)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_door_186f9480',
     SpriteIdentity(0x8ea60, 0x186f9480, 1785, (3842.0, 4493.0, 0.0)), (
         (
             MapCommand(0xdcf5f, (79, 10, 4, 0)),
             MapCommand(0xdcf4f, (15, 0, 0, 0)),
         ),
         (
             MapCommand(0xdcf83, (43, 3880, 4462, 450)),
             MapCommand(0xdcf73, (15, 0, 0, 0)),
         ),
         (
             MapCommand(0xdcfa7, (77, 1, 25, 0)),
             MapCommand(0xdcf97, (15, 0, 0, 0)),
         ),
         (
         ),
     ), None),
    ('supplemental_logic_186f9cf0',
     SpriteIdentity(0x8ebb0, 0x186f9cf0, 922, (3515.0, 4584.0, 0.0)), (
         (
             MapCommand(0xdd0f2, (43, 3462, 4534, 80)),
             MapCommand(0xdd0e2, (116, 126, 0, 0)),
             MapCommand(0xdd0d2, (40, 3500, 0, 0)),
             MapCommand(0xdd0c2, (71, 3, 0, 0)),
         ),
         (
             MapCommand(0xdd116, (77, 1, 42, 0)),
             MapCommand(0xdd106, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_186fcd80',
     SpriteIdentity(0x8f3c0, 0x186fcd80, 922, (5211.0, 4287.0, 0.0)), (
         (
             MapCommand(0xddccc, (77, 1, 20, 0)),
             MapCommand(0xddcbc, (43, 5177, 4323, 280)),
             MapCommand(0xddcac, (78, 1, 21, 1)),
         ),
         (
             MapCommand(0xddd00, (77, 1, 21, 0)),
             MapCommand(0xddcf0, (135, 112, 0, 0)),
             MapCommand(0xddce0, (35, 923, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_generator_186fcf58',
     SpriteIdentity(0x8f420, 0x186fcf58, 908, (5325.0, 4245.0, 0.0)), (
         (
             MapCommand(0xddfc2, (77, 1, 22, 0)),
             MapCommand(0xddfb2, (43, 4282, 3695, 400)),
             MapCommand(0xddfa2, (40, 1000, 22, 0)),
             MapCommand(0xddf92, (35, 1092, 0, 0)),
             MapCommand(0xddf82, (73, 0, 0, 0)),
             MapCommand(0xddf72, (33, 4903, 4085, 0)),
             MapCommand(0xddf62, (40, 8000, 22, 0)),
             MapCommand(0xddf52, (33, 4099, 3587, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_generator_186fd6c8',
     SpriteIdentity(0x8f540, 0x186fd6c8, 908, (5210.0, 4339.0, 0.0)), (
         (
             MapCommand(0xde7a0, (77, 1, 22, 0)),
             MapCommand(0xde790, (43, 4282, 3695, 400)),
             MapCommand(0xde780, (40, 1000, 22, 0)),
             MapCommand(0xde770, (35, 1092, 0, 0)),
             MapCommand(0xde760, (73, 0, 0, 0)),
             MapCommand(0xde750, (33, 4903, 4085, 0)),
             MapCommand(0xde740, (40, 8000, 22, 0)),
             MapCommand(0xde730, (33, 4099, 3587, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_generator_186fd930',
     SpriteIdentity(0x8f5a0, 0x186fd930, 908, (5111.0, 4305.0, 0.0)), (
         (
             MapCommand(0xde90c, (77, 1, 20, 0)),
             MapCommand(0xde8fc, (43, 6137, 3566, 200)),
             MapCommand(0xde8ec, (35, 1025, -20, -20)),
             MapCommand(0xde8dc, (35, 1025, -20, -20)),
             MapCommand(0xde8cc, (35, 1025, -20, -20)),
             MapCommand(0xde8bc, (35, 1025, -20, -20)),
             MapCommand(0xde8ac, (35, 1025, -20, -20)),
             MapCommand(0xde89c, (35, 1025, -20, -20)),
             MapCommand(0xde88c, (35, 1025, -20, -20)),
             MapCommand(0xde87c, (35, 1025, -20, -20)),
             MapCommand(0xde86c, (35, 1025, -20, -20)),
             MapCommand(0xde85c, (35, 1025, -20, -20)),
             MapCommand(0xde84c, (35, 1025, -20, -20)),
             MapCommand(0xde83c, (35, 1025, -20, -20)),
             MapCommand(0xde82c, (35, 1025, -20, -20)),
             MapCommand(0xde81c, (35, 1025, -20, -20)),
             MapCommand(0xde80c, (73, 1025, -20, -20)),
             MapCommand(0xde7fc, (33, 4879, 4068, 0)),
             MapCommand(0xde7ec, (33, 4589, 3886, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_npc_186feb70',
     SpriteIdentity(0x8f900, 0x186feb70, 1155, (4129.0, 4238.0, 2.0)), (
         (
             MapCommand(0xdef9a, (88, 10, 0, 0)),
             MapCommand(0xdef8a, (43, 3014, 4890, 250)),
             MapCommand(0xdef7a, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_186ff2d8',
     SpriteIdentity(0x8f9f0, 0x186ff2d8, 922, (3928.0, 4235.0, 0.0)), (
         (
             MapCommand(0xdf093, (43, 3874, 4180, 80)),
             MapCommand(0xdf083, (116, 112, 0, 0)),
             MapCommand(0xdf073, (40, 3500, 0, 0)),
             MapCommand(0xdf063, (71, 3, 0, 0)),
         ),
         (
             MapCommand(0xdf0b7, (77, 1, 23, 0)),
             MapCommand(0xdf0a7, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_generator_187000a8',
     SpriteIdentity(0x8fc90, 0x187000a8, 908, (2603.0, 4204.0, 0.0)), (
         (
             MapCommand(0xdfa2f, (79, 11, 1, 0)),
             MapCommand(0xdfa1f, (43, 3990, 3428, 150)),
             MapCommand(0xdfa0f, (35, 1025, -70, -70)),
             MapCommand(0xdf9ff, (35, 1025, -70, -70)),
             MapCommand(0xdf9ef, (35, 1025, -70, -70)),
             MapCommand(0xdf9df, (35, 1037, -70, -70)),
             MapCommand(0xdf9cf, (35, 1025, -70, -70)),
             MapCommand(0xdf9bf, (35, 1025, -70, -70)),
             MapCommand(0xdf9af, (35, 1025, -70, -70)),
             MapCommand(0xdf99f, (35, 1030, -70, -70)),
             MapCommand(0xdf98f, (35, 1025, -70, -70)),
             MapCommand(0xdf97f, (35, 1025, -70, -70)),
             MapCommand(0xdf96f, (35, 1025, -70, -70)),
             MapCommand(0xdf95f, (35, 1037, -70, -70)),
             MapCommand(0xdf94f, (35, 1025, -70, -70)),
             MapCommand(0xdf93f, (35, 1030, -70, -70)),
             MapCommand(0xdf92f, (35, 1025, -70, -70)),
             MapCommand(0xdf91f, (35, 1025, -70, -70)),
             MapCommand(0xdf90f, (35, 1025, -70, -70)),
             MapCommand(0xdf8ff, (35, 1037, -70, -70)),
             MapCommand(0xdf8ef, (35, 1037, -70, -70)),
             MapCommand(0xdf8df, (35, 1025, -70, -70)),
             MapCommand(0xdf8cf, (35, 1025, -70, -70)),
             MapCommand(0xdf8bf, (35, 1037, -70, -70)),
             MapCommand(0xdf8af, (35, 1025, -70, -70)),
             MapCommand(0xdf89f, (35, 1025, -70, -70)),
             MapCommand(0xdf88f, (35, 1037, -70, -70)),
             MapCommand(0xdf87f, (35, 1025, -70, -70)),
             MapCommand(0xdf86f, (35, 1025, -70, -70)),
             MapCommand(0xdf85f, (35, 1037, -70, -70)),
             MapCommand(0xdf84f, (73, 0, 0, 0)),
             MapCommand(0xdf83f, (33, 2666, 4269, 0)),
             MapCommand(0xdf82f, (33, 2720, 4238, 0)),
             MapCommand(0xdf81f, (33, 2647, 4155, 0)),
             MapCommand(0xdf80f, (33, 2588, 4098, 0)),
             MapCommand(0xdf7ff, (33, 2679, 4101, 0)),
             MapCommand(0xdf7ef, (33, 2801, 4097, 0)),
             MapCommand(0xdf7df, (33, 2914, 4094, 0)),
             MapCommand(0xdf7cf, (33, 2996, 4045, 0)),
             MapCommand(0xdf7bf, (33, 2971, 3915, 0)),
             MapCommand(0xdf7af, (33, 2871, 3862, 0)),
             MapCommand(0xdf79f, (33, 3031, 3775, 0)),
             MapCommand(0xdf78f, (33, 3315, 3758, 0)),
             MapCommand(0xdf77f, (33, 3430, 3605, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_door_187034e0',
     SpriteIdentity(0x905c0, 0x187034e0, 1785, (4845.0, 4041.0, 0.0)), (
         (
             MapCommand(0xe04ad, (43, 4923, 4037, 250)),
             MapCommand(0xe049d, (15, 0, 0, 0)),
             MapCommand(0xe048d, (40, 1500, 1, 0)),
             MapCommand(0xe047d, (131, 1, 2, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_npc_18704518',
     SpriteIdentity(0x90950, 0x18704518, 1155, (2978.0, 3995.0, 0.0)), (
         (
             MapCommand(0xe09c3, (88, 30, 0, 0)),
             MapCommand(0xe09b3, (43, 2023, 4616, 250)),
             MapCommand(0xe09a3, (40, 2000, 2000, 0)),
             MapCommand(0xe0993, (33, 2790, 4129, 0)),
             MapCommand(0xe0983, (115, 36, 0, 0)),
             MapCommand(0xe0973, (33, 2652, 4237, 0)),
             MapCommand(0xe0963, (40, 20000, 0, 0)),
             MapCommand(0xe0953, (33, 3774, 3236, 0)),
             MapCommand(0xe0943, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_npc_18704a08',
     SpriteIdentity(0x909e0, 0x18704a08, 1155, (2904.0, 3917.0, 0.0)), (
         (
             MapCommand(0xe1024, (88, 30, 0, 0)),
             MapCommand(0xe1014, (43, 2023, 4616, 250)),
             MapCommand(0xe1004, (40, 2000, 1000, 0)),
             MapCommand(0xe0ff4, (33, 2563, 4175, 0)),
             MapCommand(0xe0fe4, (40, 20000, 0, 0)),
             MapCommand(0xe0fd4, (33, 3774, 3236, 0)),
             MapCommand(0xe0fc4, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('remote_room_entry',
     SpriteIdentity(0x90cb0, 0x18705c68, 922, (6286.0, 3670.0, 0.0)), (
         (
             MapCommand(0xe1712, (43, 6327, 3703, 90)),
             MapCommand(0xe1702, (91, 1650, 939, 0)),
             MapCommand(0xe16f2, (136, 13, 0, 0)),
             MapCommand(0xe16e2, (71, 3, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_generator_18706a48',
     SpriteIdentity(0x90fe0, 0x18706a48, 908, (5062.0, 3619.0, 0.0)), (
         (
             MapCommand(0xe1971, (77, 1, 20, 0)),
             MapCommand(0xe1961, (43, 6137, 3566, 200)),
             MapCommand(0xe1951, (35, 1025, -60, -60)),
             MapCommand(0xe1941, (35, 1025, -60, -60)),
             MapCommand(0xe1931, (35, 1025, -60, -60)),
             MapCommand(0xe1921, (35, 1025, -60, -60)),
             MapCommand(0xe1911, (35, 1025, -60, -60)),
             MapCommand(0xe1901, (35, 1025, -60, -60)),
             MapCommand(0xe18f1, (35, 1025, -60, -60)),
             MapCommand(0xe18e1, (73, 0, 0, 0)),
             MapCommand(0xe18d1, (33, 4825, 3776, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_18707f48',
     SpriteIdentity(0x91430, 0x18707f48, 1025, (3379.0, 3728.0, 0.0)), (
         (
             MapCommand(0xe1fe0, (43, 2023, 4616, 250)),
             MapCommand(0xe1fd0, (32, 410012168, 0, 0)),
             MapCommand(0xe1fc0, (32, 410010904, 0, 0)),
             MapCommand(0xe1fb0, (33, 3884, 3258, 0)),
             MapCommand(0xe1fa0, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_npc_18709fa8',
     SpriteIdentity(0x91a30, 0x18709fa8, 1170, (4927.0, 3362.0, 0.0)), (
         (
             MapCommand(0xe2d15, (88, 0, 150, 0)),
             MapCommand(0xe2d05, (77, 1, 20, 0)),
             MapCommand(0xe2cf5, (63, 4660, 3953, 0)),
             MapCommand(0xe2ce5, (41, 96, 0, 0)),
             MapCommand(0xe2cd5, (33, 4660, 3953, 0)),
             MapCommand(0xe2cc5, (46, 4660, 3953, 0)),
             MapCommand(0xe2cb5, (77, 1, 22, 0)),
             MapCommand(0xe2ca5, (43, 4383, 3822, 550)),
             MapCommand(0xe2c95, (40, 800, 0, 0)),
             MapCommand(0xe2c85, (33, 4284, 3575, 0)),
             MapCommand(0xe2c75, (115, 243, 0, 0)),
             MapCommand(0xe2c65, (41, 224, 0, 0)),
             MapCommand(0xe2c55, (44, 4147, 3438, 0)),
             MapCommand(0xe2c45, (46, 4147, 3438, 0)),
             MapCommand(0xe2c35, (10, 0, 0, 0)),
             MapCommand(0xe2c25, (40, 14200, 0, 0)),
             MapCommand(0xe2c15, (43, 3852, 3356, 550)),
             MapCommand(0xe2c05, (131, 11, 1, 0)),
             MapCommand(0xe2bf5, (40, 2500, 0, 0)),
             MapCommand(0xe2be5, (33, 3818, 3391, 0)),
             MapCommand(0xe2bd5, (40, 2000, 1000, 0)),
             MapCommand(0xe2bc5, (33, 3576, 3464, 0)),
             MapCommand(0xe2bb5, (46, 3576, 3464, 0)),
             MapCommand(0xe2ba5, (77, 1, 23, 0)),
             MapCommand(0xe2b95, (43, 3533, 3859, 480)),
             MapCommand(0xe2b85, (40, 900, 800, 0)),
             MapCommand(0xe2b75, (33, 3455, 3635, 0)),
             MapCommand(0xe2b65, (33, 3590, 3954, 0)),
             MapCommand(0xe2b55, (33, 3910, 4219, 0)),
             MapCommand(0xe2b45, (33, 3855, 4465, 0)),
             MapCommand(0xe2b35, (33, 3267, 4902, 2)),
             MapCommand(0xe2b25, (41, 160, 2, 0)),
             MapCommand(0xe2b15, (46, 3267, 4902, 2)),
             MapCommand(0xe2b05, (131, 11, 2, 0)),
             MapCommand(0xe2af5, (79, 10, 4, 0)),
             MapCommand(0xe2ae5, (41, 160, 2, 0)),
             MapCommand(0xe2ad5, (79, 14, 1, 0)),
             MapCommand(0xe2ac5, (115, 244, 0, 0)),
             MapCommand(0xe2ab5, (40, 300, 0, 0)),
             MapCommand(0xe2aa5, (33, 3091, 4949, 1)),
             MapCommand(0xe2a95, (33, 2734, 5274, 0)),
             MapCommand(0xe2a85, (33, 2527, 5405, 90)),
             MapCommand(0xe2a75, (44, 2198, 5502, 90)),
             MapCommand(0xe2a65, (41, 224, 0, 0)),
             MapCommand(0xe2a55, (46, 2198, 5502, 90)),
             MapCommand(0xe2a45, (10, 0, 0, 0)),
             MapCommand(0xe2a35, (40, 1000, 0, 0)),
             MapCommand(0xe2a25, (115, 245, 0, 0)),
             MapCommand(0xe2a15, (10, 0, 0, 0)),
             MapCommand(0xe2a05, (78, 1, 24, 0)),
             MapCommand(0xe29f5, (40, 75000, 0, 0)),
             MapCommand(0xe29e5, (115, 246, 0, 0)),
             MapCommand(0xe29d5, (40, 15000, 0, 0)),
             MapCommand(0xe29c5, (78, 1, 25, 0)),
             MapCommand(0xe29b5, (40, 600, 0, 0)),
             MapCommand(0xe29a5, (115, 247, 0, 0)),
             MapCommand(0xe2995, (40, 600, 0, 0)),
             MapCommand(0xe2985, (33, 2565, 5606, 90)),
             MapCommand(0xe2975, (33, 2668, 5683, 90)),
             MapCommand(0xe2965, (33, 2711, 5877, 90)),
             MapCommand(0xe2955, (33, 2557, 6006, 90)),
             MapCommand(0xe2945, (33, 2275, 5859, 90)),
             MapCommand(0xe2935, (33, 1872, 5835, 90)),
             MapCommand(0xe2925, (63, 94, 6957, 0)),
         ),
         (
             MapCommand(0xe2d69, (77, 1, 19, 0)),
             MapCommand(0xe2d59, (115, 37, 0, 0)),
             MapCommand(0xe2d49, (40, 15000, 0, 0)),
             MapCommand(0xe2d39, (43, 4980, 3440, 100)),
             MapCommand(0xe2d29, (71, 4, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870ba80',
     SpriteIdentity(0x91f70, 0x1870ba80, 1025, (3929.0, 3329.0, 0.0)), (
         (
             MapCommand(0xe3af3, (43, 2023, 4616, 250)),
             MapCommand(0xe3ae3, (32, 410012168, 0, 0)),
             MapCommand(0xe3ad3, (32, 410010904, 0, 0)),
             MapCommand(0xe3ac3, (33, 3884, 3258, 0)),
             MapCommand(0xe3ab3, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870bb58',
     SpriteIdentity(0x91fa0, 0x1870bb58, 1025, (3850.0, 3349.0, 0.0)), (
         (
             MapCommand(0xe3b68, (43, 2023, 4616, 250)),
             MapCommand(0xe3b58, (32, 410012168, 0, 0)),
             MapCommand(0xe3b48, (32, 410010904, 0, 0)),
             MapCommand(0xe3b38, (33, 3884, 3258, 0)),
             MapCommand(0xe3b28, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870bc98',
     SpriteIdentity(0x91fd0, 0x1870bc98, 1025, (3614.0, 3494.0, 0.0)), (
         (
             MapCommand(0xe3bdd, (43, 2023, 4616, 250)),
             MapCommand(0xe3bcd, (32, 410012168, 0, 0)),
             MapCommand(0xe3bbd, (32, 410010904, 0, 0)),
             MapCommand(0xe3bad, (33, 3884, 3258, 0)),
             MapCommand(0xe3b9d, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870be00',
     SpriteIdentity(0x92000, 0x1870be00, 1025, (3684.0, 3542.0, 0.0)), (
         (
             MapCommand(0xe3c52, (43, 2023, 4616, 250)),
             MapCommand(0xe3c42, (32, 410012168, 0, 0)),
             MapCommand(0xe3c32, (32, 410010904, 0, 0)),
             MapCommand(0xe3c22, (33, 3884, 3258, 0)),
             MapCommand(0xe3c12, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870bf40',
     SpriteIdentity(0x92030, 0x1870bf40, 1025, (3614.0, 3454.0, 0.0)), (
         (
             MapCommand(0xe3cc7, (43, 2023, 4616, 250)),
             MapCommand(0xe3cb7, (32, 410012168, 0, 0)),
             MapCommand(0xe3ca7, (32, 410010904, 0, 0)),
             MapCommand(0xe3c97, (33, 3884, 3258, 0)),
             MapCommand(0xe3c87, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870c018',
     SpriteIdentity(0x92060, 0x1870c018, 1025, (3773.0, 3383.0, 0.0)), (
         (
             MapCommand(0xe3d3c, (43, 2023, 4616, 250)),
             MapCommand(0xe3d2c, (32, 410012168, 0, 0)),
             MapCommand(0xe3d1c, (32, 410010904, 0, 0)),
             MapCommand(0xe3d0c, (33, 3884, 3258, 0)),
             MapCommand(0xe3cfc, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870c0f0',
     SpriteIdentity(0x92090, 0x1870c0f0, 1025, (3694.0, 3454.0, 0.0)), (
         (
             MapCommand(0xe3db1, (43, 2023, 4616, 250)),
             MapCommand(0xe3da1, (32, 410012168, 0, 0)),
             MapCommand(0xe3d91, (32, 410010904, 0, 0)),
             MapCommand(0xe3d81, (33, 3884, 3258, 0)),
             MapCommand(0xe3d71, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870c300',
     SpriteIdentity(0x920c0, 0x1870c300, 1025, (3614.0, 3414.0, 0.0)), (
         (
             MapCommand(0xe3e26, (43, 2023, 4616, 250)),
             MapCommand(0xe3e16, (32, 410012168, 0, 0)),
             MapCommand(0xe3e06, (32, 410010904, 0, 0)),
             MapCommand(0xe3df6, (33, 3884, 3258, 0)),
             MapCommand(0xe3de6, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870c3d8',
     SpriteIdentity(0x920f0, 0x1870c3d8, 1025, (3614.0, 3374.0, 0.0)), (
         (
             MapCommand(0xe3e9b, (43, 2023, 4616, 250)),
             MapCommand(0xe3e8b, (32, 410012168, 0, 0)),
             MapCommand(0xe3e7b, (32, 410010904, 0, 0)),
             MapCommand(0xe3e6b, (33, 3884, 3258, 0)),
             MapCommand(0xe3e5b, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870c4b0',
     SpriteIdentity(0x92120, 0x1870c4b0, 1025, (3694.0, 3414.0, 0.0)), (
         (
             MapCommand(0xe3f10, (43, 2023, 4616, 250)),
             MapCommand(0xe3f00, (32, 410012168, 0, 0)),
             MapCommand(0xe3ef0, (32, 410010904, 0, 0)),
             MapCommand(0xe3ee0, (33, 3884, 3258, 0)),
             MapCommand(0xe3ed0, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_1870c588',
     SpriteIdentity(0x92150, 0x1870c588, 922, (3591.0, 3500.0, 1.0)), (
         (
             MapCommand(0xe3f75, (77, 1, 22, 0)),
             MapCommand(0xe3f65, (43, 3231, 3422, 620)),
             MapCommand(0xe3f55, (40, 5000, 2000, 0)),
             MapCommand(0xe3f45, (131, 10, 3, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870c620',
     SpriteIdentity(0x92180, 0x1870c620, 1025, (3654.0, 3454.0, 0.0)), (
         (
             MapCommand(0xe3ff1, (43, 2023, 4616, 250)),
             MapCommand(0xe3fe1, (32, 410012168, 0, 0)),
             MapCommand(0xe3fd1, (32, 410010904, 0, 0)),
             MapCommand(0xe3fc1, (33, 3884, 3258, 0)),
             MapCommand(0xe3fb1, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870c6f8',
     SpriteIdentity(0x921b0, 0x1870c6f8, 1025, (3654.0, 3374.0, 0.0)), (
         (
             MapCommand(0xe4066, (43, 2023, 4616, 250)),
             MapCommand(0xe4056, (32, 410012168, 0, 0)),
             MapCommand(0xe4046, (32, 410010904, 0, 0)),
             MapCommand(0xe4036, (33, 3884, 3258, 0)),
             MapCommand(0xe4026, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870c878',
     SpriteIdentity(0x921e0, 0x1870c878, 1025, (3654.0, 3494.0, 0.0)), (
         (
             MapCommand(0xe40db, (43, 2023, 4616, 250)),
             MapCommand(0xe40cb, (32, 410012168, 0, 0)),
             MapCommand(0xe40bb, (32, 410010904, 0, 0)),
             MapCommand(0xe40ab, (33, 3884, 3258, 0)),
             MapCommand(0xe409b, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870c950',
     SpriteIdentity(0x92210, 0x1870c950, 1025, (3781.0, 3427.0, 0.0)), (
         (
             MapCommand(0xe4150, (43, 2023, 4616, 250)),
             MapCommand(0xe4140, (32, 410012168, 0, 0)),
             MapCommand(0xe4130, (32, 410010904, 0, 0)),
             MapCommand(0xe4120, (33, 3884, 3258, 0)),
             MapCommand(0xe4110, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870cad0',
     SpriteIdentity(0x92240, 0x1870cad0, 1025, (3501.0, 3479.0, 0.0)), (
         (
             MapCommand(0xe41c5, (43, 2023, 4616, 250)),
             MapCommand(0xe41b5, (32, 410012168, 0, 0)),
             MapCommand(0xe41a5, (32, 410010904, 0, 0)),
             MapCommand(0xe4195, (33, 3884, 3258, 0)),
             MapCommand(0xe4185, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870cba8',
     SpriteIdentity(0x92270, 0x1870cba8, 1025, (3541.0, 3479.0, 0.0)), (
         (
             MapCommand(0xe423a, (43, 2023, 4616, 250)),
             MapCommand(0xe422a, (32, 410012168, 0, 0)),
             MapCommand(0xe421a, (32, 410010904, 0, 0)),
             MapCommand(0xe420a, (33, 3884, 3258, 0)),
             MapCommand(0xe41fa, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870cc80',
     SpriteIdentity(0x922a0, 0x1870cc80, 1025, (3520.0, 3579.0, 0.0)), (
         (
             MapCommand(0xe42af, (43, 2023, 4616, 250)),
             MapCommand(0xe429f, (32, 410012168, 0, 0)),
             MapCommand(0xe428f, (32, 410010904, 0, 0)),
             MapCommand(0xe427f, (33, 3884, 3258, 0)),
             MapCommand(0xe426f, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870cd58',
     SpriteIdentity(0x922d0, 0x1870cd58, 1025, (3541.0, 3519.0, 0.0)), (
         (
             MapCommand(0xe4324, (43, 2023, 4616, 250)),
             MapCommand(0xe4314, (32, 410012168, 0, 0)),
             MapCommand(0xe4304, (32, 410010904, 0, 0)),
             MapCommand(0xe42f4, (33, 3884, 3258, 0)),
             MapCommand(0xe42e4, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870ce30',
     SpriteIdentity(0x92300, 0x1870ce30, 1025, (3501.0, 3519.0, 0.0)), (
         (
             MapCommand(0xe4399, (43, 2023, 4616, 250)),
             MapCommand(0xe4389, (32, 410012168, 0, 0)),
             MapCommand(0xe4379, (32, 410010904, 0, 0)),
             MapCommand(0xe4369, (33, 3884, 3258, 0)),
             MapCommand(0xe4359, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870cf08',
     SpriteIdentity(0x92330, 0x1870cf08, 1025, (3349.0, 3554.0, 0.0)), (
         (
             MapCommand(0xe440e, (43, 2023, 4616, 250)),
             MapCommand(0xe43fe, (32, 410012168, 0, 0)),
             MapCommand(0xe43ee, (32, 410010904, 0, 0)),
             MapCommand(0xe43de, (33, 3884, 3258, 0)),
             MapCommand(0xe43ce, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_door_1870d120',
     SpriteIdentity(0x92390, 0x1870d120, 1777, (3261.0, 3501.0, 0.0)), (
         (
             MapCommand(0xe44b8, (77, 4, 3, 0)),
             MapCommand(0xe44a8, (43, 3230, 3462, 120)),
             MapCommand(0xe4498, (78, 4, 4, 0)),
             MapCommand(0xe4488, (135, 75, 0, 0)),
             MapCommand(0xe4478, (40, 800, 0, 0)),
             MapCommand(0xe4468, (131, 5, 13, 0)),
             MapCommand(0xe4458, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_1870d3c0',
     SpriteIdentity(0x923f0, 0x1870d3c0, 922, (3299.0, 3534.0, 0.0)), (
         (
             MapCommand(0xe4532, (43, 3244, 3463, 80)),
             MapCommand(0xe4522, (116, 128, 0, 0)),
             MapCommand(0xe4512, (40, 3500, 0, 0)),
             MapCommand(0xe4502, (71, 3, 0, 0)),
         ),
         (
             MapCommand(0xe4556, (77, 4, 3, 0)),
             MapCommand(0xe4546, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_door_1870de40',
     SpriteIdentity(0x92690, 0x1870de40, 1777, (5963.0, 3183.0, 0.0)), (
         (
             MapCommand(0xe46e8, (77, 1, 20, 0)),
             MapCommand(0xe46d8, (43, 5965, 3166, 110)),
             MapCommand(0xe46c8, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_npc_1870e9e0',
     SpriteIdentity(0x928a0, 0x1870e9e0, 1154, (5082.0, 3100.0, 0.0)), (
         (
             MapCommand(0xe4c6f, (77, 1, 20, 0)),
             MapCommand(0xe4c5f, (40, 500, 0, 0)),
             MapCommand(0xe4c4f, (63, 4955, 3643, 0)),
             MapCommand(0xe4c3f, (62, 1155, 0, 0)),
             MapCommand(0xe4c2f, (33, 4756, 3890, 0)),
             MapCommand(0xe4c1f, (46, 4756, 3890, 0)),
             MapCommand(0xe4c0f, (41, 96, 0, 0)),
             MapCommand(0xe4bff, (43, 4930, 3706, 270)),
             MapCommand(0xe4bef, (40, 4000, 0, 0)),
             MapCommand(0xe4bdf, (33, 4899, 4038, 0)),
             MapCommand(0xe4bcf, (33, 5027, 4118, 0)),
             MapCommand(0xe4bbf, (95, 0, 0, 0)),
             MapCommand(0xe4baf, (78, 1, 21, 0)),
             MapCommand(0xe4b9f, (40, 600, 0, 0)),
             MapCommand(0xe4b8f, (33, 5148, 4188, 0)),
             MapCommand(0xe4b7f, (33, 4699, 3925, 0)),
             MapCommand(0xe4b6f, (46, 4699, 3925, 0)),
             MapCommand(0xe4b5f, (95, 1, 0, 0)),
             MapCommand(0xe4b4f, (77, 1, 22, 0)),
             MapCommand(0xe4b3f, (43, 4383, 3822, 550)),
             MapCommand(0xe4b2f, (40, 500, 1500, 0)),
             MapCommand(0xe4b1f, (33, 4090, 3560, 0)),
             MapCommand(0xe4b0f, (41, 224, 0, 0)),
             MapCommand(0xe4aff, (46, 4090, 3560, 0)),
             MapCommand(0xe4aef, (79, 11, 1, 0)),
             MapCommand(0xe4adf, (40, 900, 0, 0)),
             MapCommand(0xe4acf, (33, 3851, 3421, 0)),
             MapCommand(0xe4abf, (33, 3683, 3560, 0)),
             MapCommand(0xe4aaf, (46, 3683, 3560, 0)),
             MapCommand(0xe4a9f, (95, 1, 2, 0)),
             MapCommand(0xe4a8f, (77, 1, 23, 0)),
             MapCommand(0xe4a7f, (43, 3533, 3859, 480)),
             MapCommand(0xe4a6f, (40, 800, 800, 0)),
             MapCommand(0xe4a5f, (33, 3567, 3551, 0)),
             MapCommand(0xe4a4f, (33, 3480, 3681, 0)),
             MapCommand(0xe4a3f, (33, 3648, 3989, 1)),
             MapCommand(0xe4a2f, (33, 3940, 4240, 0)),
             MapCommand(0xe4a1f, (33, 3732, 4580, 3)),
             MapCommand(0xe4a0f, (33, 3063, 5002, 1)),
             MapCommand(0xe49ff, (33, 2949, 4988, 2)),
             MapCommand(0xe49ef, (41, 235, 0, 0)),
             MapCommand(0xe49df, (46, 2949, 4988, 2)),
             MapCommand(0xe49cf, (79, 16, 1, 0)),
             MapCommand(0xe49bf, (33, 2860, 5178, 2)),
             MapCommand(0xe49af, (33, 2566, 5378, 80)),
             MapCommand(0xe499f, (33, 2565, 5488, 90)),
             MapCommand(0xe498f, (46, 2565, 5488, 90)),
             MapCommand(0xe497f, (77, 1, 25, 0)),
             MapCommand(0xe496f, (40, 4000, 1500, 0)),
             MapCommand(0xe495f, (33, 2593, 5619, 90)),
             MapCommand(0xe494f, (95, 0, 500, 0)),
             MapCommand(0xe493f, (33, 2708, 5746, 90)),
             MapCommand(0xe492f, (33, 2667, 5924, 90)),
             MapCommand(0xe491f, (33, 2520, 5980, 90)),
             MapCommand(0xe490f, (33, 2236, 5835, 90)),
             MapCommand(0xe48ff, (33, 2028, 5787, 90)),
             MapCommand(0xe48ef, (33, 1853, 5875, 90)),
             MapCommand(0xe48df, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), 1155),
    ('supplemental_npc_1870eb48',
     SpriteIdentity(0x928d0, 0x1870eb48, 1154, (5031.0, 3092.0, 0.0)), (
         (
             MapCommand(0xe4fa4, (77, 1, 20, 0)),
             MapCommand(0xe4f94, (40, 500, 0, 0)),
             MapCommand(0xe4f84, (63, 5026, 3626, 0)),
             MapCommand(0xe4f74, (62, 1155, 0, 0)),
             MapCommand(0xe4f64, (33, 4737, 3841, 0)),
             MapCommand(0xe4f54, (46, 4737, 3841, 0)),
             MapCommand(0xe4f44, (95, 1, 0, 0)),
             MapCommand(0xe4f34, (77, 1, 22, 0)),
             MapCommand(0xe4f24, (43, 4383, 3822, 550)),
             MapCommand(0xe4f14, (40, 500, 1500, 0)),
             MapCommand(0xe4f04, (33, 4535, 3798, 0)),
             MapCommand(0xe4ef4, (33, 4012, 3546, 0)),
             MapCommand(0xe4ee4, (41, 96, 0, 0)),
             MapCommand(0xe4ed4, (46, 4012, 3546, 0)),
             MapCommand(0xe4ec4, (79, 11, 1, 0)),
             MapCommand(0xe4eb4, (40, 900, 0, 0)),
             MapCommand(0xe4ea4, (33, 3926, 3456, 0)),
             MapCommand(0xe4e94, (33, 3637, 3513, 0)),
             MapCommand(0xe4e84, (46, 3637, 3513, 0)),
             MapCommand(0xe4e74, (95, 1, 2, 0)),
             MapCommand(0xe4e64, (77, 1, 23, 0)),
             MapCommand(0xe4e54, (43, 3533, 3859, 480)),
             MapCommand(0xe4e44, (40, 500, 800, 0)),
             MapCommand(0xe4e34, (33, 3490, 3678, 0)),
             MapCommand(0xe4e24, (33, 3500, 3821, 0)),
             MapCommand(0xe4e14, (33, 3661, 4000, 2)),
             MapCommand(0xe4e04, (33, 3921, 4222, 0)),
             MapCommand(0xe4df4, (33, 3755, 4580, 3)),
             MapCommand(0xe4de4, (33, 3286, 4903, 2)),
             MapCommand(0xe4dd4, (33, 3181, 5112, 1)),
             MapCommand(0xe4dc4, (46, 3181, 5112, 1)),
             MapCommand(0xe4db4, (41, 96, 0, 0)),
             MapCommand(0xe4da4, (79, 16, 1, 0)),
             MapCommand(0xe4d94, (40, 500, 0, 0)),
             MapCommand(0xe4d84, (33, 2860, 5178, 2)),
             MapCommand(0xe4d74, (33, 2607, 5349, 57)),
             MapCommand(0xe4d64, (33, 2511, 5490, 90)),
             MapCommand(0xe4d54, (46, 2511, 5490, 90)),
             MapCommand(0xe4d44, (77, 1, 25, 0)),
             MapCommand(0xe4d34, (40, 4000, 1500, 0)),
             MapCommand(0xe4d24, (33, 2593, 5619, 90)),
             MapCommand(0xe4d14, (95, 0, 500, 0)),
             MapCommand(0xe4d04, (33, 2708, 5746, 90)),
             MapCommand(0xe4cf4, (33, 2667, 5924, 90)),
             MapCommand(0xe4ce4, (33, 2520, 5980, 90)),
             MapCommand(0xe4cd4, (33, 2236, 5835, 90)),
             MapCommand(0xe4cc4, (33, 2028, 5787, 90)),
             MapCommand(0xe4cb4, (33, 1853, 5875, 90)),
             MapCommand(0xe4ca4, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), 1155),
    ('supplemental_monster_1870f570',
     SpriteIdentity(0x92ae0, 0x1870f570, 1092, (4023.0, 3296.0, 0.0)), (
         (
             MapCommand(0xe5171, (88, 300, 0, 0)),
             MapCommand(0xe5161, (43, 2023, 4616, 250)),
             MapCommand(0xe5151, (40, 3500, 0, 0)),
             MapCommand(0xe5141, (33, 2796, 4170, 0)),
             MapCommand(0xe5131, (32, 410010904, 0, 0)),
             MapCommand(0xe5121, (32, 410012168, 0, 0)),
             MapCommand(0xe5111, (33, 3830, 3216, 0)),
             MapCommand(0xe5101, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870f7b0',
     SpriteIdentity(0x92b10, 0x1870f7b0, 1025, (3921.0, 3280.0, 0.0)), (
         (
             MapCommand(0xe51e6, (43, 2023, 4616, 250)),
             MapCommand(0xe51d6, (32, 410012168, 0, 0)),
             MapCommand(0xe51c6, (32, 410010904, 0, 0)),
             MapCommand(0xe51b6, (33, 3884, 3258, 0)),
             MapCommand(0xe51a6, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870f888',
     SpriteIdentity(0x92b40, 0x1870f888, 1025, (3957.0, 3224.0, 0.0)), (
         (
             MapCommand(0xe525b, (43, 2023, 4616, 250)),
             MapCommand(0xe524b, (32, 410012168, 0, 0)),
             MapCommand(0xe523b, (32, 410010904, 0, 0)),
             MapCommand(0xe522b, (33, 3884, 3258, 0)),
             MapCommand(0xe521b, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870fa38',
     SpriteIdentity(0x92b70, 0x1870fa38, 1025, (3862.0, 3258.0, 0.0)), (
         (
             MapCommand(0xe52d0, (43, 2023, 4616, 250)),
             MapCommand(0xe52c0, (32, 410012168, 0, 0)),
             MapCommand(0xe52b0, (32, 410010904, 0, 0)),
             MapCommand(0xe52a0, (33, 3884, 3258, 0)),
             MapCommand(0xe5290, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_1870fb78',
     SpriteIdentity(0x92ba0, 0x1870fb78, 922, (3984.0, 3186.0, 0.0)), (
         (
             MapCommand(0xe5325, (79, 10, 3, 0)),
             MapCommand(0xe5315, (43, 4095, 3107, 190)),
             MapCommand(0xe5305, (131, 5, 5, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_1870fd08',
     SpriteIdentity(0x92c00, 0x1870fd08, 1092, (3838.0, 3166.0, 0.0)), (
         (
             MapCommand(0xe5681, (88, 300, 0, 0)),
             MapCommand(0xe5671, (43, 2023, 4616, 250)),
             MapCommand(0xe5661, (40, 4000, 0, 0)),
             MapCommand(0xe5651, (32, 410012168, 0, 0)),
             MapCommand(0xe5641, (32, 410010904, 0, 0)),
             MapCommand(0xe5631, (33, 3830, 3216, 0)),
             MapCommand(0xe5621, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_door_1870ff48',
     SpriteIdentity(0x92c30, 0x1870ff48, 1777, (3711.0, 3182.0, 0.0)), (
         (
             MapCommand(0xe5716, (77, 3, 5, 0)),
             MapCommand(0xe5706, (43, 3690, 3154, 120)),
             MapCommand(0xe56f6, (78, 3, 6, 0)),
             MapCommand(0xe56e6, (135, 75, 0, 0)),
             MapCommand(0xe56d6, (40, 800, 0, 0)),
             MapCommand(0xe56c6, (131, 5, 12, 0)),
             MapCommand(0xe56b6, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_18710150',
     SpriteIdentity(0x92c60, 0x18710150, 1025, (3822.0, 3258.0, 0.0)), (
         (
             MapCommand(0xe578b, (43, 2023, 4616, 250)),
             MapCommand(0xe577b, (32, 410012168, 0, 0)),
             MapCommand(0xe576b, (32, 410010904, 0, 0)),
             MapCommand(0xe575b, (33, 3884, 3258, 0)),
             MapCommand(0xe574b, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_18710290',
     SpriteIdentity(0x92c90, 0x18710290, 1025, (3822.0, 3298.0, 0.0)), (
         (
             MapCommand(0xe5800, (43, 2023, 4616, 250)),
             MapCommand(0xe57f0, (32, 410012168, 0, 0)),
             MapCommand(0xe57e0, (32, 410010904, 0, 0)),
             MapCommand(0xe57d0, (33, 3884, 3258, 0)),
             MapCommand(0xe57c0, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_18710368',
     SpriteIdentity(0x92cc0, 0x18710368, 1025, (3728.0, 3262.0, 0.0)), (
         (
             MapCommand(0xe5875, (43, 2023, 4616, 250)),
             MapCommand(0xe5865, (32, 410012168, 0, 0)),
             MapCommand(0xe5855, (32, 410010904, 0, 0)),
             MapCommand(0xe5845, (33, 3884, 3258, 0)),
             MapCommand(0xe5835, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_monster_18710568',
     SpriteIdentity(0x92cf0, 0x18710568, 1025, (3722.0, 3324.0, 0.0)), (
         (
             MapCommand(0xe58ea, (43, 2023, 4616, 250)),
             MapCommand(0xe58da, (32, 410012168, 0, 0)),
             MapCommand(0xe58ca, (32, 410010904, 0, 0)),
             MapCommand(0xe58ba, (33, 3884, 3258, 0)),
             MapCommand(0xe58aa, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_187106a8',
     SpriteIdentity(0x92d20, 0x187106a8, 922, (3740.0, 3207.0, 0.0)), (
         (
             MapCommand(0xe594f, (43, 3690, 3154, 80)),
             MapCommand(0xe593f, (116, 127, 0, 0)),
             MapCommand(0xe592f, (40, 3500, 0, 0)),
             MapCommand(0xe591f, (71, 3, 0, 0)),
         ),
         (
             MapCommand(0xe5973, (77, 3, 5, 0)),
             MapCommand(0xe5963, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_generator_187112c8',
     SpriteIdentity(0x92fc0, 0x187112c8, 908, (6987.0, 2996.0, 0.0)), (
         (
             MapCommand(0xe5e90, (77, 1, 20, 0)),
             MapCommand(0xe5e80, (43, 5947, 3189, 350)),
             MapCommand(0xe5e70, (35, 1025, -30, -30)),
             MapCommand(0xe5e60, (35, 1025, -30, -30)),
             MapCommand(0xe5e50, (35, 1025, -30, -30)),
             MapCommand(0xe5e40, (35, 1037, -30, -30)),
             MapCommand(0xe5e30, (35, 1025, -30, -30)),
             MapCommand(0xe5e20, (35, 1025, -30, -30)),
             MapCommand(0xe5e10, (35, 1025, -30, -30)),
             MapCommand(0xe5e00, (35, 1025, -30, -30)),
             MapCommand(0xe5df0, (35, 1037, -30, -30)),
             MapCommand(0xe5de0, (35, 1025, -30, -30)),
             MapCommand(0xe5dd0, (73, 1037, -30, -30)),
             MapCommand(0xe5dc0, (33, 6867, 3073, 0)),
             MapCommand(0xe5db0, (33, 6714, 3014, 0)),
             MapCommand(0xe5da0, (33, 6594, 2908, 0)),
             MapCommand(0xe5d90, (33, 6469, 2851, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_npc_18712778',
     SpriteIdentity(0x933b0, 0x18712778, 1154, (4971.0, 3050.0, 0.0)), (
         (
             MapCommand(0xe6469, (77, 1, 20, 0)),
             MapCommand(0xe6459, (40, 500, 0, 0)),
             MapCommand(0xe6449, (63, 4996, 3574, 0)),
             MapCommand(0xe6439, (62, 1155, 0, 0)),
             MapCommand(0xe6429, (33, 4851, 3731, 0)),
             MapCommand(0xe6419, (33, 4565, 3846, 0)),
             MapCommand(0xe6409, (33, 4614, 3928, 0)),
             MapCommand(0xe63f9, (46, 4614, 3928, 0)),
             MapCommand(0xe63e9, (95, 1, 0, 0)),
             MapCommand(0xe63d9, (77, 1, 22, 0)),
             MapCommand(0xe63c9, (43, 4383, 3822, 550)),
             MapCommand(0xe63b9, (40, 500, 1500, 0)),
             MapCommand(0xe63a9, (33, 4246, 3495, 0)),
             MapCommand(0xe6399, (41, 96, 0, 0)),
             MapCommand(0xe6389, (46, 4246, 3495, 0)),
             MapCommand(0xe6379, (79, 11, 1, 0)),
             MapCommand(0xe6369, (40, 900, 0, 0)),
             MapCommand(0xe6359, (33, 3830, 3349, 0)),
             MapCommand(0xe6349, (33, 3459, 3421, 0)),
             MapCommand(0xe6339, (46, 3459, 3421, 0)),
             MapCommand(0xe6329, (41, 160, 0, 0)),
             MapCommand(0xe6319, (77, 1, 23, 0)),
             MapCommand(0xe6309, (40, 1800, 0, 0)),
             MapCommand(0xe62f9, (43, 3533, 3859, 480)),
             MapCommand(0xe62e9, (33, 3505, 3465, 0)),
             MapCommand(0xe62d9, (33, 3407, 3615, 0)),
             MapCommand(0xe62c9, (33, 3455, 3774, 0)),
             MapCommand(0xe62b9, (33, 3681, 4029, 0)),
             MapCommand(0xe62a9, (33, 3947, 4256, 0)),
             MapCommand(0xe6299, (33, 3683, 4657, 0)),
             MapCommand(0xe6289, (33, 3297, 4907, 0)),
             MapCommand(0xe6279, (33, 3305, 5008, 1)),
             MapCommand(0xe6269, (41, 96, 0, 0)),
             MapCommand(0xe6259, (46, 3305, 5008, 1)),
             MapCommand(0xe6249, (79, 16, 1, 0)),
             MapCommand(0xe6239, (40, 1200, 0, 0)),
             MapCommand(0xe6229, (33, 2860, 5178, 2)),
             MapCommand(0xe6219, (33, 2445, 5424, 90)),
             MapCommand(0xe6209, (46, 2445, 5424, 90)),
             MapCommand(0xe61f9, (77, 1, 25, 0)),
             MapCommand(0xe61e9, (40, 4000, 1500, 0)),
             MapCommand(0xe61d9, (33, 2593, 5619, 90)),
             MapCommand(0xe61c9, (95, 0, 500, 0)),
             MapCommand(0xe61b9, (33, 2708, 5746, 90)),
             MapCommand(0xe61a9, (33, 2667, 5924, 90)),
             MapCommand(0xe6199, (33, 2520, 5980, 90)),
             MapCommand(0xe6189, (33, 2236, 5835, 90)),
             MapCommand(0xe6179, (33, 2028, 5787, 90)),
             MapCommand(0xe6169, (33, 1853, 5875, 90)),
             MapCommand(0xe6159, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), 1155),
    ('supplemental_npc_18712a48',
     SpriteIdentity(0x93410, 0x18712a48, 1154, (4933.0, 3019.0, 13.0)), (
         (
             MapCommand(0xe68f3, (88, 0, 450, 0)),
             MapCommand(0xe68e3, (77, 1, 20, 0)),
             MapCommand(0xe68d3, (63, 4924, 3725, 0)),
             MapCommand(0xe68c3, (40, 2000, 0, 0)),
             MapCommand(0xe68b3, (115, 41, 0, 0)),
             MapCommand(0xe68a3, (41, 32, 0, 0)),
             MapCommand(0xe6893, (95, 1, 0, 0)),
             MapCommand(0xe6883, (62, 1155, 0, 0)),
             MapCommand(0xe6873, (43, 4930, 3706, 450)),
             MapCommand(0xe6863, (41, 32, 0, 0)),
             MapCommand(0xe6853, (43, 4930, 3706, 270)),
             MapCommand(0xe6843, (115, 38, 0, 0)),
             MapCommand(0xe6833, (40, 2500, 0, 0)),
             MapCommand(0xe6823, (95, 1, 2, 0)),
             MapCommand(0xe6813, (33, 4846, 3911, 0)),
             MapCommand(0xe6803, (33, 4843, 3973, 0)),
             MapCommand(0xe67f3, (33, 5093, 4258, 0)),
             MapCommand(0xe67e3, (78, 1, 21, 0)),
             MapCommand(0xe67d3, (115, 40, 0, 0)),
             MapCommand(0xe67c3, (33, 4752, 3967, 0)),
             MapCommand(0xe67b3, (46, 4752, 3967, 0)),
             MapCommand(0xe67a3, (95, 1, 2, 0)),
             MapCommand(0xe6793, (40, 18000, 0, 0)),
             MapCommand(0xe6783, (115, 38, 1, 0)),
             MapCommand(0xe6773, (77, 1, 22, 0)),
             MapCommand(0xe6763, (115, 39, 0, 0)),
             MapCommand(0xe6753, (43, 4383, 3822, 550)),
             MapCommand(0xe6743, (40, 800, 0, 0)),
             MapCommand(0xe6733, (33, 4166, 3532, 0)),
             MapCommand(0xe6723, (41, 224, 0, 0)),
             MapCommand(0xe6713, (46, 4166, 3532, 0)),
             MapCommand(0xe6703, (79, 11, 1, 0)),
             MapCommand(0xe66f3, (40, 900, 0, 0)),
             MapCommand(0xe66e3, (33, 4006, 3457, 0)),
             MapCommand(0xe66d3, (33, 3779, 3486, 0)),
             MapCommand(0xe66c3, (115, 43, 0, 0)),
             MapCommand(0xe66b3, (33, 3551, 3529, 0)),
             MapCommand(0xe66a3, (46, 3551, 3529, 0)),
             MapCommand(0xe6693, (95, 1, 2, 0)),
             MapCommand(0xe6683, (77, 1, 23, 0)),
             MapCommand(0xe6673, (40, 1000, 0, 0)),
             MapCommand(0xe6663, (43, 3533, 3859, 480)),
             MapCommand(0xe6653, (115, 42, 0, 0)),
             MapCommand(0xe6643, (33, 3462, 3647, 0)),
             MapCommand(0xe6633, (33, 3466, 3753, 0)),
             MapCommand(0xe6623, (33, 3639, 3969, 0)),
             MapCommand(0xe6613, (33, 3898, 4209, 0)),
             MapCommand(0xe6603, (33, 3953, 4342, 0)),
             MapCommand(0xe65f3, (33, 3904, 4403, 0)),
             MapCommand(0xe65e3, (33, 3146, 4915, 2)),
             MapCommand(0xe65d3, (33, 3100, 4869, 0)),
             MapCommand(0xe65c3, (41, 244, 0, 0)),
             MapCommand(0xe65b3, (46, 3100, 4869, 0)),
             MapCommand(0xe65a3, (79, 16, 1, 0)),
             MapCommand(0xe6593, (40, 1000, 0, 0)),
             MapCommand(0xe6583, (33, 2860, 5178, 2)),
             MapCommand(0xe6573, (33, 2425, 5403, 90)),
             MapCommand(0xe6563, (46, 2425, 5403, 90)),
             MapCommand(0xe6553, (77, 1, 25, 0)),
             MapCommand(0xe6543, (40, 4000, 1500, 0)),
             MapCommand(0xe6533, (33, 2593, 5619, 90)),
             MapCommand(0xe6523, (95, 0, 500, 0)),
             MapCommand(0xe6513, (33, 2708, 5746, 90)),
             MapCommand(0xe6503, (33, 2667, 5924, 90)),
             MapCommand(0xe64f3, (33, 2520, 5980, 90)),
             MapCommand(0xe64e3, (33, 2236, 5835, 90)),
             MapCommand(0xe64d3, (33, 2028, 5787, 90)),
             MapCommand(0xe64c3, (33, 1853, 5875, 90)),
             MapCommand(0xe64b3, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), 1155),
    ('supplemental_generator_18715048',
     SpriteIdentity(0x939e0, 0x18715048, 908, (6522.0, 2681.0, 0.0)), (
         (
             MapCommand(0xe6f15, (77, 1, 20, 0)),
             MapCommand(0xe6f05, (43, 5947, 3189, 350)),
             MapCommand(0xe6ef5, (35, 1025, -30, -30)),
             MapCommand(0xe6ee5, (35, 1025, -30, -30)),
             MapCommand(0xe6ed5, (35, 1025, -30, -30)),
             MapCommand(0xe6ec5, (35, 1037, -30, -30)),
             MapCommand(0xe6eb5, (35, 1025, -30, -30)),
             MapCommand(0xe6ea5, (35, 1025, -30, -30)),
             MapCommand(0xe6e95, (35, 1025, -30, -30)),
             MapCommand(0xe6e85, (35, 1025, -30, -30)),
             MapCommand(0xe6e75, (35, 1037, -30, -30)),
             MapCommand(0xe6e65, (35, 1025, -30, -30)),
             MapCommand(0xe6e55, (73, 1037, -30, -30)),
             MapCommand(0xe6e45, (33, 6324, 2657, 0)),
             MapCommand(0xe6e35, (33, 6473, 2794, 0)),
             MapCommand(0xe6e25, (33, 6642, 2922, 0)),
             MapCommand(0xe6e15, (33, 6800, 2879, 0)),
             MapCommand(0xe6e05, (33, 6647, 2703, 0)),
             MapCommand(0xe6df5, (33, 6522, 2681, 0)),
             MapCommand(0xe6de5, (71, 6, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_generator_187157d0',
     SpriteIdentity(0x93b00, 0x187157d0, 908, (6251.0, 2593.0, 0.0)), (
         (
             MapCommand(0xe710b, (77, 1, 20, 0)),
             MapCommand(0xe70fb, (43, 5947, 3189, 350)),
             MapCommand(0xe70eb, (35, 1025, -30, -30)),
             MapCommand(0xe70db, (35, 1025, -30, -30)),
             MapCommand(0xe70cb, (35, 1025, -30, -30)),
             MapCommand(0xe70bb, (35, 1037, -30, -30)),
             MapCommand(0xe70ab, (35, 1025, -30, -30)),
             MapCommand(0xe709b, (35, 1025, -30, -30)),
             MapCommand(0xe708b, (35, 1025, -30, -30)),
             MapCommand(0xe707b, (35, 1025, -30, -30)),
             MapCommand(0xe706b, (35, 1037, -30, -30)),
             MapCommand(0xe705b, (35, 1025, -30, -30)),
             MapCommand(0xe704b, (73, 1037, -30, -30)),
             MapCommand(0xe703b, (33, 6324, 2657, 0)),
             MapCommand(0xe702b, (33, 6473, 2794, 0)),
             MapCommand(0xe701b, (33, 6642, 2922, 0)),
             MapCommand(0xe700b, (33, 6800, 2879, 0)),
             MapCommand(0xe6ffb, (33, 6647, 2703, 0)),
             MapCommand(0xe6feb, (33, 6522, 2681, 0)),
             MapCommand(0xe6fdb, (71, 6, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_generator_18716168',
     SpriteIdentity(0x93ce0, 0x18716168, 908, (5469.0, 2697.0, 0.0)), (
         (
             MapCommand(0xe72ed, (43, 5252, 4605, 300)),
             MapCommand(0xe72dd, (35, 1037, -10, -10)),
             MapCommand(0xe72cd, (40, 500, 3000, 0)),
             MapCommand(0xe72bd, (35, 1025, -10, -10)),
             MapCommand(0xe72ad, (40, 500, 3000, 0)),
             MapCommand(0xe729d, (35, 1025, -10, -10)),
             MapCommand(0xe728d, (35, 1025, -10, -10)),
             MapCommand(0xe727d, (40, 500, 3000, 0)),
             MapCommand(0xe726d, (71, 9, 0, 0)),
             MapCommand(0xe725d, (73, 0, 0, 0)),
             MapCommand(0xe724d, (95, 0, 0, 0)),
             MapCommand(0xe723d, (33, 5297, 2810, 0)),
             MapCommand(0xe722d, (33, 5042, 2904, 0)),
         ),
         (
             MapCommand(0xe7311, (77, 1, 20, 0)),
             MapCommand(0xe7301, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_generator_18716260',
     SpriteIdentity(0x93d10, 0x18716260, 908, (5525.0, 2733.0, 0.0)), (
         (
             MapCommand(0xe73e2, (43, 5212, 4657, 300)),
             MapCommand(0xe73d2, (35, 1025, -10, -10)),
             MapCommand(0xe73c2, (40, 500, 3000, 0)),
             MapCommand(0xe73b2, (35, 1037, -10, -10)),
             MapCommand(0xe73a2, (40, 500, 3000, 0)),
             MapCommand(0xe7392, (35, 1025, -10, -10)),
             MapCommand(0xe7382, (71, 9, 0, 0)),
             MapCommand(0xe7372, (73, 0, 0, 0)),
             MapCommand(0xe7362, (95, 0, 0, 0)),
             MapCommand(0xe7352, (33, 5363, 2809, 0)),
             MapCommand(0xe7342, (33, 5087, 2930, 0)),
         ),
         (
             MapCommand(0xe7406, (77, 1, 20, 0)),
             MapCommand(0xe73f6, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_logic_1871e798',
     SpriteIdentity(0x950c0, 0x1871e798, 922, (204.0, 1084.0, 0.0)), (
         (
             MapCommand(0xe8e95, (43, 144, 1059, 75)),
             MapCommand(0xe8e85, (135, 103, 0, 0)),
             MapCommand(0xe8e75, (40, 200, 0, 0)),
             MapCommand(0xe8e65, (78, 1, 20, 1)),
             MapCommand(0xe8e55, (131, 1, 3, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('remote_room_exit',
     SpriteIdentity(0x95390, 0x1871f6d8, 922, (1567.0, 876.0, 0.0)), (
         (
             MapCommand(0xe93f0, (43, 1468, 786, 150)),
             MapCommand(0xe93e0, (91, 6166, 3580, 0)),
             MapCommand(0xe93d0, (136, 13, 0, 0)),
             MapCommand(0xe93c0, (71, 3, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_18724de8',
     SpriteIdentity(0x95e40, 0x18724de8, 1370, (2744.0, 9571.0, 180.0)), (
         (
             MapCommand(0xe9b65, (43, 3166, 9316, 470)),
             MapCommand(0xe9b55, (40, 2200, 0, 0)),
             MapCommand(0xe9b45, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_18725158',
     SpriteIdentity(0x95ea0, 0x18725158, 1370, (3092.545166015625, 9396.154296875, 220.03294372558594)), (
         (
             MapCommand(0xe9bcf, (43, 3166, 9316, 470)),
             MapCommand(0xe9bbf, (40, 3000, 0, 0)),
             MapCommand(0xe9baf, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_187296e0',
     SpriteIdentity(0x96680, 0x187296e0, 1258, (2882.545166015625, 9724.154296875, 64.0329360961914)), (
         (
             MapCommand(0xea631, (43, 3166, 9316, 470)),
             MapCommand(0xea621, (40, 800, 2500, 0)),
             MapCommand(0xea611, (62, 1227, 0, 0)),
             MapCommand(0xea601, (40, 50, 100, 0)),
             MapCommand(0xea5f1, (62, 1258, 0, 0)),
             MapCommand(0xea5e1, (40, 50, 100, 0)),
             MapCommand(0xea5d1, (62, 1227, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_18729af0',
     SpriteIdentity(0x966e0, 0x18729af0, 1258, (3276.545166015625, 9445.154296875, 64.0329360961914)), (
         (
             MapCommand(0xea6db, (43, 3166, 9316, 470)),
             MapCommand(0xea6cb, (40, 800, 2500, 0)),
             MapCommand(0xea6bb, (62, 1227, 0, 0)),
             MapCommand(0xea6ab, (40, 50, 100, 0)),
             MapCommand(0xea69b, (62, 1258, 0, 0)),
             MapCommand(0xea68b, (40, 50, 100, 0)),
             MapCommand(0xea67b, (62, 1227, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_18729c68',
     SpriteIdentity(0x96710, 0x18729c68, 1258, (2724.545166015625, 9373.154296875, 149.03294372558594)), (
         (
             MapCommand(0xea770, (43, 3166, 9316, 470)),
             MapCommand(0xea760, (40, 500, 2500, 0)),
             MapCommand(0xea750, (62, 1227, 0, 0)),
             MapCommand(0xea740, (40, 50, 100, 0)),
             MapCommand(0xea730, (62, 1258, 0, 0)),
             MapCommand(0xea720, (40, 50, 100, 0)),
             MapCommand(0xea710, (62, 1227, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1872a440',
     SpriteIdentity(0x967d0, 0x1872a440, 1361, (4503.0, 9034.0, 0.0)), (
         (
             MapCommand(0xea7f4, (43, 4504, 9035, 70)),
             MapCommand(0xea7e4, (134, -1, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1872a520',
     SpriteIdentity(0x96800, 0x1872a520, 1364, (4339.0, 9171.0, 2.0)), (
         (
             MapCommand(0xea839, (43, 4445, 9110, 250)),
             MapCommand(0xea829, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1872a808',
     SpriteIdentity(0x96860, 0x1872a808, 1364, (3736.0, 9121.0, 2.0)), (
         (
             MapCommand(0xea893, (43, 3902, 9254, 300)),
             MapCommand(0xea883, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1872aaf0',
     SpriteIdentity(0x968c0, 0x1872aaf0, 1258, (2903.545166015625, 9245.154296875, 149.03294372558594)), (
         (
             MapCommand(0xea98d, (43, 3166, 9316, 470)),
             MapCommand(0xea97d, (40, 800, 2500, 0)),
             MapCommand(0xea96d, (62, 1227, 0, 0)),
             MapCommand(0xea95d, (40, 1000, 500, 0)),
             MapCommand(0xea94d, (62, 1258, 0, 0)),
             MapCommand(0xea93d, (40, 50, 100, 0)),
             MapCommand(0xea92d, (62, 1227, 0, 0)),
             MapCommand(0xea91d, (40, 0, 50, 0)),
             MapCommand(0xea90d, (62, 1258, 0, 0)),
             MapCommand(0xea8fd, (40, 20, 100, 0)),
             MapCommand(0xea8ed, (40, 20, 100, 0)),
             MapCommand(0xea8dd, (71, 5, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1872b610',
     SpriteIdentity(0x96a40, 0x1872b610, 1364, (3704.0, 8930.0, 2.0)), (
         (
             MapCommand(0xeaaf5, (98, 1, 0, 0)),
             MapCommand(0xeaae5, (77, 1, 39, 0)),
             MapCommand(0xeaad5, (98, 0, 0, 0)),
             MapCommand(0xeaac5, (43, 3777, 8843, 170)),
             MapCommand(0xeaab5, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1872b6a8',
     SpriteIdentity(0x96a70, 0x1872b6a8, 1364, (3393.0, 8884.0, 11.0)), (
         (
             MapCommand(0xeab7a, (98, 1, 0, 0)),
             MapCommand(0xeab6a, (43, 3662, 8514, 30)),
             MapCommand(0xeab5a, (40, 1000, 0, 0)),
             MapCommand(0xeab4a, (98, 0, 0, 0)),
             MapCommand(0xeab3a, (43, 3247, 8785, 280)),
             MapCommand(0xeab2a, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1872c1f0',
     SpriteIdentity(0x96c80, 0x1872c1f0, 1364, (3819.0, 8675.0, 2.0)), (
         (
             MapCommand(0xeacf1, (98, 1, 0, 0)),
             MapCommand(0xeace1, (77, 1, 39, 0)),
             MapCommand(0xeacd1, (98, 0, 0, 0)),
             MapCommand(0xeacc1, (43, 3726, 8576, 150)),
             MapCommand(0xeacb1, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1872c2d0',
     SpriteIdentity(0x96cb0, 0x1872c2d0, 1364, (3379.0, 8501.0, 1.0)), (
         (
             MapCommand(0xead76, (98, 1, 0, 0)),
             MapCommand(0xead66, (43, 3662, 8514, 30)),
             MapCommand(0xead56, (40, 1000, 0, 0)),
             MapCommand(0xead46, (98, 0, 0, 0)),
             MapCommand(0xead36, (43, 3390, 8340, 190)),
             MapCommand(0xead26, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1872d9b8',
     SpriteIdentity(0x97010, 0x1872d9b8, 1364, (4063.0, 7924.0, 11.0)), (
         (
             MapCommand(0xeaf60, (98, 1, 0, 0)),
             MapCommand(0xeaf50, (43, 3662, 8514, 30)),
             MapCommand(0xeaf40, (40, 1000, 0, 0)),
             MapCommand(0xeaf30, (98, 0, 0, 0)),
             MapCommand(0xeaf20, (43, 4014, 7885, 180)),
             MapCommand(0xeaf10, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1872e028',
     SpriteIdentity(0x97100, 0x1872e028, 1359, (1828.0, 6668.0, 180.0)), (
         (
             MapCommand(0xeb149, (43, 1827, 6675, 350)),
             MapCommand(0xeb139, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('campaign_return_exit',
     SpriteIdentity(0x975e0, 0x18730508, 1712, (1852.0, 5888.0, 90.0)), (
         (
             MapCommand(0xebb67, (98, 1, 0, 0)),
             MapCommand(0xebb57, (77, 1, 25, 0)),
             MapCommand(0xebb47, (98, 0, 0, 0)),
             MapCommand(0xebb37, (43, 1852, 5948, 200)),
             MapCommand(0xebb27, (131, 9, 1, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_187314b0',
     SpriteIdentity(0x97910, 0x187314b0, 1364, (2501.0, 5555.0, 90.0)), (
         (
             MapCommand(0xebeeb, (98, 1, 0, 0)),
             MapCommand(0xebedb, (77, 1, 25, 0)),
             MapCommand(0xebecb, (98, 0, 0, 0)),
             MapCommand(0xebebb, (43, 2620, 5644, 90)),
             MapCommand(0xebeab, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_18732bb8',
     SpriteIdentity(0x97e50, 0x18732bb8, 1358, (1798.0, 5347.0, 90.0)), (
         (
             MapCommand(0xec479, (43, 1845, 5321, 45)),
             MapCommand(0xec469, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_18733248',
     SpriteIdentity(0x97f70, 0x18733248, 1358, (4616.0, 5102.0, 0.0)), (
         (
             MapCommand(0xec5d7, (43, 4624, 5111, 90)),
             MapCommand(0xec5c7, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_187338c0',
     SpriteIdentity(0x980c0, 0x187338c0, 1358, (3702.8994140625, 5067.134765625, 0.0)), (
         (
             MapCommand(0xec7a6, (77, 1, 42, 0)),
             MapCommand(0xec796, (43, 3621, 5084, 120)),
             MapCommand(0xec786, (40, 1500, 0, 0)),
             MapCommand(0xec776, (15, 0, 0, 0)),
         ),
         (
             MapCommand(0xec7ea, (77, 1, 42, 0)),
             MapCommand(0xec7da, (43, 3776, 4760, 90)),
             MapCommand(0xec7ca, (40, 1500, 0, 0)),
             MapCommand(0xec7ba, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_18733b20',
     SpriteIdentity(0x98150, 0x18733b20, 1359, (3163.0, 4954.0, 2.0)), (
         (
             MapCommand(0xec8d8, (43, 3596, 3927, 150)),
             MapCommand(0xec8c8, (43, 3161, 4961, 350)),
             MapCommand(0xec8b8, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_18735140',
     SpriteIdentity(0x98540, 0x18735140, 1359, (2839.0, 4754.0, 0.0)), (
         (
             MapCommand(0xece51, (43, 2836, 4763, 180)),
             MapCommand(0xece41, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_18736648',
     SpriteIdentity(0x988d0, 0x18736648, 1359, (4445.0, 4561.0, 0.0)), (
         (
             MapCommand(0xed3bc, (43, 4443, 4563, 250)),
             MapCommand(0xed3ac, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_18736ab0',
     SpriteIdentity(0x989c0, 0x18736ab0, 1364, (3948.0, 4398.0, 3.0)), (
         (
             MapCommand(0xed528, (98, 1, 0, 0)),
             MapCommand(0xed518, (77, 1, 23, 0)),
             MapCommand(0xed508, (98, 0, 0, 0)),
             MapCommand(0xed4f8, (43, 3808, 4503, 160)),
             MapCommand(0xed4e8, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_187374f8',
     SpriteIdentity(0x98c00, 0x187374f8, 1358, (3031.4892578125, 4587.61767578125, 0.0)), (
         (
             MapCommand(0xed7e9, (77, 1, 42, 0)),
             MapCommand(0xed7d9, (43, 2979, 4652, 110)),
             MapCommand(0xed7c9, (40, 1500, 0, 0)),
             MapCommand(0xed7b9, (15, 0, 0, 0)),
         ),
         (
             MapCommand(0xed82d, (77, 1, 42, 0)),
             MapCommand(0xed81d, (43, 3464, 4519, 110)),
             MapCommand(0xed80d, (40, 1500, 0, 0)),
             MapCommand(0xed7fd, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_187375f8',
     SpriteIdentity(0x98c30, 0x187375f8, 1356, (2687.0, 4570.0, 50.0)), (
         (
             MapCommand(0xed86e, (43, 4049, 3481, 200)),
             MapCommand(0xed85e, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_18737b38',
     SpriteIdentity(0x98cf0, 0x18737b38, 1358, (5899.0, 4171.0, 0.0)), (
         (
             MapCommand(0xed9e2, (77, 1, 23, 0)),
             MapCommand(0xed9d2, (43, 5693, 4309, 130)),
             MapCommand(0xed9c2, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1873ae60',
     SpriteIdentity(0x995c0, 0x1873ae60, 1358, (2050.27001953125, 4059.31689453125, 0.0)), (
         (
             MapCommand(0xee595, (43, 2057, 4057, 130)),
             MapCommand(0xee585, (15, 0, 0, 0)),
         ),
         (
             MapCommand(0xee5b9, (43, 2137, 3998, 130)),
             MapCommand(0xee5a9, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1873b8c0',
     SpriteIdentity(0x99770, 0x1873b8c0, 1359, (4869.0, 3757.0, 0.0)), (
         (
             MapCommand(0xee7f6, (77, 1, 20, 0)),
             MapCommand(0xee7e6, (43, 4855, 3778, 300)),
             MapCommand(0xee7d6, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1873bb18',
     SpriteIdentity(0x997d0, 0x1873bb18, 1359, (4837.0, 3802.0, 18.0)), (
         (
             MapCommand(0xee890, (43, 4855, 3778, 300)),
             MapCommand(0xee880, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1873c758',
     SpriteIdentity(0x99a40, 0x1873c758, 1359, (6154.0, 3556.0, 0.0)), (
         (
             MapCommand(0xeeb7d, (77, 1, 20, 0)),
             MapCommand(0xeeb6d, (43, 6307, 3674, 300)),
             MapCommand(0xeeb5d, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1873c7f0',
     SpriteIdentity(0x99a70, 0x1873c7f0, 1364, (6163.0, 3573.0, 5.0)), (
         (
             MapCommand(0xeebc2, (43, 6300, 3681, 150)),
             MapCommand(0xeebb2, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1873ca40',
     SpriteIdentity(0x99ad0, 0x1873ca40, 1361, (5037.0, 3466.0, 0.0)), (
         (
             MapCommand(0xeec5c, (43, 5037, 3469, 70)),
             MapCommand(0xeec4c, (78, 1, 19, 0)),
             MapCommand(0xeec3c, (15, 0, 0, 0)),
         ),
         (
             MapCommand(0xeec80, (77, 1, 20, 0)),
             MapCommand(0xeec70, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1873ceb0',
     SpriteIdentity(0x99bf0, 0x1873ceb0, 1358, (4455.0, 3475.0, 0.0)), (
         (
             MapCommand(0xeed4e, (43, 4465, 3470, 40)),
             MapCommand(0xeed3e, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1873d540',
     SpriteIdentity(0x99d70, 0x1873d540, 1359, (3648.0, 3439.0, 0.0)), (
         (
             MapCommand(0xeeebe, (77, 1, 22, 0)),
             MapCommand(0xeeeae, (43, 3731, 3335, 250)),
             MapCommand(0xeee9e, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1873d798',
     SpriteIdentity(0x99dd0, 0x1873d798, 1358, (3550.0, 3350.0, 0.0)), (
         (
             MapCommand(0xeef88, (43, 3507, 3274, 52)),
             MapCommand(0xeef78, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1873f230',
     SpriteIdentity(0x9a220, 0x1873f230, 1358, (6089.74462890625, 3006.796630859375, 0.0)), (
         (
             MapCommand(0xef631, (77, 1, 20, 0)),
             MapCommand(0xef621, (43, 6127, 3014, 220)),
             MapCommand(0xef611, (40, 300, 0, 0)),
             MapCommand(0xef601, (15, 0, 0, 0)),
         ),
         (
             MapCommand(0xef675, (77, 1, 20, 0)),
             MapCommand(0xef665, (43, 5946, 2892, 220)),
             MapCommand(0xef655, (40, 200, 0, 0)),
             MapCommand(0xef645, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1873f4c8',
     SpriteIdentity(0x9a280, 0x1873f4c8, 1358, (4583.0, 3035.0, 0.0)), (
         (
             MapCommand(0xef6cb, (43, 4584, 3025, 50)),
             MapCommand(0xef6bb, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_1873f7b0',
     SpriteIdentity(0x9a310, 0x1873f7b0, 1358, (4144.0, 2846.000244140625, 0.0)), (
         (
             MapCommand(0xef74c, (79, 10, 3, 0)),
             MapCommand(0xef73c, (43, 4095, 3107, 190)),
             MapCommand(0xef72c, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_187400c8',
     SpriteIdentity(0x9a4c0, 0x187400c8, 1358, (6678.0, 2679.0, 0.0)), (
         (
             MapCommand(0xef9c1, (43, 6715, 2620, 55)),
             MapCommand(0xef9b1, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_187406c0',
     SpriteIdentity(0x9a5e0, 0x187406c0, 1359, (263.0, 1068.0, 0.0)), (
         (
             MapCommand(0xefb4f, (43, 262, 1067, 200)),
             MapCommand(0xefb3f, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),
    ('supplemental_marker_18740880',
     SpriteIdentity(0x9a640, 0x18740880, 1359, (1628.0, 904.0, 0.0)), (
         (
             MapCommand(0xefbd9, (43, 1627, 910, 150)),
             MapCommand(0xefbc9, (15, 0, 0, 0)),
         ),
         (
         ),
         (
         ),
         (
         ),
     ), None),

)

LEVEL02_REMAINING_TRIGGERS = tuple(
    trigger
    for name, sprite, stacks, runtime_vid in _LEVEL02_REMAINING_SOURCES
    for trigger in _remaining_source_triggers(name, sprite, stacks, runtime_vid)
)

REMOTE_ROOM_ENTRY_TRIGGER = next(
    trigger for trigger in LEVEL02_REMAINING_TRIGGERS
    if trigger.name == 'remote_room_entry'
)
REMOTE_ROOM_EXIT_TRIGGER = next(
    trigger for trigger in LEVEL02_REMAINING_TRIGGERS
    if trigger.name == 'remote_room_exit'
)

# Original two-way ScriptEvent13 route. Each source keeps its original goal
# and ACT_LOOP(3,0,0); the shared controller provides a per-hero reusable pair,
# native collision checks and queued traversal. Starting inside the remote
# room from arbitrary saves has not been validated by this data-only change.
LEVEL02_EXTRA_PORTALS = (
    LogicalPortal(
        'remote_room_entry', 'level02', REMOTE_ROOM_ENTRY_TRIGGER.sprite,
        REMOTE_ROOM_ENTRY_TRIGGER.trigger, 0xE1712,
        (1650, 939, 0), 0xE1702, 0xE16F2,
        PortalPolicy('level02_remote_room', 'leader_pending', True, 40, True,
                     (-20, 20), (0, 0), True, consume_invalid_event=True),
    ),
    LogicalPortal(
        'remote_room_exit', 'level02', REMOTE_ROOM_EXIT_TRIGGER.sprite,
        REMOTE_ROOM_EXIT_TRIGGER.trigger, 0xE93F0,
        (6166, 3580, 0), 0xE93E0, 0xE93D0,
        PortalPolicy('level02_remote_room', 'leader_pending', True, 40, True,
                     (-20, 20), (0, 0), True, consume_invalid_event=True),
    ),
)
