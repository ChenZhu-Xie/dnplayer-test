import json
import os
import sys
import time

# 添加当前目录到路径，确保可以导入modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import logger, emulator_manager, visual_bot

def load_config(config_path="config.json"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"找不到配置文件: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def workflow_step(step_config, confidence=0.8, log=None):
    name = step_config.get('name', '未命名步骤')
    image_path = step_config.get('image', '')
    action = step_config.get('action', 'click')
    timeout = step_config.get('timeout', 30)
    post_wait = step_config.get('post_wait', 0)

    if not image_path:
        if log:
            log.error(f"[工作流] ✗ 步骤 '{name}' 未配置图像路径")
        return False

    if not os.path.exists(image_path):
        if log:
            log.error(f"[工作流] ✗ 步骤 '{name}' 的图像不存在: {image_path}")
        return False

    start_time = time.time()
    check_count = 0

    if log:
        log.info("")
        log.info(f"[工作流] ▶ 开始步骤: {name}")
        log.info(f"[工作流]   目标: {os.path.basename(image_path)} | 动作: {action} | 超时: {timeout}s")

    while time.time() - start_time < timeout:
        check_count += 1
        elapsed = time.time() - start_time

        try:
            found = visual_bot.find_only(image_path, confidence=confidence, log=None)

            if found:
                if action == 'click':
                    visual_bot.find_and_click(
                        image_path,
                        log=None,
                        confidence=confidence,
                        max_attempts=1,
                        retry_delay=0
                    )
                    if log:
                        log.info(f"[工作流] ✓ 步骤完成: {name} (检测到+点击, 耗时 {elapsed:.2f}s)")
                else:
                    if log:
                        log.info(f"[工作流] ✓ 步骤完成: {name} (检测到, 耗时 {elapsed:.2f}s)")

                if post_wait > 0:
                    if log:
                        log.info(f"[工作流]   缓冲等待: {post_wait}秒...")
                    time.sleep(post_wait)

                return True

        except Exception as e:
            pass

        time.sleep(0.5)

    if log:
        log.error(f"[工作流] ✗ 步骤超时: {name} (经过 {check_count} 次检测, {timeout}s)")
    return False

def execute_workflow(steps, confidence=0.8, log=None):
    """
    执行完整工作流链

    参数:
        steps: 步骤列表
        confidence: 图像识别置信度
        log: 日志对象

    返回:
        bool: 所有步骤是否成功
    """
    if not steps:
        if log:
            log.warning("[工作流] 警告: 工作流步骤为空")
        return True

    if log:
        log.info("")
        log.info("=" * 50)
        log.info("[工作流] 启动链式操作模式")
        log.info(f"[工作流] 总共 {len(steps)} 个步骤")
        log.info("=" * 50)

    for i, step in enumerate(steps, 1):
        if log:
            log.info(f"")
            log.info(f"[{i}/{len(steps)}] 执行中...")

        success = workflow_step(step, confidence=confidence, log=log)

        if not success:
            if log:
                log.error("")
                log.error("=" * 50)
                log.error(f"[工作流] 中断: 步骤 {i} 失败，终止后续操作")
                log.error("=" * 50)
            return False

    if log:
        log.info("")
        log.info("=" * 50)
        log.info("[工作流] ✓ 所有步骤成功完成!")
        log.info("=" * 50)

    return True

def ensure_app_started(target_icon, verify_icon, confidence=0.8, timeout=90, post_click_wait=5, log=None):
    """
    闭环控制启动逻辑 - Click & Verify 模式

    逻辑:
    1. 优先检测 verify_icon (悬浮窗/验证标志) - 如果存在，说明已启动成功
    2. 如果 verify_icon 不存在，检测 target_icon (游戏图标) 并点击
    3. 点击后等待 post_click_wait 秒，让应用加载
    4. 循环直到 verify_icon 出现或超时

    参数:
        target_icon: 要点击的游戏图标路径
        verify_icon: 用于验证启动成功的悬浮窗图标路径
        confidence: 图像识别置信度
        timeout: 总超时时间(秒)
        post_click_wait: 点击后等待时间(秒)
        log: 日志对象

    返回:
        bool: 是否成功启动
    """
    start_time = time.time()
    loop_count = 0
    click_count = 0

    if log:
        log.info("")
        log.info("=" * 50)
        log.info("[闭环控制] Click & Verify 模式启动")
        log.info("=" * 50)
        log.info(f"点击目标: {os.path.basename(target_icon)}")
        log.info(f"验证目标: {os.path.basename(verify_icon)}")
        log.info(f"超时设置: {timeout}秒 | 点击后等待: {post_click_wait}秒")
        log.info("")

    while True:
        loop_count += 1
        elapsed = time.time() - start_time

        if elapsed > timeout:
            if log:
                log.error(f"[闭环控制] ✗ 启动超时! 经过 {loop_count} 轮循环 ({elapsed:.1f}秒)")
                log.error(f"[闭环控制] 点击次数: {click_count} | 最终状态: 未检测到验证图标")
            return False

        if log and loop_count % 10 == 1:
            log.info(f"[闭环控制] 第 {loop_count} 轮检测... (已耗时 {elapsed:.1f}秒)")

        if visual_bot.find_only(verify_icon, confidence=confidence, log=log):
            if log:
                log.info("")
                log.info("=" * 50)
                log.info(f"[闭环控制] ✓ 启动成功!")
                log.info(f"[闭环控制] 验证图标已检测到，耗时 {elapsed:.2f}秒")
                log.info(f"[闭环控制] 总循环: {loop_count}轮 | 点击次数: {click_count}")
                log.info("=" * 50)
            return True

        if visual_bot.find_only(target_icon, confidence=confidence, log=log):
            click_count += 1
            if log:
                log.info(f"[闭环控制] 检测到游戏图标，执行第 {click_count} 次点击...")

            visual_bot.find_and_click(
                target_icon,
                log=None,
                confidence=confidence,
                max_attempts=1,
                retry_delay=0
            )

            if log:
                log.info(f"[闭环控制] 点击完成，等待 {post_click_wait} 秒让应用加载...")
            time.sleep(post_click_wait)
            continue

        time.sleep(0.5)

def main():
    try:
        # 1. 初始化配置和日志
        config = load_config()
        log = logger.setup_logger(config['settings']['log_file'])

        log.info("=" * 50)
        log.info("LDPlayer OpenClaw 自动化系统启动")
        log.info("=" * 50)

        log.info(f"模拟器路径: {config['paths']['dnplayer_exe']}")
        log.info(f"识别精度: {config['settings']['click_confidence']}")

        has_workflow = 'workflow' in config and 'steps' in config['workflow']
        has_legacy = 'target_icon' in config.get('paths', {})

        log.info(f"工作流模式: {'已启用' if has_workflow else '未配置'}")

        log.info("")
        log.info("[步骤1] 执行模拟器重启...")
        emulator_manager.restart_dnplayer(
            dnplayer_path=config['paths']['dnplayer_exe'],
            auto_find_registry=config['settings'].get('auto_find_from_registry', True),
            log=log
        )

        log.info("")
        log.info("[步骤2] 启动自动化流程...")

        if has_workflow:
            steps = config['workflow']['steps']
            success = execute_workflow(
                steps=steps,
                confidence=config['settings']['click_confidence'],
                log=log
            )
        elif has_legacy:
            target_img = config['paths']['target_icon']
            log.info("使用旧版模式...")
            success = visual_bot.wait_and_click(
                image_path=target_img,
                timeout=60,
                interval=0.5,
                confidence=config['settings']['click_confidence'],
                log=log
            )
        else:
            log.error("错误: 配置文件中未找到 workflow 或 target_icon")
            success = False

        if success:
            log.info("")
            log.info("[成功] 任务完成!")
        else:
            log.error("")
            log.error("[失败] 任务执行失败")

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
