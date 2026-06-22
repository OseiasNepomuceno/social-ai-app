import json
import subprocess
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
# PICOCLAW
# =========================

PICOCLAW_BIN = os.getenv("PICOCLAW_BIN", "/opt/render/project/src/tools/picoclaw")

def chamar_picoclaw(mensagem: str, timeout: int = 120) -> dict:
    """Envia prompt ao PicoClaw e retorna conteúdo limpo."""
    print(f"🦞 PicoClaw acionado — {len(mensagem)} chars no prompt")
    try:
        resultado = subprocess.run(
            [PICOCLAW_BIN, 'agent', '-m', mensagem],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        saida = resultado.stdout.strip()

        # Remove linhas de UI do terminal (bordas, ícones, progresso)
        linhas = saida.split('\n')
        linhas_limpas = [
            l for l in linhas
            if l.strip()
            and '█' not in l
            and '╚' not in l
            and '╔' not in l
            and '╗' not in l
            and '╝' not in l
            and '🦞' not in l
            and not l.startswith('0')
        ]
        resposta = '\n'.join(linhas_limpas).strip()

        # Remove códigos ANSI de cor/formatação
        resposta = re.sub(r'\x1b\[[0-9;]*m', '', resposta)
        resposta = re.sub(r'\[0m', '', resposta)

        # Remove markdown desnecessário
        resposta = re.sub(r'\*\*(.*?)\*\*', r'\1', resposta)
        resposta = re.sub(r'\*(.*?)\*', r'\1', resposta)

        # Garante parágrafos separados por linha em branco
        resposta = '\n\n'.join(
            p.strip() for p in resposta.split('\n') if p.strip()
        )

        if resultado.returncode != 0 or not resposta:
            print(f"❌ PicoClaw erro: {resultado.stderr.strip()}")
            return {"success": False, "conteudo": resultado.stderr.strip() or "Sem resposta"}

        print(f"✅ PicoClaw respondeu: {len(resposta)} caracteres")
        return {"success": True, "conteudo": resposta}

    except subprocess.TimeoutExpired:
        print("⏱️ PicoClaw timeout")
        return {"success": False, "conteudo": "Timeout"}
    except Exception as e:
        print(f"❌ PicoClaw exceção: {str(e)}")
        return {"success": False, "conteudo": str(e)}

print("🚀 Sistema IA SaaS com PicoClaw iniciado 🦞")

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

# Lê prompt base do arquivo
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
# CHAMADA AO PICOCLAW
# =========================

print("\n🦞 Gerando conteúdo com PicoClaw...")
resultado = chamar_picoclaw(prompt_final, timeout=120)

if not resultado.get("success"):
    print(f"\n❌ Erro na geração: {resultado.get('conteudo', 'Desconhecido')}")
    exit(1)

conteudo_ia = resultado["conteudo"]

# =========================
# FORMATAÇÃO DO CONTEÚDO (PARÁGRAFOS)
# =========================

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
