"""Use synchronized scatter when ACT_BUILD_UNIT creates an important child.

Pure transformation of the pinned OLD executable. Apply only to isolated
co-op campaign copies, after isolation/story patches and before diagnostics.
The native parent-important branch is unchanged. Only its two local-RNG
fallback calls additionally consider the already resolved child descriptor.
"""
from __future__ import annotations

import hashlib
import struct

from old_native_campaign_patch import BASELINE_SHA256, ISOLATION_PATCHES, STORY_PATCHES

IMAGE_BASE = 0x400000
FEATURE = "old-campaign-spawn-scatter-sync-v1"
CAVE_VA = 0x59A500
LOCAL_RNG_VA = 0x42ACF0
SHARED_RNG_VA = 0x42CC00
HOOK_VAS = (0x44E039, 0x44E07A)
TEXT_VIRTUAL_SIZE_FIELD = 0x230
ORIGINAL_TEXT_VIRTUAL_SIZE = 0x1994C6


def _relative(opcode: int, source: int, destination: int) -> bytes:
    return bytes([opcode]) + struct.pack("<i", destination - source - 5)


def _stub() -> bytes:
    # At the original ACT35 frame's ESP, +0x28 holds the validated child VID
    # descriptor (44DFD5). Both fallback calls have just pushed one argument.
    # CALL adds its return address; our PUSHFD/PUSH ECX add another eight bytes.
    # Consequently [ESP+0x38] here is exactly that descriptor, not a sprite.
    # Neither a new stack frame nor an absolute address/relocation is needed.
    code = bytearray.fromhex("9c518b4c2438f78130050000001000007407")
    code.extend(bytes.fromhex("599d"))
    code.extend(_relative(0xE9, CAVE_VA + len(code), SHARED_RNG_VA))
    code.extend(bytes.fromhex("599d"))
    code.extend(_relative(0xE9, CAVE_VA + len(code), LOCAL_RNG_VA))
    return bytes(code)


STUB = _stub()
# The cave is verified zero padding in the existing executable .text raw
# allocation. Extend only VirtualSize to cover it explicitly. RawSize, section
# alignment, section permissions, SizeOfImage and all relocations stay intact.
SPAWN_PATCHES = (
    (IMAGE_BASE + TEXT_VIRTUAL_SIZE_FIELD,
     struct.pack("<I", ORIGINAL_TEXT_VIRTUAL_SIZE),
     struct.pack("<I", CAVE_VA + len(STUB) - (IMAGE_BASE + 0x1000))),
    (CAVE_VA, b"\0" * len(STUB), STUB),
    *tuple((va, _relative(0xE8, va, LOCAL_RNG_VA),
            _relative(0xE8, va, CAVE_VA)) for va in HOOK_VAS),
)

# These guards explain the otherwise opaque stack-offset assumption. The
# normalized whole-file hash independently pins every original instruction.
CONTEXT_GUARDS = (
    (0x44DFBF, bytes.fromhex("85c00f8485030000")),  # child must be non-null
    (0x44DFD5, bytes.fromhex("89442428")),          # cache child descriptor
    (0x44E01E, bytes.fromhex("8b4d44")),            # X uses parent descriptor
    (0x44E025, bytes.fromhex("8b9130050000f7d885d7507407")),
    (0x44E05F, bytes.fromhex("8b4d44")),            # Y uses parent descriptor
    (0x44E066, bytes.fromhex("8b8130050000f7de85c7567407")),
)


def patch(image: bytes) -> tuple[bytes, dict]:
    """Return exact patched bytes and metadata; never read/write a process.

    Accepts only the original PE plus known isolation/story modifications.
    Already or partially applied spawn patches, fixture/trace additions, and
    every other changed byte are rejected. Callers can normalize SPAWN_PATCHES
    when validating later diagnostic compositions.
    """
    if not isinstance(image, bytes):
        raise TypeError("Expected executable bytes")
    for va, expected in CONTEXT_GUARDS:
        at = va - IMAGE_BASE
        if image[at:at + len(expected)] != expected:
            raise ValueError(f"Unsupported ACT35 calling context at {va:#x}")
    for va, before, _ in SPAWN_PATCHES:
        at = va - IMAGE_BASE
        if image[at:at + len(before)] != before:
            raise ValueError(f"Spawn patch is already applied or bytes are unknown at {va:#x}")
    normalized = bytearray(image)
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
        raise ValueError("Unsupported spawn executable: normalized SHA-256 mismatch")
    output = bytearray(image)
    for va, before, after in SPAWN_PATCHES:
        if len(before) != len(after):
            raise AssertionError("Spawn patch must preserve file size")
        at = va - IMAGE_BASE
        output[at:at + len(before)] = after
    result = bytes(output)
    return result, {
        "feature": FEATURE,
        "baseline_sha256": BASELINE_SHA256,
        "input_sha256": hashlib.sha256(image).hexdigest(),
        "output_sha256": hashlib.sha256(result).hexdigest(),
        "scope": "Isolated co-op campaign ACT_BUILD_UNIT negative-coordinate scatter only",
        "rng_policy": "Shared RNG if parent OR child VID is ImportantForSync; otherwise original local RNG",
        "preserved": ["original parent-important branch", "inclusive random bound",
                      "coordinate formula and scatter range", "spawn order and count",
                      "child VID properties", "native parent/child importance warning"],
        "cached_child_descriptor_frame_offset": 0x28,
        "stub_descriptor_esp_offset": 0x38,
        "stub_va": hex(CAVE_VA), "stub_size": len(STUB),
        "calling_convention": "Preserve ECX/EFLAGS for RNG entry; restore ESP then tail-jump to unchanged native RNG",
        "section_change": "Extend .text VirtualSize within existing zero raw padding; no new section/relocations",
        "accepted_input_patches": accepted,
        "patches": [{"va": hex(va), "before": before.hex(), "after": after.hex(),
                     "location": "PE section header" if va == IMAGE_BASE + TEXT_VIRTUAL_SIZE_FIELD else "code"}
                    for va, before, after in SPAWN_PATCHES],
    }
