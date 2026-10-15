import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import logger, emulator_manager, GameBot
from modules.game_bot import BotTimeoutError

def load_config(config_path="config.json"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"找不到配置文件: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def cleanup_previous_scripts(log=None):
    """双重保障：清理任何残留的旧 main_controller.py Python 进程"""
    import psutil
    curr_pid = os.getpid()
    for p in psutil.process_iter(['pid', 'name']):
        try:
            if p.info['pid'] == curr_pid:
                continue
            name = (p.info.get('name') or '').lower()
            if 'python' in name:
                try:
                    cmdline = ' '.join(p.cmdline() or []).lower()
                    if 'main_controller.py' in cmdline:
                        if log:
                            log.info(f"清理旧脚本残留进程 (PID: {p.info['pid']})...")
                        p.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def run_automation(config, log):
    """执行完整的自动化流程"""
    cleanup_previous_scripts(log)
    
    exe_path_conf = (
        config['paths'].get('mumu_exe') or 
        config['paths'].get('emulator_exe') or 
        config['paths'].get('dnplayer_exe')
    )
    vm_index = config['settings'].get('vm_index', '1')
    should_restart = config['settings'].get('restart_emulator', True)
    
    log.info("")
    log.info("[启动] 开始执行自动化流程...")
    
    if should_restart:
        target_name = f"device-{vm_index}" if vm_index != "auto" else "模拟器"
        log.info(f"[步骤1] 执行 {target_name} 重启流程 (关闭 -> 确认无进程 -> reboot)...")
        emulator_manager.restart_emulator(
            emulator_path=exe_path_conf,
            vm_index=vm_index,
            auto_find_registry=config['settings'].get('auto_find_from_registry', True),
            log=log
        )
    else:
        log.info("[步骤1] 检查模拟器运行状态...")
        emulator_manager.ensure_emulator_running(
            emulator_path=exe_path_conf,
            vm_index=vm_index,
            auto_find_registry=config['settings'].get('auto_find_from_registry', True),
            log=log
        )
    
    log.info("")
    log.info("[步骤2] 启动游戏自动化流程...")
    log.info("流程: DL_entry -> start -> user -> switch -> login(第2个) -> IT_float -> continue")
    
    bot = GameBot(
        confidence=config['settings']['click_confidence'],
        step_timeout=config['settings'].get('step_timeout', 120),
        window_width=config['settings'].get('target_window_width', 796),
        window_height=config['settings'].get('target_window_height', 1348),
        auto_resize_window=config['settings'].get('auto_resize_window', False),
        assets_dir="assets",
        log=log
    )
    
    return bot.run()

def main():
    try:
        config = load_config()
        log = logger.setup_logger(config['settings']['log_file'])
        
        log.info("=" * 50)
        log.info("MuMuPlayer 游戏自动化系统启动")
        log.info("=" * 50)
        
        exe_path_conf = (
            config['paths'].get('mumu_exe') or 
            config['paths'].get('emulator_exe') or 
            config['paths'].get('dnplayer_exe')
        )
        if isinstance(exe_path_conf, list):
            log.info(f"配置的模拟器路径: {', '.join(exe_path_conf)}")
        else:
            log.info(f"配置的模拟器路径: {exe_path_conf}")
        if 'vm_index' in config['settings']:
            log.info(f"目标 VM 实例: {config['settings']['vm_index']}")
        log.info(f"识别精度: {config['settings']['click_confidence']}")
        log.info(f"步骤超时: {config['settings'].get('step_timeout', 120)}秒")
        
        max_retries = 2  # 总共尝试次数
        attempt = 0
        
        while attempt < max_retries:
            attempt += 1
            if attempt > 1:
                log.warning(f"\n[重试] 正在进行第 {attempt} 次尝试...\n")
            
            try:
                result = run_automation(config, log)
                
                if result["success"]:
                    log.info("")
                    log.info(f"[成功] 账号切换完成! 共执行 {result['completed_steps']}/{result['total_steps']} 步")
                    print(f"RESULT: SUCCESS | 步骤: {result['completed_steps']}/{result['total_steps']}")
                    sys.exit(0)
                else:
                    log.error(f"[失败] 流程中断于: {result['failed_step']}")
                    if attempt < max_retries:
                        log.info("准备自动重试...")
                        time.sleep(5)
                        continue
                    else:
                        print(f"RESULT: FAILED | 失败步骤: {result['failed_step']} | 已完成: {result['completed_steps']}/{result['total_steps']}")
                        sys.exit(1)
                        
            except BotTimeoutError as e:
                log.error(f"[超时] {e}")
                if attempt < max_retries:
                    log.info("监测到超时，将重置模拟器并重头开始...")
                    time.sleep(5)
                    continue
                else:
                    print(f"RESULT: TIMEOUT | {e}")
                    sys.exit(1)
            except KeyboardInterrupt:
                log.info("")
                log.info("[中断] 用户手动停止脚本")
                print("RESULT: INTERRUPTED")
                sys.exit(2)
            except Exception as e:
                log.error(f"")
                log.error(f"[错误] 流程执行异常: {e}")
                if attempt < max_retries:
                    log.info("发生异常，尝试恢复...")
                    time.sleep(5)
                    continue
                else:
                    print(f"RESULT: ERROR - {e}")
                    import traceback
                    traceback.print_exc()
                    sys.exit(3)
        
        log.info("")
        log.info("=" * 50)
        log.info("自动化任务结束 (已达最大重试次数)")
        log.info("=" * 50)
        
    except FileNotFoundError as e:
        print(f"[致命错误] {e}")
        print("请确保 config.json 文件存在且格式正确")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[致命错误] 配置文件格式错误: {e}")
        print("请检查 config.json 是否为有效的 JSON 格式")
        sys.exit(1)
    except Exception as e:
        print(f"[致命错误] 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
