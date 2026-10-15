"""Apply per-player display and session settings to an isolated runtime."""
from old_native_installation import MOD


def configure_runtime(role, folder, *, force_windowed=True, safe_video=False, infinite_health=False):
    import winreg

    expected = (MOD / "runtime" / ("old-game-" + role)).resolve()
    if folder.resolve() != expected or not (folder / ".old-native-probe").is_file():
        raise RuntimeError("Refusing a runtime without the isolated-copy marker")
    registry_path = "Software\\SigmaTeam\\AS2CoopPrototype\\old-game-" + role
    config = (folder / "AlienShooter.cfg").read_text("cp1251")
    expected_line = "RegPath=HKEY_CURRENT_USER\\" + registry_path
    if not any(line.strip().lower() == expected_line.lower() for line in config.splitlines()):
        raise RuntimeError("The game configuration does not use its isolated registry key")
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, registry_path,
                           access=winreg.KEY_READ | winreg.KEY_SET_VALUE | winreg.KEY_WOW64_32KEY) as key:
        # A fresh launch always clears the previous session's test mode. The
        # manual lobby transfers the host preference before its prepare/ack.
        winreg.SetValueEx(key, 'CoopTestHealthActive', 0, winreg.REG_DWORD, 0)
        winreg.SetValueEx(key, 'CoopTestHealthRequested', 0, winreg.REG_DWORD, int(infinite_health))
        def current(name, fallback):
            try:
                return winreg.QueryValueEx(key, name)[0]
            except FileNotFoundError:
                return fallback
        try:
            preference = int(current('CoopFullScreen', current('FullScreen', 0)))
        except (ValueError, TypeError):
            preference = 0
        fullscreen = 0 if force_windowed or safe_video else int(preference == 1)
        winreg.SetValueEx(key, 'FullScreen', 0, winreg.REG_DWORD, fullscreen)
        if safe_video:
            for name, value in (('CoopFullScreen', 0), ('ScreenX', 800), ('ScreenY', 600)):
                winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
            # common_defs2.lgc/GetPlayerRegPath uses <game key>\ProfileN.
            # Reset all existing profiles in this role so loading another name
            # cannot immediately restore the unusable mode. Preserve other values.
            for index in range(winreg.QueryInfoKey(key)[0]):
                name = winreg.EnumKey(key, index)
                if name.lower().startswith('profile') and name[7:].lstrip('-').isdigit():
                    with winreg.OpenKey(key, name, access=winreg.KEY_SET_VALUE | winreg.KEY_WOW64_32KEY) as profile:
                        winreg.SetValueEx(profile, 'Resolution', 0, winreg.REG_DWORD, 0)
        for name, value in (("RespawnWeapon", 1), ("TimeLimit", 20), ("FragLimit", 100)):
            if current(name, None) is None:
                winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
    for path in folder.glob("old-game-*.txt"):
        path.unlink()
    for path in folder.glob("old-transition-level-*-frame-*.txt"):
        path.unlink()
    for name in ("Logs", "Saves", "Screens"):
        (folder / name).mkdir(exist_ok=True)
    # The new build deliberately has no fixture patch; remove stale metadata.
    (folder / "input-fixture.json").unlink(missing_ok=True)
