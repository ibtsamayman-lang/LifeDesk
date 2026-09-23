"""
document_extractor.py
----------------------
Handles turning a raw uploaded file (PDF / PNG / JPG) into plain text,
using PyMuPDF for native PDF text and falling back to OCR (pytesseract)
when little or no text is found. Designed to never raise — callers get
back a TextExtractionResult with a human-readable note about what
strategy was used, even on partial or total failure.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    from PIL import Image, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pytesseract
    HAS_TESSERACT = True
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        HAS_TESSERACT = False
except ImportError:
    HAS_TESSERACT = False


MIN_TEXT_LENGTH = 30  # below this, a PDF page is considered "textless"


@dataclass
class TextExtractionResult:
    text: str = ""
    method: str = "none"
    note: str = ""
    success: bool = False


class DocumentExtractor:
    """Extracts plain text from PDF and image files."""

    def extract(self, file_path: str) -> TextExtractionResult:
        suffix = Path(file_path).suffix.lower()
        try:
            if suffix == ".pdf":
                return self._extract_pdf(file_path)
            elif suffix in (".png", ".jpg", ".jpeg"):
                return self._extract_image(file_path)
            else:
                return TextExtractionResult(
                    note=f"Unsupported file type: {suffix}", success=False
                )
        except Exception as exc:  # never let extraction crash the app
            return TextExtractionResult(
                note=f"Extraction failed unexpectedly ({type(exc).__name__}). "
                     f"The document was saved, but no text could be read.",
                success=False,
            )

    # ------------------------------------------------------------- PDF ----
    def _extract_pdf(self, file_path: str) -> TextExtractionResult:
        if not HAS_FITZ:
            return TextExtractionResult(
                note="PDF library unavailable. Could not read this PDF.", success=False
            )

        native_text = ""
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    native_text += page.get_text() + "\n"
        except Exception:
            native_text = ""

        if len(native_text.strip()) >= MIN_TEXT_LENGTH:
            return TextExtractionResult(
                text=native_text.strip(),
                method="pdf_text",
                note="Text-based PDF extraction was used.",
                success=True,
            )

        # Fall back to OCR on rendered pages
        if not HAS_TESSERACT or not HAS_PIL:
            note = "OCR is unavailable. Text-based PDF extraction was used."
            return TextExtractionResult(
                text=native_text.strip(),
                method="pdf_text_partial",
                note=note,
                success=len(native_text.strip()) > 0,
            )

        ocr_text = ""
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_bytes = pix.tobytes("png")
                    import io
                    image = Image.open(io.BytesIO(img_bytes))
                    ocr_text += pytesseract.image_to_string(image) + "\n"
        except Exception:
            pass

        combined = (native_text + "\n" + ocr_text).strip()
        if combined:
            return TextExtractionResult(
                text=combined,
                method="pdf_ocr",
                note="Scanned PDF detected — OCR was used to extract text.",
                success=True,
            )
        return TextExtractionResult(
            note="No text could be extracted from this PDF, even with OCR.",
            success=False,
        )

    # ----------------------------------------------------------- Image ----
    def _extract_image(self, file_path: str) -> TextExtractionResult:
        if not HAS_PIL:
            return TextExtractionResult(
                note="Image library unavailable. Could not read this image.", success=False
            )
        if not HAS_TESSERACT:
            return TextExtractionResult(
                note="OCR is unavailable. Image text could not be read automatically.",
                success=False,
            )
        try:
            image = Image.open(file_path)
            image = ImageOps.exif_transpose(image)
            gray = image.convert("L")
            text = pytesseract.image_to_string(gray)
            if text.strip():
                return TextExtractionResult(
                    text=text.strip(), method="image_ocr", note="OCR was used on the image.",
                    success=True,
                )
            return TextExtractionResult(
                note="OCR ran but found no readable text in this image.", success=False
            )
        except Exception:
            return TextExtractionResult(
                note="This image could not be processed.", success=False
            )
