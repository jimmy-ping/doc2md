"""Universal Pandoc fallback for any format that native parsers can't handle.

Uses the system pandoc binary to convert to GFM (GitHub Flavored Markdown)
and normalizes the output into a ConversionResult.
"""

import subprocess
import tempfile
from pathlib import Path

from converters.base import BaseConverter, ConversionResult


class PandocFallback(BaseConverter):
    """Convert documents using Pandoc as a universal fallback."""

    # Pandoc-supported input formats we care about
    FORMAT_MAP = {
        ".docx": "docx",
        ".pptx": "pptx",
        ".odt": "odt",
        ".rtf": "rtf",
        ".html": "html",
        ".htm": "html",
        ".epub": "epub",
    }

    def convert(self) -> ConversionResult:
        ext = self.file_path.suffix.lower()
        input_fmt = self.FORMAT_MAP.get(ext, ext.lstrip("."))

        images: list[tuple[str, bytes]] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            media_dir = tmp / "media"
            media_dir.mkdir(exist_ok=True)
            output_file = tmp / "output.md"

            # Run pandoc
            cmd = [
                "pandoc",
                str(self.file_path),
                "-f", input_fmt,
                "-t", "gfm",
                "--wrap=none",
                f"--extract-media={media_dir}",
                "-o", str(output_file),
            ]

            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Pandoc 转换失败: {e.stderr.strip()}")
            except FileNotFoundError:
                raise RuntimeError("未找到 Pandoc，请运行: brew install pandoc")
            except subprocess.TimeoutExpired:
                raise RuntimeError("Pandoc 转换超时（超过 120 秒）")

            # Read generated markdown
            markdown = output_file.read_text(encoding="utf-8")

            # Collect extracted images
            if media_dir.exists():
                for img_file in sorted(media_dir.rglob("*")):
                    if img_file.is_file():
                        img_bytes = img_file.read_bytes()
                        filename, png_bytes = self._next_image(img_bytes, img_file.suffix.lstrip("."))
                        images.append((filename, png_bytes))
                        # Update markdown references to use our naming
                        old_path = str(img_file.relative_to(tmp))
                        new_path = f"images/{filename}"
                        markdown = markdown.replace(old_path, new_path)
                        # Also try replacing the absolute media path
                        markdown = markdown.replace(str(img_file), new_path)

        return ConversionResult(
            markdown=markdown.strip(),
            images=images,
            metadata={"format": input_fmt, "engine": "pandoc"},
        )
