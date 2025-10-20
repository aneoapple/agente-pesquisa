# main.py - Lógica final do Backend para o Render

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from bs4 import BeautifulSoup
from google import genai
import sys
# Importa sys para corrigir um erro comum de ambiente Python3.13 no Render

# Inicializa o aplicativo Flask
app = Flask(__name__)
# Permite que o seu site do GitHub Pages acesse esta API (CORS)
CORS(app, resources={r"/*": {"origins": "https://aneoapple.github.io"}}) 

# --- CONFIGURAÇÃO DA CHAVE DE API ---
# A chave GEMINI_API_KEY será lida automaticamente pelo Render
# a partir das Variáveis de Ambiente que você configurou.
# ------------------------------------

# Lista de URLs alvo
URLS_ALVO = ["https://www.affix.com.br/", "https://www.alter.com.br/"]

# Inicializa o cliente Gemini (usará a variável de ambiente)
# O try/except é para prevenir falha se a chave não for encontrada
try:
    client = genai.Client()
except Exception as e:
    # Se a chave não estiver na variável de ambiente do Render, o cliente pode falhar
    print(f"Erro ao inicializar o cliente Gemini: {e}", file=sys.stderr)
    client = None # Define como None para ser verificado na rota da API

def extrair_texto_da_url(url):
    """
    Faz o scraping usando a biblioteca Requests (versão básica)
    e retorna o texto limpo da página.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() 
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remoção de elementos não textuais
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
            
        return soup.get_text(separator=' ', strip=True)
    
    except Exception as e:
        # Se houver um erro de bloqueio/acesso, retorna esta mensagem.
        return f"ERRO_SCRAPING: {url}. Detalhe: {e}"

def agente_analise_ia(pergunta_usuario):
    """
    Função que integra Scraping Básico e Análise de IA.
    """
    # 1. Faz o Scraping
    conteudo_scraped = ""
    for url in URLS_ALVO:
        texto = extrair_texto_da_url(url)
        conteudo_scraped += f"\n\n--- CONTEÚDO DE: {url} ---\n\n{texto}"

    # 2. Constrói o Prompt de Análise (RAG Dinâmico)
    system_instruction = (
        "Você é um especialista em análise de conteúdo web. Sua tarefa é responder à pergunta do usuário "
        "usando APENAS as informações contidas no 'CONTEÚDO SCRAPED' abaixo. "
        "Indique qual site (Affix ou Alter) contém a informação, se possível."
    )

    prompt_completo = (f"{system_instruction}\n\n--- CONTEÚDO SCRAPED ---\n{conteudo_scraped}\n\n--- PERGUNTA DO USUÁRIO ---\n{pergunta_usuario}")

    # 3. Chama o Modelo Gemini
    if client:
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=prompt_completo
        )
        return response.text
    else:
        return "Erro: O cliente Gemini não foi inicializado. Verifique a chave de API."

# -------------------------------------------------------------------
# O ENDPOINT REAL DA API
# -------------------------------------------------------------------

@app.route('/pesquisa', methods=['POST'])
def pesquisa_api():
    try:
        data = request.get_json()
        pergunta = data.get('pergunta', '')
        
        if not pergunta:
            return jsonify({"resposta": "Erro: Pergunta não fornecida."}), 400

        # Executa a função de análise de IA
        resposta_ia = agente_analise_ia(pergunta)
        
        return jsonify({"resposta": resposta_ia}), 200

    except Exception as e:
        # Se houver um erro de servidor durante a execução
        return jsonify({"resposta": f"Erro interno do servidor: {e}"}), 500

# Esta é a instrução para o Gunicorn (o servidor web)
# Ele a carrega para iniciar a aplicação 'app'
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 8080))
