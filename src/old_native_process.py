"""Close only game processes owned by the current launcher."""
import ctypes
from ctypes import wintypes
import subprocess


def owned_windows(pid):
    """Read window handles belonging to one launcher-owned game process."""
    user = ctypes.WinDLL('user32', use_last_error=True)
    result = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    def read_window(hwnd, _):
        owner = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            title = ctypes.create_unicode_buffer(2048)
            cls = ctypes.create_unicode_buffer(256)
            user.GetWindowTextW(hwnd, title, len(title))
            user.GetClassNameW(hwnd, cls, len(cls))
            result.append(dict(handle=int(hwnd), title=title.value, window_class=cls.value))
        return True
    callback = callback_type(read_window)
    user.EnumWindows(callback, 0)
    parents = list(result)
    for window in parents:
        user.EnumChildWindows(wintypes.HWND(window['handle']), callback, 0)
    return result


def close_owned(process):
    if process is None or process.poll() is not None:
        return
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    for window in owned_windows(process.pid):
        if window['window_class']=='AlienShooter':
            user.PostMessageW(window['handle'],0x10,0,0)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.terminate()
        process.wait(timeout=5)
