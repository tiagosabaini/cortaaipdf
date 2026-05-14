from flask import Flask, render_template, request, send_file
import io
import fitz  # PyMuPDF
import os
import zipfile
from PIL import Image

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_preview', methods=['POST'])
def upload_preview():
    if 'pdf' not in request.files:
        return {"error": "Sem arquivo"}, 400
    pdf = request.files['pdf']
    pdf_path = os.path.join(UPLOAD_FOLDER, pdf.filename)
    pdf.save(pdf_path)
    return {"filename": pdf.filename}

@app.route('/preview/<filename>/<int:pagnumber>')
def preview(filename, pagnumber):
    pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(pdf_path): return "Erro", 404
    
    doc = fitz.open(pdf_path)
    total = len(doc)
    pagnumber = max(0, min(pagnumber, total - 1))
    
    page = doc[pagnumber]
    pix = page.get_pixmap(dpi=100) 
    img_data = pix.tobytes("png")
    doc.close()
    return send_file(io.BytesIO(img_data), mimetype='image/png')

@app.route('/processar', methods=['POST'])
def processar():
    filename = request.form['filename']
    inicio = int(request.form['inicio'])
    fim = int(request.form['fim'])
    
    # x, y, w, h, dispW, dispH, realW, realH
    data = list(map(float, request.form['coords'].split(',')))
    x, y, w, h, dispW, dispH, realW, realH = data
    
    scale_x = realW / dispW
    scale_y = realH / dispH

    pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    doc = fitz.open(pdf_path)
    zip_path = os.path.join(UPLOAD_FOLDER, "recortes.zip")

    with zipfile.ZipFile(zip_path, 'w') as zip_f:
        for p in range(inicio, fim + 1):
            if p >= len(doc): break
            page = doc[p]
            pix = page.get_pixmap(dpi=300)
            img_full = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            dpi_m = 300 / 100
            left = x * scale_x * dpi_m
            top = y * scale_y * dpi_m
            right = (x + w) * scale_x * dpi_m
            bottom = (y + h) * scale_y * dpi_m
            
            img_cortada = img_full.crop((left, top, right, bottom))
            img_name = f"pagina_{p+1}.png"
            img_path = os.path.join(UPLOAD_FOLDER, img_name)
            img_cortada.save(img_path)
            zip_f.write(img_path, img_name)
            os.remove(img_path)

    doc.close()
    return send_file(zip_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)