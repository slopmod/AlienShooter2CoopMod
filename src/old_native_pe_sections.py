"""Section-order accounting for the guarded OLD executable patch chain.

This checks section names and placement only. The trigger and compiler-capacity
normalizers must verify their exact payloads before baseline hash validation.
"""
from collections.abc import Mapping


BASE_SECTION_NAMES = (b'.text', b'.rdata', b'.data', b'.rsrc', b'.reloc')
PARTY_SECTION_NAME = b'.oparty'


def logical_section_count(sections):
    """Exclude the optional .oparty at index5 and .ocap before diagnostics.

    Accept the tuple records used by production patchers and the named mappings
    used by the RNG diagnostic. An arbitrary extra section is never discounted.
    """
    names = []
    for section in sections:
        name = section['name'] if isinstance(section, Mapping) else section[0]
        if not isinstance(name, bytes) or not 1 <= len(name) <= 8:
            raise ValueError('Invalid PE section name')
        names.append(name.rstrip(b'\0'))
    if tuple(names[:5]) != BASE_SECTION_NAMES:
        raise ValueError('Unsupported original PE section prefix')
    party_indices = [i for i, name in enumerate(names) if name == PARTY_SECTION_NAME]
    if party_indices and party_indices != [5]:
        raise ValueError('The optional .oparty section must occur once at index5')
    capacity_indices = [i for i, name in enumerate(names) if name == b'.ocap']
    if capacity_indices:
        if len(capacity_indices) != 1 or capacity_indices[0] < 5:
            raise ValueError('The optional .ocap section must occur once after the original sections')
        if any(name not in (b'.osave', b'.oinput', b'.orng') for name in names[capacity_indices[0] + 1:]):
            raise ValueError('Only diagnostics may follow compiler capacity')
    save_indices = [i for i, name in enumerate(names) if name == b'.osave']
    if save_indices and (len(save_indices) != 1 or not capacity_indices or save_indices[0] != capacity_indices[0] + 1):
        raise ValueError('Checkpoint section must immediately follow compiler capacity')
    # Layout only: the capacity normalizer verifies the complete generated
    # section and all hooks before any predecessor/hash is accepted.
    return len(names) - bool(party_indices) - bool(capacity_indices) - bool(save_indices)
