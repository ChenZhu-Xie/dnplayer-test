import cv2
import numpy as np
import os
import pyautogui
import time

def audit_and_fix():
    # 模拟器位置
    left, top, w, h = 3095, 345, 796, 1348
    
    # 1. 加载当前屏幕
    screen = pyautogui.screenshot(region=(left, top, w, h))
    screen_img = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
    gray_screen = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
    
    # 2. 加载现有资产进行对比
    asset_path = "assets/assistant_update/update_btn.png"
    if not os.path.exists(asset_path):
        print(f"FAIL: 资产 {asset_path} 不存在")
        return
    
    template = cv2.imread(asset_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        print(f"FAIL: 无法读取资产 {asset_path}")
        return
        
    res = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    print(f"当前资产匹配度评分: {max_val:.4f}")
    
    # 3. 如果匹配度太低 (比如由于透明度或UI变动)，重新抓取并修正
    if max_val < 0.8:
        print("警告: 匹配度过低! 启动自动修复流程...")
        # 寻找屏幕中下部语义权重最大的按钮 (利用我之前学到的本领)
        edged = cv2.Canny(gray_screen, 50, 150)
        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        candidates = []
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            # 按钮通常尺寸比例
            if (w*0.1 < cw < w*0.7) and (h*0.03 < ch < h*0.15):
                dist_to_center = abs((x + cw//2) - w//2)
                if dist_to_center < w * 0.2 and y > h * 0.5:
                    candidates.append((x, y, cw, ch, dist_to_center))
        
        if candidates:
            candidates.sort(key=lambda c: (c[4], -c[1]))
            tx, ty, tw, th, _ = candidates[0]
            
            # 覆盖旧资产
            new_btn = screen_img[ty:ty+th, tx:tx+tw]
            cv2.imwrite(asset_path, new_btn)
            print(f"✓ 资产库已自我更新: {asset_path} (位置: {tx, ty})")
            
            # 执行点击
            pyautogui.click(left + tx + tw//2, top + ty + th//2)
            print(f"✓ 弹窗已尝试点掉 at: ({left + tx + tw//2}, {top + ty + th//2})")
            
            # 验证
            time.sleep(2)
            final_check = pyautogui.screenshot(region=(left, top, w, h))
            final_img = cv2.cvtColor(np.array(final_check), cv2.COLOR_RGB2BGR)
            diff = cv2.absdiff(screen_img, final_img)
            if np.mean(diff) > 10:
                print("✓ 验证成功: 模拟器界面已恢复正常业务流程。")
            else:
                print("✗ 验证失败: 界面无显著变化。")
        else:
            print("FAIL: 未能在屏幕中检测到任何符合按钮语义的区域。")
    else:
        print("资产匹配良好，说明是逻辑层面的屏蔽或漏检。")

if __name__ == "__main__":
    audit_and_fix()
