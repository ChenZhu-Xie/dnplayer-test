import pyautogui
import time
import os

pyautogui.FAILSAFE = True

class GameBot:
    def __init__(self, confidence=0.8, assets_dir="assets", log=None):
        self.confidence = confidence
        self.assets_dir = assets_dir
        self.log = log
        
        # 导入 TemplateMatcher
        from .template_matcher import TemplateMatcher
        self.matcher = TemplateMatcher(
            assets_dir=assets_dir,
            confidence=confidence,
            log=log
        )
        
        # 定义逻辑目标名称（对应文件夹名）
        self.TARGET_IT = "IT"
        self.TARGET_IT_FLOAT = "IT_float"
        self.TARGET_DL_ENTRY = "DL_entry"
        self.TARGET_START = "start"
        self.TARGET_USER = "user"
        self.TARGET_SWITCH = "switch_account"
        self.TARGET_LOGIN = "login"
        self.TARGET_CONTINUE = "continue"
        self.TARGET_OFFLINE = "offline_retry"
        self.TARGET_DOWNLOAD = "download_resources"
        self.TARGET_UPDATE = "update_needed"

    def _click_location(self, x, y):
        pyautogui.click(x, y)
        if self.log:
            self.log.debug(f"点击坐标: ({x}, {y})")

    def check_interrupts(self):
        """全局中断检测，返回 True 表示已处理中断"""
        # 检测断线重连
        pos = self.matcher.find_target(self.TARGET_OFFLINE)
        if pos:
            if self.log:
                self.log.info(">>> 监测到断线重试，正在点击...")
            self._click_location(pos[0], pos[1])
            time.sleep(1)
            return True

        # 检测资源下载
        pos = self.matcher.find_target(self.TARGET_DOWNLOAD)
        if pos:
            if self.log:
                self.log.info(">>> 监测到资源下载，正在点击...")
            self._click_location(pos[0], pos[1])
            time.sleep(1)
            return True

        # 检测更新弹窗
        pos = self.matcher.find_target(self.TARGET_UPDATE)
        if pos:
            if self.log:
                self.log.info(">>> 监测到更新弹窗，正在消除...")
            x, y = pos
            self._click_location(x, y + 300)
            time.sleep(1)
            return True

        return False

    def execute_step(self, success_target, action_target=None, action_index=0, 
                     click_offset=None, success_check="exists", action_from_bottom=False):
        """通用原子操作"""
        if self.log:
            self.log.info(f"--- 阶段开始: 等待 {success_target} ---")
        
        loop_count = 0
        while True:
            loop_count += 1
            
            if self.check_interrupts():
                continue

            # 检查成功条件
            if success_check == "exists":
                if self.matcher.target_exists(success_target):
                    if self.log:
                        self.log.info(f"*** 成功检测到 {success_target} ***")
                    break
            else:
                if not self.matcher.target_exists(success_target):
                    if self.log:
                        self.log.info(f"*** {success_target} 已消失 ***")
                    break

            # 执行动作
            if action_target:
                if action_from_bottom:
                    all_matches = self.matcher.find_all_targets(action_target)
                    if all_matches:
                        actual_index = -(action_index + 1)
                        if len(all_matches) > action_index:
                            target = all_matches[actual_index]
                            x, y = target
                            
                            if self.log:
                                self.log.info(f"点击 {action_target} (从下往上第 {action_index + 1} 个)")
                            
                            self._click_location(x, y)
                            
                            if click_offset:
                                time.sleep(0.2)
                                off_x, off_y = click_offset
                                self._click_location(x + off_x, y + off_y)
                else:
                    pos = self.matcher.find_target(action_target)
                    if pos:
                        x, y = pos
                        
                        if self.log:
                            self.log.info(f"点击 {action_target}")
                        
                        self._click_location(x, y)
                        
                        if click_offset:
                            time.sleep(0.2)
                            off_x, off_y = click_offset
                            self._click_location(x + off_x, y + off_y)
                    else:
                        if self.log and loop_count % 5 == 0:
                            self.log.info(f"等待中... 未找到 {action_target}")

            time.sleep(0.5)

        if self.log:
            self.log.info("阶段完成，等待 2 秒...")
        time.sleep(2)
        return True

    def run(self):
        """主业务流程"""
        
        if self.log:
            self.log.info("=" * 50)
            self.log.info("开始游戏自动化流程")
            self.log.info("=" * 50)
        
        steps = [
            ("点击IT图标", self.TARGET_IT_FLOAT, self.TARGET_IT, {}),
            ("点击DL_entry", self.TARGET_START, self.TARGET_DL_ENTRY, {}),
            ("点击user", self.TARGET_SWITCH, self.TARGET_USER, {}),
            ("点击switch_account", self.TARGET_LOGIN, self.TARGET_SWITCH, {}),
            ("点击最下面login", self.TARGET_LOGIN, self.TARGET_LOGIN, {
                "action_index": 0, "action_from_bottom": True, "success_check": "disappear"
            }),
            ("点击IT_float偏移", self.TARGET_CONTINUE, self.TARGET_IT_FLOAT, {
                "click_offset": (-280, 0)
            }),
            ("点击continue直到消失", self.TARGET_CONTINUE, self.TARGET_CONTINUE, {
                "success_check": "disappear"
            }),
        ]
        
        completed_steps = 0
        failed_step = None
        
        for i, (step_name, success_target, action_target, kwargs) in enumerate(steps, 1):
            if self.log:
                self.log.info(f"\n[步骤 {i}/{len(steps)}] {step_name}")
            
            try:
                success = self.execute_step(
                    success_target=success_target,
                    action_target=action_target,
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
