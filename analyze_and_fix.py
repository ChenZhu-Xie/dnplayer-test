import cv2
import numpy as np
import pyautogui
import os
import time

def solve_update_dialog(win_pos):
    left, top, width, height = win_pos
    print(f"开始精准分析模拟器弹窗: {win_pos}")
    
    # 1. 加载模拟器截图
    img = cv2.imread("emulator_focus.png")
    if img is None:
        print("ERROR: 无法读取截图文件")
        return False
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. 寻找按钮 (结合多种特征)
    # 策略：在模拟器中下部寻找宽度适中、边缘清晰的矩形
    edged = cv2.Canny(gray, 30, 100)
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    potential_buttons = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        # 按钮在模拟器中的比例通常在 15%-50% 宽，5%-15% 高
        if (width * 0.15 < w < width * 0.6) and (height * 0.03 < h < height * 0.15):
            # 按钮通常在屏幕的中下部
            if (width * 0.2 < x < width * 0.8) and (y > height * 0.5):
                potential_buttons.append((x, y, w, h))
    
    if not potential_buttons:
        print("未检测到明显按钮，尝试语义重心法 (点击底部中心区域)...")
        # 兜底：点击公告底部通常的位置
        click_rel_x, click_rel_y = width // 2, int(height * 0.85)
    else:
        # 选最底下的那个
        potential_buttons.sort(key=lambda b: b[1], reverse=True)
        target_x, target_y, target_w, target_h = potential_buttons[0]
        
        # 裁剪并保存为正式资产
        btn_crop = img[target_y:target_y+target_h, target_x:target_x+target_w]
        os.makedirs("assets/update_needed", exist_ok=True)
        cv2.imwrite("assets/update_needed/update_btn.png", btn_crop)
        print("已正式保存资产: assets/update_needed/update_btn.png")
        
        click_rel_x = target_x + target_w // 2
        click_rel_y = target_y + target_h // 2

    # 3. 执行点击 (转换到屏幕绝对坐标)
    abs_x = left + click_rel_x
    abs_y = top + click_rel_y
    print(f"执行点击坐标: ({abs_x}, {abs_y})")
    pyautogui.click(abs_x, abs_y)
    
    # 4. 验证 (闭环)
    time.sleep(2)
    # 再次截图确认
    new_shot = pyautogui.screenshot(region=(left, top, width, height))
    new_img = cv2.cvtColor(np.array(new_shot), cv2.COLOR_RGB2BGR)
    
    # 计算差异
    diff = cv2.absdiff(img, new_img)
    non_zero_count = np.count_nonzero(diff)
    print(f"验证差异点数: {non_zero_count}")
    
    if non_zero_count > 1000: # 有明显变化
        print("✓ 验证成功: 界面已发生变化，弹窗已处理。")
        return True
    else:
        print("✗ 验证失败: 界面无变化，弹窗可能仍在。")
        return False

if __name__ == "__main__":
    # 使用之前定位到的坐标
    win_rect = (1560, 346, 796, 1348)
    solve_update_dialog(win_rect)
