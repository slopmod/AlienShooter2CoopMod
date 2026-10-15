"""Bounded summaries of native evidence; no process attachment or game writes."""
from pathlib import Path


MARKERS = {
    'queue_overflow': 'Received messages stack is full',
    'rng_divergence': 'Synchro rand error',
    'input_order_error': 'Incorrect order message',
    'peer_disconnect': 'DPN_MSGID_DESTROY_PLAYER',
}


def summarize_log(path):
    result = {name: {'count': 0, 'first': None, 'last': None} for name in MARKERS}
    try:
        with Path(path).open('r', encoding='cp1251', errors='replace') as stream:
            for line in stream:
                for name, marker in MARKERS.items():
                    if marker in line:
                        row = result[name]
                        row['count'] += 1
                        sample = line.strip()[:512]
                        if row['first'] is None:
                            row['first'] = sample
                        row['last'] = sample
    except OSError as error:
        return {'available': False, 'error': str(error), 'events': result}
    return {'available': True, 'events': result,
            'has_sync_errors': any(result[name]['count'] for name in
                                   ('queue_overflow', 'rng_divergence', 'input_order_error'))}
