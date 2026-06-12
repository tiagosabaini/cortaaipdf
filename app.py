import io
import os
import sqlite3
import zipfile
from flask import Flask, render_template, request, send_file
import fitz  # PyMuPDF
from PIL import Image

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
DATABASE = 'database.db'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS configuracoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                nome TEXT, 
                coords TEXT
            )
        ''')

@app.route('/')
def index():
    with sqlite3.connect(DATABASE) as conn:
        configs = conn.execute('SELECT * FROM configuracoes').fetchall()
    return render_template('index.html', configs=configs)

@app.route('/upload_preview', methods=['POST'])
def upload_preview():
    if 'pdf' not in request.files:
        return {"error": "Sem arquivo no envio"}, 400
    
    pdf = request.files['pdf']
    if pdf.filename == '':
        return {"error": "Nenhum arquivo selecionado"}, 400

    pdf_path = os.path.join(UPLOAD_FOLDER, pdf.filename)
    pdf.save(pdf_path)
    
    with fitz.open(pdf_path) as doc:
        total_pages = len(doc)
    
    return {"filename": pdf.filename, "total_pages": total_pages}

@app.route('/preview/<filename>/<int:pagnumber>')
def preview(filename, pagnumber):
    pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(pdf_path):
        return {"error": "Arquivo não encontrado"}, 404
    
    with fitz.open(pdf_path) as doc:
        total = len(doc)
        pagnumber = max(0, min(pagnumber, total - 1))
        
        page = doc[pagnumber]
        pix = page.get_pixmap(dpi=100)
        img_data = pix.tobytes("png")
        
    return send_file(io.BytesIO(img_data), mimetype='image/png')

@app.route('/processar', methods=['POST'])
def processar():
    filename = request.form['filename']
    inicio = int(request.form['inicio'])
    fim = int(request.form['fim'])
    
    # Recebe: X, Y, W, H, img_w, img_h
    dados = list(map(float, request.form['coords'].split(',')))
    c_x, c_y, c_w, c_h = dados[0], dados[1], dados[2], dados[3]
    img_w, img_h = dados[4], dados[5]
    
    pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    zip_path = os.path.join(UPLOAD_FOLDER, "recortes.zip")

    if not os.path.exists(pdf_path):
        return {"error": "Arquivo original não encontrado"}, 404

    with fitz.open(pdf_path) as doc:
        with zipfile.ZipFile(zip_path, 'w') as zip_f:
            for p in range(inicio, fim + 1):
                if p >= len(doc):
                    break
                
                page = doc[p] 
                
                # Renderiza a imagem final em alta resolução (300 DPI)
                pix_alta = page.get_pixmap(dpi=300) 
                img_alta = Image.frombytes("RGB", [pix_alta.width, pix_alta.height], pix_alta.samples)
                
                # ESCALA MATEMÁTICA PURA: Tamanho de Alta Resolução / Tamanho visível na Tela
                escala_x = pix_alta.width / img_w
                escala_y = pix_alta.height / img_h
                
                # Conversão direta das coordenadas da tela para os pixels reais da imagem de alta resolucao
                x_base = c_x * escala_x
                y_base = c_y * escala_y
                w_base = c_w * escala_x
                h_base = c_h * escala_y
                
                # Margem de expansão de 9% para garantir que não coma as bordas selecionadas
                fator_expansao = 0.09

                delta_w = w_base * fator_expansao
                delta_h = h_base * fator_expansao
                
                x1 = round(x_base - (delta_w / 2))
                y1 = round(y_base - (delta_h / 2))
                x2 = round((x_base + w_base) + (delta_w / 2))
                y2 = round((y_base + h_base) + (delta_h / 2))
                
                # Restringe aos limites físicos da imagem gerada
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(pix_alta.width, x2)
                y2 = min(pix_alta.height, y2)
                
                area = (x1, y1, x2, y2)
                
                img_cortada = img_alta.crop(area)
                img_name = f"pagina_{p}.png"
                img_path = os.path.join(UPLOAD_FOLDER, img_name)
                
                img_cortada.save(img_path)
                zip_f.write(img_path, img_name)
                os.remove(img_path)

    return send_file(zip_path, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)