import pyautogui
import time
import os

# 禁用pyautogui的安全功能(防止鼠标移动到屏幕边缘时抛出异常)
pyautogui.FAILSAFE = True

def find_and_click(image_path, log=None, confidence=0.8, max_attempts=3, retry_delay=2):
    """
    纯视觉识图点击 - 赤兔助手
    
    参数:
        image_path: 图标图片的路径
        log: 日志对象
        confidence: 匹配相似度 (0.1~1.0)
        max_attempts: 最大尝试次数
        retry_delay: 重试间隔(秒)
    
    返回:
        bool: 是否成功点击
    """
    if not os.path.exists(image_path):
        msg = f"视觉资源丢失: 找不到图片 {image_path}"
        if log:
            log.error(msg)
        else:
            print(msg)
        return False
    
    # 转换为绝对路径
    image_path = os.path.abspath(image_path)
    
    for attempt in range(1, max_attempts + 1):
        if log:
            log.info(f"[{attempt}/{max_attempts}] 正在屏幕上寻找图标: {os.path.basename(image_path)}")
        
        try:
            # 在屏幕上寻找图片中心点
            location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
            
            if location:
                if log:
                    log.info(f"发现目标，坐标: ({location.x}, {location.y})")
                
                # 移动鼠标并点击
                pyautogui.moveTo(location.x, location.y, duration=0.5)
                time.sleep(0.2)
                pyautogui.click(location.x, location.y)
                
                if log:
                    log.info("点击成功！")
                return True
            else:
                if log:
                    log.warning(f"第 {attempt} 次尝试: 当前屏幕未发现目标图标")
                
                if attempt < max_attempts:
                    if log:
                        log.info(f"{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                    
        except Exception as e:
            error_msg = f"视觉识别发生异常: {e}"
            if log:
                log.error(error_msg)
            else:
                print(error_msg)
            return False
    
    # 所有尝试都失败了
    if log:
        log.error(f"经过 {max_attempts} 次尝试，未能找到目标图标")
    return False

def find_multiple_and_click(image_path, log=None, confidence=0.8):
    """
    查找屏幕上所有匹配的图标并依次点击
    
    参数:
        image_path: 图标图片的路径
        log: 日志对象
        confidence: 匹配相似度
    
    返回:
        int: 成功点击的数量
    """
    if not os.path.exists(image_path):
        if log:
            log.error(f"视觉资源丢失: 找不到图片 {image_path}")
        return 0
    
    image_path = os.path.abspath(image_path)
    
    try:
        # 查找所有匹配的位置
        locations = list(pyautogui.locateAllOnScreen(image_path, confidence=confidence))
        
        if not locations:
            if log:
                log.info(f"屏幕上未找到任何匹配: {os.path.basename(image_path)}")
            return 0
        
        if log:
            log.info(f"找到 {len(locations)} 个匹配目标")
        
        clicked_count = 0
        for location in locations:
            center = pyautogui.center(location)
            pyautogui.click(center.x, center.y)
            clicked_count += 1
            time.sleep(0.3)  # 点击间隔
        
        if log:
            log.info(f"成功点击 {clicked_count} 个目标")
        return clicked_count
        
    except Exception as e:
        if log:
            log.error(f"批量点击异常: {e}")
        return 0

def wait_for_image(image_path, timeout=30, interval=0.5, confidence=0.8, log=None):
    """
    轮询等待直到指定图像出现在屏幕上 - OpenClaw 模式
    
    参数:
        image_path: 要等待的图像路径
        timeout: 最大等待时间(秒)
        interval: 每次检测间隔(秒)
        confidence: 匹配相似度
        log: 日志对象
    
    返回:
        bool: 是否在超时前找到图像
    """
    if not os.path.exists(image_path):
        if log:
            log.error(f"图像资源不存在: {image_path}")
        return False
    
    image_path = os.path.abspath(image_path)
    
    if log:
        log.info(f"[OpenClaw] 轮询等待: {os.path.basename(image_path)} (超时: {timeout}s, 间隔: {interval}s)")
    
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < timeout:
        check_count += 1
        elapsed = time.time() - start_time
        
        try:
            location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
            if location:
                if log:
                    log.info(f"[OpenClaw] ✓ 第 {check_count} 次检测命中! 耗时 {elapsed:.2f}秒")
                return True
        except:
            pass
        
        time.sleep(interval)
    
    if log:
        log.warning(f"[OpenClaw] ✗ 超时: 经过 {check_count} 次检测 ({timeout}秒)，图像未出现")
    return False

def wait_and_click(image_path, timeout=60, interval=0.5, confidence=0.8, log=None):
    """
    轮询等待图像出现后点击 - OpenClaw 核心逻辑
    """
    if not os.path.exists(image_path):
        if log:
            log.error(f"图像资源不存在: {image_path}")
        return False
    
    image_path = os.path.abspath(image_path)
    
    if log:
        log.info(f"[OpenClaw] 启动轮询检测: {os.path.basename(image_path)}")
        log.info(f"[OpenClaw] 配置: 超时={timeout}秒, 轮询间隔={interval}秒, 置信度={confidence}")
    
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < timeout:
        check_count += 1
        elapsed = time.time() - start_time
        
        try:
            location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
            
            if location:
                if log:
                    log.info(f"[OpenClaw] ✓ 第 {check_count} 次检测命中! 耗时 {elapsed:.2f}秒")
                    log.info(f"[OpenClaw] 目标坐标: ({location.x}, {location.y})")
                
                pyautogui.moveTo(location.x, location.y, duration=0.3)
                time.sleep(0.1)
                pyautogui.click(location.x, location.y)
                
                if log:
                    log.info(f"[OpenClaw] ✓ 点击执行成功")
                return True
                
        except Exception as e:
            pass
        
        time.sleep(interval)
    
    if log:
        log.warning(f"[OpenClaw] ✗ 轮询超时: 经过 {check_count} 次检测 ({timeout}秒)，未找到目标")
    return False

def find_only(image_path, confidence=0.8, log=None):
    """
    纯检测函数 - 只查找不点击
    用于闭环控制中的验证步骤
    
    参数:
        image_path: 要检测的图像路径
        confidence: 匹配相似度
        log: 日志对象
    
    返回:
        bool: 是否找到图像
    """
    if not os.path.exists(image_path):
        if log:
            log.debug(f"检测资源不存在: {image_path}")
        return False
    
    image_path = os.path.abspath(image_path)
    
    try:
        location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
        if location:
            return True
    except:
        pass
    
    return False
