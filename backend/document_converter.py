"""
Unified Document to PDF Converter
Converts various document formats (DOC, DOCX, MD, TXT) to PDF before processing.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional
import subprocess
import logging

# Markdown to PDF
try:
    import markdown
    from weasyprint import HTML
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

# Word to PDF
try:
    from docx2pdf import convert as docx2pdf_convert
    DOCX2PDF_AVAILABLE = True
except ImportError:
    DOCX2PDF_AVAILABLE = False

# Alternative: LibreOffice conversion (more reliable for server environments)
def check_libreoffice():
    """Check if LibreOffice is available for document conversion."""
    try:
        result = subprocess.run(
            ['libreoffice', '--version'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

LIBREOFFICE_AVAILABLE = check_libreoffice()

logger = logging.getLogger(__name__)


def txt_to_pdf(input_path: str, output_path: str) -> bool:
    """
    Convert plain text file to PDF.
    
    Args:
        input_path: Path to input TXT file
        output_path: Path to output PDF file
    
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        
        # Read text content
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            text_content = f.read()
        
        # Create PDF
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='CustomBody',
            parent=styles['BodyText'],
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=6
        ))
        
        # Split text into paragraphs and add to PDF
        for line in text_content.split('\n'):
            if line.strip():
                # Escape XML special characters
                line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                p = Paragraph(line, styles['CustomBody'])
                elements.append(p)
            else:
                elements.append(Spacer(1, 0.2*inch))
        
        # Build PDF
        doc.build(elements)
        logger.info(f"Successfully converted TXT to PDF: {input_path} -> {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error converting TXT to PDF: {e}")
        return False


def md_to_pdf(input_path: str, output_path: str) -> bool:
    """
    Convert Markdown file to PDF.
    
    Args:
        input_path: Path to input MD file
        output_path: Path to output PDF file
    
    Returns:
        True if conversion successful, False otherwise
    """
    if not MARKDOWN_AVAILABLE:
        logger.error("Markdown/WeasyPrint not available. Install with: pip install markdown weasyprint")
        return False
    
    try:
        # Read markdown content
        with open(input_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Convert markdown to HTML
        html_content = markdown.markdown(
            md_content,
            extensions=['extra', 'codehilite', 'tables', 'toc']
        )
        
        # Wrap in basic HTML structure with styling
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    padding: 20px;
                    max-width: 800px;
                    margin: 0 auto;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #333;
                    margin-top: 24px;
                    margin-bottom: 16px;
                }}
                code {{
                    background-color: #f4f4f4;
                    padding: 2px 4px;
                    border-radius: 3px;
                }}
                pre {{
                    background-color: #f4f4f4;
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 16px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f4f4f4;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Convert HTML to PDF
        HTML(string=full_html).write_pdf(output_path)
        logger.info(f"Successfully converted MD to PDF: {input_path} -> {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error converting MD to PDF: {e}")
        return False


def doc_to_pdf_libreoffice(input_path: str, output_path: str) -> bool:
    """
    Convert DOC/DOCX to PDF using LibreOffice.
    
    Args:
        input_path: Path to input DOC/DOCX file
        output_path: Path to output PDF file
    
    Returns:
        True if conversion successful, False otherwise
    """
    if not LIBREOFFICE_AVAILABLE:
        logger.error("LibreOffice not available for document conversion")
        return False
    
    try:
        # Get output directory
        output_dir = os.path.dirname(output_path)
        if not output_dir:
            output_dir = '.'
        
        # Run LibreOffice conversion
        result = subprocess.run(
            [
                'libreoffice',
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', output_dir,
                input_path
            ],
            capture_output=True,
            timeout=60,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"LibreOffice conversion failed: {result.stderr}")
            return False
        
        # LibreOffice creates PDF with same base name
        base_name = Path(input_path).stem
        generated_pdf = os.path.join(output_dir, f"{base_name}.pdf")
        
        # Rename to desired output path if different
        if generated_pdf != output_path and os.path.exists(generated_pdf):
            os.rename(generated_pdf, output_path)
        
        logger.info(f"Successfully converted DOC/DOCX to PDF: {input_path} -> {output_path}")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"LibreOffice conversion timed out for: {input_path}")
        return False
    except Exception as e:
        logger.error(f"Error converting DOC/DOCX to PDF: {e}")
        return False


def doc_to_pdf_python(input_path: str, output_path: str) -> bool:
    """
    Convert DOC/DOCX to PDF using Python library (Windows only).
    
    Args:
        input_path: Path to input DOC/DOCX file
        output_path: Path to output PDF file
    
    Returns:
        True if conversion successful, False otherwise
    """
    if not DOCX2PDF_AVAILABLE:
        logger.error("docx2pdf not available. Install with: pip install docx2pdf")
        return False
    
    try:
        docx2pdf_convert(input_path, output_path)
        logger.info(f"Successfully converted DOC/DOCX to PDF: {input_path} -> {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error converting DOC/DOCX to PDF with docx2pdf: {e}")
        return False


def convert_to_pdf(input_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Unified function to convert various document formats to PDF.
    
    Supported formats: .txt, .md, .doc, .docx
    
    Args:
        input_path: Path to input document
        output_path: Optional path to output PDF. If not provided, creates temp file.
    
    Returns:
        Path to converted PDF file, or None if conversion failed
    """
    input_path = str(input_path)
    
    # Determine file extension
    _, ext = os.path.splitext(input_path.lower())
    
    # If already PDF, return as-is
    if ext == '.pdf':
        logger.info(f"File is already PDF: {input_path}")
        return input_path
    
    # Create output path if not provided
    if output_path is None:
        # Create temp file with .pdf extension
        temp_fd, output_path = tempfile.mkstemp(suffix='.pdf')
        os.close(temp_fd)  # Close file descriptor, we just need the path
    
    # Convert based on file type
    success = False
    
    if ext == '.txt':
        success = txt_to_pdf(input_path, output_path)
    
    elif ext == '.md':
        success = md_to_pdf(input_path, output_path)
    
    elif ext in ['.doc', '.docx']:
        # Try LibreOffice first (more reliable for servers)
        if LIBREOFFICE_AVAILABLE:
            success = doc_to_pdf_libreoffice(input_path, output_path)
        elif DOCX2PDF_AVAILABLE:
            success = doc_to_pdf_python(input_path, output_path)
        else:
            logger.error("No DOC/DOCX converter available. Install LibreOffice or docx2pdf")
    
    else:
        logger.error(f"Unsupported file format: {ext}")
        return None
    
    if success and os.path.exists(output_path):
        return output_path
    else:
        logger.error(f"Conversion failed for: {input_path}")
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        return None


# Convenience function for integration with existing pipeline
def ensure_pdf_format(file_path: str) -> str:
    """
    Ensure a document is in PDF format, converting if necessary.
    
    Args:
        file_path: Path to input file
    
    Returns:
        Path to PDF file (may be original if already PDF, or converted temp file)
    
    Raises:
        ValueError: If conversion fails
    """
    result = convert_to_pdf(file_path)
    if result is None:
        raise ValueError(f"Failed to convert document to PDF: {file_path}")
    return result


if __name__ == "__main__":
    # Test the converter
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python document_converter.py <input_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = convert_to_pdf(input_file, output_file)
    
    if result:
        print(f"✓ Conversion successful: {result}")
    else:
        print("✗ Conversion failed")
        sys.exit(1)
