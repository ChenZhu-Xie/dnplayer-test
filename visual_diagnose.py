import cv2
import numpy as np
import os

def diagnose():
    img = cv2.imread("emulator_focus.png")
    if img is None:
        print("FAIL: Cannot read emulator_focus.png")
        return
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    
    # 查找所有显著矩形块 (可能是弹窗)
    edged = cv2.Canny(gray, 30, 100)
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    print(f"--- 图像语义诊断报告 (Size: {w}x{h}) ---")
    
    # 统计中心区域的平均亮度，判断是否被蒙版遮挡
    center_roi = gray[h//3:2*h//3, w//4:3*w//4]
    avg_brightness = np.mean(center_roi)
    print(f"中心区域平均亮度: {avg_brightness:.2f}")

    found_any = False
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        # 寻找模拟器中的弹窗特征 (通常占据 50%+ 宽，且在中心)
        if cw > w * 0.5 and ch > h * 0.1:
            print(f"检测到大型 UI 容器: L={x}, T={y}, W={cw}, H={ch}")
            found_any = True
            
            # 在这个容器内寻找按钮
            roi = gray[y:y+ch, x:x+cw]
            # 寻找 ROI 里的子轮廓
            sub_edged = cv2.Canny(roi, 50, 150)
            sub_cnts, _ = cv2.findContours(sub_edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for scnt in sub_cnts:
                sx, sy, sw, sh = cv2.boundingRect(scnt)
                # 寻找典型的确认/关闭按钮尺寸
                if 50 < sw < 300 and 30 < sh < 100:
                    print(f"  [发现交互按钮]: RelX={sx}, RelY={sy}, AbsX={x+sx+sw//2}, AbsY={y+sy+sh//2}")

    if not found_any:
        print("未发现明显的弹窗容器，画面可能已进入游戏背景。")

if __name__ == "__main__":
    diagnose()
