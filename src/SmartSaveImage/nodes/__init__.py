"""SmartSaveImage 节点模块"""

from .folder_manager import SmartFolderManager
from .image_saver import SmartImageSaver

# 导出节点映射
NODE_CLASS_MAPPINGS = {
    "SmartFolderManager": SmartFolderManager,
    "SmartImageSaver": SmartImageSaver,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SmartFolderManager": "SmartFolderManager",
    "SmartImageSaver": "SmartImageSaver",
}

__all__ = [
    "SmartFolderManager",
    "SmartImageSaver", 
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
]
