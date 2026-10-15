"""Localize mod-authored native UI after composition, before profile hashing.

The original script patch guards deliberately keep their canonical Russian
sources. This last pass changes only curated quoted UI literals and generated
menu captions. Original dictionary lookups, item names, IDs, comments, binary
record properties and native game text remain untouched. Different languages
remain different multiplayer profiles; both peers must select the same one.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import struct

from old_native_ui_resources import MenuResource

CATALOG = Path(__file__).with_name('locales') / 'native-ui.json'
# A token stream, rather than text replacement, keeps comments and escaped
# quotes out of the translation surface. Store literal contents as LGC source
# spelling in the catalog (including the game's escaped line breaks).
TOKENS = re.compile(r'//[^\r\n]*|/\*[\s\S]*?\*/|"((?:[^"\\]|\\.)*)"|[{}]')
CYRILLIC = re.compile(r'[\u0400-\u04ff]')
ITEM_TITLES = re.compile(r'(?m)^[ \t]*(?:static\s+)?string\s+OldHudItemTitles\s*\[\s*\d*\s*\]\s*=\s*\{')
LEGACY_ITEM_TITLES = re.compile(r'(?m)^OldShopItemTitle\(string key\)\s*\{')


def _protected_ranges(source: str) -> list[tuple[int, int]]:
    """The item title table is copied from Text/Weapon.txt, not mod prose."""
    ranges = []
    for pattern in (ITEM_TITLES, LEGACY_ITEM_TITLES):
        for match in pattern.finditer(source):
            depth = 1
            for token in TOKENS.finditer(source, match.end()):
                if token.group(0) == '{':
                    depth += 1
                elif token.group(0) == '}':
                    depth -= 1
                    if not depth:
                        ranges.append((match.start(), token.end()))
                        break
            else:
                raise ValueError('Unterminated original item title block')
    return ranges


def _catalog(path: Path = CATALOG) -> tuple[dict, str]:
    raw = path.read_bytes()
    data = json.loads(raw)
    if data.get('schema') != 1:
        raise ValueError('Unsupported native UI translation catalog')
    seen = set()
    for entry in data['messages']:
        key = entry['source']
        if key in seen or not entry['files']:
            raise ValueError('Duplicate or unscoped native UI translation: ' + key)
        seen.add(key)
        for language in ('ru', 'en'):
            text = entry[language]
            text.encode('cp1251')
            # These are source string contents, so unescaped quotes/newlines
            # would change the compiled script, rather than its presentation.
            literal = TOKENS.fullmatch('"' + text + '"')
            if ('\n' in text or '\r' in text or '\0' in text
                    or literal is None or literal.group(1) != text):
                raise ValueError('Unsafe native UI literal: ' + key)
    return data, hashlib.sha256(raw).hexdigest()


def _script(path: str, raw: bytes, language: str, data: dict) -> tuple[bytes, int, int]:
    source = raw.decode('cp1251')
    protected = _protected_ranges(source)
    lookup = {entry['source']: entry[language] for entry in data['messages']
              if path in entry['files']}
    stock = set(data.get('original_literals', {}).get(path, []))
    translated = {entry[language] for entry in data['messages'] if path in entry['files']}
    count = preserved = 0
    missing = []

    def replace(match: re.Match) -> str:
        nonlocal count, preserved
        literal = match.group(1)
        if literal is None:
            return match.group(0)
        if any(start <= match.start() < end for start, end in protected):
            preserved += 1
            return match.group(0)
        if literal in lookup:
            count += 1
            return '"' + lookup[literal] + '"'
        if CYRILLIC.search(literal) and literal not in stock and literal not in translated:
            line = source.count('\n', 0, match.start()) + 1
            missing.append(f'{path}:{line}: {literal}')
        return match.group(0)

    result = TOKENS.sub(replace, source)
    if missing:
        raise ValueError('Missing mod UI translations:\n' + '\n'.join(missing[:30]))
    return result.encode('cp1251'), count, preserved


def _menu(path: str, raw: bytes, language: str, data: dict) -> tuple[bytes, int]:
    controls = data.get('menu_controls', {}).get(path)
    if not controls:
        return raw, 0
    resource = MenuResource.read(raw)
    if struct.unpack_from('<I', resource.header, 16)[0] != 19:
        raise ValueError('Unsupported localized menu record version: ' + path)
    lookup = {entry['source']: entry[language] for entry in data['messages']
              if path in entry['files']}
    translated = set(lookup.values())
    records, count, found = [], 0, set()
    for record in resource.records[:-1]:
        name, tail = record[60:].split(b'\0', 1)
        control = name.decode('cp1251')
        if control in controls:
            found.add(control)
            if not tail or not tail.endswith(b'\0') or b'\0' in tail[:-1]:
                raise ValueError('Unsupported caption record: ' + path + '/' + control)
            literal = tail[:-1].decode('cp1251')
            if literal in lookup:
                record = record[:60] + name + b'\0' + lookup[literal].encode('cp1251') + b'\0'
                count += 1
            elif literal not in translated:
                raise ValueError('Missing mod menu translation: ' + path + '/' + control + ': ' + literal)
        records.append(record)
    if found != set(controls):
        raise ValueError('Localized menu controls missing: ' + path + ': ' + ', '.join(sorted(set(controls) - found)))
    result = MenuResource(resource.header, resource.sprite_header,
                          tuple(records) + resource.records[-1:]).encode()
    return result, count


def apply(files: dict[str, bytes], language: str) -> dict:
    """Translate a composed file set in place; fail atomically on missing text.

    Call before bind_scripts and before disk writes. Partial dictionaries are
    supported for the final regenerated lobby. Paths are case-insensitive as
    in the original engine. Existing translated input is accepted unchanged.
    """
    if language not in ('en', 'ru'):
        raise ValueError('Unsupported mod UI language: ' + str(language))
    data, catalog_hash = _catalog()
    result, counts = {}, {}
    original_item_literals = 0
    for path, raw in files.items():
        normalized = str(path).replace('\\', '/').lower()
        if normalized.endswith('.lgc'):
            output, count, preserved = _script(normalized, raw, language, data)
            original_item_literals += preserved
        elif normalized.endswith('.men'):
            output, count = _menu(normalized, raw, language, data)
        else:
            continue
        if count:
            counts[path] = count
        if output != raw:
            result[path] = output
    files.update(result)
    return {'feature': 'native-mod-ui-ru-en-v1', 'language': language,
            'catalog_sha256': catalog_hash, 'catalog_messages': len(data['messages']),
            'localized_files': counts, 'literal_occurrences': sum(counts.values()),
            'original_item_literals_preserved': original_item_literals,
            'same_language_peers_required': True, 'missing_translations': []}
