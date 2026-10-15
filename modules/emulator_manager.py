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

def restart_via_mumu_manager(mumu_manager_path, vm_index=None, log=None):
    """
    通过 MuMuManager 命令行优雅重启/启动 MuMu 实例
    """
    running_vms, vm_data = get_mumu_running_vms(mumu_manager_path, log)
    
    target_vm = vm_index
    if not target_vm or target_vm == "auto":
        if running_vms:
            target_vm = running_vms[0]
        else:
            # 默认启动 index 1 或 0
            target_vm = "1" if "1" in vm_data else "0"
            
    is_running = target_vm in running_vms
    action = "restart" if is_running else "launch"
    
    if log:
        log.info(f"使用 MuMuManager 控制 VM [{target_vm}] 执行 {action} 操作...")
    
    try:
        cmd = [mumu_manager_path, "control", "-v", str(target_vm), action]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=15)
        if res.returncode == 0:
            if log:
                log.info(f"MuMuManager {action} 命令发送成功 (VM: {target_vm})")
            time.sleep(3)
            return True
        else:
            if log:
                log.warning(f"MuMuManager 命令返回非零: {res.stderr or res.stdout}")
    except Exception as e:
        if log:
            log.error(f"调用 MuMuManager 异常: {e}")
            
    return False

def wait_for_device_process(timeout=30, log=None):
    """等待模拟器渲染进程出现"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        _, proc, name = get_running_process(["mumunxdevice.exe", "nemuplayer.exe", "dnplayer.exe"])
        if proc:
            if log:
                log.info(f"✓ 检测到模拟器实例画面已就绪 (进程: {name}, PID: {proc.pid})")
            time.sleep(2)
            return True
        time.sleep(1)
    if log:
        log.warning("提示：尚未检测到模拟器实例窗口，请确认实例是否已在 MuMu 中启动")
    return False

def ensure_emulator_running(emulator_path=None, vm_index=None, auto_find_registry=True, log=None):
    """
    确保模拟器处于运行状态。
    绝不强杀重启，绝不调用会导致无前台窗口的后台 CLI 开机。
    1. 若设备渲染进程 (MuMuNxDevice.exe / dnplayer.exe) 已在运行：直接使用；
    2. 若仅主外壳 (MuMuNxMain.exe) 运行但实例未开：提示并等待设备窗口出现；
    3. 若完全未运行：启动 MuMuNxMain.exe 桌面主程序并等待。
    """
    target_vm = vm_index if (vm_index and vm_index != "auto") else "1"
    
    # 1. 检查设备渲染进程是否已经在运行
    dev_exe, dev_proc, dev_name = get_running_process(["mumunxdevice.exe", "nemuplayer.exe", "dnplayer.exe"])
    if dev_proc:
        if log:
            log.info(f"✓ 模拟器实例已在运行中 (PID: {dev_proc.pid}, 进程: {dev_name})，跳过冷启动")
        return True

    # 2. 检查主界面外壳进程是否在运行
    main_exe, main_proc, _ = get_running_process(["mumunxmain.exe"])
    if main_proc:
        if log:
            log.info(f"检测到 MuMu 模拟器主程序已打开 (PID: {main_proc.pid})")
            log.info(f"等待检测到实例 [{target_vm}] 运行窗口...")
        return wait_for_device_process(timeout=30, log=log)

    # 3. 如果完全未运行，启动主程序界面 (MuMuNxMain.exe)
    if log:
        log.info("模拟器当前未运行，正在启动桌面主程序界面...")

    paths_to_check = []
    if isinstance(emulator_path, list):
        paths_to_check.extend(emulator_path)
    elif emulator_path:
        paths_to_check.append(emulator_path)

    # 优先启动 MuMuNxMain.exe (确保带完整前台主界面，而不是无头的后台服务)
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
        start_process(valid_path, log=log)
        if log:
            log.info("已发送启动主程序命令，等待模拟器主界面及实例就绪...")
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
        if restart_via_mumu_manager(mumu_mgr, vm_index=vm_index, log=log):
            wait_for_emulator_ready(mumu_mgr=mumu_mgr, vm_index=target_vm, timeout=60, log=log)
            return True
        if log:
            log.warning("MuMuManager 控制失败，退回传统进程管理方式...")

    # 2. 传统进程模式：查杀并重新启动
    running_exe, proc, proc_name = get_running_process()
    if proc:
        kill_all_emulator_processes(log)
        time.sleep(2)
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
                            log.info(f"✓ MuMu 模拟器已完全启动 (VM: {vm_index or '1'}, PID: {info.get('pid')})")
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
                        log.info(f"✓ 模拟器核心进程 [{pname}] 已检测到运行")
                    time.sleep(3)
                    return True
        time.sleep(1.5)
        
    if log:
        log.warning("等待模拟器就绪超时，将继续尝试后续自动化步骤...")
    return False

# 兼容旧名称
def restart_dnplayer(dnplayer_path, auto_find_registry=True, log=None):
    return restart_emulator(emulator_path=dnplayer_path, auto_find_registry=auto_find_registry, log=log)
