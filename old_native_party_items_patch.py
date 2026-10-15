"""Share real story-item pickup events and bounded quest removal with army 3.

Pure byte transformation for the pinned OLD executable, after spawn/crush and
before optional trigger/input/trace patches. No synthetic pickup, item grant,
quest-state write, or change to the quest server's canonical reward owner.
"""
from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass

from old_native_campaign_patch import BASELINE_SHA256, ISOLATION_PATCHES, STORY_PATCHES
from old_native_spawn_rng_patch import SPAWN_PATCHES
from old_native_crush_sync_patch import CRUSH_PATCHES, normalize_optional as normalize_crush
from old_native_story_item_registry import LEGACY_REGISTRY, LEVEL02_REGISTRY, REGISTRY, StoryItemRegistry

IMAGE_BASE = 0x400000
FEATURE = "old-campaign-party-items-v1"
REGISTERED_FEATURE = "old-campaign-registered-story-items-v1"
CAVE_VA = 0x59A6A0
CAVE_SIZE = 0x260
BIND_VA = CAVE_VA
REMOVE_VA = CAVE_VA + 0x80
KEY_NAME_VA = CAVE_VA + 0x240
DYNAMITE_NAME_VA = KEY_NAME_VA + len(LEGACY_REGISTRY.item_names[0].encode("ascii")) + 1
TEXT_VIRTUAL_SIZE_FIELD = 0x230
CRUSH_TEXT_VIRTUAL_SIZE = 0x1996A0
PARTY_ITEMS_TEXT_VIRTUAL_SIZE = 0x199900
BIND_HOOK = 0x4B8323
REMOVE_HOOK = 0x48AE58
BIND_DISPLACED = bytes.fromhex("8b86f4000000")
REMOVE_DISPLACED = bytes.fromhex("8b16508bceff522c")


def _relative(opcode: int, source: int, destination: int) -> bytes:
    return bytes([opcode]) + struct.pack("<i", destination - source - 5)


class _Code:
    def __init__(self, va: int):
        self.va, self.code, self.labels, self.jumps = va, bytearray(), {}, []

    def emit(self, code: str):
        self.code.extend(bytes.fromhex(code))

    def label(self, name: str):
        self.labels[name] = len(self.code)

    def branch(self, condition: int, label: str):
        self.emit(f"0f{condition:02x}00000000")
        self.jumps.append((len(self.code) - 4, label))

    def call(self, target: int):
        self.code.extend(_relative(0xE8, self.va + len(self.code), target))

    def jump(self, target: int):
        self.code.extend(_relative(0xE9, self.va + len(self.code), target))

    def base_ebp(self):
        # EIP-relative image base, so added instructions need no relocations.
        self.emit("e800000000")
        return_rva = self.va + len(self.code) - IMAGE_BASE
        self.emit("5d81ed" + struct.pack("<I", return_rva).hex())

    def finish(self) -> bytes:
        for at, label in self.jumps:
            struct.pack_into("<i", self.code, at, self.labels[label] - at - 4)
        return bytes(self.code)


def _bind_stub() -> bytes:
    c = _Code(BIND_VA)
    c.emit("9c60")  # Preserve all registers/flags around added binding.
    c.base_ebp()
    c.emit("8b85dc4d200085c0")  # game global
    c.branch(0x84, "done")
    c.emit("3bb0cc090000")  # ESI is exactly game.players[3].
    c.branch(0x85, "done")
    c.emit("8b858ca4330085c0")  # shared quest server
    c.branch(0x84, "done")
    c.emit("8b8e4402000085c9")  # guest item-taker
    c.branch(0x84, "done")
    c.emit("50")
    c.call(0x4926E0)  # Existing thiscall setter, ret 4; one binding, no event.
    c.label("done")
    c.emit("619d")
    c.code.extend(BIND_DISPLACED)
    c.jump(BIND_HOOK + len(BIND_DISPLACED))
    return c.finish()


def _remove_stub(name_locations=None, *, compact=False) -> bytes:
    if name_locations is None:
        name_locations = ((KEY_NAME_VA, LEGACY_REGISTRY.item_names[0]),
                          (DYNAMITE_NAME_VA, LEGACY_REGISTRY.item_names[1]))
    if not name_locations:
        raise ValueError("Story-item removal requires an admitted item")
    c = _Code(REMOVE_VA)
    c.emit("50")  # Save the requested base ID below the original argument.
    c.code.extend(REMOVE_DISPLACED)  # Unconditionally attempt original owner.
    c.emit("9c6084c0")  # Snapshot the exact original post-call machine state.
    c.branch(0x85, "done")  # AL=true: never consume from a second hero.
    c.base_ebp()
    c.emit("8b5c2424")  # Requested base ID above PUSHAD/PUSHFD: +36.
    c.emit("8bbddc4d200085ff")
    c.branch(0x84, "done")
    c.emit("8b87c009000085c0")  # canonical army0 player
    c.branch(0x84, "done")
    c.emit("3bb094010000")  # ESI must be its RPG owner; no general party loot.
    c.branch(0x85, "done")

    def resolve(name_va: int, missing: str):
        # Same two virtual calls as EXT_GetIdByName=120 at 499B42..499B79:
        # registry.virtual+0C(name, 1), then descriptor.virtual+0C() -> base ID.
        # Native return IDs are resolved for the loaded config, never assumed.
        c.emit("8b8d88a4330085c9")
        c.branch(0x84, "done")
        c.emit("8d85" + struct.pack("<I", name_va - IMAGE_BASE).hex())
        c.emit("8b116a0150ff520c85c0")
        c.branch(0x84, missing)
        c.emit("8b108bc8ff520c3bc3")

    if compact:
        # Walk contiguous NUL-terminated names with one native resolver body.
        # ESI is saved in PUSHAD; registry virtual calls preserve it. No heap,
        # hardcoded item IDs or change to the original ownership preference.
        first = name_locations[0][0] - IMAGE_BASE
        end = name_locations[-1][0] + len(name_locations[-1][1]) + 1 - IMAGE_BASE
        c.emit('8db5' + struct.pack('<I', first).hex())
        c.label('item_loop')
        c.emit('8b8d88a4330085c9'); c.branch(0x84, 'done')
        c.emit('8b116a0156ff520c85c0'); c.branch(0x84, 'advance_name')
        c.emit('8b108bc8ff520c3bc3'); c.branch(0x84, 'fallback')
        c.label('advance_name')
        c.emit('0fb6068d760185c0'); c.branch(0x85, 'advance_name')
        c.emit('8bd62bd581fa' + struct.pack('<I', end).hex())
        c.branch(0x82, 'item_loop')
        c.branch(0x83, 'done')
    else:
        for index, (name_va, _) in enumerate(name_locations):
            last = index == len(name_locations) - 1
            next_label = "done" if last else f"item_{index + 1}"
            resolve(name_va, next_label)
            c.branch(0x85 if last else 0x84, "done" if last else "fallback")
            if not last:
                c.label(next_label)
    c.label("fallback")
    c.emit("8b87cc09000085c0")  # game.players[3]
    c.branch(0x84, "done")
    c.emit("8b889401000085c9")
    c.branch(0x84, "done")
    if compact:
        c.emit('8b87c00900003b8894010000')
    else:
        c.emit("3bce")
    c.branch(0x84, "done")
    c.emit("8b1153ff522c")  # Original RPG removal incl. native dirty notification.
    c.label("done")
    # The caller ignores AL and immediately INC/CMPs its loop index. Preserve
    # the original post-call EAX/ECX/EDX too; all added lookup/fallback clobbers
    # are confined to this saved context. LEA discards saved ID without flags.
    c.emit("619d8d642404")
    c.jump(REMOVE_HOOK + len(REMOVE_DISPLACED))
    return c.finish()


@dataclass(frozen=True, slots=True)
class CompiledItemProfile:
    """Pure generated bytes. Being compilable does not admit a runtime profile."""
    registry: StoryItemRegistry
    bind_stub: bytes
    remove_stub: bytes
    name_locations: tuple[tuple[int, str], ...]
    cave: bytes
    patches: tuple[tuple[int, bytes, bytes], ...]


def compile_profile(registry: StoryItemRegistry) -> CompiledItemProfile:
    if not isinstance(registry, StoryItemRegistry):
        raise TypeError("Expected immutable story-item registry")
    names = tuple((name, name.encode("ascii") + b"\0") for name in registry.item_names)
    # The legacy names keep their exact addresses. Larger admitted rosters use
    # the preceding unused padding, bounded by the generated code's actual end.
    name_offset = min(KEY_NAME_VA - CAVE_VA, CAVE_SIZE - sum(len(raw) for _, raw in names))
    if name_offset <= REMOVE_VA - CAVE_VA:
        raise ValueError("Story-item names exceed reserved native cave capacity")
    locations = []
    cursor = name_offset
    for name, raw in names:
        locations.append((CAVE_VA + cursor, name))
        cursor += len(raw)
    bind_stub = _bind_stub()
    remove_stub = _remove_stub(tuple(locations), compact=len(locations) > 5)
    if len(bind_stub) > REMOVE_VA - BIND_VA or REMOVE_VA - CAVE_VA + len(remove_stub) >= name_offset:
        raise ValueError("Story-item profile exceeds reserved native cave capacity")
    cave = bytearray(CAVE_SIZE)
    cave[:len(bind_stub)] = bind_stub
    cave[REMOVE_VA - CAVE_VA:REMOVE_VA - CAVE_VA + len(remove_stub)] = remove_stub
    for (va, _), (_, raw) in zip(locations, names):
        cave[va - CAVE_VA:va - CAVE_VA + len(raw)] = raw
    cave = bytes(cave)
    patches = (
        (IMAGE_BASE + TEXT_VIRTUAL_SIZE_FIELD,
         struct.pack("<I", CRUSH_TEXT_VIRTUAL_SIZE),
         struct.pack("<I", PARTY_ITEMS_TEXT_VIRTUAL_SIZE)),
        (CAVE_VA, b"\0" * CAVE_SIZE, cave),
        (BIND_HOOK, BIND_DISPLACED,
         _relative(0xE9, BIND_HOOK, BIND_VA) + b"\x90"),
        (REMOVE_HOOK, REMOVE_DISPLACED,
         _relative(0xE9, REMOVE_HOOK, REMOVE_VA) + b"\x90" * 3),
    )
    return CompiledItemProfile(registry, bind_stub, remove_stub, tuple(locations), cave, patches)


LEGACY_PROFILE = compile_profile(LEGACY_REGISTRY)
LEVEL02_PROFILE = compile_profile(LEVEL02_REGISTRY)
REGISTERED_PROFILE = compile_profile(REGISTRY)
BIND_STUB = LEGACY_PROFILE.bind_stub
REMOVE_STUB = LEGACY_PROFILE.remove_stub
CAVE = LEGACY_PROFILE.cave
PARTY_ITEMS_PATCHES = LEGACY_PROFILE.patches
# Deliberately NOT a cache of every profile ever passed to compile_profile().
# Historical registered two-item bytes are exactly LEGACY_PROFILE, so they
# remain accepted after admitting the larger current roster. Unknown partial
# profiles remain rejected; compilation alone never expands this allowlist.
TRUSTED_PROFILES = (LEGACY_PROFILE, LEVEL02_PROFILE, REGISTERED_PROFILE)

# Pinned exact caller/ABI anchors in addition to the whole normalized hash.
CONTEXT_GUARDS = (
    (0x4B80F0, bytes.fromhex("5355568bf157")),
    (0x4B8276, bytes.fromhex("a18ca4730085c00f85a0000000")),
    (0x4B8312, bytes.fromhex("8b8e44020000a18ca47300508b11ff5234")),
    (0x4B8323, bytes.fromhex("8b86f400000085c0751e")),
    (0x4926E0, bytes.fromhex("8b442404894144c20400")),
    (0x492A64, bytes.fromhex("8b4f448b442418506a008b11c744241800000000ff5258")),
    (0x48AE58, bytes.fromhex("8b16508bceff522c433bdd7ce6")),
    (0x48CA60, bytes.fromhex("8b54240453568bf1528b8ea80100008b01ff501c8ad884db74088d4e0ce8ee5afeff8ac35e5bc20400")),
    (0x499B42, bytes.fromhex("c706ffffffff8b0d88a4730085c9")),
    (0x499B62, bytes.fromhex("8b116a0150ff520c85c00f84b90000008b108bc8ff520c")),
    (0x499C8F, b"\x02"),  # String-command120 jump-table entry.
    (0x4B9B35, bytes.fromhex("a1dc4d60008bd683e2078b8c90c0090000")),
)


def normalize_optional(image: bytes) -> tuple[bytes, bool]:
    """Remove a complete item patch before removing crush/spawn patches.

    A caller must first unwrap the later party-trigger/diagnostic patches.
    This group detector is not a replacement for that caller's whole-file SHA.
    """
    if not isinstance(image, bytes):
        raise TypeError("Expected executable bytes")
    if all(image[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] == before
           for va, before, _ in PARTY_ITEMS_PATCHES[1:]):
        return image, False
    for profile in TRUSTED_PROFILES:
        if all(image[va - IMAGE_BASE:va - IMAGE_BASE + len(after)] == after
               for va, _, after in profile.patches):
            normalized = bytearray(image)
            for va, before, _ in profile.patches:
                normalized[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] = before
            return bytes(normalized), True
    raise ValueError("Unknown or incomplete trusted party-item patch group")


def _patch(image: bytes, profile: CompiledItemProfile) -> tuple[bytes, dict]:
    """Require known crush/spawn and only known isolation/story byte changes."""
    if not isinstance(image, bytes):
        raise TypeError("Expected executable bytes")
    _, already = normalize_optional(image)
    if already:
        raise ValueError("Party-item patch is already applied")
    for va, expected in CONTEXT_GUARDS:
        if image[va - IMAGE_BASE:va - IMAGE_BASE + len(expected)] != expected:
            raise ValueError(f"Unsupported party-item native context at {va:#x}")
    for va, _, after in CRUSH_PATCHES:
        if image[va - IMAGE_BASE:va - IMAGE_BASE + len(after)] != after:
            raise ValueError(f"Complete crush patch required at {va:#x}")
    normalized, _ = normalize_crush(image)
    normalized = bytearray(normalized)
    for va, before, after in SPAWN_PATCHES:
        if normalized[va - IMAGE_BASE:va - IMAGE_BASE + len(after)] != after:
            raise ValueError(f"Complete spawn patch required at {va:#x}")
        normalized[va - IMAGE_BASE:va - IMAGE_BASE + len(before)] = before
    for va, before, after in ISOLATION_PATCHES + STORY_PATCHES:
        at = va - IMAGE_BASE
        if normalized[at:at + len(before)] not in (before, after):
            raise ValueError(f"Unknown executable modification at {va:#x}")
        normalized[at:at + len(before)] = before
    if hashlib.sha256(normalized).hexdigest() != BASELINE_SHA256:
        raise ValueError("Unsupported party-item executable: normalized SHA-256 mismatch")
    output = bytearray(image)
    for va, before, after in profile.patches:
        at = va - IMAGE_BASE
        if output[at:at + len(before)] != before or len(before) != len(after):
            raise AssertionError(f"Party-item patch source or size mismatch at {va:#x}")
        output[at:at + len(before)] = after
    result = bytes(output)
    return result, {
        "feature": FEATURE,
        "baseline_sha256": BASELINE_SHA256,
        "input_sha256": hashlib.sha256(image).hexdigest(),
        "output_sha256": hashlib.sha256(result).hexdigest(),
        "requires": "old-campaign-crush-sync-v1",
        "pickup_policy": "Bind army3 item-taker to original shared quest server during native initialization; original CSI_TAKE only",
        "removal_policy": "Original owner first; if missing and owner is army0, fallback to army3 for dynamically resolved Obj_accesskey/Obj_dynamite only",
        "canonical_reward_owner_preserved": True,
        "item_names": list(profile.registry.item_names),
        "native_item_id_resolution": "Same registry/descriptor virtual calls as EXT_GetIdByName120; no fixed numeric IDs",
        "native_removal": "RPG owner virtual+0x2C; native inventory and dirty notification",
        "abi": "Added operations preserve full GPR/EFLAGS state and ESP; no x87/SSE or RNG operations",
        "cave_va": hex(CAVE_VA), "cave_size": CAVE_SIZE,
        "stubs": [{"kind": "binding", "va": hex(BIND_VA), "size": len(profile.bind_stub)},
                  {"kind": "removal", "va": hex(REMOVE_VA), "size": len(profile.remove_stub)}],
        "section_change": "Extend existing .text VirtualSize to0x199900 within zero raw padding; no new section/relocations",
        "normalization_order": "party triggers if present, party items, crush, spawn, isolation/story",
        "runtime_validated": False,
        "patches": [{"va": hex(va), "before": before.hex(), "after": after.hex()}
                    for va, before, after in profile.patches],
    }


def patch(image: bytes) -> tuple[bytes, dict]:
    """Frozen legacy API: preserve its executable bytes and metadata exactly."""
    return _patch(image, LEGACY_PROFILE)


def patch_registered(image: bytes, levels_bytes: bytes) -> tuple[bytes, dict]:
    """Apply only the current audited roster after validating original quests."""
    REGISTRY.validate_levels(levels_bytes)
    result, metadata = _patch(image, REGISTERED_PROFILE)
    catalog = REGISTRY.manifest()
    metadata.update({
        "feature": REGISTERED_FEATURE,
        "catalog": catalog,
        "catalog_sha256": hashlib.sha256(json.dumps(catalog, sort_keys=True,
                                                      separators=(",", ":")).encode()).hexdigest(),
        "removal_policy": "Original owner first; if missing and owner is army0, fallback to army3 only for the audited roster",
        "quest_scope": "Item allowlist at original RemItem call site; not a per-quest filter",
        "pickup_scope": "Existing shared native CSI_TAKE binding for all real named pickups; catalog records are source guards",
        "code_to_names_gap": REGISTERED_PROFILE.name_locations[0][0] - REMOVE_VA - len(REGISTERED_PROFILE.remove_stub),
        "code_to_names_gap_positive": True,
        "legacy_two_item_normalization_preserved": True,
    })
    return result, metadata
