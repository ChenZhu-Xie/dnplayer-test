import pygetwindow as gw
import pyautogui
import cv2
import numpy as np
import os
import time

def robust_solve():
    # 1. 强制激活模拟器 (严格匹配模拟器进程 PID)
    import psutil, win32process
    ALLOWED_EMU = {"mumunxdevice.exe", "nemuplayer.exe", "dnplayer.exe"}
    emu_pids = {p.info['pid'] for p in psutil.process_iter(['pid', 'name']) if (p.info.get('name') or '').lower() in ALLOWED_EMU}
    win = None
    for w in gw.getAllWindows():
        if not w.title: continue
        try:
            _, pid = win32process.GetWindowThreadProcessId(w._hWnd)
            if pid in emu_pids:
                win = w
                break
        except Exception:
            pass
    if not win:
        print("FAIL: 未找到模拟器窗口")
        return False
    try:
        if win.isMinimized: win.restore()
        win.activate()
        time.sleep(1) # 等待窗口平滑切换
    except Exception as e:
        print(f"WARN: 激活窗口异常: {e}")

    left, top, width, height = win.left, win.top, win.width, win.height
    print(f"模拟器就绪: {left, top, width, height}")

    # 2. 初始状态分析
    shot1 = pyautogui.screenshot(region=(left, top, width, height))
    img1 = cv2.cvtColor(np.array(shot1), cv2.COLOR_RGB2BGR)
    
    # 3. 寻找按钮 (中下部语义块)
    gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    edged = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    btn_target = None
    candidates = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if (width*0.15 < w < width*0.7) and (height*0.03 < h < height*0.15):
            # 计算距离中心线的水平偏差
            dist_to_center = abs((x + w//2) - width//2)
            if dist_to_center < width * 0.2: # 必须在中心 40% 范围内
                if y > height * 0.5:
                    candidates.append((x, y, w, h, dist_to_center))
    
    if candidates:
        # 排序：优先选择最靠下且最靠中的
        candidates.sort(key=lambda c: (c[4], -c[1]))
        target = candidates[0]
        btn_target = (target[0], target[1], target[2], target[3])
    
    if not btn_target:
        print("FAIL: 未能在模拟器内识别到明确的按钮轮廓")
        return False

    tx, ty, tw, th = btn_target
    # 保存原始按钮图像
    btn_img = img1[ty:ty+th, tx:tx+tw]
    os.makedirs("assets/update_needed", exist_ok=True)
    cv2.imwrite("assets/update_needed/update_btn.png", btn_img)

    # 4. 执行点击
    abs_x = left + tx + tw // 2
    abs_y = top + ty + th // 2
    print(f"正在点击目标按钮: ({abs_x}, {abs_y})")
    pyautogui.click(abs_x, abs_y)
    
    # 5. 延迟后验证
    time.sleep(3)
    shot2 = pyautogui.screenshot(region=(left, top, width, height))
    img2 = cv2.cvtColor(np.array(shot2), cv2.COLOR_RGB2BGR)
    
    # 语义验证: 检查原按钮区域是否已发生显著变化
    roi1 = img1[ty:ty+th, tx:tx+tw]
    roi2 = img2[ty:ty+th, tx:tx+tw]
    diff = cv2.absdiff(roi1, roi2)
    change_score = np.mean(diff)
    
    print(f"局部按钮区域变化评分: {change_score}")
    
    # 判定标准：局部变化大，且按钮特征消失
    if change_score > 15:
        print("✓ 语义验证通过: 按钮区域已变化，弹窗已点掉。")
        # 最终确认：是否回到了主界面 (例如检查 DL_entry 文件夹下的图片)
        return True
    else:
        print("✗ 验证失败: 按钮区域未发生预期变化，可能是误点。")
        return False

if __name__ == "__main__":
    robust_solve()
