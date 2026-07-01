"""PDF → Markdown converter using PyMuPDF (fitz).

Extracts text and embedded images from each page.
Images placed at top/bottom of page based on their position heuristics.
"""

from pathlib import Path

import fitz  # PyMuPDF

from converters.base import BaseConverter, ConversionResult


class PDFConverter(BaseConverter):
    """Convert PDF files to Markdown with image extraction."""

    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self._seen_xrefs: set[int] = set()  # Deduplicate images across pages

    def convert(self) -> ConversionResult:
        doc = fitz.open(str(self.file_path))

        if doc.is_encrypted:
            # Try empty password
            if not doc.authenticate(""):
                doc.close()
                raise ValueError("PDF 已加密，无法读取")

        metadata = {
            "format": "pdf",
            "page_count": doc.page_count,
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
        }

        md_parts: list[str] = []
        images: list[tuple[str, bytes]] = []

        # Document title
        title = doc.metadata.get("title", "")
        if title:
            md_parts.append(f"# {title}\n")

        for page_num in range(doc.page_count):
            page = doc[page_num]
            page_md, page_images = self._convert_page(page, page_num + 1)
            if page_md.strip():
                md_parts.append(page_md)
            images.extend(page_images)

        doc.close()

        markdown = "\n\n".join(md_parts)
        return ConversionResult(
            markdown=self._clean_text(markdown),
            images=images,
            metadata=metadata,
        )

    def _convert_page(
        self, page: fitz.Page, page_num: int
    ) -> tuple[str, list[tuple[str, bytes]]]:
        """Convert a single page to markdown.

        Returns:
            (page_markdown, list_of_image_tuples)
        """
        lines: list[str] = []
        images: list[tuple[str, bytes]] = []

        # Page separator
        lines.append(f"---")
        lines.append(f"<!-- 第 {page_num} 页 -->")

        # Get page dimensions for image position heuristics
        page_height = page.rect.height
        threshold = page_height * 0.25  # top 25% = "top of page"

        # Extract images first to know their positions
        image_list = page.get_images(full=True)
        top_images: list[str] = []  # Image refs to place before text
        bottom_images: list[str] = []  # Image refs to place after text

        for img_info in image_list:
            xref = img_info[0]
            if xref in self._seen_xrefs:
                continue
            self._seen_xrefs.add(xref)

            try:
                base_image = doc_extract_image(page.parent, xref)
                if base_image is None:
                    continue
                img_bytes = base_image["image"]
                ext = base_image.get("ext", "png")
                filename, png_bytes = self._next_image(img_bytes, ext)
                images.append((filename, png_bytes))
                img_md = self._image_md(filename)

                # Heuristic: check if image is near top of page
                img_rects = page.get_image_rects(img_info)
                is_top = False
                if img_rects:
                    for rect in img_rects:
                        if hasattr(rect, 'y0') and rect.y0 < threshold:
                            is_top = True
                            break
                        elif hasattr(rect, 'top_left') and rect.top_left.y < threshold:
                            is_top = True
                            break

                if is_top:
                    top_images.append(img_md)
                else:
                    bottom_images.append(img_md)
            except Exception:
                continue

        # Place top-of-page images
        for ref in top_images:
            lines.append(ref)

        # Extract text
        text = page.get_text("text")
        if text.strip():
            lines.append(text.rstrip())

        # Place bottom-of-page images
        for ref in bottom_images:
            lines.append(ref)

        return "\n".join(lines), images


def doc_extract_image(doc: fitz.Document, xref: int) -> dict | None:
    """Wrapper for doc.extract_image that handles errors."""
    try:
        return doc.extract_image(xref)
    except Exception:
        return None
