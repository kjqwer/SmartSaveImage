"""图片处理工具模块"""

import os
import json
import numpy as np
from PIL import Image, PngImagePlugin
import piexif
from typing import Dict, Any, Optional, Tuple


class ImageProcessor:
    """图片处理器"""
    
    def __init__(self):
        self.supported_formats = {
            "png": {"extension": ".png", "pil_format": "PNG"},
            "jpeg": {"extension": ".jpg", "pil_format": "JPEG"},
            "webp": {"extension": ".webp", "pil_format": "WEBP"},
            "bmp": {"extension": ".bmp", "pil_format": "BMP"},
            "tiff": {"extension": ".tiff", "pil_format": "TIFF"},
        }
    
    def tensor_to_pil(self, tensor_image) -> Image.Image:
        """将tensor图片转换为PIL图片"""
        # 处理批次维度
        if len(tensor_image.shape) == 4:
            tensor_image = tensor_image.squeeze(0)
        
        # 转换为numpy数组并调整范围到0-255
        image_np = (tensor_image.cpu().numpy() * 255).astype(np.uint8)
        
        # 转换为PIL图片
        return Image.fromarray(image_np)
    
    def prepare_save_kwargs(self, file_format: str, quality_settings: Dict[str, Any]) -> Dict[str, Any]:
        """准备保存参数"""
        format_info = self.supported_formats.get(file_format, self.supported_formats["png"])
        save_kwargs = {"format": format_info["pil_format"]}
        
        if file_format == "png":
            save_kwargs["compress_level"] = quality_settings.get("png_compression", 6)
            save_kwargs["optimize"] = quality_settings.get("optimize_size", False)
            
        elif file_format == "jpeg":
            save_kwargs["quality"] = quality_settings.get("jpeg_quality", 95)
            save_kwargs["optimize"] = quality_settings.get("optimize_size", False)
            
        elif file_format == "webp":
            if quality_settings.get("webp_lossless", False):
                save_kwargs["lossless"] = True
            else:
                save_kwargs["quality"] = quality_settings.get("webp_quality", 90)
            save_kwargs["method"] = 6  # 最佳压缩方法
            
        return save_kwargs
    
    def add_png_metadata(self, pil_image: Image.Image, metadata_text: Optional[str], 
                        workflow_data: Optional[Dict], save_kwargs: Dict) -> Dict:
        """为PNG格式添加元数据"""
        if metadata_text or workflow_data:
            pnginfo = PngImagePlugin.PngInfo()
            
            if metadata_text:
                pnginfo.add_text("parameters", metadata_text)
            
            if workflow_data:
                pnginfo.add_text("workflow", json.dumps(workflow_data))
            
            save_kwargs["pnginfo"] = pnginfo
        
        return save_kwargs
    
    def add_exif_metadata(self, metadata_text: Optional[str], 
                         workflow_data: Optional[Dict]) -> Optional[bytes]:
        """创建EXIF元数据（用于JPEG和WebP）"""
        if not metadata_text and not workflow_data:
            return None
        
        try:
            exif_dict = {}
            
            if metadata_text:
                # 将元数据添加到UserComment字段
                exif_dict["Exif"] = {
                    piexif.ExifIFD.UserComment: b"UNICODE\0" + metadata_text.encode("utf-16be")
                }
            
            if workflow_data:
                # 将工作流数据添加到ImageDescription字段
                workflow_json = json.dumps(workflow_data)
                exif_dict["0th"] = {
                    piexif.ImageIFD.ImageDescription: f"Workflow:{workflow_json}"
                }
            
            return piexif.dump(exif_dict)
            
        except Exception as e:
            print(f"[ImageProcessor] EXIF元数据创建失败: {e}")
            return None
    
    def save_image(self, tensor_image, filepath: str, file_format: str,
                  quality_settings: Dict[str, Any], metadata_text: Optional[str] = None,
                  embed_workflow: bool = False, workflow_data: Optional[Dict] = None) -> bool:
        """保存图片并嵌入元数据"""
        try:
            # 转换为PIL图片
            pil_image = self.tensor_to_pil(tensor_image)
            
            # 准备保存参数
            save_kwargs = self.prepare_save_kwargs(file_format, quality_settings)
            
            # 根据格式添加元数据
            if file_format == "png":
                # PNG使用PngInfo
                save_kwargs = self.add_png_metadata(
                    pil_image, metadata_text, 
                    workflow_data if embed_workflow else None, 
                    save_kwargs
                )
                
            elif file_format in ["jpeg", "webp"]:
                # JPEG和WebP使用EXIF
                exif_bytes = self.add_exif_metadata(
                    metadata_text,
                    workflow_data if embed_workflow else None
                )
                if exif_bytes:
                    save_kwargs["exif"] = exif_bytes
            
            # 保存图片
            pil_image.save(filepath, **save_kwargs)
            return True
            
        except Exception as e:
            print(f"[ImageProcessor] 保存图片失败 {filepath}: {e}")
            return False
    
    def create_backup(self, filepath: str) -> bool:
        """为现有文件创建备份"""
        if not os.path.exists(filepath):
            return True
        
        try:
            backup_path = filepath + ".backup"
            
            # 如果备份已存在，先删除
            if os.path.exists(backup_path):
                os.remove(backup_path)
            
            # 重命名原文件为备份
            os.rename(filepath, backup_path)
            print(f"[ImageProcessor] 创建备份: {backup_path}")
            return True
            
        except Exception as e:
            print(f"[ImageProcessor] 创建备份失败: {e}")
            return False
    
    def get_image_info(self, tensor_image) -> Tuple[int, int]:
        """获取图片尺寸信息"""
        if len(tensor_image.shape) == 4:
            # 批次格式: (batch, height, width, channels)
            return tensor_image.shape[2], tensor_image.shape[1]  # width, height
        elif len(tensor_image.shape) == 3:
            # 单张格式: (height, width, channels)
            return tensor_image.shape[1], tensor_image.shape[0]  # width, height
        else:
            return 0, 0
