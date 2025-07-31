import os
import base64
import pdfplumber
import pandas as pd
import fitz
import camelot
from pdf2image import convert_from_path
import pytesseract

from flask import Flask, request, render_template, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
        # 1) Guardar PDF
        f = request.files['pdf']
        filename = secure_filename(f.filename)
        in_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(in_path)

        # 2) Preparar ruta de salida .md
        base, _ = os.path.splitext(in_path)
        out_md = base + '.md'

        # 3) Extraer imágenes a Base64
        img_map = {}
        doc = fitz.open(in_path)
        for p in range(len(doc)):
            for idx, img in enumerate(doc.get_page_images(p), start=1):
                info = doc.extract_image(img[0])
                b64 = base64.b64encode(info['image']).decode()
                img_map[f"page{p+1}_{idx}"] = f"data:image/{info['ext']};base64,{b64}"
        doc.close()

        # 4) Extraer texto y tablas (Camelot)
        with pdfplumber.open(in_path) as pdf, open(out_md, 'w', encoding='utf-8') as md:
            for i, page in enumerate(pdf.pages, start=1):
                md.write(f'## Página {i}\n\n')
                md.write((page.extract_text() or '') + '\n\n')
                tables = camelot.read_pdf(in_path, pages=str(i))
                for t in tables:
                    md.write(t.df.to_markdown(index=False) + '\n\n')
                for key, uri in img_map.items():
                    if key.startswith(f'page{i}_'):
                        md.write(f'![{key}]({uri})\n\n')

        # 5) Enviar Markdown
        return send_file(
            out_md,
            as_attachment=True,
            download_name=os.path.basename(out_md),
            mimetype='text/markdown'
        )
if __name__ == '__main__':
    app.run(debug=True)
