import requests
from bs4 import BeautifulSoup
from google import genai

# Lista de URLs alvo
URLS_ALVO = ["https://www.affix.com.br/", "https://www.alter.com.br/"]

# Inicializa o cliente (usará a variável de ambiente)
client = genai.Client()

def extrair_texto_da_url(url):
    # ... (código da função extrair_texto_da_url que já criamos) ...
    # (O código é o mesmo do seu main.py)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() 
        soup = BeautifulSoup(response.content, 'html.parser')
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        return f"ERRO_SCRAPING: {url}"

def agente_local_run(pergunta_usuario):
    # 1. Faz o Scraping
    conteudo_scraped = ""
    for url in URLS_ALVO:
        texto = extrair_texto_da_url(url)
        conteudo_scraped += f"\n\n--- CONTEÚDO DE: {url} ---\n\n{texto}"

    # 2. Constrói o Prompt
    system_instruction = ("Você é um especialista em análise de conteúdo web. Sua tarefa é responder à pergunta do usuário "
                          "usando APENAS as informações contidas no 'CONTEÚDO SCRAPED' abaixo. "
                          "Indique qual site (Affix ou Alter) contém a informação, se possível.")

    prompt_completo = (f"{system_instruction}\n\n--- CONTEÚDO SCRAPED ---\n{conteudo_scraped}\n\n--- PERGUNTA DO USUÁRIO ---\n{pergunta_usuario}")

    # 3. Chama o Modelo Gemini
    response = client.models.generate_content(
        model='gemini-2.5-flash', 
        contents=prompt_completo
    )
    return response.text

# 4. Interface de Teste no Colab
# Este bloco simula o que o seu frontend faria
pergunta = input("Digite sua pergunta de pesquisa (Ex: O que é a Alter Benefícios?): ")
resposta = agente_local_run(pergunta)

print("\n--- Resposta da IA ---")
print(resposta)
