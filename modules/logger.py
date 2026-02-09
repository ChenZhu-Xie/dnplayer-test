import logging
import sys

def setup_logger(log_file="bot_run.log"):
    """
    配置日志记录器
    同时输出到文件和控制台
    """
    # 创建日志记录器
    logger = logging.getLogger("dnplayer_bot")
    logger.setLevel(logging.INFO)
    
    # 如果已经有处理器，不重复添加
    if logger.handlers:
        return logger
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
