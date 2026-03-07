import pygetwindow as gw
import pyautogui
import cv2
import numpy as np
import os

def locate_emulator():
    # 尝试寻找雷电模拟器的窗口
    # 雷电模拟器窗口标题通常包含 "雷电模拟器" 或 "LDPlayer"
    titles = gw.getAllTitles()
    target_title = None
    for t in titles:
        if "雷电模拟器" in t or "LDPlayer" in t:
            target_title = t
            break
    
    if not target_title:
        print("ERROR: 未找到雷电模拟器窗口")
        return None
    
    win = gw.getWindowsWithTitle(target_title)[0]
    print(f"找到窗口: {target_title}")
    print(f"位置: L={win.left}, T={win.top}, W={win.width}, H={win.height}")
    
    # 将窗口置于前台
    try:
        if win.isMinimized:
            win.restore()
        win.activate()
    except Exception as e:
        print(f"激活窗口失败 (可能已经在前台): {e}")
    
    # 截取模拟器区域
    screenshot = pyautogui.screenshot(region=(win.left, win.top, win.width, win.height))
    screenshot.save("emulator_focus.png")
    print("已保存模拟器焦点截图: emulator_focus.png")
    return (win.left, win.top, win.width, win.height)

if __name__ == "__main__":
    locate_emulator()
