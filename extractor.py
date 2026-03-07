import cv2
import numpy as np
import os
import pyautogui

def extract_real_button():
    # 模拟器位置
    left, top, w, h = 3081, 175, 796, 1348
    
    # 1. 读取当前严重遮挡下的截图
    img = cv2.imread("emulator_focus.png")
    if img is None:
        print("FAIL: Cannot read screenshot")
        return
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. 寻找弹窗中的显著矩形 (利用边缘检测)
    edged = cv2.Canny(gray, 30, 80)
    # 对边缘进行闭运算，连接断裂的线条
    kernel = np.ones((5,5), np.uint8)
    closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
    
    # 在屏幕中下部区域寻找最大矩形
    roi = closed[int(h*0.3):int(h*0.9), int(w*0.1):int(w*0.9)]
    contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    best_btn = None
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        # 寻找符合按钮长宽比的矩形
        if 80 < cw < 450 and 30 < ch < 130:
            # 按钮通常在屏幕中轴线附近
            dist_to_center = abs((x + cw//2) - (w*0.45))
            if dist_to_center < w * 0.2:
                best_btn = (x + int(w*0.1), y + int(h*0.3), cw, ch)
                # 选最靠上的那个 (通常是确定/更新按钮)
                break
            
    if best_btn:
        bx, by, bw, bh = best_btn
        btn_crop = img[by:by+bh, bx:bx+bw]
        asset_path = "assets/assistant_update/update_btn.png"
        cv2.imwrite(asset_path, btn_crop)
        print(f"✓ 真正的更新按钮已重新保存至: {asset_path}")
        print(f"位置: {bx, by, bw, bh}")
    else:
        print("FAIL: 未能在暗色背景中提取出高亮按钮。")

if __name__ == "__main__":
    extract_real_button()
