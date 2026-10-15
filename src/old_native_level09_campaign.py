"""Reviewed original Level09 entry and exits for the common lifecycle adapter.

Both finish stacks wait for q1_87; the earlier start/music/quest commands on
the invisible exit source are retained as evidence, not replayed by the mod.
The common q56 robot allegiance change already allies army3 with both heroes.
"""
from old_native_interaction_schema import MapCommand, SpriteIdentity
from old_native_level02_finish_patch import FinishGate


SCRIPT_SHA256 = 'dbfc1d985f65154a8ab023a68fbc8358ae782261f82e3de7bd49498aee058030'
ENTRY = (SCRIPT_SHA256, SpriteIdentity(0x437F0, 0x08CDE350, 250, (1730, 2701, 0)))
FINISH_MONEY = 12000
SHOP = (2289, 2481)
PORTALS = ()

GATES = (
    FinishGate('original_exit', SpriteIdentity(0x43790, 0x08CDE190, 922, (1763, 2708, 0)),
        (1625, 2578, 200), (1, 87), (
            MapCommand(0x671E6, (131, 9, 1, 0)),
            MapCommand(0x671F6, (43, 1625, 2578, 200)),
            MapCommand(0x67206, (77, 1, 87, 0)),
            MapCommand(0x67216, (131, 1, 3, 0)),
            MapCommand(0x67226, (43, 2411, 3230, 400)),
            MapCommand(0x67236, (78, 1, 55, 0)),
            MapCommand(0x67246, (131, 1, 2, 0)),
        )),
    FinishGate('green_exit', SpriteIdentity(0x46DC0, 0x08CF96E0, 1712, (1717, 2690, 3)),
        (1721, 2658, 200), (1, 87), (
            MapCommand(0x6A072, (131, 9, 1, 0)),
            MapCommand(0x6A082, (43, 1721, 2658, 200)),
            MapCommand(0x6A092, (98, 0, 0, 0)),
            MapCommand(0x6A0A2, (77, 1, 87, 0)),
            MapCommand(0x6A0B2, (98, 1, 0, 0)),
        )),
)
