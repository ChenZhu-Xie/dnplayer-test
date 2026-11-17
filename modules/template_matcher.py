import cv2
import os
import numpy as np
import pyautogui

class TemplateMatcher:
    """
    多样板图片匹配器
    支持每个逻辑目标对应多个样板图片（不同分辨率、状态等）
    支持目标颜色特征过滤（如严格要求红色登录文字，杜绝黑色登录误识别）
    """
    
    def __init__(self, assets_dir="assets", confidence=0.8, log=None, color_rules=None):
        """
        初始化加载器
        
        参数:
            assets_dir: 资源根目录路径
            confidence: 匹配阈值 (0~1)
            log: 日志对象
            color_rules: 目标颜色规则字典，如 {"login": "red"}
        """
        self.assets_dir = assets_dir
        self.confidence = confidence
        self.log = log
        # 核心数据结构: {逻辑名: [图片1, 图片2, ...]}
        self.templates = {}
        self.template_sizes = {}  # 存储每个模板的尺寸
        
        # 默认颜色过滤规则：目标名称 -> 颜色要求类型
        # 'login' 必须为红色文字，杜绝黑白或普通灰色'登录'误识别
        self.color_rules = {
            "login": "red",
        }
        if color_rules:
            self.color_rules.update(color_rules)
            
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
                        rule_desc = f" (颜色过滤: {self.color_rules[folder_name]})" if folder_name in self.color_rules else ""
                        self.log.info(f"[{folder_name}] 加载了 {count} 张样板{rule_desc}")

    def _verify_color_red(self, roi):
        """
        验证 ROI 区域内是否包含红色的文字/主体（用于严格区分红色登录与黑色登录）
        """
        if roi is None or roi.size == 0:
            return False
        
        h, w = roi.shape[:2]
        total_pixels = h * w
        if total_pixels == 0:
            return False
            
        # 1. RGB 差值条件: R 分量显著占优 (排除黑、白、灰、蓝、绿)
        b = roi[:, :, 0].astype(int)
        g = roi[:, :, 1].astype(int)
        r = roi[:, :, 2].astype(int)
        rgb_red = (r >= 120) & (r - g >= 25) & (r - b >= 25)
        
        # 2. HSV 色相与饱和度条件: 确保属于红橙/红紫色系且有足够色彩饱和度
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        h_channel = hsv[:, :, 0]
        s_channel = hsv[:, :, 1]
        v_channel = hsv[:, :, 2]
        hsv_red = ((h_channel <= 15) | (h_channel >= 165)) & (s_channel >= 35) & (v_channel >= 45)
        
        # 综合判定: 像素点必须同时符合 RGB 红色优势与 HSV 红色特性
        red_mask = rgb_red & hsv_red
        red_count = int(np.sum(red_mask))
        red_ratio = red_count / total_pixels
        
        # 判定标准: 红色特征像素数至少 15 个，且占整个模板面积至少 2%
        return (red_count >= 15) and (red_ratio >= 0.02)

    def _verify_color(self, roi, rule):
        """颜色规则总分发器"""
        if not rule:
            return True
        if rule == "red":
            return self._verify_color_red(roi)
        return True

    def find_target(self, target_name, screen_image=None, region=None, color_filter=None):
        """
        在屏幕截图中寻找目标
        
        参数:
            target_name: 逻辑目标名称（即文件夹名，如 'login'）
            screen_image: 屏幕截图（OpenCV格式），为None则自动截屏
            region: 截屏区域 (left, top, width, height)，为None则全屏
            color_filter: 颜色过滤规则（如 'red'），若为None则自动应用预设规则
        
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
        
        # 自动截屏 (BGR格式)
        if screen_image is None:
            if region:
                screen_image = pyautogui.screenshot(region=region)
            else:
                screen_image = pyautogui.screenshot()
            screen_bgr = cv2.cvtColor(np.array(screen_image), cv2.COLOR_RGB2BGR)
        else:
            if len(screen_image.shape) == 3:
                screen_bgr = screen_image
            else:
                screen_bgr = None  # 仅提供了灰度图，无法进行颜色校验
        
        # 灰度图供形状匹配
        if screen_bgr is not None:
            screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
        else:
            screen_gray = screen_image

        # 确定颜色校验规则
        rule = color_filter if color_filter is not None else self.color_rules.get(target_name)
        if rule and screen_bgr is None and self.log:
            self.log.warning(f"目标 [{target_name}] 要求颜色校验({rule})，但提供的屏幕截图缺少彩色通道")

        # 遍历该目标下的所有样板图片
        for i, template in enumerate(self.templates[target_name]):
            try:
                # 模板必须小于屏幕
                if template.shape[0] > screen_gray.shape[0] or template.shape[1] > screen_gray.shape[1]:
                    continue
                
                # 执行模板匹配
                res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
                h, w = template.shape[:2]

                # 无颜色过滤规则时，直接使用高效的 minMaxLoc
                if not rule or screen_bgr is None:
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                    if max_val >= self.confidence:
                        center_x = max_loc[0] + w // 2
                        center_y = max_loc[1] + h // 2
                        if self.log:
                            self.log.info(f"匹配 [{target_name}] 样板{i+1} 成功 (置信度: {max_val:.2f})")
                        if region:
                            center_x += region[0]
                            center_y += region[1]
                        return (center_x, center_y)
                    continue

                # 有颜色过滤规则时：寻找所有满足置信度阈值的局部峰值，并验证颜色
                loc = np.where(res >= self.confidence)
                pts = list(zip(*loc[::-1])) # [(x1, y1), ...]
                if not pts:
                    continue

                # 按置信度降序排序，优先检查最高置信度的点
                pts.sort(key=lambda pt: res[pt[1], pt[0]], reverse=True)
                
                checked_peaks = []
                for pt in pts:
                    x, y = pt
                    cx, cy = x + w // 2, y + h // 2
                    
                    # 避免对同一物理按钮重复切片校验
                    if any(((cx - p[0])**2 + (cy - p[1])**2)**0.5 < 20 for p in checked_peaks):
                        continue
                    checked_peaks.append((cx, cy))

                    score = float(res[y, x])
                    roi = screen_bgr[y:y+h, x:x+w]
                    
                    # 校验颜色
                    if self._verify_color(roi, rule):
                        if self.log:
                            self.log.info(f"匹配 [{target_name}] (颜色校验:{rule}通过) 样板{i+1} 成功 (置信度: {score:.2f})")
                        if region:
                            cx += region[0]
                            cy += region[1]
                        return (cx, cy)
                    else:
                        if self.log:
                            self.log.debug(f"目标 [{target_name}] 样板{i+1} 虽有匹配 (置信度: {score:.2f})，但未通过颜色校验({rule})，已过滤")

            except Exception as e:
                if self.log:
                    self.log.debug(f"匹配 {target_name} 样板{i+1} 时出错: {e}")
                continue
        
        # 所有样板都未找到满足条件的匹配
        return None
    
    def find_all_targets(self, target_name, screen_image=None, region=None, color_filter=None):
        """
        查找所有匹配的目标（用于点击第N个场景，如从下往上点击最下面的登录按钮）
        
        返回:
            [(x1, y1), (x2, y2), ...] 按Y坐标排序的列表（从上到下）
        """
        if target_name not in self.templates:
            return []
        
        # 自动截屏 (BGR格式)
        if screen_image is None:
            if region:
                screen_image = pyautogui.screenshot(region=region)
            else:
                screen_image = pyautogui.screenshot()
            screen_bgr = cv2.cvtColor(np.array(screen_image), cv2.COLOR_RGB2BGR)
        else:
            if len(screen_image.shape) == 3:
                screen_bgr = screen_image
            else:
                screen_bgr = None
        
        if screen_bgr is not None:
            screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
        else:
            screen_gray = screen_image

        rule = color_filter if color_filter is not None else self.color_rules.get(target_name)
        all_matches = []
        
        # 遍历所有样板
        for i, template in enumerate(self.templates[target_name]):
            try:
                if template.shape[0] > screen_gray.shape[0] or template.shape[1] > screen_gray.shape[1]:
                    continue
                
                res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
                h, w = template.shape[:2]
                
                # 找到所有大于阈值的位置
                loc = np.where(res >= self.confidence)
                pts = list(zip(*loc[::-1]))
                if not pts:
                    continue

                # 按置信度降序排序
                pts.sort(key=lambda pt: res[pt[1], pt[0]], reverse=True)
                
                sample_checked_peaks = []
                for pt in pts:
                    x, y = pt
                    center_x = pt[0] + w // 2
                    center_y = pt[1] + h // 2
                    
                    if region:
                        center_x += region[0]
                        center_y += region[1]

                    # 局部峰值去重
                    if any(((center_x - p[0])**2 + (center_y - p[1])**2)**0.5 < 20 for p in sample_checked_peaks):
                        continue
                    sample_checked_peaks.append((center_x, center_y))

                    # 颜色校验
                    if rule and screen_bgr is not None:
                        roi = screen_bgr[y:y+h, x:x+w]
                        if not self._verify_color(roi, rule):
                            if self.log:
                                self.log.debug(f"find_all_targets: 目标 [{target_name}] 坐标({center_x}, {center_y}) 未通过颜色校验({rule})，跳过")
                            continue
                    
                    # 全局去重（跨样板去重）
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
    
    def target_exists(self, target_name, screen_image=None, region=None, color_filter=None):
        """
        检查目标是否存在（不返回坐标，仅检查）
        
        返回:
            bool: 是否存在
        """
        return self.find_target(target_name, screen_image=screen_image, region=region, color_filter=color_filter) is not None
