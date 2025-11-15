"""智能文件夹管理器节点"""

import os
import folder_paths
from ..core import MetadataExtractor, MetadataBuilder, PathManager
from ..utils import InputValidator


class SmartFolderManager:
    """智能文件夹管理器 - 负责管理文件夹结构和元数据收集"""
    
    CATEGORY = "SmartSave"
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("images", "folder_path", "metadata_json")
    FUNCTION = "generate_path"

    def __init__(self):
        self.metadata_extractor = MetadataExtractor()
        self.metadata_builder = MetadataBuilder()
        self.path_manager = PathManager()
        self.validator = InputValidator()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "输入图片，用于提取尺寸信息并传递给保存节点"}),
                "base_folder": ("STRING", {
                    "default": "output", 
                    "multiline": False,
                    "tooltip": "基础文件夹路径，可以是相对路径或绝对路径"
                }),
                "create_subfolders": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "是否自动创建子文件夹"
                }),
            },
            "optional": {
                # 文件夹层级开关
                "enable_date_folder": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "是否创建日期文件夹"
                }),
                "enable_model_folder": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "是否创建模型文件夹"
                }),
                "enable_seed_folder": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "是否创建种子文件夹"
                }),
                "enable_prompt_folder": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "是否创建提示词文件夹"
                }),
                "enable_custom_folder": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "是否使用自定义文件夹"
                }),
                
                # 日期相关
                "date_format": ("STRING", {
                    "default": "yyyy-MM-dd", 
                    "multiline": False,
                    "tooltip": "日期格式: yyyy年 MM月 dd日 hh时 mm分 ss秒"
                }),
                "include_time": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "是否在日期中包含时间"
                }),
                
                # 模型信息来源选择
                "model_source": (["auto", "manual"], {
                    "default": "auto",
                    "tooltip": "模型信息来源：auto=从元数据/外部输入获取，manual=手动选择"
                }),
                "manual_model_name": (folder_paths.get_filename_list("checkpoints"), {
                    "tooltip": "手动选择模型（仅在model_source=manual时生效）"
                }),
                "model_input": ("MODEL", {
                    "tooltip": "从模型加载器节点输入（仅在model_source=auto时生效）"
                }),
                
                # 种子信息
                "seed_source": (["manual", "external"], {
                    "default": "manual",
                    "tooltip": "种子来源：manual=手动输入，external=外部输入"
                }),
                "manual_seed": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 0xffffffffffffffff,
                    "tooltip": "手动设置种子值"
                }),
                "seed_input": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "tooltip": "从外部节点输入种子"
                }),
                
                # 提示词信息
                "prompt_source": (["manual", "external"], {
                    "default": "manual", 
                    "tooltip": "提示词来源：manual=手动输入，external=外部输入"
                }),
                "manual_prompt": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "tooltip": "手动输入正向提示词"
                }),
                "manual_negative_prompt": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "tooltip": "手动输入负向提示词"
                }),
                "conditioning_positive": ("CONDITIONING", {
                    "tooltip": "从正向条件节点输入（仅在prompt_source=external时生效）"
                }),
                "conditioning_negative": ("CONDITIONING", {
                    "tooltip": "从负向条件节点输入（仅在prompt_source=external时生效）"
                }),
                
                # 自定义路径
                "custom_subfolder": ("STRING", {
                    "default": "", 
                    "multiline": False,
                    "tooltip": "自定义子文件夹名称"
                }),
                
                # 显示选项
                "model_short_name": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "使用模型短名称（去除扩展名）"
                }),
                "prompt_max_length": ("INT", {
                    "default": 50, 
                    "min": 10, 
                    "max": 200,
                    "tooltip": "提示词文件夹名最大长度"
                }),
                "sanitize_names": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "清理文件名中的非法字符"
                }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    def generate_path(self, images, base_folder, create_subfolders,
                     enable_date_folder=True, enable_model_folder=True, 
                     enable_seed_folder=True, enable_prompt_folder=False, enable_custom_folder=False,
                     date_format="yyyy-MM-dd", include_time=False,
                     model_source="auto", manual_model_name=None, model_input=None,
                     seed_source="manual", manual_seed=0, seed_input=0,
                     prompt_source="manual", manual_prompt="", manual_negative_prompt="",
                     conditioning_positive=None, conditioning_negative=None,
                     custom_subfolder="", model_short_name=True, prompt_max_length=50, sanitize_names=True,
                     prompt=None, extra_pnginfo=None):
        """生成文件夹路径和元数据"""
        
        # 验证输入
        if not self.validator.validate_folder_path(base_folder):
            print(f"[SmartFolderManager] 无效的基础文件夹路径: {base_folder}")
            base_folder = "output"
        
        if date_format and not self.validator.validate_date_format(date_format):
            print(f"[SmartFolderManager] 无效的日期格式: {date_format}")
            date_format = "yyyy-MM-dd"
        
        # 清理输入字符串
        manual_prompt = self.validator.sanitize_input_string(manual_prompt, prompt_max_length * 2)
        manual_negative_prompt = self.validator.sanitize_input_string(manual_negative_prompt, prompt_max_length * 2)
        custom_subfolder = self.validator.sanitize_input_string(custom_subfolder, 100)
        
        # 从图片中提取尺寸信息
        image_metadata = {}
        if images is not None and len(images) > 0:
            try:
                # 获取第一张图片的尺寸
                if len(images.shape) == 4:  # [batch, height, width, channels]
                    height, width = images.shape[1], images.shape[2]
                elif len(images.shape) == 3:  # [height, width, channels]
                    height, width = images.shape[0], images.shape[1]
                else:
                    height, width = 0, 0
                
                image_metadata["width"] = width
                image_metadata["height"] = height
                print(f"[SmartFolderManager] 从图片提取尺寸: {width}x{height}")
            except Exception as e:
                print(f"[SmartFolderManager] 提取图片尺寸失败: {e}")
                image_metadata["width"] = 0
                image_metadata["height"] = 0
        
        # 1. 根据用户选择构建元数据
        final_metadata = {}
        
        # 模型信息
        if model_source == "manual":
            final_metadata["model"] = manual_model_name
        else:  # auto
            # 优先从外部输入获取
            if model_input is not None:
                external_model = self.extract_model_from_input(model_input)
                if external_model:
                    final_metadata["model"] = external_model
                else:
                    # 从工作流元数据获取
                    workflow_metadata = self.metadata_extractor.extract_from_prompt(prompt)
                    final_metadata["model"] = workflow_metadata.get("model")
            else:
                # 从工作流元数据获取
                workflow_metadata = self.metadata_extractor.extract_from_prompt(prompt)
                final_metadata["model"] = workflow_metadata.get("model")
        
        # 种子信息
        if seed_source == "manual":
            final_metadata["seed"] = manual_seed
        else:  # external
            final_metadata["seed"] = seed_input
        
        # 提示词信息
        if prompt_source == "manual":
            final_metadata["positive_prompt"] = manual_prompt if manual_prompt.strip() else None
            final_metadata["negative_prompt"] = manual_negative_prompt if manual_negative_prompt.strip() else None
        else:  # external
            # 从conditioning输入提取（这里暂时标记有输入，具体文本仍需要从工作流获取）
            if conditioning_positive is not None:
                final_metadata["has_positive_conditioning"] = True
            if conditioning_negative is not None:
                final_metadata["has_negative_conditioning"] = True
        
        # 尺寸信息（直接从图片获取）
        final_metadata["width"] = image_metadata.get("width", 0)
        final_metadata["height"] = image_metadata.get("height", 0)
        
        # 2. 构建文件夹路径
        path_segments = []
        base_path = self.path_manager.resolve_base_path(base_folder, folder_paths.get_output_directory())
        
        # 按开关添加各层文件夹
        if enable_date_folder:
            date_str = self.path_manager.format_date(date_format, include_time)
            path_segments.append(date_str)
        
        if enable_model_folder and final_metadata.get("model"):
            model_name = final_metadata["model"]
            if model_short_name:
                model_name = os.path.splitext(os.path.basename(model_name))[0]
            if sanitize_names:
                model_name = self.path_manager.sanitize_filename(model_name)
            path_segments.append(model_name)
        
        if enable_seed_folder and final_metadata.get("seed") is not None:
            seed_str = f"seed_{final_metadata['seed']}"
            path_segments.append(seed_str)
        
        if enable_prompt_folder and final_metadata.get("positive_prompt"):
            prompt_text = final_metadata["positive_prompt"]
            prompt_clean = prompt_text.replace("\n", " ").strip()[:prompt_max_length]
            if sanitize_names:
                prompt_clean = self.path_manager.sanitize_filename(prompt_clean)
            path_segments.append(prompt_clean)
        
        if enable_custom_folder and custom_subfolder:
            if sanitize_names:
                custom_subfolder = self.path_manager.sanitize_filename(custom_subfolder)
            path_segments.append(custom_subfolder)
        
        # 构建最终路径
        if path_segments:
            folder_path = os.path.join(base_path, *path_segments)
        else:
            folder_path = base_path
        
        # 创建文件夹
        if create_subfolders:
            if not self.path_manager.ensure_directory_exists(folder_path):
                print(f"[SmartFolderManager] 创建文件夹失败，使用默认输出目录")
                folder_path = folder_paths.get_output_directory()
            else:
                print(f"[SmartFolderManager] 文件夹路径: {folder_path}")
        
        # 构建用户输入记录
        user_inputs = {
            "enable_date_folder": enable_date_folder,
            "enable_model_folder": enable_model_folder,
            "enable_seed_folder": enable_seed_folder,
            "enable_prompt_folder": enable_prompt_folder,
            "enable_custom_folder": enable_custom_folder,
            "date_format": date_format,
            "include_time": include_time,
            "model_source": model_source,
            "seed_source": seed_source,
            "prompt_source": prompt_source,
            "manual_model_name": manual_model_name,
            "manual_seed": manual_seed,
            "manual_prompt": manual_prompt,
            "custom_subfolder": custom_subfolder,
        }
        
        # 构建元数据JSON
        metadata_json = self.metadata_builder.build_metadata_json(
            folder_path, "flexible", final_metadata, user_inputs
        )
        
        return (images, folder_path, metadata_json)
    
    def extract_model_from_input(self, model_input):
        """从模型输入中提取模型名称（简化版）"""
        if model_input is None:
            return None
        
        try:
            # 尝试多种方式提取模型名称
            if hasattr(model_input, 'model_path'):
                return model_input.model_path
            elif hasattr(model_input, 'model') and hasattr(model_input.model, 'model_path'):
                return model_input.model.model_path
            elif isinstance(model_input, dict):
                return model_input.get('model_path') or model_input.get('checkpoint_path')
        except Exception as e:
            print(f"[SmartFolderManager] 从模型输入提取名称失败: {e}")
        
        return None
    
    def extract_from_external_inputs(self, model_input, conditioning_positive, conditioning_negative, latent_input):
        """从外部输入节点提取元数据"""
        metadata = {}
        
        # 从模型输入提取模型名称
        if model_input is not None:
            try:
                # 尝试多种方式从模型对象中提取信息
                model_name = None
                
                # 方法1: 检查是否有model_path属性
                if hasattr(model_input, 'model_path'):
                    model_name = model_input.model_path
                
                # 方法2: 检查model对象的属性
                elif hasattr(model_input, 'model'):
                    model_obj = model_input.model
                    if hasattr(model_obj, 'model_path'):
                        model_name = model_obj.model_path
                    elif hasattr(model_obj, 'checkpoint_path'):
                        model_name = model_obj.checkpoint_path
                
                # 方法3: 检查是否是字典格式
                elif isinstance(model_input, dict):
                    model_name = model_input.get('model_path') or model_input.get('checkpoint_path')
                
                if model_name:
                    metadata["model"] = model_name
                    print(f"[SmartFolderManager] 从外部输入提取模型: {model_name}")
                else:
                    print(f"[SmartFolderManager] 模型输入已连接，但无法提取模型名称")
                    
            except Exception as e:
                print(f"[SmartFolderManager] 从模型输入提取信息失败: {e}")
        
        # 从conditioning提取提示词
        # 注意：ComfyUI的conditioning对象通常不直接包含原始文本
        # 但我们可以尝试一些方法
        if conditioning_positive is not None:
            try:
                # conditioning通常是一个包含编码后数据的复杂结构
                # 我们标记有外部conditioning输入，但文本提取仍依赖工作流
                metadata["has_positive_conditioning"] = True
                print(f"[SmartFolderManager] 检测到正向条件输入")
            except Exception as e:
                print(f"[SmartFolderManager] 处理正向条件输入失败: {e}")
        
        if conditioning_negative is not None:
            try:
                metadata["has_negative_conditioning"] = True
                print(f"[SmartFolderManager] 检测到负向条件输入")
            except Exception as e:
                print(f"[SmartFolderManager] 处理负向条件输入失败: {e}")
        
        # 从latent提取尺寸信息
        if latent_input is not None:
            try:
                if isinstance(latent_input, dict) and "samples" in latent_input:
                    samples = latent_input["samples"]
                    if hasattr(samples, 'shape') and len(samples.shape) >= 3:
                        # latent通常是 [batch, channels, height, width]
                        # 需要乘以8因为latent空间是1/8分辨率
                        height = samples.shape[-2] * 8
                        width = samples.shape[-1] * 8
                        metadata["width"] = width
                        metadata["height"] = height
                        print(f"[SmartFolderManager] 从latent提取尺寸: {width}x{height}")
            except Exception as e:
                print(f"[SmartFolderManager] 从latent提取尺寸失败: {e}")
        
        return metadata
