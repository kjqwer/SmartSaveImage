"""元数据提取和构建模块"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional


class MetadataExtractor:
    """从ComfyUI工作流中提取元数据"""
    
    def __init__(self):
        self.supported_checkpoint_nodes = [
            "CheckpointLoaderSimple", 
            "CheckpointLoader", 
            "CheckpointLoaderV2"
        ]
        self.supported_sampler_nodes = [
            "KSampler", 
            "KSamplerAdvanced",
            "SamplerCustom",
            "SamplerCustomAdvanced",
            # 添加更多可能的采样器节点类型
        ]
        self.supported_text_nodes = [
            "CLIPTextEncode", 
            "CLIPTextEncodeSDXL", 
            "T5TextEncode"
        ]
    
    def extract_from_workflow(self, extra_pnginfo: Optional[Dict]) -> Dict[str, Any]:
        """从工作流信息中提取元数据"""
        metadata = {
            "model": None,
            "seed": None,
            "steps": None,
            "cfg": None,
            "sampler": None,
            "scheduler": None,
            "positive_prompt": None,
            "negative_prompt": None,
            "width": None,
            "height": None,
        }
        
        if not isinstance(extra_pnginfo, dict):
            return metadata
            
        workflow = extra_pnginfo.get("workflow", {})
        if not isinstance(workflow, dict):
            return metadata
            
        nodes_data = workflow.get("nodes", [])
        text_prompts = []  # 收集所有文本提示
        
        for node in nodes_data:
            if not isinstance(node, dict):
                continue
                
            class_type = node.get("class_type", "")
            inputs = node.get("inputs", {})
            
            # 提取模型信息
            if class_type in self.supported_checkpoint_nodes:
                if "ckpt_name" in inputs and not metadata["model"]:
                    metadata["model"] = inputs["ckpt_name"]
            
            # 提取采样器信息
            elif class_type in self.supported_sampler_nodes:
                if "seed" in inputs and metadata["seed"] is None:
                    metadata["seed"] = inputs["seed"]
                if "steps" in inputs and metadata["steps"] is None:
                    metadata["steps"] = inputs["steps"]
                if "cfg" in inputs and metadata["cfg"] is None:
                    metadata["cfg"] = inputs["cfg"]
                if "sampler_name" in inputs and not metadata["sampler"]:
                    metadata["sampler"] = inputs["sampler_name"]
                if "scheduler" in inputs and not metadata["scheduler"]:
                    metadata["scheduler"] = inputs["scheduler"]
            
            # 提取文本提示
            elif class_type in self.supported_text_nodes:
                text = inputs.get("text", "")
                if text and isinstance(text, str):
                    text_prompts.append(text.strip())
        
        # 分配正负提示词（通常第一个是正向，第二个是负向）
        if text_prompts:
            metadata["positive_prompt"] = text_prompts[0]
            if len(text_prompts) > 1:
                metadata["negative_prompt"] = text_prompts[1]
        
        return metadata
    
    def extract_from_prompt(self, prompt: Optional[Dict]) -> Dict[str, Any]:
        """从prompt参数中提取元数据（备用方案）"""
        metadata = {
            "model": None,
            "seed": None,
            "steps": None,
            "cfg": None,
            "sampler": None,
            "scheduler": None,
        }
        
        if not isinstance(prompt, dict):
            return metadata
            
        for node_id, node_data in prompt.items():
            if not isinstance(node_data, dict):
                continue
                
            class_type = node_data.get("class_type", "")
            inputs = node_data.get("inputs", {})
            
            if class_type in self.supported_checkpoint_nodes and not metadata["model"]:
                metadata["model"] = inputs.get("ckpt_name")
            elif class_type in self.supported_sampler_nodes:
                if metadata["seed"] is None:
                    metadata["seed"] = inputs.get("seed")
                if metadata["steps"] is None:
                    metadata["steps"] = inputs.get("steps")
                if metadata["cfg"] is None:
                    metadata["cfg"] = inputs.get("cfg")
                if not metadata["sampler"]:
                    metadata["sampler"] = inputs.get("sampler_name")
                if not metadata["scheduler"]:
                    metadata["scheduler"] = inputs.get("scheduler")
        
        return metadata


class MetadataBuilder:
    """构建用于保存的元数据"""
    
    def build_parameters_text(self, metadata: Dict[str, Any]) -> str:
        """构建参数文本（用于嵌入图片）"""
        parts = []
        
        # 正向提示词
        positive = metadata.get("positive_prompt")
        if positive:
            parts.append(str(positive))
        
        # 负向提示词
        negative = metadata.get("negative_prompt")
        if negative:
            parts.append(f"Negative prompt: {negative}")
        
        # 技术参数
        params = []
        
        steps = metadata.get("steps")
        if steps is not None:
            params.append(f"Steps: {steps}")
            
        sampler = metadata.get("sampler")
        scheduler = metadata.get("scheduler")
        if sampler:
            if scheduler and scheduler != "normal":
                params.append(f"Sampler: {sampler} {scheduler}")
            else:
                params.append(f"Sampler: {sampler}")
        
        cfg = metadata.get("cfg")
        if cfg is not None:
            params.append(f"CFG scale: {cfg}")
            
        seed = metadata.get("seed")
        if seed is not None:
            params.append(f"Seed: {seed}")
        
        width = metadata.get("width")
        height = metadata.get("height")
        if width and height:
            params.append(f"Size: {width}x{height}")
        
        model = metadata.get("model")
        if model:
            model_name = os.path.splitext(os.path.basename(model))[0]
            # 这里可以添加模型哈希计算，但为了性能考虑暂时省略
            params.append(f"Model: {model_name}")
        
        if params:
            parts.append(", ".join(params))
        
        return "\n".join(parts)
    
    def build_metadata_json(self, folder_path: str, structure_mode: str, 
                           workflow_metadata: Dict, user_inputs: Dict) -> str:
        """构建完整的元数据JSON"""
        metadata = {
            "folder_path": folder_path,
            "structure_mode": structure_mode,
            "timestamp": datetime.now().isoformat(),
            "workflow_metadata": workflow_metadata,
            "user_inputs": user_inputs,
            "version": "1.0"
        }
        
        return json.dumps(metadata, ensure_ascii=False, indent=2)
