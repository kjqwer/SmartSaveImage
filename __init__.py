"""智能保存图片 - ComfyUI节点包"""

import os

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]

__author__ = "kj"
__email__ = "2990346238@qq.com"
__version__ = "0.1.0"

# 从子包导入节点映射
from .src.SmartSaveImage import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# 声明Web目录以支持国际化 - 指向当前目录让ComfyUI能找到locales文件夹
WEB_DIRECTORY = os.path.dirname(__file__)