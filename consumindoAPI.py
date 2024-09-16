import requests
import os

# URL da API
BASE_URL = 'http://localhost:5000'

# Usuário e senha para login
username = 'user1'
password = 'password1'

# Função para fazer login e obter o token JWT
def login_and_get_token():
    login_url = f'{BASE_URL}/login'
    payload = {'username': username, 'password': password}
    
    response = requests.post(login_url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        token = data['access_token']
        print("Login realizado com sucesso! Token obtido.")
        return token
    else:
        print(f"Falha no login: {response.json().get('msg')}")
        return None

# Função para baixar arquivo protegido usando o token JWT
def download_file(file_type, token):
    download_url = f'{BASE_URL}/download/{file_type}'
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    response = requests.get(download_url, headers=headers)
    
    if response.status_code == 200:
        # Define o nome do arquivo baixado
        file_name = f'{file_type}.csv'
        
        # Salva o conteúdo em um arquivo
        with open(file_name, 'wb') as file:
            file.write(response.content)
        
        print(f'Arquivo {file_name} baixado com sucesso!')
    elif response.status_code == 401:
        print("Token inválido ou expirado. Faça login novamente.")
    else:
        print(f"Erro ao baixar arquivo: {response.status_code} - {response.text}")

# Main function
def main():
    # Realiza o login e obtém o token JWT
    token = login_and_get_token()
    
    if token:
        # Tipos de arquivos disponíveis para download
        files_to_download = ['Producao', 'Processamento', 'Comercializacao', 'Importacao', 'Exportacao']
        
        # Baixa cada arquivo usando o token JWT
        for file_type in files_to_download:
            download_file(file_type, token)

if __name__ == "__main__":
    main()
