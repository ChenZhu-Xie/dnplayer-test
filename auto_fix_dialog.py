import cv2
import numpy as np
import pyautogui
import os
import time

def find_and_click_dialog_button():
    print("开始自动化视觉分析与修复流程...")
    
    # 1. 截取当前屏幕
    screenshot = pyautogui.screenshot()
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. 寻找可能是按钮的矩形区域
    # 针对公告/更新弹窗，通常会有明显的按钮背景色或边框
    # 这里我们使用 Canny 边缘检测和轮廓发现
    edged = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    potential_buttons = []
    screen_h, screen_w = gray.shape
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        
        # 过滤掉太小或太大的形状（按钮通常在一定范围内）
        # 假设按钮宽度在 80-400 之间，高度在 30-150 之间
        if 80 < w < 400 and 30 < h < 150:
            # 按钮通常在屏幕中间区域
            if (screen_w * 0.2 < x < screen_w * 0.8) and (screen_h * 0.2 < y < screen_h * 0.8):
                potential_buttons.append((x, y, w, h))
    
    if not potential_buttons:
        print("未通过几何分析发现明显的按钮，尝试色域分析...")
        # 尝试寻找常见的 UI 按钮颜色 (例如蓝色, 橙色)
        # 这里使用 HSV 空间进行颜色过滤
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 定义颜色的 HSV 范围 (这里以常见的蓝色按钮为例)
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # 如果蓝色没找到，尝试黄色/橙色
        if cv2.countNonZero(mask) < 500:
            lower_orange = np.array([10, 100, 100])
            upper_orange = np.array([25, 255, 255])
            mask = cv2.inRange(hsv, lower_orange, upper_orange)

        # 寻找掩码中的轮廓
        m_contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in m_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if 60 < w < 500 and 25 < h < 200:
                potential_buttons.append((x, y, w, h))

        if not potential_buttons:
            # 最后的兜底策略：点击屏幕中心偏下的位置（通常是公告按钮所在）
            print("未能通过颜色分析发现按钮，执行兜底点击（屏幕中心偏下区域）...")
            click_x = screen_w // 2
            click_y = int(screen_h * 0.7) # 假设按钮在 70% 的高度处
            pyautogui.click(click_x, click_y)
            return True

    # 3. 排序并选择最可能的按钮（通常是弹窗中最下方的按钮）
    potential_buttons.sort(key=lambda b: b[1], reverse=True)
    target_x, target_y, target_w, target_h = potential_buttons[0]
    
    click_x = target_x + target_w // 2
    click_y = target_y + target_h // 2
    
    print(f"检测到潜在按钮位置: ({click_x}, {click_y})，尺寸: {target_w}x{target_h}")
    
    # 4. 自动截取该按钮并存入 assets 以备后用 (自动化维护)
    button_crop = img[target_y:target_y+target_h, target_x:target_x+target_w]
    assets_dir = "assets/auto_detected"
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
    
    timestamp = int(time.time())
    crop_path = f"{assets_dir}/button_{timestamp}.png"
    cv2.imwrite(crop_path, button_crop)
    print(f"已自动抓取按钮图像并保存至: {crop_path}")
    
    # 5. 执行点击
    print(f"正在执行自动点击...")
    pyautogui.click(click_x, click_y)
    return True

if __name__ == "__main__":
    success = find_and_click_dialog_button()
    if success:
        print("自动化修复成功：已点击弹窗按钮并抓取样本。")
    else:
        print("自动化修复失败：未能准确锁定弹窗按钮。")
