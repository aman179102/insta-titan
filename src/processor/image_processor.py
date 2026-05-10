import os
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont, ExifTags
from io import BytesIO
from typing import Optional, Tuple
from src.utils.helpers import logger


class ImageProcessor:
    def __init__(self, config: dict):
        self.config = config.get("processor", {})

    def process(self, image_path: str) -> Tuple[bool, str]:
        try:
            img = Image.open(image_path)
            original_format = img.format or "JPEG"
            if self.config.get("strip_exif", True):
                img = self._strip_exif(img)
            if self.config.get("resize_to_instagram", True):
                img = self._resize_instagram(img)
            if self.config.get("auto_enhance", False):
                img = self._auto_enhance(img)
            if self.config.get("add_watermark", False):
                img = self._add_watermark(img)
            max_size = self.config.get("max_size_mb", 10) * 1024 * 1024
            quality = self.config.get("optimize_quality", 85)
            img.save(image_path, format=original_format, quality=quality, optimize=True)
            if os.path.getsize(image_path) > max_size:
                self._compress_to_size(image_path, max_size, quality)
            return True, image_path
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return False, image_path

    def create_collage(self, image_paths: list, output_path: str,
                       layout: str = "grid") -> Optional[str]:
        try:
            images = [Image.open(p) for p in image_paths]
            if layout == "grid":
                cols = 2
                rows = (len(images) + 1) // 2
                thumb_w = 600
                thumb_h = 600
                canvas = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (255, 255, 255))
                for i, img in enumerate(images):
                    img.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
                    x = (i % cols) * thumb_w + (thumb_w - img.width) // 2
                    y = (i // cols) * thumb_h + (thumb_h - img.height) // 2
                    canvas.paste(img, (x, y))
                canvas.save(output_path, quality=85)
                return output_path
            return None
        except Exception as e:
            logger.error(f"Collage creation failed: {e}")
            return None

    def _resize_instagram(self, img: Image.Image) -> Image.Image:
        target_ratio = 1.0
        w, h = img.size
        ratio = w / h
        if abs(ratio - 1.0) < 0.1:
            return img
        if ratio > target_ratio:
            new_w = int(h * target_ratio)
            offset = (w - new_w) // 2
            img = img.crop((offset, 0, offset + new_w, h))
        else:
            new_h = int(w / target_ratio)
            offset = (h - new_h) // 2
            img = img.crop((0, offset, w, offset + new_h))
        return img

    def _strip_exif(self, img: Image.Image) -> Image.Image:
        data = list(img.getdata())
        clean = Image.new(img.mode, img.size)
        clean.putdata(data)
        return clean

    def _auto_enhance(self, img: Image.Image) -> Image.Image:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.05)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.1)
        img = img.filter(ImageFilter.SHARPEN)
        return img

    def _add_watermark(self, img: Image.Image) -> Image.Image:
        text = self.config.get("watermark_text", "@instaauto")
        opacity = self.config.get("watermark_opacity", 0.3)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        font_size = max(20, img.width // 30)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = img.width - tw - 20
        y = img.height - th - 20
        alpha = int(255 * opacity)
        draw.text((x, y), text, font=font, fill=(255, 255, 255, alpha))
        return Image.alpha_composite(img, overlay)

    def _compress_to_size(self, image_path: str, max_bytes: int, quality: int = 85):
        img = Image.open(image_path)
        while os.path.getsize(image_path) > max_bytes and quality > 10:
            quality -= 5
            img.save(image_path, quality=quality, optimize=True)
