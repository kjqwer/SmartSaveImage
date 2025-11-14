"""Top-level package for SmartSaveImage."""

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    
]

__author__ = """kj"""
__email__ = "2990346238@qq.com"
__version__ = "0.0.1"

from .src.SmartSaveImage.nodes import NODE_CLASS_MAPPINGS
from .src.SmartSaveImage.nodes import NODE_DISPLAY_NAME_MAPPINGS
import os
import re
import json
import hashlib
import numpy as np
from PIL import Image, PngImagePlugin
import piexif
import folder_paths
import nodes

class SmartSaveImage:
    CATEGORY = "IO/Output"
    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "process"

    token_pattern = re.compile(r"(%[^%]+%)")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "folder_plan": ("STRING", {"default": "", "multiline": True}),
                "file_format": (["png", "jpeg", "webp"],),
                "preview_only": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "quality": ("INT", {"default": 100, "min": 1, "max": 100}),
                "lossless_webp": ("BOOLEAN", {"default": False}),
                "embed_workflow": ("BOOLEAN", {"default": False}),
                "add_counter": ("BOOLEAN", {"default": True}),
                "root_dir": ("STRING", {"default": "output", "multiline": False}),
            },
            "hidden": {
                "id": "UNIQUE_ID",
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    def sanitize(self, s):
        return re.sub(r"[:*?\"<>|]", "_", s)

    def sanitize_segment(self, s):
        s = str(s)
        s = re.sub(r"[:*?\"<>|]", "_", s)
        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"[^A-Za-z0-9_\-]", "_", s)
        return s.strip("_")

    def build_metadata(self, prompt, extra_pnginfo, steps, sampler_name, scheduler, cfg, seed, width, height, modelname):
        parts = []
        ptxt = (json.dumps(prompt) if isinstance(prompt, dict) else (prompt or ""))
        parts.append(str(ptxt).replace("\n", " ").strip())
        neg = ""
        if isinstance(extra_pnginfo, dict):
            neg = extra_pnginfo.get("neg_prompt", "")
        if neg:
            parts.append(f"Negative prompt: {str(neg).replace('\n',' ').strip()}")
        params = []
        if steps is not None:
            params.append(f"Steps: {steps}")
        if sampler_name:
            if scheduler and scheduler != "normal":
                params.append(f"Sampler: {sampler_name} {scheduler}")
            else:
                params.append(f"Sampler: {sampler_name}")
        if cfg is not None:
            params.append(f"CFG Scale: {cfg}")
        if seed is not None:
            params.append(f"Seed: {seed}")
        params.append(f"Size: {width}x{height}")
        modelhash = None
        modellabel = None
        if modelname:
            try:
                ckpt_path = folder_paths.get_full_path("checkpoints", modelname)
                h = hashlib.sha256()
                with open(ckpt_path, "rb") as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(chunk)
                modelhash = h.hexdigest()[:10]
            except Exception:
                modelhash = None
            modellabel = os.path.splitext(os.path.basename(modelname))[0]
        if modellabel:
            if modelhash:
                params.append(f"Model hash: {modelhash}, Model: {modellabel}")
            else:
                params.append(f"Model: {modellabel}")
        parts.append(", ".join(params))
        return "\n".join(parts)

    def extract_from_workflow(self, extra_pnginfo):
        out = {"seed": None, "steps": None, "cfg": None, "sampler_name": None, "scheduler": None, "model": None}
        wf = None
        if isinstance(extra_pnginfo, dict):
            wf = extra_pnginfo.get("workflow")
        if isinstance(wf, dict):
            nodes_list = wf.get("nodes") or []
            for n in nodes_list:
                if not isinstance(n, dict):
                    continue
                ct = n.get("class_type") or n.get("type")
                inputs = n.get("inputs") or {}
                if ct in ("CheckpointLoaderSimple", "CheckpointLoader", "CheckpointLoaderV2"):
                    m = inputs.get("ckpt_name") or inputs.get("model") or inputs.get("ckpt")
                    if m and not out["model"]:
                        out["model"] = m
                if ct in ("KSampler", "KSamplerAdvanced"):
                    if inputs.get("seed") is not None:
                        out["seed"] = inputs.get("seed")
                    if inputs.get("steps") is not None:
                        out["steps"] = inputs.get("steps")
                    if inputs.get("cfg") is not None:
                        out["cfg"] = inputs.get("cfg")
                    if inputs.get("sampler_name") is not None:
                        out["sampler_name"] = inputs.get("sampler_name")
                    if inputs.get("scheduler") is not None:
                        out["scheduler"] = inputs.get("scheduler")
        return out

    def extract_from_prompt(self, prompt):
        out = {"seed": None, "steps": None, "cfg": None, "sampler_name": None, "scheduler": None, "model": None}
        if isinstance(prompt, dict):
            nodes_list = prompt.get("nodes") or []
            for n in nodes_list:
                if not isinstance(n, dict):
                    continue
                ct = n.get("class_type") or n.get("type")
                inputs = n.get("inputs") or {}
                if ct in ("CheckpointLoaderSimple", "CheckpointLoader", "CheckpointLoaderV2"):
                    m = inputs.get("ckpt_name") or inputs.get("model") or inputs.get("ckpt")
                    if m and not out["model"]:
                        out["model"] = m
                if ct in ("KSampler", "KSamplerAdvanced"):
                    if inputs.get("seed") is not None:
                        out["seed"] = inputs.get("seed")
                    if inputs.get("steps") is not None:
                        out["steps"] = inputs.get("steps")
                    if inputs.get("cfg") is not None:
                        out["cfg"] = inputs.get("cfg")
                    if inputs.get("sampler_name") is not None:
                        out["sampler_name"] = inputs.get("sampler_name")
                    if inputs.get("scheduler") is not None:
                        out["scheduler"] = inputs.get("scheduler")
        return out

    def format_template(self, template, metadata_dict):
        result = template
        matches = re.findall(self.token_pattern, template)
        for seg in matches:
            inner = seg.strip("%")
            parts = inner.split(":")
            key = parts[0]
            if key == "seed":
                val = metadata_dict.get("seed")
                if isinstance(val, (int, float)):
                    if isinstance(val, int) and val < 0:
                        rep = "rand"
                    else:
                        rep = str(val)
                else:
                    rep = "seed"
                result = result.replace(seg, self.sanitize_segment(rep))
            elif key == "width":
                result = result.replace(seg, self.sanitize_segment(metadata_dict.get("width", "")))
            elif key == "height":
                result = result.replace(seg, self.sanitize_segment(metadata_dict.get("height", "")))
            elif key == "pprompt":
                raw = metadata_dict.get("prompt", "untitled")
                txt = str(raw).replace("\n", " ").strip()
                if len(parts) >= 2:
                    try:
                        n = int(parts[1])
                        txt = txt[:n]
                    except Exception:
                        pass
                result = result.replace(seg, self.sanitize_segment(txt))
            elif key == "nprompt":
                raw = metadata_dict.get("negative_prompt", "")
                txt = str(raw).replace("\n", " ").strip()
                if len(parts) >= 2:
                    try:
                        n = int(parts[1])
                        txt = txt[:n]
                    except Exception:
                        pass
                result = result.replace(seg, self.sanitize_segment(txt))
            elif key == "model":
                m = str(metadata_dict.get("model", "model"))
                m = os.path.splitext(os.path.basename(m))[0]
                if len(parts) >= 2:
                    try:
                        n = int(parts[1])
                        m = m[:n]
                    except Exception:
                        pass
                result = result.replace(seg, self.sanitize_segment(m))
            elif key == "date":
                from datetime import datetime
                now = datetime.now()
                table = {"yyyy": f"{now.year:04d}", "yy": f"{now.year % 100:02d}", "MM": f"{now.month:02d}", "dd": f"{now.day:02d}", "hh": f"{now.hour:02d}", "mm": f"{now.minute:02d}", "ss": f"{now.second:02d}"}
                fmt = "yyyyMMddhhmmss"
                if len(parts) >= 2:
                    fmt = parts[1]
                for k, v in table.items():
                    fmt = fmt.replace(k, v)
                result = result.replace(seg, fmt)
        parts = [self.sanitize_segment(p) for p in result.split("/") if p and p.strip()]
        if not parts:
            return "ComfyUI"
        return "/".join(parts)

    def save_batch(self, images, full_output_folder, base_filename, file_format, quality, lossless_webp, embed_workflow, png_parameters_text, extra_pnginfo, add_counter, counter_start):
        results = []
        if not os.path.exists(full_output_folder):
            os.makedirs(full_output_folder, exist_ok=True)
        for i, image in enumerate(images):
            arr = 255.0 * image.cpu().numpy()
            pil = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
            fname = base_filename
            if add_counter:
                fname += f"_{counter_start + i:05}_"
            if file_format == "png":
                file = fname + ".png"
                pnginfo = PngImagePlugin.PngInfo()
                if png_parameters_text:
                    pnginfo.add_text("parameters", png_parameters_text)
                if embed_workflow and extra_pnginfo is not None and isinstance(extra_pnginfo, dict) and "workflow" in extra_pnginfo:
                    pnginfo.add_text("workflow", json.dumps(extra_pnginfo["workflow"]))
                pil.save(os.path.join(full_output_folder, file), format="PNG", compress_level=4, pnginfo=pnginfo)
            elif file_format == "jpeg":
                file = fname + ".jpg"
                save_kwargs = {"quality": quality, "optimize": True}
                if png_parameters_text:
                    try:
                        exif_dict = {"Exif": {piexif.ExifIFD.UserComment: b"UNICODE\0" + png_parameters_text.encode("utf-16be")}}
                        exif_bytes = piexif.dump(exif_dict)
                        save_kwargs["exif"] = exif_bytes
                    except Exception:
                        pass
                pil.save(os.path.join(full_output_folder, file), format="JPEG", **save_kwargs)
            else:
                file = fname + ".webp"
                save_kwargs = {"quality": quality, "lossless": lossless_webp, "method": 0}
                try:
                    exif_dict = {}
                    if png_parameters_text:
                        exif_dict["Exif"] = {piexif.ExifIFD.UserComment: b"UNICODE\0" + png_parameters_text.encode("utf-16be")}
                    if embed_workflow and extra_pnginfo is not None and isinstance(extra_pnginfo, dict) and "workflow" in extra_pnginfo:
                        exif_dict["0th"] = {piexif.ImageIFD.ImageDescription: "Workflow:" + json.dumps(extra_pnginfo["workflow"])}
                    exif_bytes = piexif.dump(exif_dict)
                    save_kwargs["exif"] = exif_bytes
                except Exception:
                    pass
                pil.save(os.path.join(full_output_folder, file), format="WEBP", **save_kwargs)
            results.append({"filename": file, "subfolder": os.path.basename(os.path.normpath(full_output_folder)), "type": "output"})
        return results

    def process(self, images, folder_plan, file_format, preview_only, quality=100, lossless_webp=False, embed_workflow=False, add_counter=True, root_dir="", id=None, prompt=None, extra_pnginfo=None):
        rd = (root_dir or "").strip()
        base = folder_paths.get_output_directory()
        if rd.lower() in ("", "output", ".", "./", "/"):
            output_dir = base
        elif os.path.isabs(rd):
            output_dir = rd
        else:
            output_dir = os.path.join(base, rd)
        if not isinstance(images, (list, tuple, np.ndarray)):
            if len(images.shape) == 3:
                images = [images]
            else:
                images = [img for img in images]
        h = images[0].shape[0]
        w = images[0].shape[1]
        plan = {}
        try:
            plan = json.loads(folder_plan) if isinstance(folder_plan, str) and folder_plan.strip() else {}
        except Exception:
            plan = {}
        segments = plan.get("segments") if isinstance(plan, dict) else None
        meta = plan.get("metadata") if isinstance(plan, dict) else None
        if not isinstance(meta, dict):
            ex = self.extract_from_prompt(prompt)
            if not any(v is not None for v in ex.values()):
                ex = self.extract_from_workflow(extra_pnginfo)
            pos_text = None
            neg_text = None
            wf = extra_pnginfo.get("workflow") if isinstance(extra_pnginfo, dict) else None
            if isinstance(wf, dict):
                for n in wf.get("nodes", []) or []:
                    if not isinstance(n, dict):
                        continue
                    ct = n.get("class_type") or n.get("type")
                    inputs = n.get("inputs") or {}
                    if ct in ("CLIPTextEncode", "CLIPTextEncodeSDXL", "T5TextEncode") and isinstance(inputs.get("text"), str):
                        if pos_text is None:
                            pos_text = inputs.get("text")
                        elif neg_text is None:
                            neg_text = inputs.get("text")
            if pos_text is None and isinstance(prompt, dict):
                for n in prompt.get("nodes", []) or []:
                    if not isinstance(n, dict):
                        continue
                    ct = n.get("class_type") or n.get("type")
                    inputs = n.get("inputs") or {}
                    if ct in ("CLIPTextEncode", "CLIPTextEncodeSDXL", "T5TextEncode") and isinstance(inputs.get("text"), str):
                        if pos_text is None:
                            pos_text = inputs.get("text")
                        elif neg_text is None:
                            neg_text = inputs.get("text")
            meta = {"seed": ex.get("seed"), "steps": ex.get("steps"), "cfg": ex.get("cfg"), "sampler_name": ex.get("sampler_name"), "scheduler": ex.get("scheduler"), "model": ex.get("model"), "width": w, "height": h, "prompt": (pos_text if isinstance(pos_text, str) and pos_text.strip() else (prompt if isinstance(prompt, str) else "untitled")), "negative_prompt": (neg_text if isinstance(neg_text, str) else (extra_pnginfo.get("neg_prompt", "") if isinstance(extra_pnginfo, dict) else ""))}
        if not isinstance(segments, list) or not segments:
            template = "ComfyUI/%date:yyyy-MM-dd%/%model%/%seed%/%pprompt:64%"
            processed_prefix = self.format_template(template, meta)
        else:
            cleaned = [self.sanitize_segment(s) for s in segments if isinstance(s, str) and s.strip()]
            if not cleaned:
                processed_prefix = "ComfyUI"
            else:
                processed_prefix = "/".join(cleaned)
        if preview_only:
            res = nodes.PreviewImage().save_images(images, filename_prefix=processed_prefix, prompt=prompt, extra_pnginfo=extra_pnginfo)
            return {"ui": res.get("ui", {}), "result": (images,)}
        full_output_folder, base_filename, counter, subfolder, processed_prefix2 = folder_paths.get_save_image_path(processed_prefix, output_dir, w, h)
        metadata_text = self.build_metadata(meta.get("prompt"), extra_pnginfo, meta.get("steps"), meta.get("sampler_name"), meta.get("scheduler"), meta.get("cfg"), meta.get("seed"), w, h, meta.get("model"))
        results = self.save_batch(images, full_output_folder, base_filename, file_format, quality, lossless_webp, embed_workflow, metadata_text, extra_pnginfo, add_counter, counter)
        return {"ui": {"images": results}, "result": (images,)}

class SmartMetaCollector:
    CATEGORY = "IO/Output"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("folder_plan",)
    FUNCTION = "collect"

    @classmethod
    def INPUT_TYPES(cls):
        import comfy
        return {
            "required": {
                "mode": (["workflow", "custom"],),
                "enable_date": ("BOOLEAN", {"default": True}),
                "date_format": ("STRING", {"default": "yyyy-MM-dd", "multiline": False}),
                "enable_model": ("BOOLEAN", {"default": True}),
                "enable_seed": ("BOOLEAN", {"default": True}),
                "enable_prompt": ("BOOLEAN", {"default": True}),
                "prompt_len": ("INT", {"default": 64, "min": 1, "max": 512}),
            },
            "optional": {
                "modelname": (folder_paths.get_filename_list("checkpoints"),),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "positive": ("STRING", {"default": "", "multiline": True}),
                "negative": ("STRING", {"default": "", "multiline": True}),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS,),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS,),
                "width": ("INT", {"default": 0, "min": 0, "max": 16384}),
                "height": ("INT", {"default": 0, "min": 0, "max": 16384}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    def collect(self, mode, enable_date, date_format, enable_model, enable_seed, enable_prompt, prompt_len, modelname=None, seed=0, positive="", negative="", sampler_name=None, scheduler=None, width=0, height=0, prompt=None, extra_pnginfo=None):
        segs = ["ComfyUI"]
        meta = {"seed": None, "steps": None, "cfg": None, "sampler_name": None, "scheduler": None, "model": None, "width": width if width else None, "height": height if height else None, "prompt": None, "negative_prompt": None}
        if mode == "workflow":
            wf = extra_pnginfo.get("workflow") if isinstance(extra_pnginfo, dict) else None
            ex = SmartSaveImage().extract_from_workflow(extra_pnginfo)
            meta.update(ex)
            pos_text = None
            neg_text = None
            if isinstance(wf, dict):
                for n in wf.get("nodes", []) or []:
                    if not isinstance(n, dict):
                        continue
                    ct = n.get("class_type") or n.get("type")
                    inputs = n.get("inputs") or {}
                    if ct in ("CLIPTextEncode", "CLIPTextEncodeSDXL", "T5TextEncode") and isinstance(inputs.get("text"), str):
                        if pos_text is None:
                            pos_text = inputs.get("text")
                        elif neg_text is None:
                            neg_text = inputs.get("text")
            meta["prompt"] = pos_text if isinstance(pos_text, str) and pos_text.strip() else "untitled"
            meta["negative_prompt"] = neg_text if isinstance(neg_text, str) else ""
        else:
            meta["model"] = modelname or meta["model"]
            meta["seed"] = seed
            meta["sampler_name"] = sampler_name
            meta["scheduler"] = scheduler
            meta["prompt"] = positive if isinstance(positive, str) and positive.strip() else "untitled"
            meta["negative_prompt"] = negative if isinstance(negative, str) else ""
        from datetime import datetime
        if enable_date:
            now = datetime.now()
            table = {"yyyy": f"{now.year:04d}", "yy": f"{now.year % 100:02d}", "MM": f"{now.month:02d}", "dd": f"{now.day:02d}", "hh": f"{now.hour:02d}", "mm": f"{now.minute:02d}", "ss": f"{now.second:02d}"}
            fmt = date_format or "yyyy-MM-dd"
            for k, v in table.items():
                fmt = fmt.replace(k, v)
            segs.append(SmartSaveImage().sanitize_segment(fmt))
        if enable_model:
            m = os.path.splitext(os.path.basename(meta.get("model") or "model"))[0]
            segs.append(SmartSaveImage().sanitize_segment(m))
        if enable_seed:
            s = meta.get("seed")
            segs.append(SmartSaveImage().sanitize_segment((str(s) if s is not None else "seed")))
        if enable_prompt:
            p = str(meta.get("prompt") or "untitled").replace("\n", " ")
            p = p[:prompt_len] if isinstance(prompt_len, int) and prompt_len > 0 else p
            segs.append(SmartSaveImage().sanitize_segment(p))
        plan = {"segments": segs, "metadata": meta}
        return (json.dumps(plan),)


NODE_CLASS_MAPPINGS = {
    "Smart Save Image": SmartSaveImage,
    "Smart Meta Collector": SmartMetaCollector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Smart Save Image": "Smart Save Image",
    "Smart Meta Collector": "Smart Meta Collector",
}

