# main.py - Lógica de Extração de PDF para o Render

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
            for i, page in enumerate(pdf.pages):
                texto_total += page.extract_text()
                # Limita a extração para não sobrecarregar o modelo de IA e o servidor.
                # O limite de 287 PDFs inteiros pode ser muito grande para uma única requisição.
                # Vamos limitar a 5 PDFs por requisição para evitar timeout e limite de tokens.
                if i >= 5: 
                    break 

        if not texto_total.strip():
            return f"ERRO_PDF: Conteúdo vazio na URL {url}."

        return texto_total

    except Exception as e:
        return f"ERRO_EXTRAÇÃO_PDF: {url}. Detalhe: {e}"

def agente_analise_ia(pergunta_usuario):
    """
    Função que integra Leitura de CSV, Extração de PDF e Análise de IA.
    """
    try:
        # 1. Leitura do CSV para obter as URLs
        if not os.path.exists(CSV_FILE_NAME):
             return "ERRO FATAL: Arquivo CSV não encontrado no servidor."
             
        df = pd.read_csv(CSV_FILE_NAME)
        # Usaremos as 5 primeiras URLs para um teste rápido e para evitar o timeout de 287 downloads.
        # Em produção, você precisaria de um sistema assíncrono para processar 287 arquivos.
        urls_para_analise = df['url'].head(5).tolist()

        # 2. Coleta de Conteúdo (Extração de PDF)
        conteudo_coletado = ""
        for url in urls_para_analise:
            texto = extrair_texto_do_pdf(url)
            conteudo_coletado += f"\n\n--- FONTE: {url} ---\n\n{texto}"

        # 3. Constrói o Prompt de Análise
        system_instruction = (
            "Você é um especialista em análise de documentos de planos de saúde. "
            "Sua tarefa é responder à pergunta do usuário usando APENAS as informações "
            "contidas no 'CONTEÚDO DOS PDFS' abaixo. Se a informação não estiver disponível, diga que não foi encontrada."
        )

        prompt_completo = (f"{system_instruction}\n\n--- CONTEÚDO DOS PDFS ---\n{conteudo_coletado}\n\n--- PERGUNTA DO USUÁRIO ---\n{pergunta_usuario}")

        # 4. Chama o Modelo Gemini
        if client:
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=prompt_completo
            )
            return response.text
        else:
            return "Erro: O cliente Gemini não foi inicializado. Verifique a chave de API."

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
        return jsonify({"resposta": f"Erro interno do servidor: {e}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 8080))
