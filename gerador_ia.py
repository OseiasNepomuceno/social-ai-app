import json
from openai import OpenAI
from dotenv import load_dotenv
import os
import re
from datetime import datetime
from supabase import create_client
from services.supabase_storage import upload_image

# =========================
# ENV
# =========================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# IA CLIENT
# =========================

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

print("Sistema IA SaaS iniciado 🚀")

# =========================
# INPUTS
# =========================

user_id = input("Digite seu USER_ID (Supabase Auth): ")

tema = input("Digite o tema do conteúdo: ")

rede = input("Escolha a rede (instagram/linkedin): ").lower()

print("\nEscolha o modo do conteúdo:")
modo_escolha = input("1-Viral 2-Autoridade 3-Vendas 4-Storytelling: ")

print("\nEscolha o nicho:")
nicho_escolha = input("1-Contabilidade 2-Advocacia 3-Saúde 4-Marketing 5-Imobiliária 6-Arquiteturaedesigndeinteriores 7-Diversidadeerepresentacao 8-Engenharia 9-Fitnessbem-estar 10-Fotografiadealimentos 11-Gestao_negocios 12-Limpeza 13-Psicologia 14-Saudementalemindfulness 15-Politica: ")

data_postagem = input("\nData (DD/MM/AAAA): ")
hora_postagem = input("Hora (HH:MM): ")

# =========================
# MAPAS
# =========================

modos = {
    "1": "viral",
    "2": "autoridade",
    "3": "vendas",
    "4": "storytelling"
}

nichos = {
    "1": "contabilidade",
    "2": "advocacia",
    "3": "saude",
    "4": "marketing",
    "5": "imobiliaria",
    "6": "arquiteturaedesigndeinteriores",
    "7": "diversidadeerepresentacao",
    "8": "engenharia",
    "9": "fitnessbem-estar",
    "10": "fotografiadealimentos",
    "11": "gestao_negocios",
    "12": "limpeza",
    "13": "psicologia",
    "14": "saudementalemindfulness",
    "15": "politica"
}

modo_nome = modos.get(modo_escolha, "viral")
nicho_nome = nichos.get(nicho_escolha, "marketing")

# =========================
# CARREGAR PROMPT BASEADO NA REDE
# =========================

arquivo_prompt = f"prompts/{rede}.txt"

# Lê prompt base do arquivo, que deve conter o texto robusto para geração do LinkedIn adaptado por nicho e modo
with open(arquivo_prompt, "r", encoding="utf-8") as f:
    prompt_base = f.read()

# =========================
# CONSTRUIR PROMPT FINAL PARA IA
# =========================

prompt_final = f"""
{prompt_base}

Tema do post: {tema}
Modo: {modo_nome}
Nicho: {nicho_nome}

Crie o conteúdo conforme acima, entregando um texto pronto para publicação no {rede.capitalize()}.
"""

# =========================
# CHAMADA À IA
# =========================

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": prompt_final}]
)

conteudo_ia = response.choices[0].message.content

# =========================
# FORMATAÇÃO DO CONTEÚDO (PARÁGRAFOS)
# =========================

# Garantir espaçamento profissional com linhas em branco entre parágrafos.
# Remove linhas vazias e junta parágrafos com duas quebras de linha

conteudo_formatado = "\n\n".join(
    [paragrafo.strip() for paragrafo in conteudo_ia.split("\n") if paragrafo.strip() != ""]
)

print("\n===== CONTEÚDO GERADO =====\n")
print(conteudo_formatado)

# =========================
# SALVAR NO SUPABASE (SaaS CORE)
# =========================

nome_arquivo = re.sub(r'[^a-zA-Z0-9_]', '', tema.replace(" ", "_").lower())

novo_post = {
    "user_id": user_id,
    "tema": tema,
    "rede": rede,
    "modo": modo_nome,
    "nicho": nicho_nome,
    "data": data_postagem,
    "hora": hora_postagem,
    "conteudo": conteudo_formatado,
    "arquivo": f"ai_generated/{nome_arquivo}.txt",
    "status": "pendente",
    "imagem_url": "",
    "created_at": str(datetime.now())
}

supabase.table("posts").insert(novo_post).execute()

print("\n🚀 Post salvo no SaaS (Supabase) com sucesso!")
