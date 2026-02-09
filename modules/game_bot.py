import pyautogui
import time
import os

pyautogui.FAILSAFE = True

class GameBot:
    def __init__(self, confidence=0.8, assets_dir="assets", log=None):
        self.confidence = confidence
        self.assets_dir = assets_dir
        self.log = log
        
        # 核心流程图片
        self.img_it = os.path.join(assets_dir, "IT.png")
        self.img_it_float = os.path.join(assets_dir, "IT_float.png")
        self.img_dl_entry = os.path.join(assets_dir, "DL_entry.png")
        self.img_start = os.path.join(assets_dir, "start.png")
        self.img_user = os.path.join(assets_dir, "user.png")
        self.img_switch = os.path.join(assets_dir, "switch_account.png")
        self.img_login = os.path.join(assets_dir, "login.png")
        self.img_continue = os.path.join(assets_dir, "continue.png")
        
        # 异常/中断图片
        self.img_offline = os.path.join(assets_dir, "offline_retry.png")
        self.img_download = os.path.join(assets_dir, "download_resources.png")
        self.img_update = os.path.join(assets_dir, "update_needed.png")

    def _get_path(self, filename):
        return os.path.join(self.assets_dir, filename)

    def _click_location(self, x, y):
        pyautogui.click(x, y)
        if self.log:
            self.log.debug(f"点击坐标: ({x}, {y})")

    def _find_all(self, image_path):
        try:
            return list(pyautogui.locateAllOnScreen(image_path, confidence=self.confidence))
        except:
            return []

    def _find_one(self, image_path):
        try:
            return pyautogui.locateOnScreen(image_path, confidence=self.confidence)
        except:
            return None

    def check_interrupts(self):
        """
        全局中断检测 - 每轮循环都要执行
        返回 True 表示发生了中断并已处理
        """
        # 1. 检测断线重连
        if os.path.exists(self.img_offline):
            loc = self._find_one(self.img_offline)
            if loc:
                if self.log:
                    self.log.info(">>> 监测到断线重试，正在点击...")
                x, y = pyautogui.center(loc)
                self._click_location(x, y)
                time.sleep(1)
                return True

        # 2. 检测资源下载
        if os.path.exists(self.img_download):
            loc = self._find_one(self.img_download)
            if loc:
                if self.log:
                    self.log.info(">>> 监测到资源下载，正在点击...")
                x, y = pyautogui.center(loc)
                self._click_location(x, y)
                time.sleep(1)
                return True

        # 3. 检测更新弹窗 (特殊处理：点击窗口外部)
        if os.path.exists(self.img_update):
            loc = self._find_one(self.img_update)
            if loc:
                if self.log:
                    self.log.info(">>> 监测到更新弹窗，正在消除...")
                x, y = pyautogui.center(loc)
                # 往下移 300 像素点击
                self._click_location(x, y + 300)
                time.sleep(1)
                return True

        return False

    def execute_step(self, success_image, action_image=None, action_index=0, 
                     click_offset=None, success_check="exists", action_from_bottom=False):
        """
        通用原子操作：一直循环直到 success_image 出现
        
        参数:
            success_image: 成功标志图片路径
            action_image: 需要点击的目标图片路径
            action_index: 如果屏幕有多个 action_image，点击第几个
            click_offset: 点击 action_image 后的额外偏移点击 (dx, dy)
            success_check: "exists" (存在即成功) 或 "disappear" (消失即成功)
            action_from_bottom: 是否从底部开始计数（默认False表示从上到下）
        """
        if self.log:
            self.log.info(f"--- 阶段开始: 等待 {os.path.basename(success_image)} ---")
        
        loop_count = 0
        while True:
            loop_count += 1
            
            # 1. 优先检查异常状态
            if self.check_interrupts():
                continue

            # 2. 检查成功条件
            if success_check == "exists":
                if self._find_one(success_image):
                    if self.log:
                        self.log.info(f"*** 成功检测到 {os.path.basename(success_image)}，本阶段结束 ***")
                    break
            else:  # disappear
                if not self._find_one(success_image):
                    if self.log:
                        self.log.info(f"*** {os.path.basename(success_image)} 已消失，本阶段结束 ***")
                    break

            # 3. 执行动作
            if action_image and os.path.exists(action_image):
                targets = self._find_all(action_image)
                
                # 如果需要从底部计数，先按Y坐标排序
                if action_from_bottom and targets:
                    targets.sort(key=lambda t: t.top)
                    # 从底部取目标
                    actual_index = -(action_index + 1)
                else:
                    actual_index = action_index
                
                if len(targets) > action_index:
                    target = targets[actual_index]
                    x, y = pyautogui.center(target)
                    
                    # 记录是从底部还是顶部选择
                    pos_desc = f"第 {action_index + 1} 个"
                    if action_from_bottom:
                        pos_desc = f"从下往上第 {action_index + 1} 个"
                    
                    if self.log:
                        self.log.info(f"点击 {os.path.basename(action_image)} ({pos_desc})")
                    
                    self._click_location(x, y)
                    
                    # 偏移点击
                    if click_offset:
                        time.sleep(0.2)
                        off_x, off_y = click_offset
                        self._click_location(x + off_x, y + off_y)
                        if self.log:
                            self.log.info(f"偏移点击: ({x + off_x}, {y + off_y})")
                else:
                    if self.log and loop_count % 5 == 0:
                        self.log.info(f"等待中... 未找到操作目标 {os.path.basename(action_image)}")

            time.sleep(0.5)

            # 阶段完成后统一等待 2 秒
        if self.log:
            self.log.info("阶段完成，等待 2 秒...")
        time.sleep(2)
        return True

    def run(self):
        """主业务流程，返回执行状态"""
        
        if self.log:
            self.log.info("=" * 50)
            self.log.info("开始游戏自动化流程")
            self.log.info("=" * 50)
        
        # 定义步骤列表
        steps = [
            ("点击IT图标", self.img_it, self.img_it_float, {"action": "click"}),
            ("点击DL_entry", self.img_dl_entry, self.img_start, {"action": "click"}),
            ("点击user", self.img_user, self.img_switch, {"action": "click"}),
            ("点击switch_account", self.img_switch, self.img_login, {"action": "click"}),
            ("点击最下面login", self.img_login, self.img_login, {
                "action": "click", "action_index": 0, "action_from_bottom": True, "success_check": "disappear"
            }),
            ("点击IT_float偏移", self.img_it_float, self.img_continue, {
                "action": "click", "click_offset": (-280, 0)
            }),
            ("点击continue直到消失", self.img_continue, self.img_continue, {
                "action": "click", "success_check": "disappear"
            }),
        ]
        
        completed_steps = 0
        failed_step = None
        
        for i, (step_name, action_img, success_img, kwargs) in enumerate(steps, 1):
            if self.log:
                self.log.info(f"\n[步骤 {i}/{len(steps)}] {step_name}")
            
            try:
                success = self.execute_step(
                    success_image=success_img,
                    action_image=action_img,
                    **kwargs
                )
                if success:
                    completed_steps += 1
                else:
                    failed_step = step_name
                    if self.log:
                        self.log.error(f"步骤失败: {step_name}")
                    break
            except Exception as e:
                failed_step = step_name
                if self.log:
                    self.log.error(f"步骤异常: {step_name} - {e}")
                break
        
        if self.log:
            self.log.info("=" * 50)
            if failed_step:
                self.log.info(f"流程中断，失败步骤: {failed_step}")
            else:
                self.log.info("所有自动化流程执行完毕")
            self.log.info("=" * 50)
        
        return {
            "success": failed_step is None,
            "completed_steps": completed_steps,
            "total_steps": len(steps),
            "failed_step": failed_step
        }
