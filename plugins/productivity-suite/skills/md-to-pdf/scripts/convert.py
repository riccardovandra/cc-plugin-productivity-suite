#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["fpdf2>=2.7.0", "pillow>=10.0.0", "httpx>=0.27.0"]
# ///
"""
Markdown to PDF Converter

Converts markdown files to clean, professional PDFs.

Usage:
    python convert.py input.md output.pdf
    python convert.py input.md output.pdf --title "Custom Title"
    python convert.py input.md output.pdf --style brand
"""

import argparse
import io
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont


class MarkdownPDF(FPDF):
    """Custom PDF class with markdown rendering support."""

    def __init__(self, style: str = "default"):
        super().__init__()
        self.style = style

        # Add Unicode font support using system fonts
        self.add_font('Arial', '', '/System/Library/Fonts/Supplemental/Arial.ttf')
        self.add_font('Arial', 'B', '/System/Library/Fonts/Supplemental/Arial Bold.ttf')
        self.add_font('Arial', 'I', '/System/Library/Fonts/Supplemental/Arial Italic.ttf')
        # Add Unicode monospace font for code blocks (SF Mono supports box-drawing characters)
        self.add_font('SFMono', '', '/System/Library/Fonts/SFNSMono.ttf')
        self.default_font = 'Arial'
        self.mono_font = 'SFMono'

        self.load_style()

        # State tracking
        self.in_table = False
        self.table_data = []
        self.in_code_block = False
        self.code_lines = []

    def load_style(self):
        """Load style configuration."""
        if self.style == "brand":
            # Try to load brand config
            brand_path = Path(__file__).parent.parent.parent.parent.parent / "context/business/brand-style.json"
            if brand_path.exists():
                import json
                with open(brand_path) as f:
                    config = json.load(f)
                self.colors = {
                    "primary": self._hex_to_rgb(config.get("primary_color", "#2c3e50")),
                    "accent": self._hex_to_rgb(config.get("accent_color", "#3498db")),
                    "text": (33, 33, 33),
                    "light_gray": (236, 240, 241),
                    "table_header": self._hex_to_rgb(config.get("primary_color", "#2c3e50")),
                }
            else:
                self.colors = self._default_colors()
        elif self.style == "minimal":
            self.colors = {
                "primary": (0, 0, 0),
                "accent": (100, 100, 100),
                "text": (33, 33, 33),
                "light_gray": (245, 245, 245),
                "table_header": (100, 100, 100),
            }
        else:
            self.colors = self._default_colors()

    def _default_colors(self):
        return {
            "primary": (44, 62, 80),      # Dark blue-gray
            "accent": (52, 152, 219),      # Blue
            "text": (33, 33, 33),          # Near black
            "light_gray": (236, 240, 241), # Light gray for backgrounds
            "table_header": (44, 62, 80),  # Dark header
        }

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def header(self):
        """Page header - minimal."""
        pass

    def footer(self):
        """Page footer with page number."""
        if not getattr(self, 'no_page_numbers', False):
            self.set_y(-15)
            self.set_font(self.default_font, '', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def add_title(self, title: str):
        """Add document title."""
        self.set_font(self.default_font, 'B', 24)
        self.set_text_color(*self.colors["primary"])
        self.multi_cell(0, 12, title)
        self.ln(8)

    def add_h1(self, text: str):
        """Add H1 heading."""
        # Add page break if below 70% of page
        page_height = self.h - self.b_margin - self.t_margin
        threshold = page_height * 0.7
        if self.get_y() > threshold:
            self.add_page()

        self.ln(2)
        self.set_font(self.default_font, 'B', 18)
        self.set_text_color(*self.colors["primary"])
        text = self._process_inline(text)
        self.multi_cell(0, 10, text)
        self.ln(1)

    def add_h2(self, text: str):
        """Add H2 heading."""
        # Add page break if below 70% of page
        page_height = self.h - self.b_margin - self.t_margin
        threshold = page_height * 0.7
        if self.get_y() > threshold:
            self.add_page()

        self.ln(2)
        self.set_font(self.default_font, 'B', 14)
        self.set_text_color(*self.colors["primary"])
        text = self._process_inline(text)
        self.multi_cell(0, 8, text)
        self.ln(1)

    def add_h3(self, text: str):
        """Add H3 heading."""
        # Add page break if below 80% of page
        page_height = self.h - self.b_margin - self.t_margin
        threshold = page_height * 0.8
        if self.get_y() > threshold:
            self.add_page()

        self.ln(1)
        self.set_font(self.default_font, 'B', 12)
        self.set_text_color(*self.colors["accent"])
        text = self._process_inline(text)
        self.multi_cell(0, 7, text)
        self.ln(1)

    def add_h4(self, text: str):
        """Add H4 heading."""
        self.ln(1)
        self.set_font(self.default_font, 'B', 10)
        self.set_text_color(*self.colors["accent"])
        text = self._process_inline(text)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def add_paragraph(self, text: str):
        """Add paragraph text with inline formatting."""
        self.set_x(self.l_margin)  # Reset X position
        self.set_font(self.default_font, '', 10)
        self.set_text_color(*self.colors["text"])

        # Process inline formatting
        text = self._process_inline(text)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def add_blockquote(self, text: str):
        """Add blockquote with distinctive styling."""
        self.set_x(self.l_margin)
        self.set_font(self.default_font, 'I', 10)
        self.set_text_color(100, 100, 100)

        # Draw left border
        self.set_fill_color(200, 200, 200)
        self.cell(3, 6, '', 0, 0, 'L', True)

        # Quote text with right padding
        text = self._process_inline(text)
        self.multi_cell(0, 6, text)
        self.ln(1)

        # Reset styling
        self.set_font(self.default_font, '', 10)
        self.set_text_color(*self.colors["text"])

    def _process_inline(self, text: str) -> str:
        """Process inline markdown (bold, italic, code, links)."""
        # Remove markdown links: [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Bold **text** or __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        # Italic *text* or _text_
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        # Inline code `text`
        text = re.sub(r'`(.+?)`', r'\1', text)
        # Remove escaped backslashes: 3\. -> 3.
        text = re.sub(r'\\', '', text)
        return text

    def add_bullet(self, text: str, level: int = 0):
        """Add bullet point."""
        self.set_font(self.default_font, '', 10)
        self.set_text_color(*self.colors["text"])

        indent = 10 + (level * 8)
        bullet = "•" if level == 0 else "◦"

        text = self._process_inline(text)

        self.set_x(indent)
        self.cell(6, 6, bullet)
        self.multi_cell(0, 6, text)

    def add_numbered(self, text: str, number: int, level: int = 0):
        """Add numbered list item."""
        self.set_font(self.default_font, '', 10)
        self.set_text_color(*self.colors["text"])

        indent = 10 + (level * 8)
        text = self._process_inline(text)

        self.set_x(indent)
        self.cell(8, 6, f"{number}.")
        self.multi_cell(0, 6, text)

    def add_table(self, rows: list):
        """Add table with header row."""
        if not rows:
            return

        self.ln(2)

        # Calculate column widths
        num_cols = len(rows[0])
        page_width = self.w - 2 * self.l_margin
        col_width = page_width / num_cols

        # Header row
        self.set_font(self.default_font, 'B', 9)
        self.set_fill_color(*self.colors["table_header"])
        self.set_text_color(255, 255, 255)

        for cell in rows[0]:
            cell_text = self._process_inline(str(cell).strip())
            self.cell(col_width, 8, cell_text, 1, 0, 'L', True)
        self.ln()

        # Data rows
        self.set_font(self.default_font, '', 9)
        self.set_text_color(*self.colors["text"])
        fill = False

        for row in rows[1:]:
            if fill:
                self.set_fill_color(*self.colors["light_gray"])
            else:
                self.set_fill_color(255, 255, 255)

            for cell in row:
                cell_text = self._process_inline(str(cell).strip())
                self.cell(col_width, 7, cell_text, 1, 0, 'L', True)
            self.ln()
            fill = not fill

        self.ln(2)
        self.set_x(self.l_margin)  # Reset X position

    def add_code_block(self, lines: list):
        """Add code block as image for perfect ASCII art alignment."""
        self.ln(1)

        # Render ASCII to image
        code_text = '\n'.join(lines)
        img_path = self._render_ascii_to_image(code_text)

        if img_path:
            # Calculate available space
            page_height = self.h - self.b_margin - self.t_margin
            available_height = self.h - self.b_margin - self.get_y()

            # Get image dimensions and calculate PDF width
            with Image.open(img_path) as img:
                img_w, img_h = img.size

            # Scale to fit page width (with margins)
            max_width = self.w - 2 * self.l_margin
            scale = max_width / img_w
            pdf_width = max_width
            pdf_height = img_h * scale

            # If too tall for page, scale down further
            if pdf_height > page_height * 0.8:
                scale = (page_height * 0.8) / img_h
                pdf_height = page_height * 0.8
                pdf_width = img_w * scale

            # If doesn't fit on current page, start new page
            if pdf_height > available_height:
                self.add_page()

            # Center the image if it's narrower than page
            x_offset = self.l_margin + (max_width - pdf_width) / 2

            self.image(img_path, x=x_offset, w=pdf_width, h=pdf_height)
            self.ln(2)  # Small spacing after code block

            # Clean up temp file
            Path(img_path).unlink(missing_ok=True)
        else:
            # Fallback to text rendering if image fails
            self.set_font(self.mono_font, '', 8)
            self.set_fill_color(245, 245, 245)
            self.set_text_color(60, 60, 60)
            self.multi_cell(0, 3.5, code_text, 0, 'L')
            self.ln(4)

        self.set_x(self.l_margin)
        self.set_font(self.default_font, '', 10)

    def add_mermaid_diagram(self, mermaid_code: str):
        """Render mermaid diagram to image and add to PDF.

        Uses Kroki API for rendering with retries.
        Falls back to code block if rendering fails.
        """
        img_path = None
        max_retries = 3

        # Try Kroki API with retries
        for attempt in range(max_retries):
            try:
                import httpx
                import time

                # Kroki API: POST mermaid code, get PNG back
                response = httpx.post(
                    'https://kroki.io/mermaid/png',
                    content=mermaid_code.encode('utf-8'),
                    headers={'Content-Type': 'text/plain'},
                    timeout=30.0
                )

                if response.status_code == 200 and len(response.content) > 100:
                    temp_png = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                    temp_png.write(response.content)
                    temp_png.close()
                    img_path = temp_png.name
                    break
                elif attempt < max_retries - 1:
                    time.sleep(1)  # Wait before retry

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait before retry

        # If we have an image, add it to PDF
        if img_path:
            try:
                page_height = self.h - self.b_margin - self.t_margin
                available_height = self.h - self.b_margin - self.get_y()

                with Image.open(img_path) as img:
                    img_w, img_h = img.size

                max_width = self.w - 2 * self.l_margin
                scale = max_width / img_w if img_w > max_width else 1
                pdf_width = img_w * scale
                pdf_height = img_h * scale

                if pdf_height > page_height * 0.8:
                    scale = (page_height * 0.8) / img_h
                    pdf_height = page_height * 0.8
                    pdf_width = img_w * scale

                if pdf_height > available_height:
                    self.add_page()

                x_offset = self.l_margin + (max_width - pdf_width) / 2
                self.image(img_path, x=x_offset, w=pdf_width, h=pdf_height)
                self.ln(2)  # Small spacing after mermaid diagram

                # Clean up PNG
                Path(img_path).unlink(missing_ok=True)

                self.set_x(self.l_margin)
                return
            except Exception as e:
                Path(img_path).unlink(missing_ok=True)

        # Fallback to code block rendering
        self.add_code_block(mermaid_code.split('\n'))

    def _render_ascii_to_image(self, text: str) -> str | None:
        """Render ASCII text to an image file, return path."""
        try:
            # Try to use SF Mono or fall back to a monospace font
            font_size = 12
            try:
                font = ImageFont.truetype('/System/Library/Fonts/SFNSMono.ttf', font_size)
            except:
                try:
                    font = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', font_size)
                except:
                    font = ImageFont.load_default()

            lines = text.split('\n')

            # Calculate image size
            # Use getbbox for accurate text measurement
            test_char = 'M'
            bbox = font.getbbox(test_char)
            char_width = bbox[2] - bbox[0]
            char_height = bbox[3] - bbox[1] + 2  # Minimal line spacing

            max_line_len = max(len(line) for line in lines) if lines else 1
            img_width = int(char_width * max_line_len) + 8  # Reduced padding
            img_height = int(char_height * len(lines)) + 8  # Reduced padding

            # Create image with light gray background
            img = Image.new('RGB', (img_width, img_height), color=(245, 245, 245))
            draw = ImageDraw.Draw(img)

            # Draw each line with minimal padding
            y = 4
            for line in lines:
                draw.text((4, y), line, font=font, fill=(60, 60, 60))
                y += char_height

            # Save to temp file
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            img.save(temp_file.name, 'PNG')
            return temp_file.name

        except Exception as e:
            print(f"Warning: Could not render ASCII to image: {e}", file=sys.stderr)
            return None

    def add_hr(self):
        """Add horizontal rule."""
        self.ln(2)
        y = self.get_y()
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(2)


def parse_markdown(content: str, skip_sections: list = None) -> list:
    """Parse markdown into structured elements."""
    lines = content.split('\n')
    elements = []

    i = 0
    in_code_block = False
    code_lines = []
    code_type = None  # 'code' or 'mermaid'
    in_table = False
    table_rows = []
    list_number = 0
    skip_content = False  # Flag to skip content in certain sections

    if skip_sections is None:
        skip_sections = []

    while i < len(lines):
        line = lines[i]

        # Check if we should skip this section (Timeline section)
        for skip_header in skip_sections:
            if line.startswith(skip_header):
                skip_content = True
                break

        # Check if we're done skipping (at next header)
        if skip_content and line.startswith('#'):
            skip_content = False

        if skip_content:
            i += 1
            continue

        # Code blocks (including mermaid)
        if line.strip().startswith('```'):
            if in_code_block:
                if code_type == 'mermaid':
                    elements.append(('mermaid', '\n'.join(code_lines)))
                else:
                    elements.append(('code', code_lines))
                code_lines = []
                in_code_block = False
                code_type = None
            else:
                in_code_block = True
                # Check if mermaid diagram
                if 'mermaid' in line.lower():
                    code_type = 'mermaid'
                else:
                    code_type = 'code'
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Tables
        if '|' in line and line.strip().startswith('|'):
            # Check if separator row (|---|---|)
            if re.match(r'\|[\s\-:]+\|', line):
                i += 1
                continue

            # Parse table row
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if cells:
                if not in_table:
                    in_table = True
                    table_rows = []
                table_rows.append(cells)
            i += 1
            continue
        elif in_table:
            elements.append(('table', table_rows))
            table_rows = []
            in_table = False

        # Headers
        if line.startswith('# '):
            elements.append(('h1', line[2:].strip()))
            list_number = 0
        elif line.startswith('## '):
            elements.append(('h2', line[3:].strip()))
            list_number = 0
        elif line.startswith('### '):
            elements.append(('h3', line[4:].strip()))
            list_number = 0
        elif line.startswith('#### '):
            elements.append(('h4', line[5:].strip()))
            list_number = 0

        # Horizontal rule
        elif line.strip() in ['---', '***', '___']:
            elements.append(('hr', None))

        # Bullet lists
        elif re.match(r'^(\s*)[-*]\s+', line):
            match = re.match(r'^(\s*)[-*]\s+(.+)', line)
            if match:
                indent = len(match.group(1))
                level = indent // 2
                elements.append(('bullet', match.group(2), level))
                list_number = 0

        # Numbered lists
        elif re.match(r'^(\s*)\d+\.\s+', line):
            match = re.match(r'^(\s*)\d+\.\s+(.+)', line)
            if match:
                indent = len(match.group(1))
                level = indent // 2
                # Extract original number from markdown
                number_match = re.match(r'^(\s*)\d+\.', line)
                original_number = int(number_match.group(0).strip().split('.')[0]) if number_match else list_number + 1
                list_number = original_number
                elements.append(('numbered', match.group(2), list_number, level))

        # Blockquotes
        elif line.strip().startswith('>'):
            quote_text = line.strip()[1:].strip()
            elements.append(('blockquote', quote_text))
            list_number = 0

        # Paragraphs
        elif line.strip():
            elements.append(('paragraph', line.strip()))
            list_number = 0

        # Empty line
        else:
            list_number = 0

        i += 1

    # Handle remaining table
    if in_table and table_rows:
        elements.append(('table', table_rows))

    return elements


def convert_md_to_pdf(
    input_path: str,
    output_path: str,
    title: str = None,
    style: str = "default",
    no_page_numbers: bool = False,
    skip_sections: list = None
):
    """Convert markdown file to PDF."""

    # Read markdown
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    content = input_file.read_text(encoding='utf-8')

    # Parse markdown with section skipping
    if skip_sections is None:
        skip_sections = ['## 3. Timeline & Deliverables']

    elements = parse_markdown(content, skip_sections)

    # Create PDF
    pdf = MarkdownPDF(style=style)
    pdf.no_page_numbers = no_page_numbers
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Add title if provided, or use first H1
    title_added = False
    if title:
        pdf.add_title(title)
        title_added = True

    # Render elements
    for element in elements:
        etype = element[0]

        if etype == 'h1':
            if not title_added:
                pdf.add_title(element[1])
                title_added = True
            else:
                pdf.add_h1(element[1])
        elif etype == 'h2':
            pdf.add_h2(element[1])
        elif etype == 'h3':
            pdf.add_h3(element[1])
        elif etype == 'h4':
            pdf.add_h4(element[1])
        elif etype == 'paragraph':
            pdf.add_paragraph(element[1])
        elif etype == 'blockquote':
            pdf.add_blockquote(element[1])
        elif etype == 'bullet':
            pdf.add_bullet(element[1], element[2] if len(element) > 2 else 0)
        elif etype == 'numbered':
            pdf.add_numbered(element[1], element[2], element[3] if len(element) > 3 else 0)
        elif etype == 'table':
            pdf.add_table(element[1])
        elif etype == 'code':
            pdf.add_code_block(element[1])
        elif etype == 'mermaid':
            pdf.add_mermaid_diagram(element[1])
        elif etype == 'hr':
            pdf.add_hr()

    # Save PDF
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_file))

    print(f"PDF created: {output_file}")
    return str(output_file)


def main():
    parser = argparse.ArgumentParser(
        description="Convert Markdown to PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python convert.py document.md output.pdf
  python convert.py document.md output.pdf --title "My Report"
  python convert.py document.md output.pdf --style brand
"""
    )

    parser.add_argument('input', help='Input markdown file')
    parser.add_argument('output', help='Output PDF file')
    parser.add_argument('--title', '-t', help='Document title (overrides H1)')
    parser.add_argument('--style', '-s', choices=['default', 'brand', 'minimal'],
                        default='default', help='Style preset')
    parser.add_argument('--no-page-numbers', action='store_true',
                        help='Disable page numbers')

    args = parser.parse_args()

    convert_md_to_pdf(
        input_path=args.input,
        output_path=args.output,
        title=args.title,
        style=args.style,
        no_page_numbers=args.no_page_numbers
    )


if __name__ == '__main__':
    main()
