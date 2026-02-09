import psutil
import subprocess
import time
import os
import winreg

PROCESS_NAME = "dnplayer.exe"

def get_running_process_path(proc_name):
    """
    检查进程是否运行。
    如果运行，返回其可执行文件的完整路径和进程对象；
    如果不运行，返回 None, None。
    """
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == proc_name.lower():
                return proc.info['exe'], proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None, None

def find_path_from_registry():
    """
    尝试从 Windows 注册表查找雷电模拟器(LDPlayer)的安装路径。
    遍历卸载列表查找包含 LDPlayer 或 雷电模拟器 的项。
    """
    try:
        # 遍历卸载列表查找包含 LDPlayer 或 dnplayer 的项
        uninstall_key = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uninstall_key) as key:
            for i in range(0, winreg.QueryInfoKey(key)[0]):
                sub_key_name = winreg.EnumKey(key, i)
                with winreg.OpenKey(key, sub_key_name) as sub_key:
                    try:
                        display_name = winreg.QueryValueEx(sub_key, "DisplayName")[0]
                        if "LDPlayer" in display_name or "雷电模拟器" in display_name:
                            install_loc = winreg.QueryValueEx(sub_key, "InstallLocation")[0]
                            full_path = os.path.join(install_loc, PROCESS_NAME)
                            if os.path.exists(full_path):
                                return full_path
                    except FileNotFoundError:
                        pass
    except Exception as e:
        pass
    
    return None

def kill_process(proc, log=None):
    """优雅或强制关闭进程"""
    try:
        if log:
            log.info(f"检测到 {PROCESS_NAME} 正在运行 (PID: {proc.pid})，正在关闭...")
        else:
            print(f"检测到 {PROCESS_NAME} 正在运行 (PID: {proc.pid})，正在关闭...")
        
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

def start_process(exe_path, log=None):
    """启动程序"""
    if exe_path and os.path.exists(exe_path):
        if log:
            log.info(f"正在启动: {exe_path}")
        else:
            print(f"正在启动: {exe_path}")
        
        # 使用 subprocess.Popen 非阻塞启动，cwd参数确保在程序目录下运行，避免缺失DLL
        work_dir = os.path.dirname(exe_path)
        subprocess.Popen([exe_path], cwd=work_dir, shell=False)
        return True
    else:
        if log:
            log.error(f"错误：找不到文件路径 {exe_path}")
        else:
            print(f"错误：找不到文件路径 {exe_path}")
        return False

def restart_dnplayer(dnplayer_path, auto_find_registry=True, log=None):
    """
    重启雷电模拟器 - OpenClaw 版本
    启动后立即返回，不阻塞等待，由视觉模块负责检测启动完成
    
    参数:
        dnplayer_path: 模拟器可执行文件路径
        auto_find_registry: 是否尝试从注册表自动查找路径
        log: 日志记录器对象
    """
    if log:
        log.info(f"--- 开始重启 {PROCESS_NAME} ---")
    
    exe_path, proc = get_running_process_path(PROCESS_NAME)
    
    if proc:
        kill_process(proc, log)
        time.sleep(2)
        start_process(exe_path, log)
    else:
        if log:
            log.info(f"{PROCESS_NAME} 未运行，准备启动...")
        
        if dnplayer_path and os.path.exists(dnplayer_path):
            start_process(dnplayer_path, log)
        elif auto_find_registry:
            if log:
                log.info("尝试从注册表查找安装路径...")
            
            found_path = find_path_from_registry()
            
            if found_path:
                if log:
                    log.info(f"从注册表找到路径: {found_path}")
                start_process(found_path, log)
            else:
                if log:
                    log.error("注册表查找失败，且配置路径无效")
        else:
            if log:
                log.error("错误：未找到运行中的进程，且配置路径无效")
    
    if log:
        log.info("模拟器启动命令已发送，进入轮询检测模式...")
