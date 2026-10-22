#!/usr/bin/env python3
"""Render the three English reference translations from their editable text source."""
import html
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether

ROOT = Path(__file__).resolve().parents[1]


def main():
    fonts = Path('/System/Library/Fonts/Supplemental')
    pdfmetrics.registerFont(TTFont('Translation', str(fonts / 'Arial.ttf')))
    pdfmetrics.registerFont(TTFont('TranslationBold', str(fonts / 'Arial Bold.ttf')))
    body = ParagraphStyle('Body', fontName='Translation', fontSize=10.2, leading=14, spaceAfter=7,
                          allowWidows=0, allowOrphans=0)
    title = ParagraphStyle('Title', parent=body, fontName='TranslationBold', fontSize=18, leading=23,
                           textColor=colors.HexColor('#244d72'), spaceAfter=10, keepWithNext=True)
    heading = ParagraphStyle('Heading', parent=body, fontName='TranslationBold', fontSize=12,
                             leading=16, spaceBefore=9, spaceAfter=5, keepWithNext=True)
    small = ParagraphStyle('Small', parent=body, fontSize=8.5, leading=12,
                           textColor=colors.HexColor('#55616b'))
    bullet = ParagraphStyle('Bullet', parent=body, leftIndent=13, firstLineIndent=-13)
    reference = ParagraphStyle('Reference', parent=body, fontSize=9.5, leading=13)

    def paragraphs(text, style=body):
        return [Paragraph(html.escape(p).replace('\n', '<br/>'), style)
                for p in text.split('\n\n') if p.strip()]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#dce0e3'))
        canvas.line(43, 49, A4[0] - 43, 49)
        canvas.setFont('Translation', 8)
        canvas.setFillColor(colors.HexColor('#55616b'))
        canvas.drawString(43, 35, 'English reference translation | Not a certified translation')
        canvas.drawRightString(A4[0] - 43, 35, str(doc.page))
        canvas.restoreState()

    records = json.loads((ROOT / 'tools/additional-document-translations.json').read_text())
    for record in records:
        original, output = ROOT / record['original'], ROOT / record['output']
        if not original.is_file():
            raise FileNotFoundError(original)
        output.parent.mkdir(parents=True, exist_ok=True)
        story = [*paragraphs('ENGLISH TRANSLATION', small),
                 *paragraphs(record['title'], title), *paragraphs(record['subtitle'], small)]
        for block in record['blocks']:
            if block.get('heading'):
                story.extend(paragraphs(block['heading'], heading))
            if block.get('text'):
                story.extend(paragraphs(block['text'], reference if block.get('heading') == 'References' else body))
            for text in block.get('bullets', []):
                story.extend(paragraphs('- ' + text, bullet))
            for index, text in enumerate(block.get('numbered', []), 1):
                story.extend(paragraphs(f'{index}. {text}', bullet))
        story.append(KeepTogether([Spacer(1, 10), *paragraphs(
            'Translated from the Slovenian original. The original issued document remains authoritative. '
            'Logos, stamps, and signatures have not been reproduced.', small),
            *paragraphs('Original document: ' + original.name, small)]))
        doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=43, rightMargin=43,
                                topMargin=39, bottomMargin=64,
                                title=record['title'] + ' - English reference translation')
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        print(output.relative_to(ROOT))


if __name__ == '__main__':
    main()
