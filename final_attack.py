import cv2
import numpy as np
import pyautogui
import os
import time

def final_attack():
    # 窗口信息
    left, top, w, h = 3095, 345, 796, 1348
    print(f"执行最终闭环攻击 at: {left, top}")

    # 1. 尝试点击刚才诊断出的核心按钮 (AbsX=79, AbsY=286 是相对坐标)
    # 修正：AbsX=79, AbsY=286 应该是相对 ROI 的，或者是相对于窗口的
    # 根据之前的 diagnose 输出：RelX=40, RelY=110, AbsX=79, AbsY=286 (相对于 ROI)
    # ROI 是 (2, 161, 702, 252)
    # 那么相对于窗口的绝对坐标是：left + 2 + 40 + 按钮宽/2
    
    # 这里的绝对坐标计算：
    # 目标按钮在诊断报告中给出的 AbsX 是 79, AbsY 是 286 (相对于窗口左上角)
    target_abs_x = left + 79
    target_abs_y = top + 286
    
    print(f"正在点击疑似‘关闭/重试’按钮: ({target_abs_x}, {target_abs_y})")
    pyautogui.click(target_abs_x, target_abs_y)
    
    time.sleep(2)
    
    # 2. 再次截图并检测变化
    new_shot = pyautogui.screenshot(region=(left, top, w, h))
    new_img = cv2.cvtColor(np.array(new_shot), cv2.COLOR_RGB2BGR)
    
    # 验证原 ROI 区域是否已经变化 (说明弹窗消失)
    roi_after = new_img[161:161+252, 2:2+702]
    cv2.imwrite("assets/auto_detected/last_obstacle_fixed.png", roi_after)
    
    print("✓ 闭环操作执行完毕，已更新检测快照。")

if __name__ == "__main__":
    final_attack()
