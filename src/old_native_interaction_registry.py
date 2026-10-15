"""Compose explicitly audited map catalogs and preserve the historical API.

PARTY_TRIGGERS is the original six-entry profile used by legacy byte proofs.
REGISTRY additionally includes audited campaign ACT43 records and reviewed
portals; a catalog entry does not prove native gameplay by itself.
"""
from old_native_interaction_schema import (
    Bounds, InteractionRegistry, LogicalPortal, MapCommand, MapIdentity,
    PartyTrigger, PortalPolicy, SpriteIdentity, Triple, XYZ,
)
from old_native_level01_interactions import (
    BUNKER_PORTALS, LEVEL01, LEVEL01_PARTY_TRIGGERS, LEVEL01_OPENING_TRIGGERS,
    LEVEL01_INTERIOR_TRIGGERS,
)
from old_native_level02_interactions import (
    ADMIN_ENTRY_SPRITE, ADMIN_PORTAL, INTERIOR_CORRIDOR_GENERATORS,
    INTERIOR_LOWER_ENCOUNTERS, INTERIOR_STAIR_ENCOUNTERS, LEVEL02,
    LEVEL02_DOOR_ROOF_TRIGGERS, LEVEL02_ENCOUNTER_TRIGGERS,
    LEVEL02_LEGACY_PARTY_TRIGGERS, PERSONAL_KEY_ROOM_ROOF, Q42_DOORS,
    LEVEL02_REMAINING_TRIGGERS, LEVEL02_EXTRA_PORTALS,
)
from old_native_level03_interactions import LEVEL03, LEVEL03_TRIGGERS
from old_native_level04_interactions import LEVEL04, LEVEL04_TRIGGERS
from old_native_level05_interactions import LEVEL05, LEVEL05_TRIGGERS
from old_native_level06_interactions import LEVEL06, LEVEL06_TRIGGERS
from old_native_level07_interactions import LEVEL07, LEVEL07_TRIGGERS
from old_native_level08_interactions import LEVEL08, LEVEL08_TRIGGERS, PORTALS as LEVEL08_PORTALS
from old_native_level09_interactions import LEVEL09, LEVEL09_TRIGGERS
from old_native_level10_interactions import LEVEL10, LEVEL10_TRIGGERS
from old_native_level11_interactions import LEVEL11, LEVEL11_TRIGGERS
from old_native_level12_interactions import LEVEL12, LEVEL12_TRIGGERS
from old_native_level13_interactions import LEVEL13, LEVEL13_TRIGGERS
from old_native_level14_interactions import LEVEL14, LEVEL14_TRIGGERS
from old_native_level15_interactions import LEVEL15, LEVEL15_TRIGGERS
from old_native_campaign_portals import CAMPAIGN_PORTALS
from old_native_campaign_missions import RELOADED_ENABLED
from old_native_reloaded_interactions import (
    LEVEL72, LEVEL73, LEVEL72_TRIGGERS, LEVEL73_TRIGGERS, RELOADED_PORTALS,
)


PARTY_TRIGGERS = LEVEL01_PARTY_TRIGGERS + LEVEL02_LEGACY_PARTY_TRIGGERS
PORTALS = (BUNKER_PORTALS + (ADMIN_PORTAL,) + LEVEL02_EXTRA_PORTALS + CAMPAIGN_PORTALS + LEVEL08_PORTALS
           + (RELOADED_PORTALS if RELOADED_ENABLED else ()))
REGISTRY = InteractionRegistry(
    (LEVEL01, LEVEL02, LEVEL03, LEVEL04, LEVEL05, LEVEL06, LEVEL07, LEVEL08, LEVEL09, LEVEL10,
     LEVEL11, LEVEL12, LEVEL13, LEVEL14, LEVEL15)
    + ((LEVEL72, LEVEL73) if RELOADED_ENABLED else ()),
    PARTY_TRIGGERS + LEVEL02_ENCOUNTER_TRIGGERS + LEVEL02_DOOR_ROOF_TRIGGERS + LEVEL02_REMAINING_TRIGGERS + LEVEL01_OPENING_TRIGGERS + LEVEL01_INTERIOR_TRIGGERS + LEVEL03_TRIGGERS + LEVEL04_TRIGGERS + LEVEL05_TRIGGERS + LEVEL06_TRIGGERS + LEVEL07_TRIGGERS
    + LEVEL08_TRIGGERS + LEVEL09_TRIGGERS + LEVEL10_TRIGGERS
    + LEVEL11_TRIGGERS + LEVEL12_TRIGGERS + LEVEL13_TRIGGERS + LEVEL14_TRIGGERS
    + LEVEL15_TRIGGERS
    + ((LEVEL72_TRIGGERS + LEVEL73_TRIGGERS) if RELOADED_ENABLED else ()),
    PORTALS,
)


def validate_original_map(image: bytes, map_key: str) -> None:
    REGISTRY.validate_original_map(image, map_key)
