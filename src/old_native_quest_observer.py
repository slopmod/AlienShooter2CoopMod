"""Resolve the original campaign quest ID to the native list-based getter."""
import hashlib
import re


SOURCE_SHA256 = '5606461fbe14c683a323480b8e3b01203309153598d57ef57355ad20083ad01f'
QUEST_FIELDS = {
    'story_bunker_objective': (34, 30),
    'story_elevator_locked': (35, 31),
    'story_elevator_unlocked': (36, 32),
    'story_access_key_taken': (37, 33),
    'story_find_baker': (38, 34),
}


def prepare(old_root):
    source = (old_root / 'levels.cfg').read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported levels.cfg quest order')
    ids = re.findall(r'^\s*Quest\s*=\s*(\d+_\d+_\d+)', source.decode('cp1251'), re.M)
    group = [quest for quest in ids if quest.startswith('1_1_')]
    if len(group) != 97:
        raise ValueError('Original campaign quest list guard failed')
    fields = {}
    for field, (number, expected_index) in QUEST_FIELDS.items():
        quest_id = '1_1_' + str(number)
        if group.count(quest_id) != 1 or group.index(quest_id) != expected_index:
            raise ValueError('Original quest list guard failed: ' + quest_id)
        fields[field] = {'quest_id': quest_id, 'group_index': 0, 'subquest_index': expected_index}
    return {
        'feature': 'old-campaign-quest-observer-v2',
        'source_file': 'levels.cfg', 'source_sha256': SOURCE_SHA256,
        'field': 'story_bunker_objective', 'quest_id': '1_1_34',
        'getter': 'EXT_GETQUESTSSTATE', 'group_index': 0,
        'subquest_index': group.index('1_1_34'),
        'fields': fields,
        'read_only': True,
    }
