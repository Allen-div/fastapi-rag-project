import logging

# 全局日志配置：独立于 app.main，避免循环导入
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")
