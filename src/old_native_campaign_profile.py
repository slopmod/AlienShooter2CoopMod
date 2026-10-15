"""One explicit production composition and its peer compatibility identity."""
import hashlib
import json
import re


def production_options():
    # Return a fresh mapping: diagnostic callers may add controls/limits,
    # but must not mutate a global profile used by the normal launcher.
    return dict(campaign=True, transition=True, shared_money=True,
                campaign_shop=True, campaign_rewards=True, admin_portal=True,
                shared_portals=True, registered_interactions=True, level02_finish=True,
                gameplay_hud=True, campaign_menu=True, campaign_progression=True)


def identity(portals, items, triggers, *, level02_finish=None, gameplay_hud=None, commands=None,
             compiler_capacity=None, progression=None, checkpoint=None):
    required = (portals['catalog_sha256'], portals['output_sha256'],
                items['output_sha256'], triggers['output_sha256'])
    if not all(isinstance(v, str) and re.fullmatch(r'[0-9a-f]{64}', v) for v in required):
        raise ValueError('Production identity requires complete guarded build hashes')
    data = {'schema': 1, 'portal_catalog': portals['catalog_sha256'],
            'portal_script': portals['output_sha256'],
            'item_feature': items['feature'], 'item_code': items['output_sha256'],
            'trigger_feature': triggers['feature'], 'trigger_code': triggers['output_sha256']}
    if level02_finish is not None:
        for name in ('output_sha256', 'level02_hook'):
            value = (level02_finish[name]['output_sha256'] if name == 'level02_hook'
                     else level02_finish[name])
            if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
                raise ValueError('Production identity requires complete Level02 finish hashes')
        data.update(schema=2, level02_finish_feature=level02_finish['feature'],
                    level02_finish_script=level02_finish['output_sha256'],
                    level02_script=level02_finish['level02_hook']['output_sha256'])
    for key, component in (('gameplay_hud', gameplay_hud), ('commands', commands),
                           ('compiler_capacity', compiler_capacity), ('progression', progression),
                           ('checkpoint', checkpoint)):
        if component is not None:
            value = component['output_sha256']
            if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
                raise ValueError('Production identity requires complete ' + key + ' hashes')
            data.update(schema=3)
            data[key + '_feature'] = component['feature']
            data[key + '_code'] = value
    if checkpoint is not None:
        from old_native_campaign_checkpoint import HELPER, SCRIPT, DECLARATIONS
        data['checkpoint_protocol'] = hashlib.sha256((HELPER + SCRIPT + DECLARATIONS).encode('utf-8')).hexdigest()
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'components': data, 'sha256': digest, 'session_name': 'AS2_CAMPAIGN_' + digest[:12]}


def bind_scripts(profile, files, *, language=None, dialogue_timing=None):
    """Include final gameplay/lobby scripts without a circular session-name hash.

    The automatic probe lobby embeds a build role and the observer embeds a
    diagnostic capture limit. The automatic lobby is unused by manual play;
    the observer only records passive diagnostics. The manual
    lobby is identical for both peers and is included, with only its generated
    session token normalized. Local installation paths and video settings never
    enter this network identity.
    """
    excluded = {'Maps/old_game_lobby.lgc', 'Maps/old_game_observe.lgc'}
    previous = profile['session_name'].encode('ascii')
    hashes = {}
    for name, content in sorted(files.items()):
        if name in excluded or not (name.lower().endswith('.lgc')
                                     or name in ('Weapon.cfg', 'levels.cfg')):
            continue
        if name in ('Maps/old_campaign_lobby.lgc', 'Maps/old_campaign_retry.lgc'):
            if previous not in content:
                raise ValueError('Campaign lobby is missing its compatibility identity: ' + name)
            content = content.replace(previous, b'AS2_CAMPAIGN_PROTOCOL')
        hashes[name] = hashlib.sha256(content).hexdigest()
    if 'Maps/old_campaign_lobby.lgc' not in hashes:
        raise ValueError('Manual campaign compatibility requires its final lobby')
    data = dict(profile['components'], schema=4, runtime_scripts=hashes)
    if language is not None:
        from old_native_localization import validate_language
        data.update(schema=5, mod_language=validate_language(language))
    if dialogue_timing is not None:
        value = dialogue_timing['canonical_sha256']
        if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
            raise ValueError('Campaign compatibility requires canonical dialogue timing')
        data.update(schema=5, dialogue_timing=value)
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'components': data, 'sha256': digest, 'session_name': 'AS2_CAMPAIGN_' + digest[:12]}
