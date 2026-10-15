import pyautogui
import time
import os

pyautogui.FAILSAFE = True

class BotTimeoutError(Exception):
    """步骤执行超时异常"""
    pass

class GameBot:
    def __init__(self, confidence=0.8, assets_dir="assets", log=None, step_timeout=120,
                 window_width=796, window_height=1348, auto_resize_window=False):
        self.confidence = confidence
        self.assets_dir = assets_dir
        self.log = log
        self.step_timeout = step_timeout
        self.window_width = window_width
        self.window_height = window_height
        self.auto_resize_window = auto_resize_window

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
        self.TARGET_GAME_UPDATE = "game_update"
        self.TARGET_ASSISTANT_UPDATE = "assistant_update"

    def ensure_window_state(self, width=None, height=None):
        """
        寻找模拟器窗口（支持 MuMu Player 与 雷电模拟器），将其恢复并激活前台。
        严格绑定模拟器进程 PID，绝不采用模糊标题匹配，杜绝误操作 IDE、浏览器等外部窗口。
        """
        target_w = width if width is not None else self.window_width
        target_h = height if height is not None else self.window_height

        # 绝对排除的外部软件进程黑名单
        EXCLUDED_PROCESSES = {
            "antigravity.exe", "code.exe", "cursor.exe", "chrome.exe",
            "msedge.exe", "firefox.exe", "python.exe", "cmd.exe",
            "powershell.exe", "windowsterminal.exe"
        }

        # 模拟器专属主进程候选 (按优先级排序：优先独立渲染窗口，次选主界面)
        PRIORITY_EMU_PROCS = ["mumunxdevice.exe", "nemuplayer.exe", "dnplayer.exe"]
        SECONDARY_EMU_PROCS = ["mumunxmain.exe"]

        try:
            import pygetwindow as gw
            import psutil
            import win32process
            import win32gui
            import win32con

            # 1. 收集当前运行中的模拟器进程 PID
            p_pids = set()
            s_pids = set()
            for p in psutil.process_iter(['pid', 'name']):
                pname = (p.info.get('name') or '').lower()
                if pname in PRIORITY_EMU_PROCS:
                    p_pids.add(p.info['pid'])
                elif pname in SECONDARY_EMU_PROCS:
                    s_pids.add(p.info['pid'])

            all_windows = gw.getAllWindows()
            target_win = None

            # 2. 优先在渲染核心进程 (mumunxdevice / dnplayer) 中定位
            if p_pids:
                for win in all_windows:
                    if not win.title:
                        continue
                    try:
                        _, win_pid = win32process.GetWindowThreadProcessId(win._hWnd)
                        if win_pid in p_pids:
                            proc_name = psutil.Process(win_pid).name().lower()
                            if proc_name in EXCLUDED_PROCESSES:
                                continue
                            if not win.isMinimized and (win.width < 100 or win.height < 100):
                                continue
                            target_win = win
                            break
                    except Exception:
                        pass

            # 3. 次选：如果独立设备窗口尚未独立分离，在主程序进程 (mumunxmain) 中定位
            if not target_win and s_pids:
                for win in all_windows:
                    if not win.title:
                        continue
                    try:
                        _, win_pid = win32process.GetWindowThreadProcessId(win._hWnd)
                        if win_pid in s_pids:
                            proc_name = psutil.Process(win_pid).name().lower()
                            if proc_name in EXCLUDED_PROCESSES:
                                continue
                            if not win.isMinimized and (win.width < 200 or win.height < 200):
                                continue
                            target_win = win
                            break
                    except Exception:
                        pass

            if not target_win:
                return False

            # 如果最小化，恢复
            if target_win.isMinimized:
                target_win.restore()
                time.sleep(0.3)

            # 强效激活窗口置于前台 (突破 Windows 前台锁定)
            try:
                import win32com.client
                win32gui.ShowWindow(target_win._hWnd, win32con.SW_RESTORE)
                shell = win32com.client.Dispatch("WScript.Shell")
                shell.SendKeys('%')
                win32gui.SetForegroundWindow(target_win._hWnd)
            except Exception:
                target_win.activate()

            # 仅当显式启用了自动调整尺寸配置时才调整模拟器大小，杜绝意外变形
            if self.auto_resize_window and target_w and target_h:
                if target_win.width != target_w or target_win.height != target_h:
                    if self.log:
                        self.log.info(f"检测到模拟器尺寸异常 ({target_win.width}x{target_win.height})，正在还原为标准尺寸 ({target_w}x{target_h})...")
                    target_win.resizeTo(target_w, target_h)
                    time.sleep(1.0)

            return True
        except Exception as e:
            if self.log:
                self.log.debug(f"调整窗口状态异常: {e}")
            return False

    def _click_location(self, x, y):
        pyautogui.click(x, y)
        if self.log:
            self.log.debug(f"点击坐标: ({x}, {y})")

    def check_interrupts(self):
        """全局中断检测，返回 True 表示已处理中断"""
        # 1. 检测断线重连
        pos = self.matcher.find_target(self.TARGET_OFFLINE)
        if pos:
            if self.log:
                self.log.info(">>> 监测到断线重试，正在点击...")
            self._click_location(pos[0], pos[1])
            time.sleep(1)
            return True

        # 2. 检测资源下载
        pos = self.matcher.find_target(self.TARGET_DOWNLOAD)
        if pos:
            if self.log:
                self.log.info(">>> 监测到资源下载，正在点击...")
            self._click_location(pos[0], pos[1])
            time.sleep(1)
            return True

        # 3. 检测游戏本体更新弹窗 (全局)
        pos = self.matcher.find_target(self.TARGET_GAME_UPDATE)
        if pos:
            if self.log:
                self.log.info(">>> 监测到游戏本体更新弹窗，正在消除...")
            self._click_location(pos[0], pos[1])
            time.sleep(1)
            return True

        return False

    def handle_assistant_update(self):
        """专门处理辅助启动后的更新公告。
        不再使用不可靠的亮度感应，而是精准识别带有'开始更新'文字特征的按钮实体。
        """
        # 尝试通过样板匹配寻找真正的'开始更新'按钮
        pos = self.matcher.find_target(self.TARGET_ASSISTANT_UPDATE)
        if pos:
            if self.log:
                self.log.info(">>> [阶段性检测] 发现真正的辅助更新按钮，执行精准点击...")
            self._click_location(pos[0], pos[1])
            # 辅助更新通常伴随较长的加载或自重启
            time.sleep(10)
            return True
            
        return False

    def execute_step(self, success_target, action_target=None, action_index=0,
                     click_offset=None, success_check="exists", action_from_bottom=False,
                     post_wait=2, skip_post_wait=None, click_interval=5.0):
        """通用原子操作

        参数:
            post_wait: 阶段完成后等待的秒数（默认2秒）
            skip_post_wait: 如果未执行点击动作就直接进入下一步时的等待秒数
            click_interval: 按钮重复点击的冷却时间（秒），防止连续点击造成响应混乱
        """
        if self.log:
            self.log.info(f"--- 阶段开始: 等待 {success_target} ---")

        # 确保模拟器窗口激活并处于标准尺寸，以保证模板匹配精度
        self.ensure_window_state()

        start_time = time.time()
        last_click_time = 0
        loop_count = 0
        action_performed = False
        while True:
            # 检查是否超时
            elapsed = time.time() - start_time
            if elapsed > self.step_timeout:
                msg = f"步骤超时: 等待 {success_target} 已超过 {self.step_timeout} 秒"
                if self.log:
                    self.log.error(msg)
                raise BotTimeoutError(msg)

            loop_count += 1

            # 定期重新确认窗口状态，防止重启初期窗口未及时就绪
            if loop_count % 6 == 0:
                self.ensure_window_state()

            if self.check_interrupts():
                continue

            # 检查成功条件
            # 支持单个目标或目标列表
            targets = success_target if isinstance(success_target, list) else [success_target]
            found_break = False

            for target in targets:
                if success_check == "exists":
                    if self.matcher.target_exists(target):
                        if self.log:
                            self.log.info(f"*** 成功检测到 {target} ***")
                        found_break = True
                        break
                else:
                    if not self.matcher.target_exists(target):
                        if self.log:
                            self.log.info(f"*** {target} 已消失 ***")
                        found_break = True
                        break

            if found_break:
                break

            # 执行动作
            # 增加点击冷却时间判定，防止对同一个 action_target 频繁连续点击导致UI响应混乱
            if action_target and (time.time() - last_click_time > click_interval):
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
                            action_performed = True
                            last_click_time = time.time()

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
                        action_performed = True
                        last_click_time = time.time()

                        if click_offset:
                            time.sleep(0.2)
                            off_x, off_y = click_offset
                            self._click_location(x + off_x, y + off_y)
                    else:
                        if self.log and loop_count % 5 == 0:
                            self.log.info(f"等待中... 未找到 {action_target}")

            time.sleep(0.5)

        # 确定最终等待时间
        wait_time = post_wait
        if not action_performed and skip_post_wait is not None:
            wait_time = skip_post_wait
            if self.log:
                self.log.info(f"检测到步骤跳过，使用缩短的等待时间: {wait_time} 秒")

        if self.log:
            self.log.info(f"阶段完成，等待 {wait_time} 秒...")
        time.sleep(wait_time)
        return True

    def run(self):
        """主业务流程"""

        if self.log:
            self.log.info("=" * 50)
            self.log.info("开始游戏自动化流程")
            self.log.info("=" * 50)

        # 此时不再调用前置的 handle_initial_dialogs，因为它是阶段性的

        steps = [
            ("点击IT图标", self.TARGET_IT_FLOAT, self.TARGET_IT, {}),
            ("点击DL_entry", 
             [self.TARGET_START, self.TARGET_USER, self.TARGET_SWITCH, self.TARGET_LOGIN], 
             self.TARGET_DL_ENTRY, {"skip_post_wait": 1}),
            ("点击start", 
             [self.TARGET_USER, self.TARGET_SWITCH, self.TARGET_LOGIN], 
             self.TARGET_START, {"skip_post_wait": 1}),
            ("点击user", 
             [self.TARGET_SWITCH, self.TARGET_LOGIN], 
             self.TARGET_USER, {"post_wait": 4, "skip_post_wait": 1}),
            ("点击switch_account", self.TARGET_LOGIN, self.TARGET_SWITCH, {"post_wait": 3, "skip_post_wait": 1}),
            ("点击最下面login", self.TARGET_LOGIN, self.TARGET_LOGIN, {
                "action_index": 0, "action_from_bottom": True, "success_check": "disappear",
                "post_wait": 5
            }),
            ("点击IT_float偏移", self.TARGET_CONTINUE, self.TARGET_IT_FLOAT, {
                "click_offset": (-280, 0), "post_wait": 2
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

        # 最终阶段：账号切换已完成，等待并处理可能出现的辅助更新弹窗
        if failed_step is None:
            if self.log:
                self.log.info("\n--- 进入最终收尾阶段：监测辅助更新 ---")
            
            # 循环监测，因为辅助更新界面加载可能较慢，给予更充裕的等待时间（约30秒）
            max_retries = 15
            for i in range(max_retries):
                if self.handle_assistant_update():
                    if self.log:
                        self.log.info("收尾阶段：辅助更新已处理。")
                    break
                
                if self.log and (i + 1) % 5 == 0:
                    self.log.info(f"收尾阶段：持续监测辅助更新中 ({i + 1}/{max_retries})...")
                
                time.sleep(2)

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
