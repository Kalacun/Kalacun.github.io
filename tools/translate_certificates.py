#!/usr/bin/env python3
"""Rebuild English reference translations. Requires reportlab; not needed to build the site."""
import html
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'assets/documents/certificates/translations'


def main():
    font_dir = Path('/System/Library/Fonts/Supplemental')
    if (font_dir / 'Arial.ttf').is_file():
        pdfmetrics.registerFont(TTFont('Translation', str(font_dir / 'Arial.ttf')))
        pdfmetrics.registerFont(TTFont('TranslationBold', str(font_dir / 'Arial Bold.ttf')))
    else:
        raise SystemExit('Arial font files are required; update font_dir for your system.')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('TranslationBody', fontName='Translation', fontSize=10.5, leading=15, spaceAfter=8))
    styles.add(ParagraphStyle('TranslationTitle', fontName='TranslationBold', fontSize=20, leading=25, textColor=colors.HexColor('#244d72'), spaceAfter=12))
    styles.add(ParagraphStyle('TranslationHeading', fontName='TranslationBold', fontSize=10.5, leading=15, spaceBefore=10, spaceAfter=5))
    styles.add(ParagraphStyle('TranslationSmall', fontName='Translation', fontSize=8.5, leading=12, textColor=colors.HexColor('#55616b'), spaceAfter=7))
    styles.add(ParagraphStyle('TranslationLabel', fontName='TranslationBold', fontSize=9, leading=13))
    records = json.loads((ROOT / 'tools/certificate-translations.json').read_text())
    OUTPUT.mkdir(parents=True, exist_ok=True)

    def para(text, style='TranslationBody'):
        return Paragraph(html.escape(text), styles[style])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#dce0e3'))
        canvas.line(43, 49, A4[0] - 43, 49)
        canvas.setFont('Translation', 8)
        canvas.setFillColor(colors.HexColor('#55616b'))
        canvas.drawString(43, 35, 'English reference translation | Not a certified translation')
        canvas.drawRightString(A4[0] - 43, 35, str(doc.page))
        canvas.restoreState()

    for record in records:
        original = ROOT / f'assets/documents/certificates/{record["slug"]}.pdf'
        if not original.is_file():
            raise FileNotFoundError(original)
        target = OUTPUT / f'{record["slug"]}-en.pdf'
        doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=43, leftMargin=43,
                                topMargin=39, bottomMargin=64,
                                title=record['title'] + ' - English reference translation',
                                author='English translation prepared for Aleksander Kalacun’s academic website')
        story = [para('ENGLISH TRANSLATION', 'TranslationSmall'),
                 para(record['title'], 'TranslationTitle'),
                 para(record['document_type'], 'TranslationHeading'),
                 para(record['statement'])]
        if record.get('facts'):
            rows = [[para(label, 'TranslationLabel'), para(value)] for label, value in record['facts']]
            table = Table(rows, colWidths=[128, A4[0] - 214], hAlign='LEFT')
            table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                       ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                       ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                                       ('TOPPADDING', (0, 0), (-1, -1), 4),
                                       ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
            story += [Spacer(1, 6), table]
        if record.get('outcomes'):
            story.append(para('Competencies acquired', 'TranslationHeading'))
            for outcome in record['outcomes']:
                story.append(Paragraph('- ' + html.escape(outcome), styles['TranslationBody']))
        if record.get('signatories'):
            story.append(KeepTogether([para('Signatories identified in the original', 'TranslationHeading'),
                                      *[para(name, 'TranslationSmall') for name in record['signatories']]]))
        if record.get('funding'):
            story += [para('Funding statement', 'TranslationHeading'), para(record['funding'], 'TranslationSmall')]
        for note in record.get('notes', []):
            story.append(para(note, 'TranslationSmall'))
        story += [Spacer(1, 12), para('Translated from the Slovenian original. The original issued document remains authoritative. Logos, stamps, and signatures have not been reproduced.', 'TranslationSmall'),
                  para('Original document: ' + original.name, 'TranslationSmall')]
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        print(target.relative_to(ROOT))


if __name__ == '__main__':
    main()
