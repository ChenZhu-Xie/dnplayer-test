import cv2
import os
import numpy as np
import pyautogui

class TemplateMatcher:
    """
    多样板图片匹配器
    支持每个逻辑目标对应多个样板图片（不同分辨率、状态等）
    """
    
    def __init__(self, assets_dir="assets", confidence=0.8, log=None):
        """
        初始化加载器
        
        参数:
            assets_dir: 资源根目录路径
            confidence: 匹配阈值 (0~1)
            log: 日志对象
        """
        self.assets_dir = assets_dir
        self.confidence = confidence
        self.log = log
        # 核心数据结构: {逻辑名: [图片1, 图片2, ...]}
        self.templates = {}
        self.template_sizes = {}  # 存储每个模板的尺寸
        self._load_all_assets()
    
    def _load_all_assets(self):
        """遍历目录，加载所有图片到内存"""
        if not os.path.exists(self.assets_dir):
            if self.log:
                self.log.error(f"资源目录不存在: {self.assets_dir}")
            return
        
        # 遍历 assets 下的每一个子文件夹
        for folder_name in sorted(os.listdir(self.assets_dir)):
            folder_path = os.path.join(self.assets_dir, folder_name)
            
            # 确保是文件夹
            if os.path.isdir(folder_path):
                self.templates[folder_name] = []
                self.template_sizes[folder_name] = []
                
                # 读取文件夹内的所有图片
                for filename in sorted(os.listdir(folder_path)):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                        img_path = os.path.join(folder_path, filename)
                        # 读取为灰度图，提高匹配速度和鲁棒性
                        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                        
                        if img is not None:
                            self.templates[folder_name].append(img)
                            self.template_sizes[folder_name].append(img.shape[:2])
                            if self.log:
                                self.log.debug(f"加载样板: {folder_name}/{filename}")
                        else:
                            if self.log:
                                self.log.warning(f"无法读取图片: {img_path}")
                
                if self.log:
                    count = len(self.templates[folder_name])
                    if count > 0:
                        self.log.info(f"[{folder_name}] 加载了 {count} 张样板")
    
    def find_target(self, target_name, screen_image=None, region=None):
        """
        在屏幕截图中寻找目标
        
        参数:
            target_name: 逻辑目标名称（即文件夹名，如 'start'）
            screen_image: 屏幕截图（OpenCV格式），为None则自动截屏
            region: 截屏区域 (left, top, width, height)，为None则全屏
        
        返回:
            (x, y) 中心坐标 或 None
        """
        if target_name not in self.templates:
            if self.log:
                self.log.error(f"未找到名为 {target_name} 的样板定义")
            return None
        
        if not self.templates[target_name]:
            if self.log:
                self.log.error(f"{target_name} 文件夹中没有图片")
            return None
        
        # 自动截屏
        if screen_image is None:
            if region:
                screen_image = pyautogui.screenshot(region=region)
            else:
                screen_image = pyautogui.screenshot()
            screen_image = cv2.cvtColor(np.array(screen_image), cv2.COLOR_RGB2BGR)
        
        # 确保屏幕截图是灰度图
        if len(screen_image.shape) == 3:
            screen_gray = cv2.cvtColor(screen_image, cv2.COLOR_BGR2GRAY)
        else:
            screen_gray = screen_image
        
        # 遍历该目标下的所有样板图片
        for i, template in enumerate(self.templates[target_name]):
            try:
                # 模板必须小于屏幕
                if template.shape[0] > screen_gray.shape[0] or template.shape[1] > screen_gray.shape[1]:
                    continue
                
                # 执行模板匹配
                res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                
                if max_val >= self.confidence:
                    # 找到匹配，计算中心点
                    h, w = template.shape[:2]
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2
                    
                    if self.log:
                        self.log.info(f"匹配 [{target_name}] 样板{i+1} 成功 (置信度: {max_val:.2f})")
                    
                    # 如果指定了region，需要加上偏移量
                    if region:
                        center_x += region[0]
                        center_y += region[1]
                    
                    return (center_x, center_y)
                    
            except Exception as e:
                if self.log:
                    self.log.debug(f"匹配 {target_name} 样板{i+1} 时出错: {e}")
                continue
        
        # 所有样板都试过了，都没匹配上
        return None
    
    def find_all_targets(self, target_name, screen_image=None, region=None):
        """
        查找所有匹配的目标（用于点击第N个场景）
        
        返回:
            [(x1, y1), (x2, y2), ...] 按Y坐标排序的列表
        """
        if target_name not in self.templates:
            return []
        
        # 自动截屏
        if screen_image is None:
            if region:
                screen_image = pyautogui.screenshot(region=region)
            else:
                screen_image = pyautogui.screenshot()
            screen_image = cv2.cvtColor(np.array(screen_image), cv2.COLOR_RGB2BGR)
        
        # 确保是灰度图
        if len(screen_image.shape) == 3:
            screen_gray = cv2.cvtColor(screen_image, cv2.COLOR_BGR2GRAY)
        else:
            screen_gray = screen_image
        
        all_matches = []
        
        # 遍历所有样板
        for template in self.templates[target_name]:
            try:
                if template.shape[0] > screen_gray.shape[0] or template.shape[1] > screen_gray.shape[1]:
                    continue
                
                res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
                
                # 找到所有大于阈值的位置
                loc = np.where(res >= self.confidence)
                
                for pt in zip(*loc[::-1]):
                    h, w = template.shape[:2]
                    center_x = pt[0] + w // 2
                    center_y = pt[1] + h // 2
                    
                    if region:
                        center_x += region[0]
                        center_y += region[1]
                    
                    # 去重：如果距离已有匹配点太近，则跳过
                    is_duplicate = False
                    for existing in all_matches:
                        dist = ((center_x - existing[0])**2 + (center_y - existing[1])**2)**0.5
                        if dist < 20:  # 20像素内视为同一点
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        all_matches.append((center_x, center_y))
                        
            except Exception as e:
                continue
        
        # 按Y坐标排序（从上到下）
        all_matches.sort(key=lambda p: p[1])
        
        return all_matches
    
    def target_exists(self, target_name, screen_image=None):
        """
        检查目标是否存在（不返回坐标，仅检查）
        
        返回:
            bool: 是否存在
        """
        return self.find_target(target_name, screen_image) is not None
