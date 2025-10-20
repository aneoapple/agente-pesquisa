
# main.py
import os
import json
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# Inicializa o cliente da API Gemini
# A chave da API deve ser definida como uma variável de ambiente (GEMINI_API_KEY) no ambiente de hospedagem.
client = genai.Client()

# Lista de URLs permitidas para scraping
URLS_ALVO = [
    "https://www.affix.com.br/", 
    "https://www.alter.com.br/"
]

def extrair_texto_da_url(url):
    """
    Faz o scraping do site, remove scripts e estilos e retorna o texto limpo.
    """
    try:
        # Tenta simular um navegador comum para evitar bloqueios simples
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Aumenta o timeout para 15 segundos
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Levanta exceção para códigos de erro HTTP

        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove elementos não textuais (scripts, estilos, navegação, rodapés, etc.)
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Extrai o texto limpo e retorna
        texto_limpo = soup.get_text(separator=' ', strip=True)
        return texto_limpo

    except requests.exceptions.RequestException as e:
        return f"ERRO_SCRAPING: Não foi possível acessar a URL {url}. Detalhe: {e}"
    except Exception as e:
        return f"ERRO_GERAL: Falha ao processar o conteúdo. Detalhe: {e}"

def agente_pesquisa_dinamico(request):
    """
    Recebe a requisição HTTP do seu Frontend, faz o scraping dos sites alvo e usa a IA para analisar o conteúdo extraído.
    """
    # Configuração de CORS (necessário para a comunicação com o GitHub Pages)
    headers = {
        'Access-Control-Allow-Origin': 'https://aneoapple.github.io', 
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '3600'
    }

    # Resposta para requisição OPTIONS (pré-voo)
    if request.method == 'OPTIONS':
        return ('', 204, headers)

    try:
        # 1. Recebe a pergunta do corpo da requisição JSON
        request_json = request.get_json()
        pergunta_usuario = request_json['pergunta']
    except Exception as e:
        return (json.dumps({"resposta": f"Erro ao processar a requisição: {e}"}), 400, headers)

    
    # 2. FAZ O SCRAPING DE TODOS OS SITES ALVO
    conteudo_scraped = ""
    for url in URLS_ALVO:
        # Chama a função de scraping
        texto = extrair_texto_da_url(url)
        conteudo_scraped += f"\n\n--- CONTEÚDO DE: {url} ---\n\n{texto}"
        
        if "ERRO_SCRAPING" in texto:
             # Se houver erro de acesso (ex: bloqueio)
             print(f"Alerta: Erro no scraping de {url}")


    # 3. CONSTRÓI O PROMPT PARA A IA (RAG dinâmico)
    system_instruction = (
        "Você é um especialista em análise de conteúdo web. Sua tarefa é responder à pergunta do usuário "
        "usando APENAS as informações contidas no 'CONTEÚDO SCRAPED' abaixo. "
        "Indique qual site (Affix ou Alter) contém a informação, se possível. "
        "Se a informação não for encontrada no conteúdo extraído, responda que ela não está disponível nas fontes fornecidas."
    )

    prompt_completo = (
        f"{system_instruction}\n\n"
        f"--- CONTEÚDO SCRAPED ---\n"
        f"{conteudo_scraped}\n\n"
        f"--- PERGUNTA DO USUÁRIO ---\n"
        f"{pergunta_usuario}"
    )

    # 4. CHAMA O MODELO GEMINI
    try:
        # Configurações para reduzir a latência e custo
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=prompt_completo
        )
        
        resposta_ia = response.text
        status_code = 200

    except Exception as e:
        resposta_ia = f"Erro na chamada da API Gemini: {e}"
        status_code = 500

    # 5. RETORNA A RESPOSTA
    return (json.dumps({"resposta": resposta_ia}), status_code, headers)
