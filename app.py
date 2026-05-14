from flask import Flask, render_template, request, send_file
import io
import fitz  # PyMuPDF
import os
import zipfile
from PIL import Image
import sqlite3

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect('database.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS configuracoes 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, coords TEXT)''')
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    configs = conn.execute('SELECT * FROM configuracoes').fetchall()
    conn.close()
    return render_template('index.html', configs=configs)

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
    # Garante que a página solicitada existe no PDF
    total = len(doc)
    if pagnumber >= total: pagnumber = total - 1
    if pagnumber < 0: pagnumber = 0
    
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
    c = list(map(float, request.form['coords'].split(',')))
    
    pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    doc = fitz.open(pdf_path)
    zip_path = os.path.join(UPLOAD_FOLDER, "recortes.zip")

    with zipfile.ZipFile(zip_path, 'w') as zip_f:
        for p in range(inicio, fim + 1):
            if p >= len(doc): break
            page = doc[p] 
            pix = page.get_pixmap(dpi=300) 
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            s = 300 / 100 # Escala Preview vs Corte Final
            area = (c[0]*s, c[1]*s, (c[0]+c[2])*s, (c[1]+c[3])*s)
            
            img_cortada = img.crop(area)
            img_name = f"pagina_{p}.png"
            img_path = os.path.join(UPLOAD_FOLDER, img_name)
            img_cortada.save(img_path)
            zip_f.write(img_path, img_name)
            os.remove(img_path)

    doc.close()
    return send_file(zip_path, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
#mt fodinha kjk#