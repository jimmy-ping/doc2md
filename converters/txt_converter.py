"""Plain text converter — encoding detection + passthrough."""

from pathlib import Path

from converters.base import BaseConverter, ConversionResult


class TXTConverter(BaseConverter):
    """Convert plain text files to Markdown.

    Attempts UTF-8 first, then falls back through common Chinese encodings.
    Wraps content in a fenced code block unless it already contains markdown syntax.
    """

    # Encoding detection order
    ENCODINGS = ["utf-8", "gbk", "gb2312", "gb18030", "big5", "latin-1"]

    def convert(self) -> ConversionResult:
        text = self._read_with_encoding()
        metadata = {
            "format": "txt",
            "encoding": self._detected_encoding,
            "line_count": text.count("\n") + 1,
        }

        # If content already looks like markdown, don't wrap
        if self._looks_like_markdown(text):
            md = text
        else:
            md = f"```text\n{text}\n```\n"

        return ConversionResult(markdown=md, metadata=metadata)

    def _read_with_encoding(self) -> str:
        """Read file, trying multiple encodings in order."""
        raw = self.file_path.read_bytes()
        for enc in self.ENCODINGS:
            try:
                text = raw.decode(enc)
                self._detected_encoding = enc
                return text
            except (UnicodeDecodeError, LookupError):
                continue
        # Last resort
        self._detected_encoding = "latin-1"
        return raw.decode("latin-1", errors="replace")

    @staticmethod
    def _looks_like_markdown(text: str) -> bool:
        """Heuristic: does the text already contain markdown syntax?"""
        markers = ["# ", "## ", "```", "---", "> ", "- ", "* ", "1. ", "![", "[", "**"]
        return any(marker in text for marker in markers)
