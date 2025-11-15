"""路径管理和文件名处理工具"""

import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional


class PathManager:
    """路径管理器"""
    
    def __init__(self):
        # Windows文件名非法字符
        self.illegal_chars = r'[<>:"/\\|?*]'
        # 日期格式替换表
        self.date_formats = {
            "yyyy": lambda dt: f"{dt.year:04d}",
            "yy": lambda dt: f"{dt.year % 100:02d}",
            "MM": lambda dt: f"{dt.month:02d}",
            "dd": lambda dt: f"{dt.day:02d}",
            "hh": lambda dt: f"{dt.hour:02d}",
            "mm": lambda dt: f"{dt.minute:02d}",
            "ss": lambda dt: f"{dt.second:02d}",
        }
    
    def sanitize_filename(self, name: str, max_length: int = 100) -> str:
        """清理文件名，移除非法字符"""
        if not name:
            return "untitled"
        
        name = str(name)
        
        # 移除或替换非法字符
        name = re.sub(self.illegal_chars, '_', name)
        
        # 处理空格和特殊字符
        name = re.sub(r'\s+', '_', name)  # 多个空格替换为下划线
        name = re.sub(r'[^\w\-_.]', '_', name)  # 只保留字母数字下划线破折号点
        name = re.sub(r'_+', '_', name)  # 多个下划线合并为一个
        
        # 移除首尾的下划线和点
        name = name.strip('_.')
        
        # 限制长度
        if len(name) > max_length:
            name = name[:max_length].rstrip('_.')
            
        return name if name else "untitled"
    
    def format_date(self, date_format: str, include_time: bool = False) -> str:
        """格式化日期字符串"""
        now = datetime.now()
        
        # 如果需要包含时间但格式中没有时间部分，自动添加
        if include_time and not any(t in date_format for t in ["hh", "mm", "ss"]):
            date_format += "_hh-mm-ss"
        
        # 替换日期格式标记
        result = date_format
        for pattern, formatter in self.date_formats.items():
            result = result.replace(pattern, formatter(now))
            
        return result
    
    def build_folder_structure(self, base_path: str, structure_mode: str, 
                             metadata: Dict[str, Any], user_inputs: Dict[str, Any]) -> List[str]:
        """构建文件夹结构路径段"""
        path_segments = []
        
        if structure_mode == "date":
            date_str = self.format_date(
                user_inputs.get("date_format", "yyyy-MM-dd"),
                user_inputs.get("include_time", False)
            )
            path_segments.append(date_str)
            
        elif structure_mode == "model":
            model = user_inputs.get("model_name") or metadata.get("model")
            if model:
                if user_inputs.get("model_short_name", True):
                    model = os.path.splitext(os.path.basename(model))[0]
                path_segments.append(self.sanitize_filename(model))
                
        elif structure_mode == "seed":
            seed = user_inputs.get("seed_value")
            if seed is None:
                seed = metadata.get("seed")
            if seed is not None:
                path_segments.append(f"seed_{seed}")
                
        elif structure_mode == "prompt":
            prompt = user_inputs.get("prompt_text") or metadata.get("positive_prompt")
            if prompt:
                max_len = user_inputs.get("prompt_max_length", 50)
                prompt_clean = str(prompt).replace("\n", " ").strip()[:max_len]
                path_segments.append(self.sanitize_filename(prompt_clean))
                
        elif structure_mode == "custom":
            custom_path = user_inputs.get("custom_path", "")
            if custom_path:
                # 支持变量替换
                variables = {
                    "{date}": self.format_date(user_inputs.get("date_format", "yyyy-MM-dd")),
                    "{model}": self.sanitize_filename(
                        user_inputs.get("model_name") or metadata.get("model", "model")
                    ),
                    "{seed}": str(user_inputs.get("seed_value") or metadata.get("seed", 0)),
                    "{prompt}": self.sanitize_filename(
                        (user_inputs.get("prompt_text") or metadata.get("positive_prompt", ""))[:50]
                    ),
                }
                
                for var, value in variables.items():
                    custom_path = custom_path.replace(var, value)
                    
                # 分割路径并清理
                segments = [s.strip() for s in custom_path.split("/") if s.strip()]
                path_segments.extend([self.sanitize_filename(s) for s in segments])
                
        elif structure_mode == "auto":
            # 自动模式：日期/模型/种子的组合
            date_str = self.format_date("yyyy-MM-dd")
            path_segments.append(date_str)
            
            # 添加模型
            model = user_inputs.get("model_name") or metadata.get("model")
            if model:
                if user_inputs.get("model_short_name", True):
                    model = os.path.splitext(os.path.basename(model))[0]
                path_segments.append(self.sanitize_filename(model))
            
            # 添加种子
            seed = user_inputs.get("seed_value")
            if seed is None:
                seed = metadata.get("seed")
            if seed is not None:
                path_segments.append(f"seed_{seed}")
        
        # 限制文件夹深度
        max_depth = user_inputs.get("max_folder_depth", 5)
        path_segments = path_segments[:max_depth]
        
        return [seg for seg in path_segments if seg]
    
    def resolve_base_path(self, base_folder: str, default_output_dir: str) -> str:
        """解析基础路径"""
        if not base_folder or base_folder.lower() in ["", "output", "."]:
            return default_output_dir
        elif os.path.isabs(base_folder):
            return base_folder
        else:
            return os.path.join(default_output_dir, base_folder)
    
    def build_full_path(self, base_folder: str, structure_mode: str, 
                       metadata: Dict[str, Any], user_inputs: Dict[str, Any],
                       default_output_dir: str) -> str:
        """构建完整的文件夹路径"""
        # 解析基础路径
        base_path = self.resolve_base_path(base_folder, default_output_dir)
        
        # 构建子文件夹结构
        path_segments = self.build_folder_structure(base_path, structure_mode, metadata, user_inputs)
        
        # 组合完整路径
        if path_segments:
            return os.path.join(base_path, *path_segments)
        else:
            return base_path
    
    def ensure_directory_exists(self, path: str) -> bool:
        """确保目录存在，如果不存在则创建"""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            print(f"[PathManager] 创建目录失败: {path}, 错误: {e}")
            return False
    
    def generate_unique_filename(self, directory: str, base_filename: str, 
                               extension: str, overwrite: bool = False) -> str:
        """生成唯一的文件名（如果文件已存在且不允许覆盖）"""
        filename = f"{base_filename}{extension}"
        filepath = os.path.join(directory, filename)
        
        if not os.path.exists(filepath) or overwrite:
            return filename
        
        # 生成唯一文件名
        counter = 1
        while True:
            new_filename = f"{base_filename}_{counter:03d}{extension}"
            new_filepath = os.path.join(directory, new_filename)
            if not os.path.exists(new_filepath):
                return new_filename
            counter += 1
            
            # 防止无限循环
            if counter > 9999:
                break
        
        # 如果还是冲突，使用时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:17]  # 精确到毫秒
        return f"{base_filename}_{timestamp}{extension}"
