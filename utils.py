"""Shared utilities for doc2md — path handling, file I/O, format detection."""

import re
import sys
from pathlib import Path

from converters.base import ConversionResult


# ── Format detection ─────────────────────────────────────────

# Maps lowercase extensions to format key
EXTENSION_MAP = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",
    ".pptx": "pptx",
    ".ppt": "pptx",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".txt": "txt",
    ".md": "txt",
    ".csv": "txt",
    ".html": "txt",
    ".htm": "txt",
}


def detect_format(file_path: Path) -> str:
    """Return format key based on file extension.

    Returns:
        One of: 'pdf', 'docx', 'pptx', 'xlsx', 'txt'
    Raises:
        ValueError: if the extension is not supported.
    """
    ext = file_path.suffix.lower()
    fmt = EXTENSION_MAP.get(ext)
    if not fmt:
        raise ValueError(f"不支持的文件格式: {ext}")
    return fmt


# ── Filename / path helpers ──────────────────────────────────

def sanitize_filename(name: str, max_len: int = 120) -> str:
    """Remove characters unsafe for filesystem paths.

    Replaces: / \\ : * ? \" < > | with underscores.
    Trims whitespace and limits length.
    """
    name = re.sub(r'[/\\:*?"<>|]', "_", name.strip())
    if len(name) > max_len:
        # Keep extension intact if present
        stem, dot, ext = name.rpartition(".")
        if dot:
            name = stem[: max_len - len(ext) - 1] + "." + ext
        else:
            name = name[:max_len]
    return name or "untitled"


def ensure_output_dir(input_path: Path, output_base: Path | None = None) -> Path:
    """Create {input_name}_md/ with images/ subdirectory.

    Args:
        input_path: Path to the source file.
        output_base: Optional custom output directory. If None, uses
                     input_path.parent / {input_path.stem}_md.

    Returns:
        Path to the created output directory.
    """
    if output_base is None:
        output_dir = input_path.parent / f"{input_path.stem}_md"
    else:
        output_dir = output_base

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "images").mkdir(exist_ok=True)
    return output_dir


# ── Output writing ───────────────────────────────────────────

def write_markdown_and_images(
    result: ConversionResult,
    output_dir: Path,
    md_name: str,
) -> Path:
    """Write .md file and all images to disk.

    Args:
        result: ConversionResult from a converter.
        output_dir: Directory to write into (should already exist).
        md_name: Base name for the markdown file (without .md extension).

    Returns:
        Path to the written .md file.
    """
    # Write images
    for filename, img_bytes in result.images:
        img_path = output_dir / "images" / filename
        img_path.write_bytes(img_bytes)

    # Write markdown
    md_path = output_dir / f"{sanitize_filename(md_name)}.md"
    md_path.write_text(result.markdown, encoding="utf-8")

    return md_path


# ── Human-readable size ──────────────────────────────────────

def format_size(size_bytes: int) -> str:
    """Return human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes} {unit}"
        size_bytes //= 1024
    return f"{size_bytes} TB"


def err_exit(msg: str, code: int = 1) -> None:
    """Print error message and exit."""
    print(f"错误：{msg}", file=sys.stderr)
    sys.exit(code)
