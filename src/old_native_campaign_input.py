"""Keep the stock network weapon controls and separate the two RPG panels."""
import hashlib


FEATURE = 'old-native-campaign-input-v1'
INPUT_SHA256 = '81b94981245757edbb793e23b4e82536b1058b4eeaecf9080fc6a4211cdba344'


def patch(source):
    if not isinstance(source, bytes) or hashlib.sha256(source).hexdigest() != INPUT_SHA256:
        raise ValueError('Expected exact original input.cfg for campaign controls')
    changes = (
        (b"IA_SHOW_INVENTORY,\t\tIM_KEYDOWN,\t\t\t'C'",
         b"IA_SHOW_CHARSCREEN,\t\tIM_KEYDOWN,\t\t\t'C'"),
        (b"IA_SHOW_DEBUG_CONSOLE,\tIM_KEYDOWN,\t\t\t'Q'",
         b";IA_SHOW_DEBUG_CONSOLE,\tIM_KEYDOWN,\t\t\t'Q'"),
    )
    output = source
    for before, after in changes:
        if output.count(before) != 1:
            raise ValueError('Campaign input binding anchor changed')
        output = output.replace(before, after)
    return output, {
        'feature': FEATURE, 'input_sha256': INPUT_SHA256,
        'output_sha256': hashlib.sha256(output).hexdigest(),
        'inventory': 'I / middle mouse', 'character': 'C',
        'weapons': 'Original synchronized 1..5, Q/E and mouse wheel',
        'debug_console_q_disabled': True,
    }
