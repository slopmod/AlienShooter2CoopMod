"""Convert reviewed, pinned map records into the common interaction schema.

Catalog data is exported during development, never inferred from a player's
map at runtime. Full stacks stay in the evidence even when only ACT43 is
adapted. Effective VIDs account for preceding ACT62 in reverse stack order.
"""
from old_native_interaction_schema import MapCommand, PartyTrigger, SpriteIdentity


def proximity_catalog(map_key, rows):
    result = []
    for row in rows:
        offset, saved_id, vid, xyz, stacks = row
        sprite = SpriteIdentity(offset, saved_id, vid, tuple(xyz))
        all_commands = tuple(MapCommand(at, tuple(values)) for stack in stacks for at, values in stack)
        groups = {}
        for stack in stacks:
            effective_vid = vid
            for at, values in reversed(stack):
                if values[0] == 62:
                    effective_vid = values[1]
                elif values[0] == 43:
                    groups.setdefault((effective_vid, tuple(values[1:])), []).append(at)
        for index, ((effective_vid, trigger), records) in enumerate(groups.items()):
            result.append(PartyTrigger(
                f'{map_key}_source_{saved_id:x}_{index}', map_key, sprite, trigger,
                tuple(records), tuple(c for c in all_commands if c.offset not in records),
                source_guard='map_vid_act43', runtime_vid=effective_vid))
    return tuple(result)
