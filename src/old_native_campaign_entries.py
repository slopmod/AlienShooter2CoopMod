"""Reviewed physical-map entry/exit evidence, separate from shared machinery."""
from dataclasses import dataclass
from old_native_interaction_schema import MapCommand, SpriteIdentity
from old_native_level02_finish_patch import FinishGate, GATES as LEVEL02_GATES


@dataclass(frozen=True)
class Entry:
    script_sha256: str
    spawn: SpriteIdentity


ENTRIES = {
    3: Entry('ad0b9f7dce8e8b7634bb7e94e64de0eade8b849fea670bee4fb384690018471c',
             SpriteIdentity(0x7B290, 0x18676310, 250, (6858, 5114, 0))),
    4: Entry('1f1529e9be8c1c9674299f7a65ccdfe104564df5be13c0f4337b33a075a71e0a',
             SpriteIdentity(0x59B70, 0x185F2240, 250, (8000, 7623, 0))),
    5: Entry('6da189ac36537f97d28a115e47303081f683ca944c3287dbe4e47b8f895bc560',
             SpriteIdentity(0x618B0, 0x18586E58, 250, (12990.8837890625, 11630.43359375, 0))),
    6: Entry('4ff309287e78510d061fa5b320c2a312a92182cb1d39c24f9342a2e4185cf727',
             SpriteIdentity(0x9E660, 0x187B8C78, 250, (3445, 11060, 0))),
    7: Entry('c4844084b419a49def7e826ba4dbcab2916ead2ce1a4dda6389da6f55f62f635',
             SpriteIdentity(0xA0F70, 0x18487558, 250, (2197, 11743, 4))),
}

GATES = {
    2: LEVEL02_GATES,
    3: (FinishGate('exit', SpriteIdentity(0x7B8C0, 0x18678FA0, 922, (3977, 4099, 0)),
        (3966, 4132, 200), (1, 12), (
            MapCommand(0xBFB2F, (77, 1, 12, 1)), MapCommand(0xBFB1F, (43, 3966, 4132, 200)),
            MapCommand(0xBFB0F, (131, 9, 1, 0)))),),
    4: (FinishGate('exit', SpriteIdentity(0x6C920, 0x18676B08, 1712, (531, 565, 180)),
        (534, 560, 180), (1, 89), (
            MapCommand(0xA2B9C, (131, 9, 1, 0)), MapCommand(0xA2BAC, (43, 534, 560, 180)),
            MapCommand(0xA2BBC, (98, 0, 0, 0)), MapCommand(0xA2BCC, (77, 1, 89, 0)),
            MapCommand(0xA2BDC, (98, 1, 0, 0)))),),
    5: (FinishGate('exit', SpriteIdentity(0x6CCE0, 0x186E72B8, 1712, (1739, 10604, 0)),
        (1635, 10769, 420), (1, 76), (
            MapCommand(0xACE39, (131, 9, 1, 0)), MapCommand(0xACE49, (43, 1635, 10769, 420)),
            MapCommand(0xACE59, (98, 0, 0, 0)), MapCommand(0xACE69, (77, 1, 76, 0)),
            MapCommand(0xACE79, (98, 1, 0, 0)))),),
    # No ACT77 on this original exit: the story route leads into this room.
    # (0,0) explicitly means no extra quest condition, never a fabricated quest.
    6: (FinishGate('exit', SpriteIdentity(0xB21C0, 0x1884B400, 1712,
        (15093.3046875, 2279.052734375, 20)), (15108, 2303, 180), (0, 0), (
            MapCommand(0x106318, (131, 9, 1, 0)), MapCommand(0x106328, (43, 15108, 2303, 180)))),),
    7: (FinishGate('exit', SpriteIdentity(0xB6390, 0x1855A868, 1712,
        (8326.1875, 300.60845947265625, 74)), (8473, 175, 570), (0, 0), (
            MapCommand(0x106BE9, (131, 9, 1, 0)), MapCommand(0x106BF9, (131, 10, 1, 0)),
            MapCommand(0x106C09, (43, 8473, 175, 570)))),),
}

from old_native_level08_interactions import ENTRY as ENTRY08, GATES as GATES08
from old_native_level09_campaign import ENTRY as ENTRY09, GATES as GATES09
from old_native_level10_interactions import ENTRY as ENTRY10, GATES as GATES10

ENTRIES.update({8: Entry(*ENTRY08), 9: Entry(*ENTRY09), 10: Entry(*ENTRY10)})
GATES.update({8: GATES08, 9: GATES09, 10: GATES10})

from old_native_level11_interactions import ENTRY as ENTRY11, GATES as GATES11
from old_native_level12_interactions import ENTRY as ENTRY12, GATES as GATES12
from old_native_level13_interactions import ENTRY as ENTRY13, GATES as GATES13
from old_native_level14_interactions import ENTRY as ENTRY14, GATES as GATES14

ENTRIES.update({11: Entry(*ENTRY11), 12: Entry(*ENTRY12), 13: Entry(*ENTRY13), 14: Entry(*ENTRY14)})
GATES.update({11: GATES11, 12: GATES12, 13: GATES13, 14: GATES14})

from old_native_level15_interactions import ENTRY as ENTRY15, GATES as GATES15
ENTRIES[15] = Entry(*ENTRY15)
GATES[15] = GATES15

from old_native_campaign_missions import RELOADED_ENABLED
if RELOADED_ENABLED:
    from old_native_reloaded_interactions import RELOADED_ENTRIES, RELOADED_GATES
    ENTRIES.update({number: Entry(*row) for number, row in RELOADED_ENTRIES.items()})
    GATES.update(RELOADED_GATES)
