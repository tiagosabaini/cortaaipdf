from flask import Flask, render_template, request, send_file, redirect
import fitz, os, zipfile, sqlite3
from PIL import Image

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configuração do Banco de Dados (CRUD)
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS configuracoes 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, coords TEXT)''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    configs = conn.execute('SELECT * FROM configuracoes').fetchall()
    conn.close()
    return render_template('index.html', configs=configs)

@app.route('/salvar', methods=['POST'])
def salvar_config():
    nome = request.form['nome_config']
    coords = request.form['coords']
    conn = sqlite3.connect('database.db')
    conn.execute('INSERT INTO configuracoes (nome, coords) VALUES (?, ?)', (nome, coords))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/processar', methods=['POST'])
def processar():
    pdf = request.files['pdf']
    inicio = int(request.form['inicio'])
    fim = int(request.form['fim'])
    coords = list(map(float, request.form['coords'].split(',')))

    pdf_path = os.path.join(UPLOAD_FOLDER, pdf.filename)
    pdf.save(pdf_path)

    doc = fitz.open(pdf_path)
    zip_path = os.path.join(UPLOAD_FOLDER, "resultado.zip")

    with zipfile.ZipFile(zip_path, 'w') as zip_f:
        for p in range(inicio, fim + 1):
            if p >= len(doc): break
            page = doc[p] # Lógica +1 integrada
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            fator = 300 / 72
            area = (coords[0]*fator, coords[1]*fator, coords[2]*fator, coords[3]*fator)
            img_cortada = img.crop(area)
            img_tmp = f"pag_{p}.png"
            img_cortada.save(img_tmp)
            zip_f.write(img_tmp)
            os.remove(img_tmp)

    doc.close()
    return send_file(zip_path, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)