"""Abstract base class and shared types for all converters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from PIL import Image


@dataclass
class ConversionResult:
    """Output of any format converter.

    Attributes:
        markdown: Complete markdown text with image references.
        images: List of (filename, image_bytes) tuples for extracted images.
        metadata: Optional dict with keys like title, author, page_count, etc.
    """

    markdown: str
    images: list[tuple[str, bytes]] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class BaseConverter(ABC):
    """Abstract base for all format-specific converters.

    Subclasses must implement convert() and return a ConversionResult.
    They may use the _save_image / _image_md helpers for consistent naming.
    """

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._img_counter = 0

    @abstractmethod
    def convert(self) -> ConversionResult:
        """Parse the file and produce markdown + images."""
        ...

    # ── Image helpers (shared naming scheme) ──────────────────

    def _next_image(self, img_bytes: bytes, source_ext: str = "png") -> tuple[str, bytes]:
        """Normalize image bytes to PNG, return (filename, png_bytes).

        Args:
            img_bytes: Raw image bytes from the document.
            source_ext: Original extension hint (e.g. 'jpeg', 'png').

        Returns:
            (filename, normalized_png_bytes) — e.g. ('img_001.png', b'...')
        """
        self._img_counter += 1
        filename = f"img_{self._img_counter:03d}.png"

        # Convert to PNG if needed
        if source_ext.lower() in ("png",):
            return filename, img_bytes
        try:
            img = Image.open(BytesIO(img_bytes))
            buf = BytesIO()
            img.save(buf, format="PNG")
            return filename, buf.getvalue()
        except Exception:
            # Fallback: keep original bytes
            return filename, img_bytes

    @staticmethod
    def _image_md(filename: str, alt: str = "") -> str:
        """Return markdown image reference: ![](images/filename)."""
        alt_text = alt or filename
        return f"![{alt_text}](images/{filename})"

    @staticmethod
    def _escape_pipe(text: str) -> str:
        """Escape pipe characters in markdown table cells."""
        return str(text).replace("|", "\\|").replace("\n", " ")

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalize whitespace: collapse blank lines, strip trailing spaces."""
        lines = []
        prev_blank = False
        for line in text.splitlines():
            stripped = line.rstrip()
            is_blank = not stripped
            if is_blank and prev_blank:
                continue
            lines.append(stripped)
            prev_blank = is_blank
        return "\n".join(lines).strip("\n")
