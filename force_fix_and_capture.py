import cv2
import numpy as np
import pyautogui
import os
import time

def force_fix_and_capture():
    # 窗口信息
    left, top, w, h = 3081, 175, 796, 1348
    print(f"执行强行自愈与资产抓取: {left, top}")

    # 1. 记录点击前的状态
    img_before = cv2.imread("emulator_focus.png")
    
    # 2. 点击典型的弹窗按钮位置 (通常在高度 75% 左右，水平居中)
    click_rel_x, click_rel_y = w // 2, int(h * 0.78)
    abs_x, abs_y = left + click_rel_x, top + click_rel_y
    
    print(f"正在强行点击语义按钮位置: ({abs_x}, {abs_y})")
    pyautogui.click(abs_x, abs_y)
    time.sleep(3)
    
    # 3. 闭环验证
    new_shot = pyautogui.screenshot(region=(left, top, w, h))
    img_after = cv2.cvtColor(np.array(new_shot), cv2.COLOR_RGB2BGR)
    
    # 计算全图亮度变化
    avg_before = np.mean(img_before)
    avg_after = np.mean(img_after)
    print(f"全图平均亮度变化: {avg_before:.2f} -> {avg_after:.2f}")

    if avg_after > avg_before + 10: # 界面变亮，说明蒙版消失
        print("✓ 强行自愈成功! 正在追溯资产...")
        # 从 img_before 中根据点击位置裁剪样板
        bw, bh = 220, 90 # 常见的按钮尺寸
        bx, by = click_rel_x - bw//2, click_rel_y - bh//2
        btn_crop = img_before[by:by+bh, bx:bx+bw]
        
        asset_path = "assets/assistant_update/update_btn.png"
        os.makedirs(os.path.dirname(asset_path), exist_ok=True)
        cv2.imwrite(asset_path, btn_crop)
        print(f"✓ 真正的资产已追溯并保存: {asset_path}")
        return True
    else:
        print("✗ 强行点击未产生预期效果。")
        return False

if __name__ == "__main__":
    force_fix_and_capture()
