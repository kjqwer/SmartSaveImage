"""智能图片保存器节点"""

import os
import json
from datetime import datetime
import folder_paths
import nodes
from ..core import MetadataBuilder, ImageProcessor, PathManager
from ..utils import InputValidator


class SmartImageSaver:
    """智能图片保存器 - 负责图片保存、格式转换和压缩"""
    
    CATEGORY = "SmartSave"
    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "save_images"

    def __init__(self):
        self.metadata_builder = MetadataBuilder()
        self.image_processor = ImageProcessor()
        self.path_manager = PathManager()
        self.validator = InputValidator()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "要保存的图片（通常来自SmartFolderManager）"}),
                "folder_path": ("STRING", {
                    "default": "", 
                    "multiline": False,
                    "tooltip": "保存路径（来自SmartFolderManager）"
                }),
                "metadata_json": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "tooltip": "元数据JSON（来自SmartFolderManager）"
                }),
                "filename_prefix": ("STRING", {
                    "default": "image", 
                    "multiline": False,
                    "tooltip": "文件名前缀"
                }),
                "file_format": (["png", "jpeg", "webp", "bmp", "tiff"], {
                    "default": "png",
                    "tooltip": "图片格式"
                }),
                "preview_mode": (["save_and_preview", "preview_only", "save_only"], {
                    "default": "save_and_preview",
                    "tooltip": "保存模式"
                }),
            },
            "optional": {
                # 文件名选项
                "add_timestamp": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "在文件名中添加时间戳"
                }),
                "add_counter": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "添加计数器（批量保存时）"
                }),
                "counter_start": ("INT", {
                    "default": 1, 
                    "min": 0, 
                    "max": 99999,
                    "tooltip": "计数器起始值"
                }),
                "counter_padding": ("INT", {
                    "default": 4, 
                    "min": 1, 
                    "max": 10,
                    "tooltip": "计数器位数（补零）"
                }),
                
                # 图片质量选项
                "jpeg_quality": ("INT", {
                    "default": 95, 
                    "min": 1, 
                    "max": 100,
                    "tooltip": "JPEG质量（1-100）"
                }),
                "webp_quality": ("INT", {
                    "default": 90, 
                    "min": 1, 
                    "max": 100,
                    "tooltip": "WebP质量（1-100）"
                }),
                "webp_lossless": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "WebP无损压缩"
                }),
                "png_compression": ("INT", {
                    "default": 6, 
                    "min": 0, 
                    "max": 9,
                    "tooltip": "PNG压缩级别（0-9）"
                }),
                
                # 元数据选项
                "embed_metadata": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "嵌入元数据到图片"
                }),
                "embed_workflow": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "嵌入工作流信息"
                }),
                
                # 高级选项
                "overwrite_existing": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "覆盖已存在的文件"
                }),
                "create_backup": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "为覆盖的文件创建备份"
                }),
                "optimize_size": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "优化文件大小"
                }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    def generate_filename(self, prefix, index, add_timestamp, add_counter, 
                         counter_start, counter_padding, file_format):
        """生成文件名"""
        # 清理前缀
        prefix = self.path_manager.sanitize_filename(prefix) if prefix else "image"
        
        parts = [prefix]
        
        # 添加时间戳
        if add_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            parts.append(timestamp)
        
        # 添加计数器
        if add_counter:
            counter = str(counter_start + index).zfill(counter_padding)
            parts.append(counter)
        
        # 组合文件名
        filename = "_".join(parts)
        
        # 添加扩展名
        extensions = {
            "png": ".png",
            "jpeg": ".jpg", 
            "webp": ".webp",
            "bmp": ".bmp",
            "tiff": ".tiff"
        }
        
        filename += extensions.get(file_format, ".png")
        return filename

    def parse_metadata_json(self, metadata_json):
        """解析元数据JSON"""
        if not metadata_json:
            return {}
        
        try:
            return json.loads(metadata_json)
        except Exception as e:
            print(f"[SmartImageSaver] 解析元数据JSON失败: {e}")
            return {}

    def save_images(self, images, folder_path, metadata_json, filename_prefix, file_format, preview_mode,
                   add_timestamp=False, add_counter=True, counter_start=1, counter_padding=4,
                   jpeg_quality=95, webp_quality=90, webp_lossless=False, png_compression=6,
                   embed_metadata=True, embed_workflow=False,
                   overwrite_existing=False, create_backup=False, optimize_size=False,
                   prompt=None, extra_pnginfo=None):
        """保存图片主函数"""
        
        # 验证输入
        if not self.validator.validate_file_format(file_format):
            print(f"[SmartImageSaver] 不支持的文件格式: {file_format}")
            file_format = "png"
        
        if not self.validator.validate_quality_value(jpeg_quality):
            jpeg_quality = 95
        
        if not self.validator.validate_quality_value(webp_quality):
            webp_quality = 90
        
        if not self.validator.validate_counter_settings(counter_start, counter_padding):
            counter_start, counter_padding = 1, 4
        
        # 清理输入
        filename_prefix = self.validator.sanitize_input_string(filename_prefix, 100)
        
        # 处理预览模式
        if preview_mode == "preview_only":
            # 只预览，不保存
            try:
                result = nodes.PreviewImage().save_images(
                    images, 
                    filename_prefix=filename_prefix or "preview"
                )
                return {"ui": result.get("ui", {}), "result": (images,)}
            except Exception as e:
                print(f"[SmartImageSaver] 预览失败: {e}")
                return {"ui": {}, "result": (images,)}
        
        # 确定保存路径
        print(f"[SmartImageSaver] 接收到的folder_path: '{folder_path}' (类型: {type(folder_path)})")
        if not folder_path:
            folder_path = folder_paths.get_output_directory()
            print(f"[SmartImageSaver] 文件夹路径为空，使用默认输出目录: {folder_path}")
        elif not os.path.exists(folder_path):
            print(f"[SmartImageSaver] 文件夹不存在，尝试创建: {folder_path}")
            try:
                os.makedirs(folder_path, exist_ok=True)
            except Exception as e:
                print(f"[SmartImageSaver] 创建文件夹失败: {e}，使用默认输出目录")
                folder_path = folder_paths.get_output_directory()
        
        # 解析元数据
        metadata_dict = self.parse_metadata_json(metadata_json)
        workflow_metadata = metadata_dict.get("workflow_metadata", {})
        
        # 获取图片尺寸
        if len(images) > 0:
            width, height = self.image_processor.get_image_info(images[0])
            workflow_metadata.update({"width": width, "height": height})
        
        # 构建元数据文本
        metadata_text = None
        if embed_metadata:
            metadata_text = self.metadata_builder.build_parameters_text(workflow_metadata)
        
        # 准备质量设置
        quality_settings = {
            "jpeg_quality": jpeg_quality,
            "webp_quality": webp_quality,
            "webp_lossless": webp_lossless,
            "png_compression": png_compression,
            "optimize_size": optimize_size,
        }
        
        # 准备工作流数据
        workflow_data = None
        if embed_workflow and extra_pnginfo and "workflow" in extra_pnginfo:
            workflow_data = extra_pnginfo["workflow"]
        
        # 保存图片
        saved_images = []
        
        for i, image in enumerate(images):
            # 生成文件名
            filename = self.generate_filename(
                filename_prefix, i, add_timestamp, add_counter,
                counter_start, counter_padding, file_format
            )
            
            # 处理文件名冲突
            if not overwrite_existing:
                filename = self.path_manager.generate_unique_filename(
                    folder_path, 
                    os.path.splitext(filename)[0],
                    os.path.splitext(filename)[1],
                    overwrite_existing
                )
            
            filepath = os.path.join(folder_path, filename)
            
            # 创建备份
            if overwrite_existing and create_backup and os.path.exists(filepath):
                self.image_processor.create_backup(filepath)
            
            # 保存图片
            try:
                success = self.image_processor.save_image(
                    image, filepath, file_format, quality_settings,
                    metadata_text, embed_workflow, workflow_data
                )
                
                if success:
                    # 获取相对路径用于UI显示
                    try:
                        rel_folder = os.path.relpath(folder_path, folder_paths.get_output_directory())
                        if rel_folder == ".":
                            rel_folder = ""
                    except ValueError:
                        # 如果是绝对路径且不在输出目录下
                        rel_folder = os.path.basename(folder_path)
                    
                    saved_images.append({
                        "filename": filename,
                        "subfolder": rel_folder,
                        "type": "output"
                    })
                    print(f"[SmartImageSaver] 保存成功: {filepath}")
                else:
                    print(f"[SmartImageSaver] 保存失败: {filepath}")
                    
            except Exception as e:
                print(f"[SmartImageSaver] 保存图片时出错: {e}")
        
        # 返回结果
        result = {"result": (images,)}
        
        if preview_mode == "save_and_preview" and saved_images:
            # 保存并预览
            result["ui"] = {"images": saved_images}
        elif preview_mode == "save_only":
            # 仅保存，不显示预览 - 不返回images避免显示预览
            result["ui"] = {}
        
        return result
