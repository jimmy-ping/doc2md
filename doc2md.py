#!/usr/bin/env python3
"""文档转 Markdown — 支持 PDF/Word/PPT/Excel/TXT，自动提取图片。

用法:
    python3 doc2md.py convert input.pdf              # 转换单个文件
    python3 doc2md.py convert input.docx -o out/     # 指定输出目录
    python3 doc2md.py batch a.pdf b.docx c.pptx      # 批量转换
    python3 doc2md.py gui                            # 启动图形界面

依赖: PyMuPDF, python-docx, python-pptx, openpyxl, Pillow, Pandoc (可选)
"""

import argparse
import sys
from pathlib import Path

# Ensure project root on path for converter imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from converters.pdf_converter import PDFConverter
from converters.docx_converter import DOCXConverter
from converters.pptx_converter import PPTXConverter
from converters.xlsx_converter import XLSXConverter
from converters.txt_converter import TXTConverter
from converters.pandoc_fallback import PandocFallback
from utils import detect_format, ensure_output_dir, write_markdown_and_images, format_size, err_exit

# ── Converter registry ──────────────────────────────────────

CONVERTERS = {
    "pdf": PDFConverter,
    "docx": DOCXConverter,
    "pptx": PPTXConverter,
    "xlsx": XLSXConverter,
    "txt": TXTConverter,
}


# ── Shared conversion logic ─────────────────────────────────

def convert_file(
    file_path: Path,
    output_dir: Path | None = None,
    use_pandoc: bool = False,
) -> Path:
    """Convert one file to Markdown. Shared by CLI and GUI.

    Args:
        file_path: Path to the input file.
        output_dir: Custom output directory. None = auto-generate.
        use_pandoc: If True, use Pandoc for docx/pptx instead of native parsers.

    Returns:
        Path to the generated .md file.

    Raises:
        FileNotFoundError: if file_path does not exist.
        ValueError: if the format is unsupported.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    try:
        fmt = detect_format(file_path)
    except ValueError:
        raise ValueError(f"不支持的文件格式: {file_path.suffix}")

    # For docx/pptx, pandoc fallback is available
    if use_pandoc and fmt in ("docx", "pptx"):
        converter = PandocFallback(file_path)
    else:
        converter_cls = CONVERTERS.get(fmt)
        if converter_cls is None:
            raise ValueError(f"不支持的文件格式: .{fmt}")
        converter = converter_cls(file_path)

    result = converter.convert()

    out_dir = ensure_output_dir(file_path, output_dir)
    md_path = write_markdown_and_images(result, out_dir, file_path.stem)

    print(f"✓ 转换完成: {md_path}")
    if result.images:
        print(f"  提取图片: {len(result.images)} 张")
    if result.metadata:
        for key, val in result.metadata.items():
            if val and key not in ("format",):
                print(f"  {key}: {val}")

    return md_path


# ── CLI batch expansion ─────────────────────────────────────

def expand_inputs(paths: list[str]) -> list[Path]:
    """Expand directories and glob patterns into a flat file list."""
    supported = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".txt"}
    result = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            for f in sorted(pp.rglob("*")):
                if f.is_file() and f.suffix.lower() in supported:
                    result.append(f)
        elif pp.is_file():
            result.append(pp)
        else:
            print(f"警告：跳过不存在的路径 — {p}")
    return result


# ── CLI entry ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="文档转 Markdown — 支持 PDF/Word/PPT/Excel/TXT，自动提取图片"
    )
    sub = parser.add_subparsers(dest="command")

    # gui
    sub.add_parser("gui", help="启动图形界面")

    # convert
    cmd = sub.add_parser("convert", help="转换单个文件")
    cmd.add_argument("input", help="输入文件路径")
    cmd.add_argument("-o", "--output", help="输出目录 (默认: {文件名}_md/)")
    cmd.add_argument("--pandoc", action="store_true", help="对 DOCX/PPTX 使用 Pandoc 转换")

    # batch
    batch = sub.add_parser("batch", help="批量转换多个文件或目录")
    batch.add_argument("inputs", nargs="+", help="输入文件或目录")
    batch.add_argument("-o", "--output-dir", help="输出基目录 (每个文件生成独立子目录)")
    batch.add_argument("--pandoc", action="store_true", help="对 DOCX/PPTX 使用 Pandoc 转换")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        print("\n示例:")
        print("  python3 doc2md.py convert report.pdf")
        print("  python3 doc2md.py batch docs/ -o output/")
        print("  python3 doc2md.py gui")
        return

    if args.command == "gui":
        run_gui()
        return

    if args.command == "convert":
        try:
            output = Path(args.output) if args.output else None
            convert_file(Path(args.input), output, use_pandoc=args.pandoc)
        except (FileNotFoundError, ValueError) as e:
            err_exit(str(e))

    elif args.command == "batch":
        files = expand_inputs(args.inputs)
        if not files:
            err_exit("没有找到支持的文件")
        print(f"找到 {len(files)} 个文件\n")
        success = 0
        for i, f in enumerate(files, 1):
            print(f"[{i}/{len(files)}] {f.name}")
            try:
                base = Path(args.output_dir) if args.output_dir else None
                convert_file(f, base, use_pandoc=args.pandoc)
                success += 1
            except Exception as e:
                print(f"  ✗ 失败: {e}")
            print()
        print(f"完成: {success}/{len(files)} 成功")


# ── GUI ─────────────────────────────────────────────────────

def run_gui():
    """Launch tkinter GUI for file selection and conversion."""
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    import threading
    import queue

    root = tk.Tk()
    root.title("文档转 Markdown 工具")
    root.geometry("700x580")
    root.minsize(550, 450)

    # State
    files: list[str] = []
    output_dir = tk.StringVar(value=str(Path.home() / "Desktop"))
    extract_images = tk.BooleanVar(value=True)
    use_pandoc = tk.BooleanVar(value=False)
    msg_queue = queue.Queue()
    converting = False

    # ── Styles ──────────────────────────────────────────
    BG = "#f5f5f5"
    BLUE = "#2563eb"
    root.configure(bg=BG)

    def make_blue_btn(parent, text, command):
        """macOS tkinter button workaround — Frame + Label with hover."""
        frame = tk.Frame(parent, bg=BG)
        inner = tk.Frame(frame, bg=BLUE, cursor="hand2")
        label = tk.Label(inner, text=text, bg=BLUE, fg="white",
                         font=("PingFang SC", 11), padx=16, pady=4)
        label.pack()

        def on_enter(e):
            inner.configure(bg="#1d4ed8")
            label.configure(bg="#1d4ed8")
        def on_leave(e):
            inner.configure(bg=BLUE)
            label.configure(bg=BLUE)
        def on_click(e):
            command()

        for w in (frame, inner, label):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)
        inner.pack()
        return frame

    # ── File list section ────────────────────────────────
    file_frame = tk.LabelFrame(root, text="文件列表", bg=BG,
                                font=("PingFang SC", 11, "bold"), padx=8, pady=4)
    file_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 4))

    listbox = tk.Listbox(file_frame, selectmode=tk.EXTENDED, font=("Menlo", 10),
                         relief=tk.FLAT, bg="white", selectbackground=BLUE)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(file_frame, command=listbox.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.configure(yscrollcommand=scrollbar.set)

    btn_bar = tk.Frame(root, bg=BG)
    btn_bar.pack(fill=tk.X, padx=12, pady=2)

    def add_files():
        paths = filedialog.askopenfilenames(
            title="选择文档",
            filetypes=[
                ("所有支持的格式", "*.pdf *.docx *.pptx *.xlsx *.txt"),
                ("PDF 文件", "*.pdf"),
                ("Word 文档", "*.docx"),
                ("PowerPoint", "*.pptx"),
                ("Excel 表格", "*.xlsx"),
                ("文本文件", "*.txt"),
            ],
        )
        for p in paths:
            if p not in files:
                files.append(p)
                listbox.insert(tk.END, p)

    def remove_selected():
        selected = listbox.curselection()
        for i in reversed(selected):
            listbox.delete(i)
            del files[i]

    def clear_files():
        listbox.delete(0, tk.END)
        files.clear()

    make_blue_btn(btn_bar, "＋ 添加文件", add_files).pack(side=tk.LEFT, padx=2)
    make_blue_btn(btn_bar, "✕ 移除选中", remove_selected).pack(side=tk.LEFT, padx=2)
    make_blue_btn(btn_bar, "清空列表", clear_files).pack(side=tk.LEFT, padx=2)

    count_label = tk.Label(btn_bar, text="已选 0 个", bg=BG, fg="#666",
                           font=("PingFang SC", 10))
    count_label.pack(side=tk.RIGHT, padx=8)

    def update_count():
        count_label.configure(text=f"已选 {len(files)} 个")

    # ── Options section ──────────────────────────────────
    opt_frame = tk.LabelFrame(root, text="转换选项", bg=BG,
                               font=("PingFang SC", 11, "bold"), padx=8, pady=4)
    opt_frame.pack(fill=tk.X, padx=12, pady=4)

    out_row = tk.Frame(opt_frame, bg=BG)
    out_row.pack(fill=tk.X, pady=2)
    tk.Label(out_row, text="输出目录:", bg=BG, font=("PingFang SC", 10)).pack(side=tk.LEFT)
    out_entry = tk.Entry(out_row, textvariable=output_dir, font=("Menlo", 10), width=40)
    out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
    make_blue_btn(out_row, "浏览...",
                  lambda: output_dir.set(filedialog.askdirectory() or output_dir.get())
                  ).pack(side=tk.RIGHT)

    chk_row = tk.Frame(opt_frame, bg=BG)
    chk_row.pack(fill=tk.X, pady=2)
    tk.Checkbutton(chk_row, text="提取图片", variable=extract_images,
                   bg=BG, font=("PingFang SC", 10)).pack(side=tk.LEFT)
    tk.Checkbutton(chk_row, text="对 DOCX/PPTX 使用 Pandoc", variable=use_pandoc,
                   bg=BG, font=("PingFang SC", 10)).pack(side=tk.LEFT, padx=16)

    # ── Progress section ─────────────────────────────────
    prog_frame = tk.Frame(root, bg=BG)
    prog_frame.pack(fill=tk.X, padx=12, pady=4)

    progress = ttk.Progressbar(prog_frame, mode="determinate")
    progress.pack(fill=tk.X)

    status_label = tk.Label(prog_frame, text="就绪", bg=BG, fg="#666",
                            font=("PingFang SC", 10))
    status_label.pack(anchor=tk.W, pady=(2, 0))

    # ── Action button ────────────────────────────────────
    action_frame = tk.Frame(root, bg=BG)
    action_frame.pack(pady=(8, 12))

    def start_conversion():
        nonlocal converting
        if converting:
            return
        if not files:
            messagebox.showwarning("提示", "请先添加文件")
            return

        converting = True
        progress["maximum"] = len(files)
        progress["value"] = 0
        status_label.configure(text="开始转换...")

        def worker():
            out = Path(output_dir.get())
            for i, fp in enumerate(files):
                try:
                    msg_queue.put(("status", f"正在转换 ({i + 1}/{len(files)}): {Path(fp).name}"))
                    convert_file(Path(fp), out, use_pandoc=use_pandoc.get())
                    msg_queue.put(("progress", i + 1))
                except Exception as e:
                    msg_queue.put(("error", f"{Path(fp).name}: {e}"))
            msg_queue.put(("done", f"完成 — {len(files)} 个文件"))

        threading.Thread(target=worker, daemon=True).start()
        poll_queue()

    def poll_queue():
        try:
            while True:
                msg = msg_queue.get_nowait()
                kind, data = msg
                if kind == "status":
                    status_label.configure(text=data)
                elif kind == "progress":
                    progress["value"] = data
                elif kind == "error":
                    status_label.configure(text=f"✗ {data}")
                elif kind == "done":
                    progress["value"] = progress["maximum"]
                    status_label.configure(text=data)
                    nonlocal converting
                    converting = False
                    messagebox.showinfo("完成", data)
        except queue.Empty:
            pass
        if converting:
            root.after(100, poll_queue)

    make_blue_btn(action_frame, "🔄 开始转换", start_conversion)

    # ── Keyboard shortcuts ───────────────────────────────
    root.bind("<Command-o>", lambda e: add_files())
    root.bind("<Command-a>", lambda e: listbox.select_set(0, tk.END))
    root.bind("<BackSpace>", lambda e: remove_selected())

    # Override listbox operations to update count
    _orig_add = add_files
    def add_files_wrapped():
        _orig_add()
        update_count()
    add_files = add_files_wrapped  # type: ignore

    _orig_remove = remove_selected
    def remove_selected_wrapped():
        _orig_remove()
        update_count()
    remove_selected = remove_selected_wrapped  # type: ignore

    _orig_clear = clear_files
    def clear_files_wrapped():
        _orig_clear()
        update_count()
    clear_files = clear_files_wrapped  # type: ignore

    root.mainloop()


if __name__ == "__main__":
    main()
