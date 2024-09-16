from flask import Flask, send_file, abort, request, jsonify, render_template_string
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import logging
import os
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configuração de logging
logging.basicConfig(filename='vitibrasil.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração do JWT
app.config['JWT_SECRET_KEY'] = 'super-secret-key'  # Altere para uma chave mais segura em produção
jwt = JWTManager(app)

# Usuários cadastrados (nome de usuário e senha hash)
users = {
    'user1': generate_password_hash('password1'),
    'user2': generate_password_hash('password2')
}

# Diretório para armazenar os arquivos de teste (assets)
ASSETS_DIR = 'assets'

if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR)

files = [
    {'url': 'http://vitibrasil.cnpuv.embrapa.br/index.php?opcao=opt_02', 'name': 'Producao.csv'},
    {'url': 'http://vitibrasil.cnpuv.embrapa.br/index.php?opcao=opt_03', 'name': 'Processamento.csv'},
    {'url': 'http://vitibrasil.cnpuv.embrapa.br/index.php?opcao=opt_04', 'name': 'Comercializacao.csv'},
    {'url': 'http://vitibrasil.cnpuv.embrapa.br/index.php?opcao=opt_05', 'name': 'Importacao.csv'},
    {'url': 'http://vitibrasil.cnpuv.embrapa.br/index.php?opcao=opt_06', 'name': 'Exportacao.csv'},
]

def download_csv(url):
    try:
        logging.info(f"Iniciando o download do arquivo de {url}")
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        download_button = soup.find('span', class_='spn_small')
        if download_button:
            download_link = download_button.find_parent('a')['href']
            download_url = requests.compat.urljoin(url, download_link)

            csv_response = requests.get(download_url)
            csv_response.raise_for_status()

            logging.info(f"Arquivo baixado com sucesso de {url}")
            return csv_response.content
        else:
            logging.error(f'Botão de download não encontrado na URL {url}.')
            return None
    except requests.RequestException as e:
        logging.error(f'Erro ao acessar a URL {url}: {e}')
        return None

# Página de login com formulário
@app.route('/login', methods=['GET'])
def login_page():
    return render_template_string('''
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login</title>
            <script>
                function login() {
                    var username = document.getElementById("username").value;
                    var password = document.getElementById("password").value;
                    
                    fetch('/login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({username: username, password: password})
                    }).then(response => response.json())
                      .then(data => {
                          if (data.access_token) {
                              alert('Login realizado com sucesso!');
                              localStorage.setItem('token', data.access_token);  // Armazena o token no localStorage
                          } else {
                              alert('Falha no login: ' + (data.msg || 'Erro desconhecido'));
                          }
                      });
                }

                function downloadFile(fileType) {
                    var token = localStorage.getItem('token');  // Recupera o token do localStorage
                    if (!token) {
                        alert('Você precisa fazer login antes de baixar o arquivo.');
                        return;
                    }

                    fetch('/download/' + fileType, {
                        method: 'GET',
                        headers: {
                            'Authorization': 'Bearer ' + token  // Inclui o token no cabeçalho
                        }
                    }).then(response => {
                        if (response.ok) {
                            return response.blob();
                        } else if (response.status === 401) {
                            throw new Error('Token inválido ou expirado. Faça login novamente.');
                        } else {
                            throw new Error('Falha ao baixar o arquivo: ' + response.statusText);
                        }
                    }).then(blob => {
                        var url = window.URL.createObjectURL(blob);
                        var a = document.createElement('a');
                        a.href = url;
                        a.download = fileType + '.csv';
                        document.body.appendChild(a);  // Necessário para o Firefox
                        a.click();
                        a.remove();
                    }).catch(error => {
                        console.error('Erro:', error);
                        alert(error.message);
                    });
                }
            </script>
        </head>
        <body>
            <h2>Login</h2>
            <form onsubmit="event.preventDefault(); login();">
                <label for="username">Usuário:</label>
                <input type="text" id="username" name="username" required><br><br>
                <label for="password">Senha:</label>
                <input type="password" id="password" name="password" required><br><br>
                <button type="submit">Login</button>
            </form>

            <h2>Baixar Arquivos</h2>
            <button onclick="downloadFile('Producao')">Baixar Producao</button>
            <button onclick="downloadFile('Processamento')">Baixar Processamento</button>
            <button onclick="downloadFile('Comercializacao')">Baixar Comercializacao</button>
            <button onclick="downloadFile('Importacao')">Baixar Importacao</button>
            <button onclick="downloadFile('Exportacao')">Baixar Exportacao</button>
        </body>
        </html>
    ''')

# Endpoint para login e geração de JWT (método POST)
@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if not username or not password:
        return jsonify({"msg": "Nome de usuário e senha são obrigatórios"}), 400

    user_password_hash = users.get(username)
    if not user_password_hash or not check_password_hash(user_password_hash, password):
        return jsonify({"msg": "Credenciais inválidas"}), 401

    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token), 200

# Rota protegida por JWT para download de arquivos CSV
@app.route('/download/<file_type>', methods=['GET'])
@jwt_required()
def download(file_type):
    file_info = next((item for item in files if item['name'].lower().startswith(file_type.lower())), None)

    if not file_info:
        logging.error(f"Arquivo não encontrado: {file_type}")
        abort(404, description="Arquivo não encontrado.")

    csv_content = download_csv(file_info['url'])
    if csv_content:
        try:
            file_path = os.path.join(ASSETS_DIR, file_info['name'])
            with open(file_path, 'wb') as f:
                f.write(csv_content)
            logging.info(f"Arquivo {file_info['name']} salvo em assets.")

            return send_file(
                BytesIO(csv_content),
                as_attachment=True,
                download_name=file_info['name']
            )
        except Exception as e:
            logging.error(f'Erro ao enviar o arquivo: {e}')
            abort(500, description="Erro ao enviar o arquivo.")
    else:
        logging.error(f"Arquivo CSV não encontrado para {file_info['name']}")
        abort(404, description="Arquivo não encontrado.")

if __name__ == '__main__':
    app.run(debug=False)
