"""Audited story-item ownership declarations for the pinned OLD campaign.

Pickup bindings describe original quest events; they do not synthesize events.
The native fallback is item-scoped at the quest RemItem call site, not scoped
to these individual quests. Therefore every RemItem occurrence is recorded
and checked. Discovered items are deliberately separate from the active roster.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re

LEVELS_SHA256 = "5606461fbe14c683a323480b8e3b01203309153598d57ef57355ad20083ad01f"
_NAME = re.compile(r"Obj_[A-Za-z0-9_]+\Z")
_QUEST = re.compile(r"[0-9]+_[0-9]+_[0-9]+\Z")
_LABEL = re.compile(r"[A-Za-z0-9_]+\Z")


@dataclass(frozen=True, slots=True)
class PickupBinding:
    quest: str
    label: str

    def __post_init__(self):
        if not isinstance(self.quest, str) or not _QUEST.fullmatch(self.quest):
            raise ValueError("Invalid source quest ID")
        if not isinstance(self.label, str) or not _LABEL.fullmatch(self.label):
            raise ValueError("Invalid CSI_TAKE label")

    @property
    def value(self) -> str:
        return f"QS_BEGUN CSI_TAKE {self.label}"


@dataclass(frozen=True, slots=True)
class RemovalBinding:
    quest: str
    items: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.quest, str) or not _QUEST.fullmatch(self.quest):
            raise ValueError("Invalid source quest ID")
        if not isinstance(self.items, tuple) or not self.items or any(
                not isinstance(name, str) or not _NAME.fullmatch(name) for name in self.items):
            raise ValueError("Removal items must be a nonempty immutable name tuple")
        if len(set(self.items)) != len(self.items):
            raise ValueError("Duplicate item in audited RemItem record")

    @property
    def value(self) -> str:
        return " ".join(self.items)


@dataclass(frozen=True, slots=True)
class StoryItem:
    name: str
    pickups: tuple[PickupBinding, ...]
    removals: tuple[RemovalBinding, ...]

    def __post_init__(self):
        if not isinstance(self.name, str) or not _NAME.fullmatch(self.name):
            raise ValueError("Invalid native story-item name")
        for records, record_type in ((self.pickups, PickupBinding), (self.removals, RemovalBinding)):
            if not isinstance(records, tuple) or any(not isinstance(r, record_type) for r in records):
                raise TypeError("Story-item bindings must be immutable typed tuples")
            if len({record.quest for record in records}) != len(records):
                raise ValueError("Duplicate quest binding")
        if not self.removals or any(self.name not in record.items for record in self.removals):
            raise ValueError("Every removal binding must contain this item")


@dataclass(frozen=True, slots=True)
class OwnerPolicy:
    canonical_army: int = 0
    fallback_armies: tuple[int, ...] = (3,)
    original_owner_first: bool = True
    fallback_only_if_original_missing: bool = True

    def __post_init__(self):
        # This is the verified native ABI, not a claim of arbitrary-party support.
        if (type(self.canonical_army) is not int or self.canonical_army != 0
                or self.fallback_armies != (3,) or not isinstance(self.fallback_armies, tuple)
                or any(type(army) is not int for army in self.fallback_armies)
                or self.original_owner_first is not True
                or self.fallback_only_if_original_missing is not True):
            raise ValueError("Only the audited army0-first, army3-if-missing policy is supported")


def _quest_records(source: bytes) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    current = None
    for raw in source.decode("cp1251").splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key == "Quest":
            if value in records:
                raise ValueError(f"Duplicate source quest {value}")
            current = records[value] = {}
        elif current is not None and key in ("RemItem", "ChangeStateItem"):
            if key in current:
                raise ValueError(f"Duplicate quest field {key}")
            current[key] = value
    return records


@dataclass(frozen=True, slots=True)
class StoryItemRegistry:
    levels_sha256: str
    items: tuple[StoryItem, ...]
    owner_policy: OwnerPolicy = OwnerPolicy()

    def __post_init__(self):
        if not isinstance(self.levels_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.levels_sha256):
            raise ValueError("Invalid original levels.cfg SHA-256")
        if not isinstance(self.items, tuple) or not self.items or any(
                not isinstance(item, StoryItem) for item in self.items):
            raise TypeError("Registry requires a nonempty immutable story-item tuple")
        if len(set(self.item_names)) != len(self.items):
            raise ValueError("Duplicate native item name")
        if not isinstance(self.owner_policy, OwnerPolicy):
            raise TypeError("Registry requires a supported owner policy")
        claims = {}
        for item in self.items:
            for binding in item.removals:
                if binding.quest in claims and claims[binding.quest] != binding.items:
                    raise ValueError("Conflicting RemItem record declarations")
                claims[binding.quest] = binding.items

    @property
    def item_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.items)

    def manifest(self) -> dict:
        """Return detached JSON-serializable metadata, not mutable registry state."""
        return asdict(self)

    def validate_levels(self, source: bytes) -> None:
        if not isinstance(source, bytes):
            raise TypeError("Expected original levels.cfg bytes")
        if hashlib.sha256(source).hexdigest() != self.levels_sha256:
            raise ValueError("Unsupported story-item levels.cfg: SHA-256 mismatch")
        records = _quest_records(source)
        for item in self.items:
            for binding in item.pickups:
                if records.get(binding.quest, {}).get("ChangeStateItem") != binding.value:
                    raise ValueError(f"Changed CSI_TAKE binding for {item.name}: {binding.quest}")
            for binding in item.removals:
                if records.get(binding.quest, {}).get("RemItem") != binding.value:
                    raise ValueError(f"Changed RemItem binding for {item.name}: {binding.quest}")
            actual = {quest for quest, fields in records.items()
                      if item.name in fields.get("RemItem", "").split()}
            if actual != {binding.quest for binding in item.removals}:
                raise ValueError(f"Unregistered RemItem occurrence for {item.name}")


ACCESS_KEY = StoryItem("Obj_accesskey", (PickupBinding("1_1_37", "accesskey"),), (
    RemovalBinding("1_1_36", ("Obj_accesskey",)),
    RemovalBinding("1_1_38", ("Obj_accesskey", "Obj_dynamite")),
    RemovalBinding("1_1_43", ("Obj_accesskey", "Obj_seckey")),
))
DYNAMITE = StoryItem("Obj_dynamite", (PickupBinding("1_1_5", "explosive"),), (
    RemovalBinding("1_1_6", ("Obj_dynamite",)),
    RemovalBinding("1_1_38", ("Obj_accesskey", "Obj_dynamite")),
))

# Frozen compatibility roster. New admitted items go into REGISTRY separately,
# after their native pickup/consumption evidence, without changing legacy bytes.
LEGACY_REGISTRY = StoryItemRegistry(LEVELS_SHA256, (ACCESS_KEY, DYNAMITE))

# The original Level02 ground items already notify the shared quest server.
# Original room quests consume the optional keys; quest1/7 also clears all
# three at the next mission's entry. No extra removal is added to the q42 doors.
PERSONAL_KEY = StoryItem("Obj_personalkey", (PickupBinding("1_1_42", "personalkey"),), (
    RemovalBinding("1_1_7", ("Obj_personalkey", "Obj_perkey_andry", "Obj_perkey_statham")),
))
ANDRY_KEY = StoryItem("Obj_perkey_andry", (PickupBinding("1_3_5", "andry_key"),), (
    RemovalBinding("1_1_7", ("Obj_personalkey", "Obj_perkey_andry", "Obj_perkey_statham")),
    RemovalBinding("1_3_6", ("Obj_perkey_andry",)),
))
STATHAM_KEY = StoryItem("Obj_perkey_statham", (PickupBinding("1_4_3", "statham"),), (
    RemovalBinding("1_1_7", ("Obj_personalkey", "Obj_perkey_andry", "Obj_perkey_statham")),
    RemovalBinding("1_4_4", ("Obj_perkey_statham",)),
))
LEVEL02_REGISTRY = StoryItemRegistry(LEVELS_SHA256, LEGACY_REGISTRY.items + (PERSONAL_KEY, ANDRY_KEY, STATHAM_KEY))

RED_KEY = StoryItem('Obj_redkey', (PickupBinding('1_2_2', 'redkey'),), (
    RemovalBinding('1_2_3', ('Obj_redkey',)), RemovalBinding('1_1_26', ('Obj_redkey',)),
))
CIGAR = StoryItem('Obj_cigar', (PickupBinding('1_3_2', 'cigar'),), tuple(
    RemovalBinding(q, ('Obj_cigar',)) for q in ('1_3_3', '1_3_4', '1_1_75', '1_3_10')))
SECURITY_KEY = StoryItem('Obj_seckey', (PickupBinding('1_1_79', 'autorize_key'),), (
    RemovalBinding('1_1_18', ('Obj_seckey',)),
    RemovalBinding('1_1_43', ('Obj_accesskey', 'Obj_seckey')),
    RemovalBinding('1_3_11', ('Obj_seckey',)),
))
COMPONENT_CLEAR = (
    RemovalBinding('1_2_22', ('Obj_cooling', 'Obj_transf', 'Obj_stabil')),
    RemovalBinding('1_1_86', ('Obj_cooling', 'Obj_stabil', 'Obj_transf')),
)
STABILIZER = StoryItem('Obj_stabil', (), COMPONENT_CLEAR + tuple(
    RemovalBinding(q, ('Obj_stabil',)) for q in ('1_2_15', '1_2_28', '1_2_30')))
TRANSFORMER = StoryItem('Obj_transf', (PickupBinding('1_2_17', 'trans'),), COMPONENT_CLEAR + (
    RemovalBinding('1_2_18', ('Obj_transf',)), RemovalBinding('1_3_13', ('Obj_transf',)),
))
COOLING = StoryItem('Obj_cooling', (PickupBinding('1_2_20', 'cooler'),), COMPONENT_CLEAR)
# Later campaign evidence extends the active item without changing the frozen
# historical Level01/Level02 profiles or their executable bytes.
CAMPAIGN_DYNAMITE = StoryItem(DYNAMITE.name,
    DYNAMITE.pickups + (PickupBinding('1_1_69', 'dynamite2'),), DYNAMITE.removals)
ACCUMULATOR = StoryItem('Obj_accumulator', (PickupBinding('1_1_65', 'accum'),), (
    RemovalBinding('1_1_66', ('Obj_accumulator',)),
))
# Level10 creates this story item through its terminal callback, not CSI_TAKE.
# Its sole original RemItem use is the Level14 Baker handover branch.
DISK = StoryItem('Obj_disk', (), (RemovalBinding('1_4_7', ('Obj_disk',)),))
REGISTRY = StoryItemRegistry(LEVELS_SHA256,
    tuple(CAMPAIGN_DYNAMITE if item is DYNAMITE else item for item in LEVEL02_REGISTRY.items) + (
        RED_KEY, CIGAR, SECURITY_KEY, STABILIZER, TRANSFORMER, COOLING, ACCUMULATOR, DISK))
DISCOVERED_ITEMS = ()
