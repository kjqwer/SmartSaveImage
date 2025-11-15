"""输入验证工具"""

import os
import re
from typing import Any, List, Optional, Union


class InputValidator:
    """输入验证器"""
    
    @staticmethod
    def validate_folder_path(path: str) -> bool:
        """验证文件夹路径是否有效"""
        if not path:
            return False
        
        # 检查路径长度
        if len(path) > 260:  # Windows路径长度限制
            return False
        
        # 检查非法字符
        illegal_chars = r'[<>"|?*]'
        if re.search(illegal_chars, path):
            return False
        
        return True
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """验证文件名是否有效"""
        if not filename:
            return False
        
        # 检查长度
        if len(filename) > 255:
            return False
        
        # 检查非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        if re.search(illegal_chars, filename):
            return False
        
        # 检查保留名称（Windows）
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        
        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            return False
        
        return True
    
    @staticmethod
    def validate_date_format(date_format: str) -> bool:
        """验证日期格式字符串"""
        if not date_format:
            return False
        
        # 检查是否包含有效的日期格式标记
        valid_tokens = ['yyyy', 'yy', 'MM', 'dd', 'hh', 'mm', 'ss']
        has_valid_token = any(token in date_format for token in valid_tokens)
        
        return has_valid_token
    
    @staticmethod
    def validate_quality_value(quality: int, min_val: int = 1, max_val: int = 100) -> bool:
        """验证质量值范围"""
        return isinstance(quality, int) and min_val <= quality <= max_val
    
    @staticmethod
    def validate_file_format(file_format: str) -> bool:
        """验证文件格式"""
        supported_formats = ['png', 'jpeg', 'webp', 'bmp', 'tiff']
        return file_format.lower() in supported_formats
    
    @staticmethod
    def sanitize_input_string(input_str: str, max_length: int = 1000) -> str:
        """清理输入字符串"""
        if not isinstance(input_str, str):
            input_str = str(input_str)
        
        # 移除控制字符
        input_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', input_str)
        
        # 限制长度
        if len(input_str) > max_length:
            input_str = input_str[:max_length]
        
        return input_str.strip()
    
    @staticmethod
    def validate_counter_settings(counter_start: int, counter_padding: int) -> bool:
        """验证计数器设置"""
        return (
            isinstance(counter_start, int) and 
            isinstance(counter_padding, int) and
            0 <= counter_start <= 99999 and
            1 <= counter_padding <= 10
        )
