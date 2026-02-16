import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import logger, emulator_manager, GameBot

def load_config(config_path="config.json"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"找不到配置文件: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    try:
        config = load_config()
        log = logger.setup_logger(config['settings']['log_file'])
        
        log.info("=" * 50)
        log.info("LDPlayer 游戏自动化系统启动")
        log.info("=" * 50)
        
        exe_path_conf = config['paths']['dnplayer_exe']
        if isinstance(exe_path_conf, list):
            log.info(f"配置的模拟器路径: {', '.join(exe_path_conf)}")
        else:
            log.info(f"配置的模拟器路径: {exe_path_conf}")
        log.info(f"识别精度: {config['settings']['click_confidence']}")
        
        log.info("")
        log.info("[步骤1] 执行模拟器重启...")
        emulator_manager.restart_dnplayer(
            dnplayer_path=config['paths']['dnplayer_exe'],
            auto_find_registry=config['settings'].get('auto_find_from_registry', True),
            log=log
        )
        
        log.info("")
        log.info("[步骤2] 启动游戏自动化流程...")
        log.info("流程: DL_entry -> start -> user -> switch -> login(第2个) -> IT_float -> continue")
        log.info("")
        
        bot = GameBot(
            confidence=config['settings']['click_confidence'],
            assets_dir="assets",
            log=log
        )
        
        try:
            result = bot.run()
            log.info("")
            
            if result["success"]:
                log.info(f"[成功] 账号切换完成! 共执行 {result['completed_steps']}/{result['total_steps']} 步")
                print(f"RESULT: SUCCESS | 步骤: {result['completed_steps']}/{result['total_steps']}")
                sys.exit(0)
            else:
                log.error(f"[失败] 流程中断于: {result['failed_step']}")
                print(f"RESULT: FAILED | 失败步骤: {result['failed_step']} | 已完成: {result['completed_steps']}/{result['total_steps']}")
                sys.exit(1)
                
        except KeyboardInterrupt:
            log.info("")
            log.info("[中断] 用户手动停止脚本")
            print("RESULT: INTERRUPTED")
            sys.exit(2)
        except Exception as e:
            log.error(f"")
            log.error(f"[错误] 流程执行异常: {e}")
            print(f"RESULT: ERROR - {e}")
            import traceback
            traceback.print_exc()
            sys.exit(3)
        
        log.info("")
        log.info("=" * 50)
        log.info("自动化任务结束")
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
