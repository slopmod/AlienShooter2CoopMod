"""Explicit mission scope shared by native guards and campaign generators.

Adding a number here is not sufficient: a pinned map catalog, entry and finish
must also be installed. Unknown physical paths always retain stock behavior.
"""
from dataclasses import dataclass
import os
from pathlib import Path


def reloaded_root():
    """Optional user-owned content source; never substitutes the native engine."""
    from old_native_installation import MOD, read_settings
    configured = os.environ.get('AS2_COOP_RELOADED_DIR') or read_settings().get('reloaded_game')
    if configured == 'disabled':
        return None
    if configured:
        # Explicit selection must fail validation if absent/unsupported, never
        # silently remove stages from a user's campaign.
        return Path(configured).expanduser().resolve()
    from old_native_bundled_content import bundled_root
    bundled = bundled_root()
    if bundled is not None:
        return bundled
    candidates = (MOD.parent, MOD.parent.parent / 'Alien Shooter 2')
    return next((p.resolve() for p in candidates if all(
        (p / f'Maps/Level_07_{part}.map').is_file() for part in (2, 3))), None)


RELOADED_ROOT = reloaded_root()
RELOADED_ENABLED = RELOADED_ROOT is not None


@dataclass(frozen=True)
class Mission:
    number: int
    map_sha256: str
    finish_money: int
    shop: tuple[int, int] | None = None
    physical_name: str | None = None
    native_number: int | None = None
    entry_shop: bool = False
    ending_only: bool = False
    additional_shops: tuple[tuple[int, int], ...] = ()

    @property
    def shop_locations(self):
        return (() if self.shop is None else (self.shop,)) + self.additional_shops

    @property
    def path(self):
        return 'Maps/' + (self.physical_name or f'Level_{self.number:02d}') + '.map'

    @property
    def native(self):
        return self.number if self.native_number is None else self.native_number

    @property
    def label(self):
        return {72: '7.2', 73: '7.3'}.get(self.number, str(self.number))


BASE_MISSIONS = (
    Mission(1, '5bdc5f4ff57e06feeb7b02d36c09d76e01ef5d258b05e3c45c4e47523df694ec', 0),
    Mission(2, 'e52d86951d508743ed625ef0b4910e7ba2c4ce633e3e94029c179a466186ff79', 1000, (3665, 8506)),
    Mission(3, '78b8c6487848001346cc9f01a5e9b56612831a9378e23dcb1869f2ecd9aabebd', 2000, (6482, 5723)),
    Mission(4, '9dfcbf9ac0863c90a86d0693d29c760b3c77108e5ff21bc3c7f7ed82a5028212', 3500, (7917, 8043)),
    Mission(5, '7aa6e05d30f0938e9118a0b3bd8b7b24696dbe16b63d4899fef226567777463e', 4000, (12362, 12305)),
    Mission(6, 'e173e01fa6169eeb77222e03686a02ef465d0277069c4f7c2b2539ce740fb72b', 6000, (1859, 11739)),
    Mission(7, '78ca07180e0d2b17f9bf347dbd68c2778b926b2afee445c03ecad892d775821a', 0),
    Mission(8, '2ee10cc19a10642650b23d39d6bf253a29743265cd435ed29535f00351d196f7', 10000),
    Mission(9, '7e7c7c226c703b12ec5d1c202f502d3eac29c4a81678a09720081a4c46f6847a', 12000, (2289, 2481)),
    Mission(10, '81cf151f17e34229d344893fd38b82eb6be22387d61702f5deedd075d647668d', 20000, (2629, 2849)),
    Mission(11, '7fdb197a19349707372351550ee637a81015e6dce992240cd49b33b7a4587cde', 30000, (10070, 7743)),
    Mission(12, 'd28e08467d06689f55143d9822c767c039d6a023323e6f1f79be6665f853e076', 40000),
    Mission(13, '83d5e267e1069a7d6861737f8807b88a5180db60ecd39d2823818c0ca788fd0e', 50000, (359, 6287)),
    Mission(14, 'b15955fe7ecfb1c9343a7d008b381cbbe3b0e09ceee82c177119d7ab3b8ab875', 70000, entry_shop=True),
    Mission(15, '699f7f7c3b3635c80138f9b2e379f2d981bcbc500c60cfaf776a1853eef7c3e4', 300000,
            entry_shop=True, ending_only=True),
)
RELOADED_MISSIONS = (
    Mission(72, '39c5c2388db497d2a86ada94ffd505d24ff715306801c30143c939b680246d18', 0,
            shop=(11741, 12213), additional_shops=((22092, 11459),),
            physical_name='Level_07_2', native_number=7),
    Mission(73, '0c7b10edb58b1730b9e05bd62fcdefb8afe15ce719e9f29d683841bbc0443608', 0,
            shop=(3542, 494), physical_name='Level_07_3', native_number=7),
)
def campaign_missions(include_reloaded):
    """Insert optional road stages at their story position, never at the end."""
    result = []
    for mission in BASE_MISSIONS:
        result.append(mission)
        if include_reloaded and mission.number == 7:
            result.extend(RELOADED_MISSIONS)
    return tuple(result)


MISSIONS = campaign_missions(RELOADED_ENABLED)
MAP_NUMBERS = tuple(m.number for m in MISSIONS)
SHOP_NUMBERS = tuple(dict.fromkeys(m.native for m in MISSIONS if m.shop_locations or m.entry_shop))


def mission_by_number(number):
    return next(m for m in MISSIONS if m.number == number)


def mission_source(root, relative):
    if RELOADED_ENABLED and relative.lower() in {
        'maps/level_07_2.map', 'maps/level_07_3.map',
        'maps/level_07_2.lgc', 'maps/level_07_3.lgc',
    }:
        return RELOADED_ROOT / relative
    return Path(root) / relative


def emit_native_map_guard(c, path_register, reject, *, prefix='campaign_map'):
    """Case-insensitive exact NUL-terminated path; EAX returns mission number.

    Only EAX/flags are clobbered. reject(condition) emits a branch to the
    caller's existing refusal path; no native calls or memory writes occur.
    """
    # Check the common path once, then the explicit two-digit allowlist.
    # Adding missions grows only the tiny number table, not 17 path compares.
    def exact(offset, pattern):
        # Word comparisons keep additional physical paths within existing code
        # reservations; only letters are folded, separators remain exact.
        while pattern:
            size = 4 if len(pattern) >= 4 else 1
            part, pattern = pattern[:size], pattern[size:]
            if size == 4:
                c.load('eax', path_register, offset)
            else:
                c.emit('0fb6'); c.mem('eax', path_register, offset)
            mask = int.from_bytes(bytes(32 if 97 <= v <= 122 else 0 for v in part), 'little')
            if mask: c.alu(1, 'eax', mask)
            c.alu(7, 'eax', int.from_bytes(part, 'little')); reject('85')
            offset += size
    exact(0, b'maps\\level_')
    # Ordinary two-digit map names retain exact NUL termination. Extra stages
    # use the original physical names but the OLD engine's quest level seven.
    c.emit('0fb6'); c.mem('eax', path_register, 13)
    c.alu(7, 'eax', ord('_'))
    if RELOADED_ENABLED:
        c.jump(prefix + '_extra', '84')
    exact(13, b'.map\0')
    c.emit('0fb7'); c.mem('eax', path_register, 11)
    for mission in BASE_MISSIONS:
        c.alu(7, 'eax', int.from_bytes(f'{mission.number:02d}'.encode(), 'little'))
        c.jump(f'{prefix}_tens_{mission.number // 10}', '84')
    reject('85')
    if RELOADED_ENABLED:
        c.label(prefix + '_extra')
        c.emit('0fb7'); c.mem('eax', path_register, 11)
        c.alu(7, 'eax', int.from_bytes(b'07', 'little')); reject('85')
        exact(15, b'.map\0')
        c.emit('0fb6'); c.mem('eax', path_register, 14)
        c.alu(7, 'eax', ord('2')); c.jump(prefix + '_extra_seven', '84')
        c.alu(7, 'eax', ord('3')); reject('85')
        c.label(prefix + '_extra_seven')
        c.ri('eax', 7)
        c.jump(prefix + '_accepted')
    # Preserve the exact allowlist above, but share return blocks by decimal
    # tens. The accepted ones digit is already validated by its full ASCII
    # word comparison. MOVZX + signed imm8 SUB converts it without another
    # register, stack writes or a return block for every individual mission.
    # 01..09: 'n'-48; 10..19: 'n'-38. This also covers sparse future groups.
    groups = sorted({mission.number // 10 for mission in BASE_MISSIONS})
    for index, tens in enumerate(groups):
        c.label(f'{prefix}_tens_{tens}')
        c.emit('0fb6'); c.mem('eax', path_register, 12)
        c.emit(bytes((0x83, 0xE8, (48 - 10 * tens) & 0xFF)))
        if index + 1 < len(groups):
            c.jump(prefix + '_accepted')
    c.label(prefix + '_accepted')
