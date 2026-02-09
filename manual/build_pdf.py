"""
Build a single PDF from all manual chapters + screenshots.
Run with: python build_pdf.py
"""
import re
from pathlib import Path
from fpdf import FPDF

MANUAL_DIR = Path(__file__).parent.resolve()
OUTPUT = MANUAL_DIR / "LocalSoundsAPI_Manual.pdf"
L_MARGIN = 10
R_MARGIN = 10
PAGE_W = 210
CONTENT_W = PAGE_W - L_MARGIN - R_MARGIN  # 190mm

CHAPTERS = [
    "00-cover.md",
    "01-introduction.md",
    "02-installation.md",
    "03-getting-started.md",
    "04-upload-and-transcribe.md",
    "05-xtts-voice-cloning.md",
    "06-fish-speech.md",
    "07-kokoro-tts.md",
    "08-stable-audio.md",
    "09-ace-step-music.md",
    "10-video-production.md",
    "11-chatbot.md",
    "12-settings-and-presets.md",
    "13-cheat-sheet.md",
    "14-api-reference.md",
    "15-troubleshooting.md",
    "16-faq.md",
    "17-launcher.md",
]

# Images taller than this aspect ratio threshold are skipped (too tall to read)
MIN_ASPECT_RATIO = 0.4


class ManualPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=20)
        self.chapter_title = ""

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 8, "LocalSoundsAPI Manual", align="L")
            self.cell(0, 8, self.chapter_title, align="R",
                      new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(200, 200, 200)
            self.line(L_MARGIN, self.get_y(), PAGE_W - R_MARGIN, self.get_y())
            self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def reset_cursor(self):
        """Reset X to left margin -- call after every block element."""
        self.set_x(L_MARGIN)


def get_image_size(img_path):
    """Get image dimensions in pixels."""
    try:
        from PIL import Image
        with Image.open(img_path) as im:
            return im.size
    except ImportError:
        pass
    # Fallback: read PNG header
    try:
        with open(img_path, "rb") as f:
            data = f.read(32)
            if data[:8] == b'\x89PNG\r\n\x1a\n':
                w = int.from_bytes(data[16:20], "big")
                h = int.from_bytes(data[20:24], "big")
                return (w, h)
    except Exception:
        pass
    return (1600, 900)


def parse_table(lines):
    rows = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if cells and all(re.match(r'^[-:]+$', c) for c in cells):
            continue
        if cells:
            rows.append(cells)
    return rows


def clean_inline(text):
    """Strip markdown inline formatting to plain text."""
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace("\u2192", "->").replace("\u2014", " -- ").replace("\u2013", "-")
    return text.strip()


def place_image(pdf, img_path, max_w=170, max_h=130):
    """Place an image centered, respecting max dimensions. Returns True if placed."""
    w_px, h_px = get_image_size(img_path)
    aspect = w_px / h_px

    # Skip extremely tall/narrow images (unreadable when scaled)
    if aspect < MIN_ASPECT_RATIO:
        return False

    img_w = min(max_w, CONTENT_W)
    img_h = img_w / aspect
    if img_h > max_h:
        img_h = max_h
        img_w = img_h * aspect

    # Need a new page?
    space_left = 277 - pdf.get_y()
    if img_h + 15 > space_left:
        pdf.add_page()

    x = (PAGE_W - img_w) / 2
    y_before = pdf.get_y()
    pdf.image(str(img_path), x=x, y=y_before, w=img_w)
    # Manually advance Y past the image and reset X
    pdf.set_y(y_before + img_h + 3)
    pdf.reset_cursor()
    return True


def render_chapter(pdf, md_path):
    text = md_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # --- Images ---
        img_match = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)', stripped)
        if img_match:
            img_file = img_match.group(2).replace("%20", " ")
            img_path = MANUAL_DIR / img_file
            if img_path.exists():
                place_image(pdf, img_path)
            i += 1
            continue

        # --- Italic caption (below images) ---
        if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            caption = stripped.strip("*").strip()
            caption = clean_inline(caption)
            pdf.reset_cursor()
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(CONTENT_W, 4, caption, align="C")
            pdf.ln(4)
            pdf.set_text_color(0, 0, 0)
            pdf.reset_cursor()
            i += 1
            continue

        # --- H1 ---
        if stripped.startswith("# ") and not stripped.startswith("##"):
            title = stripped[2:].strip()
            pdf.chapter_title = title
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 22)
            pdf.set_text_color(30, 60, 120)
            pdf.multi_cell(CONTENT_W, 12, title, align="C")
            pdf.ln(8)
            pdf.set_text_color(0, 0, 0)
            pdf.reset_cursor()
            i += 1
            continue

        # --- H2 ---
        if stripped.startswith("## ") and not stripped.startswith("###"):
            heading = stripped[3:].strip()
            if pdf.get_y() > 245:
                pdf.add_page()
            pdf.ln(4)
            pdf.reset_cursor()
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(40, 80, 140)
            pdf.multi_cell(CONTENT_W, 8, heading)
            pdf.set_draw_color(40, 80, 140)
            pdf.line(L_MARGIN, pdf.get_y(), 100, pdf.get_y())
            pdf.ln(3)
            pdf.set_text_color(0, 0, 0)
            pdf.reset_cursor()
            i += 1
            continue

        # --- H3 ---
        if stripped.startswith("### "):
            heading = stripped[4:].strip()
            if pdf.get_y() > 255:
                pdf.add_page()
            pdf.ln(2)
            pdf.reset_cursor()
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(CONTENT_W, 7, heading)
            pdf.ln(2)
            pdf.set_text_color(0, 0, 0)
            pdf.reset_cursor()
            i += 1
            continue

        # --- H4 ---
        if stripped.startswith("#### "):
            heading = stripped[5:].strip()
            pdf.reset_cursor()
            pdf.set_font("Helvetica", "BI", 10)
            pdf.multi_cell(CONTENT_W, 6, heading)
            pdf.ln(1)
            pdf.reset_cursor()
            i += 1
            continue

        # --- Horizontal rule ---
        if stripped == "---":
            pdf.ln(3)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(L_MARGIN, pdf.get_y(), PAGE_W - R_MARGIN, pdf.get_y())
            pdf.ln(5)
            pdf.reset_cursor()
            i += 1
            continue

        # --- Code block ---
        if stripped.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```

            if any(cl.strip() for cl in code_lines):
                if pdf.get_y() > 250:
                    pdf.add_page()
                pdf.set_font("Courier", "", 7.5)
                pdf.set_fill_color(240, 240, 240)
                pdf.set_text_color(40, 40, 40)
                for cl in code_lines:
                    if pdf.get_y() > 272:
                        pdf.add_page()
                        pdf.set_font("Courier", "", 7.5)
                        pdf.set_fill_color(240, 240, 240)
                        pdf.set_text_color(40, 40, 40)
                    pdf.set_x(12)
                    pdf.cell(186, 4, cl.rstrip(), fill=True,
                             new_x="LMARGIN", new_y="NEXT")
                pdf.ln(3)
                pdf.set_text_color(0, 0, 0)
                pdf.reset_cursor()
            continue

        # --- Table ---
        if stripped.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1

            rows = parse_table(table_lines)
            if not rows:
                continue

            num_cols = max(len(r) for r in rows)
            col_w = CONTENT_W / num_cols

            if pdf.get_y() > 250:
                pdf.add_page()

            pdf.reset_cursor()
            for ri, row in enumerate(rows):
                if pdf.get_y() > 272:
                    pdf.add_page()

                # Pad row to num_cols
                while len(row) < num_cols:
                    row.append("")

                if ri == 0:
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_fill_color(230, 235, 245)
                else:
                    pdf.set_font("Helvetica", "", 8)
                    pdf.set_fill_color(255, 255, 255)

                cell_texts = [clean_inline(c) for c in row]

                # Estimate row height
                max_lines = 1
                for ct in cell_texts:
                    est_chars = max(1, int(col_w * 0.42))
                    nl = max(1, (len(ct) // est_chars) + 1)
                    max_lines = max(max_lines, nl)
                row_h = max(5.5, max_lines * 4.5)

                x0 = L_MARGIN
                y0 = pdf.get_y()
                for ci, ct in enumerate(cell_texts):
                    pdf.set_xy(x0 + ci * col_w, y0)
                    pdf.set_draw_color(200, 200, 200)
                    pdf.rect(x0 + ci * col_w, y0, col_w, row_h)
                    pdf.set_xy(x0 + ci * col_w + 1, y0 + 0.5)
                    pdf.multi_cell(col_w - 2, 4.5, ct, align="L")
                pdf.set_y(y0 + row_h)
                pdf.reset_cursor()
            pdf.ln(4)
            pdf.reset_cursor()
            continue

        # --- Bullet / list ---
        if re.match(r'^[-*]\s', stripped) or re.match(r'^\d+\.\s', stripped):
            indent = len(line) - len(line.lstrip())
            bullet_x = L_MARGIN + 2 + (indent * 2)
            content = re.sub(r'^[-*]\s+', '', stripped)
            content = re.sub(r'^\d+\.\s+', '', content)
            content = clean_inline(content)
            is_numbered = bool(re.match(r'^\d+\.\s', stripped))
            bullet_char = stripped.split(".")[0] + "." if is_numbered else "-"

            if pdf.get_y() > 272:
                pdf.add_page()

            pdf.set_font("Helvetica", "", 9)
            pdf.set_x(bullet_x)
            pdf.cell(5, 5, bullet_char)
            text_w = CONTENT_W - (bullet_x - L_MARGIN) - 5
            pdf.multi_cell(text_w, 5, content)
            pdf.reset_cursor()
            i += 1
            continue

        # --- Blockquote (skip) ---
        if stripped.startswith(">"):
            while i < len(lines) and lines[i].strip().startswith(">"):
                i += 1
            continue

        # --- Regular paragraph ---
        para = clean_inline(stripped)
        if para:
            pdf.reset_cursor()
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(CONTENT_W, 5.5, para)
            pdf.ln(2)
            pdf.set_text_color(0, 0, 0)
            pdf.reset_cursor()
        i += 1


def build_cover(pdf):
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 32)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 15, "LocalSoundsAPI", align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "User Manual", align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 8, "The ultimate portable, offline all-in-one audio studio",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8,
             "Text-to-Speech  |  Music Generation  |  Transcription  |  Video  |  Chatbot",
             align="C", new_x="LMARGIN", new_y="NEXT")

    hero = MANUAL_DIR / "01-introduction-uncollapsed.png"
    if hero.exists():
        pdf.ln(12)
        place_image(pdf, hero, max_w=160, max_h=140)

    pdf.set_text_color(0, 0, 0)


def main():
    pdf = ManualPDF()
    pdf.set_title("LocalSoundsAPI User Manual")
    pdf.set_author("LocalSoundsAPI")

    build_cover(pdf)

    for ch_file in CHAPTERS:
        if ch_file == "00-cover.md":
            continue
        ch_path = MANUAL_DIR / ch_file
        if ch_path.exists():
            print(f"  Rendering {ch_file}...")
            render_chapter(pdf, ch_path)
        else:
            print(f"  Skipping {ch_file} (not found)")

    pdf.output(str(OUTPUT))
    size_mb = OUTPUT.stat().st_size / (1024 * 1024)
    print(f"\nDone! {OUTPUT.name} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
