"""Local mod language preference, shared by the installer, launcher and worker.

This selects only mod-authored presentation. It does not change the supported
game executable, stock resources or native checkpoint representation.
"""
from __future__ import annotations

import os

from old_native_paths import MOD


LANGUAGES = ('en', 'ru')
DEFAULT_LANGUAGE = 'en'
LANGUAGE_FILE = MOD / 'campaign-language.txt'


def validate_language(value: str) -> str:
    value = str(value).strip().lower()
    if value not in LANGUAGES:
        raise ValueError('Unsupported mod language; choose English (en) or Russian (ru).')
    return value


def get_language() -> str:
    value = os.environ.get('AS2_COOP_LANGUAGE')
    if value is None:
        try:
            value = LANGUAGE_FILE.read_text('utf-8-sig').strip()
        except FileNotFoundError:
            value = DEFAULT_LANGUAGE
    return validate_language(value)


def set_language(language: str) -> str:
    language = validate_language(language)
    temporary = LANGUAGE_FILE.with_suffix('.txt.tmp')
    temporary.write_bytes((language + '\n').encode('ascii'))
    temporary.replace(LANGUAGE_FILE)
    os.environ['AS2_COOP_LANGUAGE'] = language
    return language


def tr(ru: str, en: str, language: str | None = None) -> str:
    return ru if validate_language(language or get_language()) == 'ru' else en


def guide_name(language: str | None = None) -> str:
    return 'INSTALL_' + validate_language(language or get_language()).upper() + '.txt'
