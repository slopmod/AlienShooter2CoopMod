"""Campaign browser layout composed from the original native menu records.

The original LAN frame, fonts, list hit regions and button animations remain
native resources.  Extra tabs and paging arrows are cloned from pinned stock
menus; no external renderer or replacement textures are involved.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct

from old_native_ui_resources import MenuResource


STOCK_HASHES = {
    'Maps/netselectgame.men': 'eb4c9853658d9d3cda6964a0256564bb9c7a7ea1e401b4296ccca127d412dcf3',
    'Maps/createplayer.men': '30059815cd165fab3c229c0db0a4f95b1e046f34bf24a2934c425eddec7e4e33',
}
TAB_NAMES = ('NewTab', 'SavesTab', 'JoinTab')
PAGE_NAMES = ('PrevPage', 'NextPage', 'PageLabel')
TAB_CENTERS = (208., 400., 592.)
ROW_ORIGIN = (132., 190.)
ROW_PITCH = 20.


def _name(record: bytes) -> str:
    return record[60:].split(b'\0', 1)[0].decode('cp1251')


def _vid(record: bytes) -> int:
    return struct.unpack_from('<I', record, 4)[0]


def _copy(record: bytes, saved_id: int, name: str, x: float, y: float,
          text: str | None = None, vid: int | None = None,
          scale: tuple[float, float] | None = None,
          direction: int | None = None) -> bytes:
    """Position at 800x600 screen coordinates, retaining native record flags.

    The destination header has editor origin (-112,-84), viewport 1024x768:
    its natural projection therefore has the same (400,300) screen center.
    Text is a separate native sprite and retains its original alignment flags.
    """
    result = bytearray(record[:60])
    struct.pack_into('<I', result, 0, saved_id)
    if vid is not None:
        struct.pack_into('<I', result, 4, vid)
    z = struct.unpack_from('<f', result, 16)[0]
    struct.pack_into('<2f', result, 8, float(x), float(y) + z)
    if scale is not None:
        struct.pack_into('<2f', result, 36, *scale)
    if direction is not None:
        struct.pack_into('<I', result, 20, direction)
    result.extend(name.encode('cp1251') + b'\0')
    if text is not None:
        result.extend(text.encode('cp1251') + b'\0')
    return bytes(result)


def prepare(old_root: Path) -> bytes:
    """Return the new netselectgame.men, without changing the source game.

    Runtime widget contract:
    * Existing ExitButton/StartButton/JoinButton/SearchButton/HostAddr remain.
    * NewTab/SavesTab/JoinTab use font4 captions named <button>Text.
    * List text remains font5, direction 1..14; selection is VID98, 0..13.
    * BrowserTitle is the only font8 sprite; BrowserDetails is its named body.
    * AddressInput retains VID718/direction64; HostAddr is the editable text.
    * PrevPage/NextPage/PageLabel have their own band below all fourteen rows.
    * StartButton and JoinButton share one primary-action position; callers
      show only the action relevant to the current screen.
    * The stock frame alone widens to 125%; fonts retain their native size.
    * Tab markers are named non-list VID98 directions100..102. Callers stop
      their click animation, set the selected frame and control visibility.
    """
    menus = {}
    for path, expected in STOCK_HASHES.items():
        raw = (Path(old_root) / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Unsupported original campaign layout asset: ' + path)
        menus[path] = MenuResource.read(raw)
    menu = menus['Maps/netselectgame.men']
    if struct.unpack_from('<4f', menu.header, 20) != (1024., 768., -112., -84.):
        raise ValueError('Original campaign layout projection differs')
    original = list(menu.records[:-1])
    named = {_name(record): record for record in original if _name(record)}
    button = named['SearchButton']
    caption = next(record for record in original
                   if _vid(record) == 4 and b'NetSearch\0' in record[60:])
    row_text = next(record for record in original if _vid(record) == 5)
    row_background = next(record for record in original if _vid(record) == 98)
    creation_records = menus['Maps/createplayer.men'].records[:-1]
    arrows = [next(record for record in creation_records if _vid(record) == vid)
              for vid in (716, 717)]

    # Keep the original native animation/hit-region records, but place them on
    # one deliberate grid. Widening only the frame and row backgrounds gives
    # save dates and instructions room without scaling native font glyphs.
    records = []
    footer = {'ExitButton': (205., 'Назад'),
              'StartButton': (595., 'Создать игру'),
              'JoinButton': (595., 'Подключиться'),
              'SearchButton': (400., 'Обновить')}
    captions = {b'MainMenu\0': 'ExitButton', b'NetStart\0': 'StartButton',
                b'Join\0': 'JoinButton', b'NetSearch\0': 'SearchButton'}
    for record in original:
        saved_id = struct.unpack_from('<I', record)[0]
        vid, name = _vid(record), _name(record)
        direction = struct.unpack_from('<I', record, 20)[0]
        if name in footer:
            record = _copy(record, saved_id, name, footer[name][0], 515., scale=(1.2, 1.))
        elif vid == 4 and any(key in record[60:] for key in captions):
            target = next(value for key, value in captions.items() if key in record[60:])
            record = _copy(record, saved_id, target + 'Text', footer[target][0], 517., footer[target][1])
        elif vid == 2231:
            record = _copy(record, saved_id, 'BrowserFrame', 400., 294., scale=(1.25, 1.))
        elif name == 'HostAddr':
            record = _copy(record, saved_id, name, 136., 151., '')
        elif vid == 718 and direction == 64:
            record = _copy(record, saved_id, 'AddressInput', 290., 151., scale=(2.2, .8))
        elif vid == 5 and 1 <= direction <= 14:
            record = _copy(record, saved_id, 'BrowserRow' + str(direction - 1),
                           ROW_ORIGIN[0], ROW_ORIGIN[1] + ROW_PITCH * (direction - 1), '')
        elif vid == 98 and 0 <= direction < 14:
            record = _copy(record, saved_id, 'BrowserSelection' + str(direction),
                           282., ROW_ORIGIN[1] + ROW_PITCH * direction + 1.,
                           scale=(1.25, ROW_PITCH / 26.))
        elif vid == 8:
            record = _copy(record, saved_id, 'BrowserTitle', 472., 124., '')
        elif vid == 3 and name == 'PlayerList':
            record = _copy(record, saved_id, 'BrowserDetails', 472., 148., '')
        elif vid == 3 and b'ESRB\0' in record[60:]:
            continue
        records.append(record)

    # Tabs sit inside the original frame's top band. Unique serialized IDs
    # prevent aliasing cloned sprites during MenuLoad. Marker directions do
    # not overlap the fourteen native list-selection directions.
    saved_id = 0x0C000001
    for index, (name, x, text) in enumerate(zip(TAB_NAMES, TAB_CENTERS,
                             ('Новая игра', 'Сохранения', 'Подключение'))):
        records.append(_copy(button, saved_id, name, x, 82., scale=(1.3, 1.)))
        records.append(_copy(caption, saved_id + 1, name + 'Text', x, 84., text))
        records.append(_copy(row_background, saved_id + 2, name + 'Mark', x, 103.,
                             scale=(.69, .12), direction=100 + index))
        saved_id += 3
    records.append(_copy(caption, saved_id, 'CampaignHeading', 400., 30.,
                         'СЕТЕВАЯ КАМПАНИЯ', vid=4))
    saved_id += 1
    records.append(_copy(row_text, saved_id, 'ListHeading', 132., 124., '', direction=0))
    saved_id += 1
    records.append(_copy(row_text, saved_id, 'AddressHint', 132., 174., '', vid=3, direction=0))
    saved_id += 1
    for name, x, arrow in zip(PAGE_NAMES[:2], (150., 420.), arrows):
        records.append(_copy(arrow, saved_id, name, x, 477.))
        saved_id += 1
    # Clone the centered caption's alignment flags rather than a body label.
    records.append(_copy(caption, saved_id, 'PageLabel', 282., 477., '', vid=3))
    result = MenuResource(menu.header, menu.sprite_header,
                          tuple(records) + (b'\xff\xff\xff\xff',)).encode()
    if MenuResource.read(result).encode() != result:
        raise ValueError('Campaign menu layout failed lossless roundtrip')
    return result
