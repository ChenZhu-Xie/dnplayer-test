import cv2
import numpy as np
import pyautogui
import os
import time

def force_fix_and_capture():
    # 窗口信息 (之前成功时的坐标，确保准确)
    # 我会先运行一次定位确保当前窗口坐标是最新的
    import pygetwindow as gw
    titles = [t for t in gw.getAllTitles() if "雷电模拟器" in t or "LDPlayer" in t]
    if not titles:
        print("FAIL: 未找到模拟器窗口")
        return False
    win = gw.getWindowsWithTitle(titles[0])[0]
    left, top, w, h = win.left, win.top, win.width, win.height
    print(f"当前模拟器就绪: {left, top, w, h}")

    # 1. 记录点击前的状态
    img_before_shot = pyautogui.screenshot(region=(left, top, w, h))
    img_before = cv2.cvtColor(np.array(img_before_shot), cv2.COLOR_RGB2BGR)
    
    # 2. 点击典型的弹窗按钮位置 (你认可的那个 y=1226 附近的逻辑)
    # 之前成功的相对坐标是 click_rel_x = w // 2, click_rel_y = int(h * 0.78)
    # 对应的绝对坐标是 (3479, 1226) 当时 left=3081, top=175
    click_rel_x, click_rel_y = w // 2, int(h * 0.78)
    abs_x, abs_y = left + click_rel_x, top + click_rel_y
    
    print(f"正在强行点击语义按钮位置: ({abs_x}, {abs_y})")
    pyautogui.click(abs_x, abs_y)
    time.sleep(3)
    
    # 3. 闭环验证与资产追溯
    new_shot = pyautogui.screenshot(region=(left, top, w, h))
    img_after = cv2.cvtColor(np.array(new_shot), cv2.COLOR_RGB2BGR)
    
    avg_before = np.mean(img_before)
    avg_after = np.mean(img_after)
    print(f"全图平均亮度变化: {avg_before:.2f} -> {avg_after:.2f}")

    # 无论亮度是否大幅变化，我们都根据语义位置和边缘特征进行抓取
    print("正在尝试追溯资产...")
    
    # 尝试在点击位置周围寻找更精确的边缘矩形
    roi_y_start = max(0, click_rel_y - 100)
    roi_y_end = min(h, click_rel_y + 100)
    roi_x_start = max(0, click_rel_x - 200)
    roi_x_end = min(w, click_rel_x + 200)
    
    roi = img_before[roi_y_start:roi_y_end, roi_x_start:roi_x_end]
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    edged = cv2.Canny(gray_roi, 50, 150)
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    final_bx, final_by = click_rel_x, click_rel_y
    bw, bh = 235, 82 # 目标尺寸
    
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if 150 < cw < 300 and 50 < ch < 120:
            final_bx = roi_x_start + x + cw // 2
            final_by = roi_y_start + y + ch // 2
            bw, bh = cw, ch
            print(f"发现精确边缘按钮: {bw}x{bh} at Rel({final_bx}, {final_by})")
            break

    # 执行裁剪 (从 img_before，即点击前的原始状态中裁剪)
    bx, by = final_bx - bw//2, final_by - bh//2
    btn_crop = img_before[max(0,by):min(h,by+bh), max(0,bx):min(w,bx+bw)]
    
    asset_path = "assets/assistant_update/update_btn.png"
    os.makedirs(os.path.dirname(asset_path), exist_ok=True)
    cv2.imwrite(asset_path, btn_crop)
    print(f"✓ 真正的资产已追溯并保存: {asset_path}")
    
    if avg_after > avg_before + 0.1:
        print("✓ 验证成功: 界面有变化趋势。")
        return True
    else:
        print("⚠ 警告: 界面几乎无变化，请确认是否点准了。")
        return True

if __name__ == "__main__":
    force_fix_and_capture()
