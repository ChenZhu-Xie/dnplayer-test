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
                     click_offset=None, success_check="exists"):
        """
        通用原子操作：一直循环直到 success_image 出现
        
        参数:
            success_image: 成功标志图片路径
            action_image: 需要点击的目标图片路径
            action_index: 如果屏幕有多个 action_image，点击第几个
            click_offset: 点击 action_image 后的额外偏移点击 (dx, dy)
            success_check: "exists" (存在即成功) 或 "disappear" (消失即成功)
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
                if len(targets) > action_index:
                    target = targets[action_index]
                    x, y = pyautogui.center(target)
                    
                    if self.log:
                        self.log.info(f"点击 {os.path.basename(action_image)} (第 {action_index + 1} 个)")
                    
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

    def run(self):
        """主业务流程"""
        
        if self.log:
            self.log.info("=" * 50)
            self.log.info("开始游戏自动化流程")
            self.log.info("=" * 50)
        
        # 修复 2: 新增前置步骤
        # 步骤 0: 点击 IT.png，直到 IT_float 出现
        self.execute_step(
            success_image=self.img_it_float,
            action_image=self.img_it
        )

        # 步骤 1: 点击 DL_entry，直到 start 出现
        self.execute_step(
            success_image=self.img_start,
            action_image=self.img_dl_entry
        )

        # 步骤 2: 点击 user，直到 switch_account 出现
        self.execute_step(
            success_image=self.img_switch,
            action_image=self.img_user
        )

        # 步骤 3: 点击 switch_account，直到 login 出现
        self.execute_step(
            success_image=self.img_login,
            action_image=self.img_switch
        )

        # 修复 1: 点击第 2 个 login 按钮，直到 login 消失
        # action_index=1 表示点击第 2 个匹配项（从上到下排序）
        self.execute_step(
            success_image=self.img_login,
            action_image=self.img_login,
            action_index=1,
            success_check="disappear"
        )

        # 步骤 5: 点击 IT_float 及其偏移，直到 continue 出现
        # 需求：点击按钮，然后立马点击左边 80px
        self.execute_step(
            success_image=self.img_continue,
            action_image=self.img_it_float,
            click_offset=(-80, 0)
        )

        # 步骤 6: 点击 continue 直到它消失
        self.execute_step(
            success_image=self.img_continue,
            action_image=self.img_continue,
            success_check="disappear"
        )

        if self.log:
            self.log.info("=" * 50)
            self.log.info("所有自动化流程执行完毕")
            self.log.info("=" * 50)
