# pip install python-docx and python-pptx
from docx import Document
from pptx import Presentation
from pptx.util import Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR
import sys
import os

# ==========================
# INPUT VALUES
# ==========================
INPUT_DOC = "/Users/sophial/Downloads/Orestes_Supertitles_V5.docx"    # .docx
OUTPUT_PPT = None   # .pptx

def read_docx(file_path):
    """Reads a .docx file line by line, preserving formatting."""
    doc = Document(file_path)
    lines = []
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            lines.append(text)
    
    return lines

def create_pptx(docx_lines, output_pptx):
    """Creates a new PowerPoint file with slides containing text from the .docx file."""
    prs = Presentation()
    prs.slide_width = Pt(1800)
    prs.slide_height = Pt(730)
    
    for line in docx_lines:
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # Use a blank slide layout
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor(0, 0, 0)  # Set black background
        
        # Create a new text box
        left = Pt(225)
        top = Pt(40)
        width = Pt(1350)
        height = Pt(650)
        textbox = slide.shapes.add_textbox(left, top, width, height)
        text_frame = textbox.text_frame
        text_frame.word_wrap = True  # Enable text wrapping
        text_frame.text = line
        
        # Format text
        paragraph = text_frame.paragraphs[0]
        paragraph.font.name = "Times New Roman"
        paragraph.font.size = Pt(65)
        paragraph.alignment = PP_ALIGN.CENTER
        paragraph.font.color.rgb = RGBColor(255, 255, 255)  # Set white text
        text_frame.margin_top = 0
        text_frame.margin_bottom = 0
        text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE  # Align vertically center
        
    prs.save(output_pptx)
    print(f"Created PowerPoint saved as {output_pptx}")

if __name__ == "__main__":
    docx_lines = read_docx(INPUT_DOC)
    if (OUTPUT_PPT == None):
        OUTPUT_PPT = os.path.splitext(INPUT_DOC)[0] + ".pptx"
    create_pptx(docx_lines, OUTPUT_PPT)
