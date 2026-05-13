import os
import re
import json
from typing import List, Optional
from src.utils.helpers import logger


class AIEngine:
    def __init__(self, config: dict):
        self.config = config.get("ai", {})
        self._caption_model = None
        self._nsfw_model = None
        self._tag_model = None

    def generate_caption(self, image_path: str, tags: list = None) -> str:
        if not self.config.get("caption_generator") or not self.config.get("enabled"):
            return self._fallback_caption(tags)
        try:
            ollama_host = self.config.get("ollama_host", "http://localhost:11434")
            model = self.config.get("ollama_model", "llama3.2")
            import requests
            prompt = f"Generate a short engaging Instagram caption for this image. Tags: {', '.join(tags or [])}. Keep it under 100 characters. Just the caption, no quotes."
            resp = requests.post(
                f"{ollama_host}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=30
            )
            if resp.status_code == 200:
                caption = resp.json().get("response", "").strip().strip('"').strip("'")
                if caption:
                    return caption
        except Exception as e:
            logger.debug(f"AI caption failed: {e}")
        return self._fallback_caption(tags)

    def generate_tags(self, image_path: str, max_tags: int = 15) -> List[str]:
        if not self.config.get("tag_generator") or not self.config.get("enabled"):
            return []
        try:
            from PIL import Image
            try:
                from transformers import BlipProcessor, BlipForConditionalGeneration
                model_name = "Salesforce/blip-image-captioning-base"
                processor = BlipProcessor.from_pretrained(model_name)
                model = BlipForConditionalGeneration.from_pretrained(model_name)
                img = Image.open(image_path).convert("RGB")
                inputs = processor(img, return_tensors="pt")
                out = model.generate(**inputs, max_length=50, num_beams=3)
                caption = processor.decode(out[0], skip_special_tokens=True)
                words = [w.strip().lower() for w in caption.split() if len(w) > 2]
                return list(set(words))[:max_tags]
            except:
                pass
        except Exception as e:
            logger.debug(f"AI tagging failed: {e}")
        return []

    def detect_nsfw(self, image_path: str) -> float:
        if not self.config.get("nsfw_detector") or not self.config.get("enabled"):
            return 0.0
        try:
            try:
                from transformers import pipeline
                classifier = pipeline("image-classification", model="Falconsai/nsfw_image_detection")
                result = classifier(image_path)
                for r in result:
                    if r["label"] == "nsfw":
                        return r["score"]
                return 0.0
            except:
                pass
        except Exception as e:
            logger.debug(f"NSFW detection failed: {e}")
        return 0.0

    def score_quality(self, image_path: str) -> float:
        if not self.config.get("quality_scorer") or not self.config.get("enabled"):
            return 5.0
        try:
            from PIL import Image
            import numpy as np
            img = Image.open(image_path).convert("L")
            arr = np.array(img)
            laplacian_var = np.var(arr)
            score = min(10.0, laplacian_var / 100)
            if img.size[0] < 640 or img.size[1] < 640:
                score -= 2.0
            return max(1.0, score)
        except:
            return 5.0

    def remove_background(self, image_path: str, output_path: str = None) -> Optional[str]:
        if not self.config.get("background_removal") or not self.config.get("enabled"):
            return None
        try:
            from rembg import remove
            from PIL import Image
            img = Image.open(image_path)
            result = remove(img)
            out_path = output_path or image_path
            result.save(out_path)
            return out_path
        except Exception as e:
            logger.error(f"Background removal failed: {e}")
            return None

    def upscale_image(self, image_path: str, output_path: str = None, scale: int = 2) -> Optional[str]:
        if not self.config.get("image_upscaling") or not self.config.get("enabled"):
            return None
        try:
            from PIL import Image
            img = Image.open(image_path)
            w, h = img.size
            new_size = (w * scale, h * scale)
            img_upscaled = img.resize(new_size, Image.LANCZOS)
            out_path = output_path or image_path
            img_upscaled.save(out_path, quality=95)
            return out_path
        except Exception as e:
            logger.error(f"Upscaling failed: {e}")
            return None

    def generate_image(self, prompt: str, output_path: str, negative_prompt: str = "",
                       width: int = 512, height: int = 512) -> Optional[str]:
        sd_config = self.config.get("stable_diffusion", {})
        if not sd_config.get("enabled"):
            return None
        try:
            from diffusers import StableDiffusionPipeline
            import torch
            model = sd_config.get("model", "runwayml/stable-diffusion-v1-5")
            pipe = StableDiffusionPipeline.from_pretrained(model, torch_dtype=torch.float16)
            pipe = pipe.to("cuda" if torch.cuda.is_available() else "cpu")
            np = negative_prompt or sd_config.get("negative_prompt", "blurry, bad quality")
            image = pipe(prompt, negative_prompt=np, width=width, height=height).images[0]
            image.save(output_path)
            return output_path
        except Exception as e:
            logger.error(f"SD image gen failed: {e}")
            return None

    def _fallback_caption(self, tags: list = None) -> str:
        templates = [
            "Beautiful capture! 📸",
            "Nature at its finest ✨",
            "Stunning view! 🔥",
            "Simply amazing 🌟",
            "What a shot!",
            "Incredible moment captured 📷",
            "Breathtaking! ✨",
        ]
        import random
        base = random.choice(templates)
        if tags:
            tag_str = " ".join(random.sample(tags, min(3, len(tags))))
            base = f"{base} #{tag_str.replace(' ', ' #')}"
        return base
