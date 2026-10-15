import psutil
import subprocess
import time
import os
import winreg
import json

# 支持的模拟器候选进程列表（优先匹配 MuMu，兼容雷电）
MUMU_PROCESS_NAMES = ["MuMuNxDevice.exe", "MuMuNxMain.exe", "MuMuManager.exe", "NemuPlayer.exe", "NemuHeadless.exe"]
LD_PROCESS_NAMES = ["dnplayer.exe"]
ALL_PROCESS_NAMES = MUMU_PROCESS_NAMES + LD_PROCESS_NAMES

PROCESS_NAME = "MuMuNxMain.exe"

def get_running_process(process_names=None):
    """
    检查指定候选进程是否运行。
    如果运行，返回 (完整路径, 进程对象, 进程名)；
    如果不运行，返回 (None, None, None)。
    """
    if process_names is None:
        process_names = ALL_PROCESS_NAMES
    
    # 统一小写比较
    names_lower = [name.lower() for name in process_names]
    
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            pname = proc.info.get('name')
            if pname and pname.lower() in names_lower:
                return proc.info.get('exe'), proc, pname
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None, None, None

def get_running_process_path(proc_name):
    """兼容旧接口"""
    exe_path, proc, _ = get_running_process([proc_name] if isinstance(proc_name, str) else proc_name)
    return exe_path, proc

def find_mumu_manager(hint_paths=None):
    """
    寻找 MuMuManager.exe 命令行工具路径
    """
    candidates = []
    if hint_paths:
        if isinstance(hint_paths, str):
            hint_paths = [hint_paths]
        for hp in hint_paths:
            if not hp:
                continue
            if hp.lower().endswith("mumumanager.exe") and os.path.exists(hp):
                return hp
            d = os.path.dirname(hp)
            c1 = os.path.join(d, "MuMuManager.exe")
            c2 = os.path.join(d, "nx_main", "MuMuManager.exe")
            if os.path.exists(c1):
                return c1
            if os.path.exists(c2):
                return c2
    
    # 从注册表寻找
    reg_path = find_path_from_registry()
    if reg_path:
        d = os.path.dirname(reg_path)
        c1 = os.path.join(d, "MuMuManager.exe")
        c2 = os.path.join(d, "nx_main", "MuMuManager.exe")
        if os.path.exists(c1):
            return c1
        if os.path.exists(c2):
            return c2
            
    return None

def find_path_from_registry():
    """
    尝试从 Windows 注册表查找模拟器安装路径。
    优先查找 MuMu Player (MuMu 12 / MuMu 6)，次选雷电模拟器 (LDPlayer)。
    """
    # 1. 优先检查 MuMuPlayerGlobal 专用卸载项
    direct_keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\MuMuPlayerGlobal"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\MuMuPlayerGlobal"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\MuMuPlayerGlobal"),
    ]
    for root, subkey in direct_keys:
        try:
            with winreg.OpenKey(root, subkey) as k:
                try:
                    uninst = winreg.QueryValueEx(k, "UninstallString")[0].strip('"\r\n ')
                    base_dir = os.path.dirname(uninst)
                    mumu_main = os.path.join(base_dir, "nx_main", "MuMuNxMain.exe")
                    if os.path.exists(mumu_main):
                        return mumu_main
                except Exception:
                    pass
                try:
                    icon = winreg.QueryValueEx(k, "DisplayIcon")[0].strip('"\r\n ')
                    if os.path.exists(icon) and icon.lower().endswith(".exe"):
                        return icon
                except Exception:
                    pass
        except Exception:
            pass

    # 2. 遍历卸载列表查找 MuMu / Nemu / LDPlayer / 雷电模拟器
    uninstall_roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
    ]
    
    # 候选结果列表（按优先级：MuMu > LDPlayer）
    mumu_candidates = []
    ld_candidates = []
    
    for root, reg_path in uninstall_roots:
        try:
            with winreg.OpenKey(root, reg_path) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                for i in range(num_subkeys):
                    try:
                        sub_key_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sub_key_name) as sub_key:
                            try:
                                display_name = winreg.QueryValueEx(sub_key, "DisplayName")[0]
                                disp_lower = display_name.lower()
                                
                                # MuMu 模拟器
                                if "mumu" in disp_lower or "nemu" in disp_lower:
                                    for prop in ["UninstallString", "InstallLocation", "DisplayIcon"]:
                                        try:
                                            val = winreg.QueryValueEx(sub_key, prop)[0].strip('"\r\n ')
                                            if os.path.isfile(val):
                                                d = os.path.dirname(val)
                                                p = os.path.join(d, "nx_main", "MuMuNxMain.exe")
                                                if os.path.exists(p):
                                                    mumu_candidates.append(p)
                                                elif os.path.exists(val) and val.endswith(".exe"):
                                                    mumu_candidates.append(val)
                                            elif os.path.isdir(val):
                                                p = os.path.join(val, "nx_main", "MuMuNxMain.exe")
                                                if os.path.exists(p):
                                                    mumu_candidates.append(p)
                                        except Exception:
                                            pass
                                
                                # 雷电模拟器
                                elif "ldplayer" in disp_lower or "雷电模拟器" in disp_lower:
                                    try:
                                        install_loc = winreg.QueryValueEx(sub_key, "InstallLocation")[0].strip('"\r\n ')
                                        full_path = os.path.join(install_loc, "dnplayer.exe")
                                        if os.path.exists(full_path):
                                            ld_candidates.append(full_path)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    except Exception:
                        pass
        except Exception:
            pass

    if mumu_candidates:
        return mumu_candidates[0]
    if ld_candidates:
        return ld_candidates[0]
        
    return None

def kill_process(proc, log=None):
    """优雅或强制关闭进程"""
    try:
        proc_name = proc.name()
        if log:
            log.info(f"检测到 {proc_name} 正在运行 (PID: {proc.pid})，正在关闭...")
        else:
            print(f"检测到 {proc_name} 正在运行 (PID: {proc.pid})，正在关闭...")
        
        proc.terminate()  # 尝试优雅关闭
        proc.wait(timeout=5)
        
        if log:
            log.info(f"进程 {proc.pid} 已优雅关闭")
    except psutil.TimeoutExpired:
        if log:
            log.warning("进程响应超时，正在强制查杀...")
        else:
            print("进程响应超时，正在强制查杀...")
        proc.kill()  # 强制关闭
    except Exception as e:
        if log:
            log.error(f"关闭进程时出错: {e}")
        else:
            print(f"关闭进程时出错: {e}")

def kill_all_emulator_processes(log=None):
    """关闭所有运行中的模拟器相关进程"""
    killed = False
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = proc.info.get('name')
            if name and name.lower() in [n.lower() for n in ALL_PROCESS_NAMES]:
                kill_process(proc, log)
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return killed

def start_process(exe_path, log=None, args=None):
    """启动程序"""
    if exe_path and os.path.exists(exe_path):
        cmd = [exe_path]
        if args:
            cmd.extend(args)
        if log:
            log.info(f"正在启动: {' '.join(cmd)}")
        else:
            print(f"正在启动: {' '.join(cmd)}")
        
        # 使用 subprocess.Popen 非阻塞启动，cwd参数确保在程序目录下运行，避免缺失DLL
        work_dir = os.path.dirname(exe_path)
        subprocess.Popen(cmd, cwd=work_dir, shell=False)
        return True
    else:
        if log:
            log.error(f"错误：找不到文件路径 {exe_path}")
        else:
            print(f"错误：找不到文件路径 {exe_path}")
        return False

def get_mumu_running_vms(mumu_manager_path, log=None):
    """
    通过 MuMuManager 获取所有 VM 信息，返回 running vm index 列表
    """
    try:
        res = subprocess.run([mumu_manager_path, "info", "-v", "all"],
                             capture_output=True, text=True, encoding="utf-8", timeout=10)
        if res.returncode == 0 and res.stdout:
            data = json.loads(res.stdout)
            running_vms = []
            for vm_idx, info in data.items():
                if info.get("is_process_started") or info.get("player_state") == "start_finished":
                    running_vms.append(vm_idx)
            return running_vms, data
    except Exception as e:
        if log:
            log.debug(f"获取 MuMuManager info 失败: {e}")
    return [], {}

def kill_and_reboot_mumu_device(mumu_manager_path, vm_index="1", wait_seconds_after_kill=3, timeout=60, log=None):
    """
    针对 MuMu 实例（如 device-1）执行严格的关闭 -> 确认无进程 -> 等待缓冲 -> 重启 (reboot) 流程：
    1. 查询当前实例状态与相关 PID；
    2. 若正在运行，发送 shutdown 优雅退出，超时若有残留则强制查杀；
    3. 严格轮询确认系统中已无任何该实例的渲染进程；
    4. 缓冲等待指定时间（默认 3 秒）以释放显卡句柄与网络端口；
    5. 调用 launch 重启 device 进程，并等待加载就绪、呼出前台窗口。
    """
    target_vm = str(vm_index) if (vm_index and vm_index != "auto") else "1"
    
    # 1. 查询当前实例状态与相关 PID
    dev_pid = None
    headless_pid = None
    is_running = False
    
    try:
        res = subprocess.run([mumu_manager_path, "info", "-v", target_vm],
                             capture_output=True, text=True, encoding="utf-8", timeout=8)
        if res.returncode == 0 and res.stdout:
            info = json.loads(res.stdout)
            is_running = info.get("is_process_started", False) or info.get("player_state") == "start_finished"
            dev_pid = info.get("pid")
            headless_pid = info.get("headless_pid")
    except Exception as e:
        if log:
            log.debug(f"获取 MuMuManager info 异常: {e}")

    # 兜底：若命令行未检出正在运行，但系统进程存在渲染核心
    if not is_running:
        _, dev_proc, _ = get_running_process(["mumunxdevice.exe"])
        if dev_proc:
            is_running = True
            dev_pid = dev_proc.pid

    # 2. 如果正在运行，执行关闭/查杀流程
    if is_running:
        pid_info = f" (渲染PID: {dev_pid}" + (f", 无头PID: {headless_pid})" if headless_pid else ")")
        if log:
            log.info(f"检测到 device-{target_vm} 正在运行{pid_info}，正在执行关闭...")
        
        # 发送 shutdown 命令
        try:
            subprocess.run([mumu_manager_path, "control", "-v", target_vm, "shutdown"],
                           capture_output=True, text=True, encoding="utf-8", timeout=10)
        except Exception as e:
            if log:
                log.warning(f"发送 shutdown 命令异常: {e}")
                
        # 轮询等待进程正常退出（最多等待 8 秒）
        wait_shutdown_start = time.time()
        graceful_exit = False
        while time.time() - wait_shutdown_start < 8:
            time.sleep(1)
            still_alive = False
            for p_id in [dev_pid, headless_pid]:
                if p_id and psutil.pid_exists(p_id):
                    still_alive = True
                    break
            if not still_alive:
                graceful_exit = True
                break
                
        # 若仍有残留，强制强杀
        if not graceful_exit:
            if log:
                log.warning(f"device-{target_vm} 退出响应超时，正在强制查杀残留进程...")
            for p_id in [dev_pid, headless_pid]:
                if p_id and psutil.pid_exists(p_id):
                    try:
                        p = psutil.Process(p_id)
                        p.kill()
                        if log:
                            log.info(f"已强制终止 PID: {p_id}")
                    except Exception:
                        pass
            # 查杀所有残留的 mumunxdevice.exe
            for proc in psutil.process_iter(['name']):
                try:
                    if (proc.info.get('name') or '').lower() == "mumunxdevice.exe":
                        proc.kill()
                except Exception:
                    pass

    # 3. 严格确认无进程阶段：轮询检查确保系统中完全没有 device 渲染进程
    if log:
        log.info(f"正在确认 device-{target_vm} 进程完全退出...")
    confirm_timeout = 10
    confirm_start = time.time()
    while time.time() - confirm_start < confirm_timeout:
        running = False
        try:
            res = subprocess.run([mumu_manager_path, "info", "-v", target_vm],
                                 capture_output=True, text=True, encoding="utf-8", timeout=5)
            if res.returncode == 0 and res.stdout:
                info = json.loads(res.stdout)
                if info.get("is_process_started"):
                    running = True
        except Exception:
            pass
            
        for proc in psutil.process_iter(['name']):
            try:
                if (proc.info.get('name') or '').lower() == "mumunxdevice.exe":
                    running = True
                    break
            except Exception:
                pass
                
        if not running:
            break
        time.sleep(1)

    if log:
        log.info(f"[OK] 确认 device-{target_vm} 进程已完全退出，系统无残留")
        log.info(f"安全缓冲等待中 ({wait_seconds_after_kill} 秒)，等待端口与显存句柄彻底释放...")
    time.sleep(wait_seconds_after_kill)

    # 4. 重新启动 (reboot / launch) device-1 进程
    if log:
        log.info(f"正在重新启动(reboot) device-{target_vm} 进程...")
        
    _, main_proc, _ = get_running_process(["mumunxmain.exe"])
    mumu_dir = os.path.dirname(mumu_manager_path)
    mumu_main = os.path.join(mumu_dir, "MuMuNxMain.exe")
    
    if not main_proc and os.path.exists(mumu_main):
        if log:
            log.info(f"模拟器主程序未运行，直接通过主程序启动实例 [{target_vm}]...")
        start_process(mumu_main, log=log, args=["-v", str(target_vm)])
    else:
        try:
            cmd = [mumu_manager_path, "control", "-v", str(target_vm), "launch"]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=15)
            if res.returncode != 0 and log:
                log.warning(f"MuMuManager launch 返回非零: {res.stderr or res.stdout}")
        except Exception as e:
            if log:
                log.error(f"调用 MuMuManager launch 异常: {e}")
                return False

    # 5. 等待加载就绪并呼出前台窗口
    ready = wait_for_emulator_ready(mumu_mgr=mumu_manager_path, vm_index=target_vm, timeout=timeout, log=log)
    if ready:
        time.sleep(2)
        try:
            subprocess.run([mumu_manager_path, "control", "-v", str(target_vm), "show_window"],
                           capture_output=True, text=True, encoding="utf-8", timeout=8)
            if log:
                log.info(f"[OK] 已呼出 device-{target_vm} 前台窗口")
        except Exception:
            pass
        return True
    else:
        if log:
            log.warning(f"device-{target_vm} 启动未在超时时间内就绪")
        return False

# 保持兼容旧名称
def restart_via_mumu_manager(mumu_manager_path, vm_index=None, log=None):
    return kill_and_reboot_mumu_device(mumu_manager_path, vm_index=vm_index, wait_seconds_after_kill=3, timeout=60, log=log)


def wait_for_device_process(timeout=30, log=None):
    """等待模拟器渲染进程出现"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        _, proc, name = get_running_process(["mumunxdevice.exe", "nemuplayer.exe", "dnplayer.exe"])
        if proc:
            if log:
                log.info(f"[OK] 检测到模拟器实例画面已就绪 (进程: {name}, PID: {proc.pid})")
            time.sleep(2)
            return True
        time.sleep(1)
    if log:
        log.warning("提示：尚未检测到模拟器实例窗口，请确认实例是否已在 MuMu 中启动")
    return False

def ensure_emulator_running(emulator_path=None, vm_index=None, auto_find_registry=True, log=None):
    """
    确保模拟器处于运行状态并呼出前台窗口。
    1. 若设备渲染进程 (MuMuNxDevice.exe / dnplayer.exe) 已在运行：直接使用；
    2. 若仅主外壳 (MuMuNxMain.exe) 运行但实例未开：调用 MuMuManager launch + show_window 呼出实例；
    3. 若完全未运行：启动 MuMuNxMain.exe -v <target_vm> 带参数启动桌面主程序并显示前台。
    """
    target_vm = vm_index if (vm_index and vm_index != "auto") else "1"
    
    # 1. 检查设备渲染进程是否已经在运行
    dev_exe, dev_proc, dev_name = get_running_process(["mumunxdevice.exe", "nemuplayer.exe", "dnplayer.exe"])
    if dev_proc:
        if log:
            log.info(f"[OK] 模拟器实例已在运行中 (PID: {dev_proc.pid}, 进程: {dev_name})，跳过冷启动")
        return True

    paths_to_check = []
    if isinstance(emulator_path, list):
        paths_to_check.extend(emulator_path)
    elif emulator_path:
        paths_to_check.append(emulator_path)

    mumu_mgr = find_mumu_manager(paths_to_check)

    # 2. 检查主界面外壳进程是否在运行
    main_exe, main_proc, _ = get_running_process(["mumunxmain.exe"])
    if main_proc:
        if log:
            log.info(f"检测到 MuMu 模拟器主程序已打开 (PID: {main_proc.pid})，正在启动并呼出实例 [{target_vm}] 前台窗口...")
        if mumu_mgr:
            try:
                subprocess.run([mumu_mgr, "control", "-v", str(target_vm), "launch"], capture_output=True, timeout=10)
                time.sleep(2)
                subprocess.run([mumu_mgr, "control", "-v", str(target_vm), "show_window"], capture_output=True, timeout=10)
            except Exception as e:
                if log:
                    log.debug(f"尝试呼出窗口异常: {e}")
        return wait_for_device_process(timeout=30, log=log)

    # 3. 如果完全未运行，启动主程序界面 (MuMuNxMain.exe -v <target_vm>)
    if log:
        log.info(f"模拟器当前未运行，正在启动桌面主程序并载入实例 [{target_vm}]...")

    valid_path = None
    for p in paths_to_check:
        if p and os.path.exists(p) and "mumunxmain.exe" in p.lower():
            valid_path = p
            break
            
    if not valid_path and auto_find_registry:
        valid_path = find_path_from_registry()

    if not valid_path:
        for p in paths_to_check:
            if p and os.path.exists(p):
                valid_path = p
                break

    if valid_path:
        launch_args = []
        if "mumunxmain.exe" in valid_path.lower():
            launch_args = ["-v", str(target_vm)]
        start_process(valid_path, log=log, args=launch_args)
        if log:
            log.info(f"已发送启动实例 [{target_vm}] 命令，等待模拟器主界面及实例就绪...")
        # 稍后调用 show_window 确保前台置顶
        if mumu_mgr:
            time.sleep(3)
            try:
                subprocess.run([mumu_mgr, "control", "-v", str(target_vm), "show_window"], capture_output=True, timeout=5)
            except Exception:
                pass
        return wait_for_device_process(timeout=60, log=log)
    else:
        if log:
            log.error("错误：未能找到模拟器可执行文件路径，请在 config.json 中检查配置")
        return False

def restart_emulator(emulator_path=None, vm_index=None, auto_find_registry=True, log=None):
    """
    重启模拟器（优先支持 MuMu Player，兼顾 LDPlayer）
    启动后立即返回，不阻塞等待，由视觉模块负责检测启动完成
    
    参数:
        emulator_path: 模拟器可执行文件路径（支持字符串或路径列表）
        vm_index: MuMu 模拟器实例编号 (例如 '1', '0' 或 'auto')
        auto_find_registry: 是否尝试从注册表自动查找路径
        log: 日志记录器对象
    """
    if log:
        log.info(f"--- 开始重启模拟器 ---")
    
    # 整理候选路径列表
    paths_to_check = []
    if isinstance(emulator_path, list):
        paths_to_check.extend(emulator_path)
    elif emulator_path:
        paths_to_check.append(emulator_path)
        
    valid_path = None
    for path in paths_to_check:
        if path and os.path.exists(path):
            valid_path = path
            break
            
    if not valid_path and auto_find_registry:
        if log:
            log.info("未找到配置路径，尝试从注册表查找模拟器安装路径...")
        valid_path = find_path_from_registry()
        if valid_path and log:
            log.info(f"从注册表找到路径: {valid_path}")

    # 1. 如果能够定位 MuMuManager.exe，优先使用官方 CLI 接口进行优雅重启
    mumu_mgr = find_mumu_manager([valid_path] + paths_to_check)
    target_vm = vm_index if (vm_index and vm_index != "auto") else "1"
    if mumu_mgr:
        if log:
            log.info(f"检测到 MuMuManager: {mumu_mgr}")
        if kill_and_reboot_mumu_device(mumu_mgr, vm_index=target_vm, wait_seconds_after_kill=3, timeout=60, log=log):
            return True
        if log:
            log.warning("MuMuManager 控制失败，退回传统进程管理方式...")

    # 2. 传统进程模式：查杀、严格确认退出、缓冲后重新启动
    running_exe, proc, proc_name = get_running_process()
    if proc:
        kill_all_emulator_processes(log)
        if log:
            log.info("正在确认模拟器进程完全退出...")
        t_start = time.time()
        while time.time() - t_start < 10:
            _, alive_proc, _ = get_running_process()
            if not alive_proc:
                break
            time.sleep(1)
        if log:
            log.info("[OK] 模拟器进程已完全退出，缓冲等待 3 秒释放显存与句柄...")
        time.sleep(3)
        
        target_launch = valid_path or running_exe
        if target_launch:
            start_process(target_launch, log)
        else:
            if log:
                log.error("错误：未能找到可执行文件路径以重新启动模拟器")
    else:
        if log:
            log.info("模拟器未运行，准备启动...")
        if valid_path:
            start_process(valid_path, log)
        else:
            if log:
                log.error("错误：未找到运行中的进程，且未能找到有效安装路径")
                
    wait_for_emulator_ready(mumu_mgr=None, vm_index=None, timeout=60, log=log)
    return True

def wait_for_emulator_ready(mumu_mgr=None, vm_index=None, timeout=60, log=None):
    """等待模拟器完成重启并就绪"""
    start_time = time.time()
    if log:
        log.info(f"正在等待模拟器加载就绪 (最大等待 {timeout} 秒)...")
    
    # 基础缓冲 3 秒
    time.sleep(3)
    
    while time.time() - start_time < timeout:
        if mumu_mgr and os.path.exists(mumu_mgr):
            try:
                cmd = [mumu_mgr, "info", "-v", str(vm_index or "1")]
                res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=5)
                if res.returncode == 0 and res.stdout:
                    info = json.loads(res.stdout)
                    state = info.get("player_state")
                    is_started = info.get("is_process_started")
                    if is_started and state == "start_finished":
                        if log:
                            log.info(f"[OK] MuMu 模拟器已完全启动 (VM: {vm_index or '1'}, PID: {info.get('pid')})")
                        time.sleep(2)
                        return True
            except Exception:
                pass
        else:
            # 传统模式：等待核心模拟器进程出现
            for p in psutil.process_iter(['name']):
                pname = (p.info.get('name') or '').lower()
                if pname in ["mumunxdevice.exe", "nemuplayer.exe", "dnplayer.exe"]:
                    if log:
                        log.info(f"[OK] 模拟器核心进程 [{pname}] 已检测到运行")
                    time.sleep(3)
                    return True
        time.sleep(1.5)
        
    if log:
        log.warning("等待模拟器就绪超时，将继续尝试后续自动化步骤...")
    return False

# 兼容旧名称
def restart_dnplayer(dnplayer_path, auto_find_registry=True, log=None):
    return restart_emulator(emulator_path=dnplayer_path, auto_find_registry=auto_find_registry, log=log)
