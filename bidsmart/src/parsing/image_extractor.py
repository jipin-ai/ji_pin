"""Image extractor for bid documents — extracts embedded images from DOCX/PDF.

Since DeepSeek V4 (deepseek-chat) does NOT support multimodal Vision API,
we extract image metadata and inject a structured summary into the document
text so the LLM knows images exist and can handle related review items
appropriately (mark as unable_to_judge instead of false non_compliant).

Future: replace with PaddleOCR or a Vision-capable model when available.
"""

from __future__ import annotations

import io
import logging
import zipfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExtractedImage:
    """An image extracted from a document."""
    data: bytes              # raw image bytes
    format: str              # png / jpeg / emf
    page_number: int         # 0 if unknown
    index: int               # 0-based image index in document
    filename: str = ""       # original filename


class ImageExtractor:
    """Extract embedded images from DOCX/PDF and generate metadata summaries."""

    @staticmethod
    def _image_count(path: str | Path) -> int:
        """Quick count of images in a document without extracting."""
        path = Path(path)
        ext = path.suffix.lower()
        if ext == ".docx":
            try:
                with zipfile.ZipFile(path) as z:
                    return len([n for n in z.namelist() if n.startswith("word/media/")])
            except Exception:
                return 0
        elif ext == ".pdf":
            try:
                import fitz
                doc = fitz.open(str(path))
                count = sum(len(doc[i].get_images()) for i in range(len(doc)))
                doc.close()
                return count
            except Exception:
                return 0
        return 0

    @staticmethod
    async def extract_from_docx(path: str | Path) -> list[ExtractedImage]:
        """Extract all images from a DOCX file's word/media/ directory."""
        path = Path(path)
        images: list[ExtractedImage] = []

        try:
            with zipfile.ZipFile(path) as z:
                media_names = sorted(
                    [n for n in z.namelist() if n.startswith("word/media/")]
                )
                for idx, name in enumerate(media_names):
                    raw = z.read(name)
                    ext = Path(name).suffix.lower()
                    fmt = ext.lstrip(".")
                    if fmt in ("jpeg", "jpg"):
                        fmt = "jpeg"
                    elif fmt == "emf":
                        fmt = "emf"  # keep as-is for metadata

                    images.append(ExtractedImage(
                        data=raw,
                        format=fmt,
                        page_number=0,
                        index=idx,
                        filename=Path(name).name,
                    ))
        except Exception as e:
            logger.error(f"Failed to extract images from DOCX {path}: {e}")

        return images

    @staticmethod
    async def extract_from_pdf(path: str | Path) -> list[ExtractedImage]:
        """Extract all embedded images from a PDF via pymupdf."""
        path = Path(path)
        images: list[ExtractedImage] = []

        try:
            import fitz
            doc = fitz.open(str(path))
            idx = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                for img_info in page.get_images(full=True):
                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                        raw = base_image["image"]
                        ext = base_image["ext"]
                        fmt = ext if ext != "jpeg" else "jpeg"

                        images.append(ExtractedImage(
                            data=raw,
                            format=fmt,
                            page_number=page_num + 1,
                            index=idx,
                            filename=f"xref{xref}.{ext}",
                        ))
                        idx += 1
                    except Exception as e:
                        logger.warning(f"Failed to extract PDF image xref={xref}: {e}")
            doc.close()
        except Exception as e:
            logger.error(f"Failed to extract images from PDF {path}: {e}")

        return images

    @staticmethod
    async def extract_and_describe(
        path: str | Path,
        doc_type: str = "docx",
    ) -> tuple[list[ExtractedImage], str]:
        """Extract images and return a human-readable summary string.

        Since DeepSeek V4 does not support multimodal Vision API,
        we generate a structured metadata description that gets
        injected into the document text. The LLM then knows images
        exist and can handle related review items appropriately
        (e.g., mark as unable_to_judge instead of false non_compliant
        when a requirement may depend on image content like seals or
        certificates).

        Returns:
            (images list, description string)
        """
        if doc_type == "docx":
            images = await ImageExtractor.extract_from_docx(path)
        elif doc_type == "pdf":
            images = await ImageExtractor.extract_from_pdf(path)
        else:
            return [], ""

        if not images:
            return [], ""

        # Build summary
        formats = sorted(set(img.format for img in images))
        pages = sorted(set(img.page_number for img in images if img.page_number > 0))
        total_size_mb = sum(len(img.data) for img in images) / (1024 * 1024)
        emf_count = sum(1 for img in images if img.format == "emf")

        desc = (
            f"\n[图片识别] 此章节所在的原始文档（{doc_type.upper()}）"
            f"包含 {len(images)} 张嵌入图片"
            f"（总大小约 {total_size_mb:.1f}MB，格式: {', '.join(formats)}"
        )
        if emf_count:
            desc += f"，其中 {emf_count} 张为 EMF 矢量图（可能为印章/公章）"
        desc += "）"
        if pages:
            desc += f"，分布在第 {min(pages)} 至 {max(pages)} 页"
        desc += (
            "。注意：这些图片尚未进行 OCR 文字识别，其内容可能包括："
            "资质证书扫描件、盖章页/公章、技术图纸、参数表格截图、"
            "签字页等关键信息。在审查与本段相关的条款时，若某项招标要求"
            "可能依赖于图片中的信息（如证书编号、盖章确认、签字等），"
            "请判定为 unable_to_judge 而非 non_compliant，"
            "并在 reason 中注明'需人工核验图片内容'。"
        )

        return images, desc


# ── Future: OCR integration ────────────────────────────────────────────
# When a Vision-capable model or local OCR (PaddleOCR) becomes available:
#   1. Add recognize_image() → DeepSeek/PaddleOCR → text
#   2. Add recognize_batch() → concurrent batch processing
#   3. Replace extract_and_describe with full OCR pipeline
#   4. Map recognized text to sections by page_number
