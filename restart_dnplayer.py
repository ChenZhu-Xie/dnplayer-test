import psutil
import subprocess
import time
import os
import winreg

PROCESS_NAME = "dnplayer.exe"
# 如果自动查找失败，将使用此默认路径（请根据实际情况修改作为保底）
DEFAULT_PATH = r"E:\Runtime\leidian\LDPlayer9\dnplayer.exe"

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
    注意：不同版本注册表键值可能不同，这里演示通用的卸载列表查找法。
    """
    print("正在尝试从注册表查找安装路径...")
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
        print(f"注册表查找失败: {e}")

    return None

def kill_process(proc):
    """优雅或强制关闭进程"""
    try:
        print(f"检测到 {PROCESS_NAME} 正在运行 (PID: {proc.pid})，正在关闭...")
        proc.terminate() # 尝试优雅关闭
        proc.wait(timeout=5)
    except psutil.TimeoutExpired:
        print("进程响应超时，正在强制查杀...")
        proc.kill() # 强制关闭
    except Exception as e:
        print(f"关闭进程时出错: {e}")

def start_process(exe_path):
    """启动程序"""
    if exe_path and os.path.exists(exe_path):
        print(f"正在启动: {exe_path}")
        # 使用 subprocess.Popen 非阻塞启动，cwd参数确保在程序目录下运行，避免缺失DLL
        work_dir = os.path.dirname(exe_path)
        subprocess.Popen([exe_path], cwd=work_dir, shell=False)
    else:
        print(f"错误：找不到文件路径 {exe_path}")

def main():
    print(f"--- 开始检查 {PROCESS_NAME} ---")

    # 1. 检查是否正在运行
    exe_path, proc = get_running_process_path(PROCESS_NAME)

    if proc:
        # 情况A：正在运行 -> 获取路径 -> 关闭 -> 重启
        kill_process(proc)
        # 稍微等待一下，确保资源释放
        time.sleep(2)
        start_process(exe_path)
    else:
        # 情况B：未运行 -> 查找路径 -> 启动
        print(f"{PROCESS_NAME} 未运行。")

        # 尝试从注册表自动查找
        found_path = find_path_from_registry()

        if found_path:
            start_process(found_path)
        elif os.path.exists(DEFAULT_PATH):
            print("注册表查找失败，使用默认配置路径。")
            start_process(DEFAULT_PATH)
        else:
            print("错误：未找到运行中的进程，且注册表查找失败，默认路径也不存在。")
            print("请在脚本顶部的 DEFAULT_PATH 中手动填入 dnplayer.exe 的路径。")

if __name__ == "__main__":
    # 此时需要管理员权限才能读取部分注册表或杀进程，建议以管理员身份运行终端
    main()
