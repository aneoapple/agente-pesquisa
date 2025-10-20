# main.py - Agente de RAG de PDF/CSV para o Render

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import pandas as pd
import requests
import io
import pdfplumber
from google import genai

# Inicializa o aplicativo Flask
app = Flask(__name__)
# Permite que o seu site do GitHub Pages acesse esta API (CORS)
CORS(app, resources={r"/*": {"origins": "https://aneoapple.github.io"}}) 

# --- CONFIGURAÇÃO ---
# O arquivo CSV deve estar no mesmo diretório que este main.py
CSV_FILE_NAME = 'affix_pdfs_manifest (3).csv'
MAX_PDFS_TO_ANALYZE = 10 # Limite para evitar timeout, já que há 287 PDFs
# --------------------

# Inicializa o cliente Gemini (usará a variável de ambiente)
try:
    client = genai.Client()
except Exception as e:
    print(f"Erro ao inicializar o cliente Gemini: {e}", file=sys.stderr)
    client = None

def extrair_texto_do_pdf(url):
    """
    Baixa o PDF de uma URL e extrai o texto de todas as páginas.
    """
    try:
        # 1. Baixar o conteúdo binário do PDF
        response = requests.get(url, timeout=30)
        response.raise_for_status() 
        pdf_bytes = io.BytesIO(response.content)

        texto_total = ""
        
        # 2. Extrair o texto usando pdfplumber
        with pdfplumber.open(pdf_bytes) as pdf:
            # Limita a extração para não sobrecarregar o modelo de IA.
            for page in pdf.pages:
                texto_total += page.extract_text() + "\n\n"
        
        if not texto_total.strip():
            return f"ERRO_PDF: Conteúdo vazio na URL {url}."

        return texto_total

    except Exception as e:
        return f"ERRO_EXTRAÇÃO_PDF: {url}. Detalhe: {e}"

def agente_analise_pdf(pergunta_usuario):
    """
    Função que integra Leitura de CSV, Extração de PDF e Análise de IA.
    """
    if not client:
        return "Erro: Cliente Gemini não inicializado. Verifique a chave de API."
        
    try:
        # 1. Leitura do CSV para obter as URLs
        if not os.path.exists(CSV_FILE_NAME):
             return f"ERRO FATAL: Arquivo CSV '{CSV_FILE_NAME}' não encontrado no servidor."
             
        df = pd.read_csv(CSV_FILE_NAME)
        
        # Filtra apenas URLs que contém 'Samp' no nome do arquivo (para focar na sua pesquisa)
        # O URL de Samp que você deu como exemplo tem "Samp" no nome.
        # df_filtrado = df[df['name'].str.contains('Samp', case=False, na=False)]
        
        # Caso queira analisar os 10 primeiros de forma genérica:
        urls_para_analise = df['url'].head(MAX_PDFS_TO_ANALYZE).tolist()
        
        if not urls_para_analise:
            return "Nenhum PDF encontrado na lista para análise."

        # 2. Coleta de Conteúdo (Extração de PDF)
        conteudo_coletado = ""
        for url in urls_para_analise:
            texto = extrair_texto_do_pdf(url)
            conteudo_coletado += f"\n\n--- FONTE: {url} ---\n\n{texto}"

        # 3. Constrói o Prompt de Análise
        system_instruction = (
            "Você é um especialista em análise de documentos de planos de saúde. "
            "Sua tarefa é responder à pergunta do usuário usando APENAS as informações "
            "contidas no 'CONTEÚDO DOS PDFS' abaixo. Se a informação não estiver disponível, diga que não foi encontrada. "
            "Forneça a resposta em formato claro e com as devidas fontes."
        )

        prompt_completo = (f"{system_instruction}\n\n--- CONTEÚDO DOS PDFS ---\n{conteudo_coletado}\n\n--- PERGUNTA DO USUÁRIO ---\n{pergunta_usuario}")

        # 4. Chama o Modelo Gemini
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=prompt_completo
        )
        return response.text

    except Exception as e:
        return f"Erro interno durante a análise: {e}"

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
        resposta_ia = agente_analise_pdf(pergunta)
        
        return jsonify({"resposta": resposta_ia}), 200

    except Exception as e:
        # Se houver um erro de servidor durante a execução
        return jsonify({"resposta": f"Erro interno do servidor: {e}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 8080))
