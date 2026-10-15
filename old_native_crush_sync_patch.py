"""Guard native crush damage against unsynchronized cosmetic movers.

Pure transformation for the pinned OLD co-op campaign executable. An important
victim may receive the three native fixed-damage crush calls only from an
important mover. Other combinations retain the original native behavior. This
is not a general collision filter, nor a claim that every desync is resolved.
Apply after the spawn scatter patch and before input/trace instrumentation.
"""
from __future__ import annotations

import hashlib
import struct

from old_native_campaign_patch import BASELINE_SHA256, ISOLATION_PATCHES, STORY_PATCHES
from old_native_spawn_rng_patch import SPAWN_PATCHES

IMAGE_BASE = 0x400000
FEATURE = "old-campaign-crush-sync-v1"
CAVE_VA = 0x59A520
SLOT_SIZE = 0x80
CAVE_SIZE = 3 * SLOT_SIZE
TEXT_VIRTUAL_SIZE_FIELD = 0x230
SPAWN_TEXT_VIRTUAL_SIZE = 0x199520
CRUSH_TEXT_VIRTUAL_SIZE = 0x1996A0
IMPORTANT_FOR_SYNC = 0x1000
DISPLACED = bytes.fromhex("8b166a006a00")

# (pre-argument hook, allow resume, skip resume, root mover register).
# Victim is ESI throughout. The original five-byte damage call sites remain
# untouched, allowing the independent passive collision trace to compose.
HOOKS = (
    (0x44C0B6, 0x44C0BC, 0x44C0C5, "ebx"),
    (0x45256E, 0x452574, 0x45257D, "edi"),
    (0x4097B3, 0x4097B9, 0x4097C2, "ebx"),
)


def _relative(opcode: int, source: int, destination: int) -> bytes:
    return bytes([opcode]) + struct.pack("<i", destination - source - 5)


def _stub(index: int) -> bytes:
    _, allow_resume, skip_resume, mover = HOOKS[index]
    start = CAVE_VA + index * SLOT_SIZE
    code = bytearray.fromhex("9c508b4644f7803005000000100000")
    # PUSHFD/PUSH EAX; read victim descriptor+530. The native calling context
    # has already dereferenced both sprites and their descriptors, so these
    # pointers are live. No new null/ownership/hierarchy guess is introduced.
    first_branch = len(code)
    code.extend(bytes.fromhex("7400"))
    code.extend(bytes.fromhex("8b4344" if mover == "ebx" else "8b4744"))
    code.extend(bytes.fromhex("f7803005000000100000"))
    second_branch = len(code)
    code.extend(bytes.fromhex("7500"))
    # Important victim + nonimportant mover: no arguments were pushed at the
    # hook yet, so restoring our two pushes is the complete stack cleanup.
    code.extend(bytes.fromhex("589d"))
    code.extend(_relative(0xE9, start + len(code), skip_resume))
    allow = len(code)
    code.extend(bytes.fromhex("589d"))
    code.extend(DISPLACED)
    code.extend(_relative(0xE9, start + len(code), allow_resume))
    for branch in (first_branch, second_branch):
        displacement = allow - (branch + 2)
        if not 0 <= displacement <= 127:
            raise AssertionError("Crush guard short branch exceeds range")
        code[branch + 1] = displacement
    if len(code) > SLOT_SIZE:
        raise AssertionError("Crush guard exceeds reserved cave slot")
    return bytes(code)


STUBS = tuple(_stub(i) for i in range(len(HOOKS)))
CAVE = b"".join(stub.ljust(SLOT_SIZE, b"\0") for stub in STUBS)
CRUSH_PATCHES = (
    (IMAGE_BASE + TEXT_VIRTUAL_SIZE_FIELD,
     struct.pack("<I", SPAWN_TEXT_VIRTUAL_SIZE),
     struct.pack("<I", CRUSH_TEXT_VIRTUAL_SIZE)),
    (CAVE_VA, b"\0" * CAVE_SIZE, CAVE),
    *tuple((hook[0], DISPLACED,
            _relative(0xE9, hook[0], CAVE_VA + i * SLOT_SIZE) + b"\x90")
           for i, hook in enumerate(HOOKS)),
)

CONTEXT_GUARDS = (
    (0x44BB20, bytes.fromhex("83ec608b442464538bd955")),  # EBX root mover
    (0x44BB57, bytes.fromhex("33f68beb")),               # EBP component
    (0x44C0AB, bytes.fromhex("8b4e448b4114f6c440740f8b166a006a006a056a558bceff5204")),
    (0x451E10, bytes.fromhex("81ec28010000535556578bf9")),  # EDI mover
    (0x45256E, bytes.fromhex("8b166a006a006a056a558bceff5204")),
    (0x40974A, bytes.fromhex("8b43448b0d4801730005a00300008d7b04")),
    (0x4097AB, bytes.fromhex("8b4e44856914740f8b166a006a006a056a558bceff5204")),
)


def normalize_optional(image: bytes) -> tuple[bytes, bool]:
    """Remove a complete crush group before a caller removes SPAWN_PATCHES.

    Does not replace a caller's complete image guard. With every non-header
    slot original, leave the shared section-header field to the spawn/base
    normalizer. A present group must be complete and have the crush header;
    unknown or partial slots are rejected even in an instrumented image.
    """
    if not isinstance(image, bytes):
        raise TypeError("Expected executable bytes")
    states = []
    for va, before, after in CRUSH_PATCHES[1:]:
        at = va - IMAGE_BASE
        current = image[at:at + len(before)]
        if current == before:
            states.append(False)
        elif current == after:
            states.append(True)
        else:
            raise ValueError(f"Unknown crush patch bytes at {va:#x}")
    if not any(states):
        return image, False
    if not all(states):
        raise ValueError("Incomplete crush patch group")
    va, _, after = CRUSH_PATCHES[0]
    at = va - IMAGE_BASE
    if image[at:at + len(after)] != after:
        raise ValueError("Crush patch section header does not match complete group")
    normalized = bytearray(image)
    for va, before, _ in CRUSH_PATCHES:
        at = va - IMAGE_BASE
        normalized[at:at + len(before)] = before
    return bytes(normalized), True


def patch(image: bytes) -> tuple[bytes, dict]:
    """Return patched bytes and metadata, with no filesystem/process access.

    Requires the complete known spawn patch and accepts only known isolation/
    story modifications in addition. The exact normalized original SHA pins
    all PE layout, pointer contexts, padding and untouched native instructions.
    Reapplication, partial groups and diagnostic/input additions are rejected.
    """
    if not isinstance(image, bytes):
        raise TypeError("Expected executable bytes")
    _, already = normalize_optional(image)
    if already:
        raise ValueError("Crush patch is already applied")
    for va, expected in CONTEXT_GUARDS:
        at = va - IMAGE_BASE
        if image[at:at + len(expected)] != expected:
            raise ValueError(f"Unsupported native crush context at {va:#x}")
    for va, _, expected in SPAWN_PATCHES:
        at = va - IMAGE_BASE
        if image[at:at + len(expected)] != expected:
            raise ValueError(f"Complete spawn patch is required at {va:#x}")
    normalized = bytearray(image)
    for va, before, _ in SPAWN_PATCHES:
        at = va - IMAGE_BASE
        normalized[at:at + len(before)] = before
    accepted = []
    for va, before, after in ISOLATION_PATCHES + STORY_PATCHES:
        at = va - IMAGE_BASE
        current = image[at:at + len(before)]
        if current not in (before, after):
            raise ValueError(f"Unknown executable modification at {va:#x}")
        if current == after:
            accepted.append(hex(va))
        normalized[at:at + len(before)] = before
    if hashlib.sha256(normalized).hexdigest() != BASELINE_SHA256:
        raise ValueError("Unsupported crush executable: normalized SHA-256 mismatch")
    output = bytearray(image)
    for va, before, after in CRUSH_PATCHES:
        at = va - IMAGE_BASE
        if output[at:at + len(before)] != before or len(before) != len(after):
            raise AssertionError(f"Crush patch source or size mismatch at {va:#x}")
        output[at:at + len(before)] = after
    result = bytes(output)
    return result, {
        "feature": FEATURE,
        "baseline_sha256": BASELINE_SHA256,
        "input_sha256": hashlib.sha256(image).hexdigest(),
        "output_sha256": hashlib.sha256(result).hexdigest(),
        "requires": "old-campaign-spawn-scatter-sync-v1",
        "scope": "Three native fixed damage-5 crush calls in isolated co-op campaign",
        "policy": "Skip only if victim VID ImportantForSync and mover VID not ImportantForSync",
        "important_flag": IMPORTANT_FOR_SYNC,
        "importance_source": "Native cached descriptor +0x530; original recursive child-to-parent importance",
        "preserved": ["important mover crush behavior", "nonimportant victim behavior",
                      "all native geometry and non-crush collision handling",
                      "allowed damage call address and return address", "all RNG calls"],
        "abi": "Preserve EAX/EFLAGS/ESP; other registers and x87/SSE untouched; replay original pre-argument bytes only on allow",
        "cave_va": hex(CAVE_VA), "cave_size": CAVE_SIZE,
        "stubs": [{"va": hex(CAVE_VA + i * SLOT_SIZE), "size": len(stub),
                   "hook": hex(HOOKS[i][0]), "allow": hex(HOOKS[i][1]),
                   "skip": hex(HOOKS[i][2]), "mover_register": HOOKS[i][3]}
                  for i, stub in enumerate(STUBS)],
        "section_change": "Extend existing .text VirtualSize 0x199520 to 0x1996A0 inside zero raw padding; no new section/relocations",
        "normalization_order": "crush, then spawn, then isolation/story",
        "accepted_input_patches": accepted,
        "evidence": "Native trace captured different nonimportant VID1310 blood crush calls against important VID1800 rats across peers",
        "limitation": "Captured blood victims were already in animation16; causality for the earlier living-rat divergence and complete runtime synchronization remains unproven",
        "patches": [{"va": hex(va), "before": before.hex(), "after": after.hex()}
                    for va, before, after in CRUSH_PATCHES],
    }
