import pygetwindow as gw
import pyautogui
import cv2
import numpy as np
import os
import psutil

ALLOWED_EMU_PROCESSES = {
    "mumunxdevice.exe", "nemuplayer.exe", "dnplayer.exe"
}

EXCLUDED_PROCESSES = {
    "antigravity.exe", "code.exe", "cursor.exe", "chrome.exe",
    "msedge.exe", "firefox.exe", "python.exe", "cmd.exe",
    "powershell.exe", "windowsterminal.exe"
}

def locate_emulator():
    """
    寻找模拟器窗口（优先支持 MuMu Player，兼容 LDPlayer）。
    严格基于进程 PID 进行匹配，杜绝误操作 Antigravity 或浏览器。
    """
    target_win = None
    
    # 收集当前系统中所有属于模拟器的 PID
    emu_pids = set()
    for p in psutil.process_iter(['pid', 'name']):
        pname = (p.info.get('name') or '').lower()
        if pname in ALLOWED_EMU_PROCESSES:
            emu_pids.add(p.info['pid'])

    if emu_pids:
        try:
            import win32process
            for win in gw.getAllWindows():
                if not win.title:
                    continue
                try:
                    _, win_pid = win32process.GetWindowThreadProcessId(win._hWnd)
                    if win_pid in emu_pids:
                        proc_name = psutil.Process(win_pid).name().lower()
                        if proc_name in EXCLUDED_PROCESSES:
                            continue
                        if not win.isMinimized and (win.width < 100 or win.height < 100):
                            continue
                        target_win = win
                        break
                except Exception:
                    pass
        except Exception:
            pass
    
    if not target_win:
        print("ERROR: 未找到模拟器窗口 (请确认 MuMu Player / 雷电模拟器 已经启动)")
        return None
    
    print(f"找到窗口: {target_win.title}")
    print(f"位置: L={target_win.left}, T={target_win.top}, W={target_win.width}, H={target_win.height}")
    
    # 将窗口置于前台
    try:
        if target_win.isMinimized:
            target_win.restore()
        target_win.activate()
    except Exception as e:
        print(f"激活窗口失败 (可能已经在前台): {e}")
    
    # 截取模拟器区域
    screenshot = pyautogui.screenshot(region=(target_win.left, target_win.top, target_win.width, target_win.height))
    screenshot.save("emulator_focus.png")
    print("已保存模拟器焦点截图: emulator_focus.png")
    return (target_win.left, target_win.top, target_win.width, target_win.height)

if __name__ == "__main__":
    locate_emulator()
