import os
import requests
from bs4 import BeautifulSoup
from google import genai

# Configuração da Chave da API Gemini
# Você deve definir a variável de ambiente. Se estiver no Colab, rode um bloco com !pip e os.environ
# Se estiver em um servidor, a chave deve ser definida no ambiente do servidor.
# --- INÍCIO DA CONFIGURAÇÃO DE CHAVE ---
# O cliente genai.Client() usará esta variável:
# os.environ['GEMINI_API_KEY'] = "SUA_CHAVE_DE_API_COMPLETA_AQUI" 
# --- FIM DA CONFIGURAÇÃO DE CHAVE ---

# Lista de URLs alvo
URLS_ALVO = ["https://www.affix.com.br/", "https://www.alter.com.br/"]

# Inicializa o cliente (usará a variável de ambiente)
client = genai.Client()

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

def agente_local_run(pergunta_usuario):
    """
    Função principal que integra Scraping Básico e Análise de IA.
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
    response = client.models.generate_content(
        model='gemini-2.5-flash', 
        contents=prompt_completo
    )
    return response.text

# 4. Interface de Teste no Colab (Executará a análise)
pergunta = input("Digite sua pergunta de pesquisa (Ex: O que é a Alter Benefícios?): ")
resposta = agente_local_run(pergunta)

print("\n--- Resposta da IA ---")
print(resposta)
