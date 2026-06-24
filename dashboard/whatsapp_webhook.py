"""
📱 WhatsApp Cloud API Webhook — CoreGov Health IA
==================================================
Recebe mensagens do WhatsApp, processa com PicoClaw e responde.

Fluxo:
  Meta ──webhook(POST)──→ /webhook/whatsapp
         ↓
    PicoClaw gera resposta (laudo, agendamento, etc.)
         ↓
  Meta ──sendMessage──→ Cliente WhatsApp
"""

import os
import re
import json
import logging
from typing import Optional

import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("whatsapp-webhook")

# ─────────────────────────────────────────────
# CONFIG (via env vars)
# ─────────────────────────────────────────────
WHATSAPP_TOKEN       = os.getenv("WHATSAPP_TOKEN", "")           # Access Token da Meta
WHATSAPP_PHONE_ID    = os.getenv("WHATSAPP_PHONE_ID", "")        # Phone Number ID
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "COREGOV_HEALTH_2026")
WHATSAPP_API_VERSION  = "v22.0"
WHATSAPP_BASE_URL     = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_ID}/messages"


# ─────────────────────────────────────────────
# CHAMAR PICOCLAW (via subprocess, igual gerador_ia.py)
# ─────────────────────────────────────────────
def chamar_picoclaw(mensagem: str, timeout: int = 60) -> dict:
    """Chama PicoClaw CLI para processar a mensagem."""
    import subprocess

    picoclaw_bin = os.getenv("PICOCLAW_BIN", "/opt/render/project/src/tools/picoclaw")

    try:
        resultado = subprocess.run(
            [picoclaw_bin, "agent", "-m", mensagem],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        saida = resultado.stdout.strip()

        # Limpa artefatos do terminal
        linhas_limpas = [
            l for l in saida.split("\n")
            if l.strip()
            and "█" not in l
            and "╚" not in l
            and "╔" not in l
            and "╗" not in l
            and "╝" not in l
            and "🦞" not in l
        ]
        resposta = "\n".join(linhas_limpas).strip()
        resposta = re.sub(r"\x1b\[[0-9;]*m", "", resposta)
        resposta = re.sub(r"\[0m", "", resposta)

        if resultado.returncode != 0 or not resposta:
            return {"success": False, "conteudo": resultado.stderr.strip() or "Sem resposta"}

        return {"success": True, "conteudo": resposta}

    except subprocess.TimeoutExpired:
        return {"success": False, "conteudo": "Timeout ao processar mensagem"}
    except Exception as e:
        return {"success": False, "conteudo": str(e)}


# ─────────────────────────────────────────────
# SISTEM PROMPT → PERSONALIDADE DO AGENTE DE SAÚDE
# ─────────────────────────────────────────────
SISTEM_PROMPT = """
Você é o Agente de Saúde da CoreGov — assistente IA especializado em clínicas, 
consultórios e profissionais autônomos da saúde (médicos, dentistas, psicólogos, 
nutricionistas, fisioterapeutas).

SUAS FUNÇÕES:
1. LAUDOS E ATESTADOS — Ajude o profissional a redigir laudos, relatórios e
   atestados médicos no formato correto (CRM, CID, data, assinatura digital).
2. AGENDAMENTO INTELIGENTE — Gerencie horários, confirme consultas, reagende
   e envie lembretes automáticos.
3. PRONTUÁRIO e ANOTAÇÕES — Organize observações clínicas breves e objetivas.
4. DÚVIDAS REGULATÓRIAS — Oriente sobre ética médica, LGPD, CFM/CFO/CFN.

REGRAS:
- Mantenha tom profissional e acolhedor.
- Respostas breves e práticas (máx 300 caracteres para WhatsApp).
- Se for solicitação de laudo/atestado, peça: nome do paciente, CID, data,
  e observações clínicas.
- Se for agendamento, pergunte: nome, data desejada, horário, tipo de consulta.
- Quando completar um laudo, ofereça envio em PDF.

Cliente diz: {mensagem}
"""


def processar_mensagem(mensagem: str, remetente: str) -> str:
    """
    Processa mensagem recebida via WhatsApp usando PicoClaw.
    Retorna texto de resposta.
    """
    prompt = SISTEM_PROMPT.format(mensagem=mensagem)

    # Tenta PicoClaw; se falhar, usa fallback
    resultado = chamar_picoclaw(prompt)
    if not resultado.get("success"):
        log.warning(f"⚠️ PicoClaw falhou para {remetente}: {resultado.get('conteudo')}")
        return "Olá! 🙏 Desculpe, estou com instabilidade momentânea. Um atendente humano vai te responder em breve."

    resposta = resultado["conteudo"]

    # Limita tamanho para WhatsApp
    if len(resposta) > 300:
        resposta = resposta[:297] + "..."

    return resposta


# ─────────────────────────────────────────────
# ENVIAR MENSAGEM PARA WHATSAPP
# ─────────────────────────────────────────────
def enviar_mensagem(para: str, texto: str) -> dict:
    """
    Envia mensagem de texto via WhatsApp Cloud API.
    Retorna resposta da API.
    """
    if not WHATSAPP_TOKEN:
        log.error("❌ WHATSAPP_TOKEN não configurado")
        return {"error": "Token não configurado"}

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": para,
        "type": "text",
        "text": {"body": texto},
    }

    try:
        resp = requests.post(
            WHATSAPP_BASE_URL,
            headers=headers,
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        log.info(f"✅ Mensagem enviada para {para}")
        return resp.json()
    except requests.exceptions.RequestException as e:
        log.error(f"❌ Falha ao enviar mensagem: {e}")
        return {"error": str(e)}


# ─────────────────────────────────────────────
# WEBHOOK HANDLERS
# ─────────────────────────────────────────────

def verificar_webhook(modo: str, token: str, desafio: str) -> Optional[str]:
    """
    Meta envia GET para verificar o webhook.
    Retorna o challenge se o token estiver correto.
    """
    if modo == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        log.info("✅ Webhook verificado com sucesso!")
        return desafio
    log.warning("❌ Falha na verificação do webhook")
    return None


def processar_payload(payload: dict) -> list:
    """
    Processa payload recebido via POST do Meta.
    Extrai mensagens e responde automaticamente.
    Retorna lista de respostas enviadas.
    """
    respostas = []

    try:
        entries = payload.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])

                for msg in messages:
                    # Extrai dados da mensagem
                    remetente = msg.get("from", "")
                    msg_id = msg.get("id", "")
                    msg_tipo = msg.get("type", "")

                    # Suporte apenas a texto por enquanto
                    if msg_tipo != "text":
                        log.info(f"📝 Tipo não suportado: {msg_tipo} de {remetente}")
                        continue

                    texto = msg.get("text", {}).get("body", "")

                    if not texto.strip():
                        continue

                    log.info(f"📩 Mensagem de {remetente}: {texto[:80]}")

                    # Processa com PicoClaw
                    resposta = processar_mensagem(texto, remetente)

                    # Envia resposta
                    envio = enviar_mensagem(remetente, resposta)
                    respostas.append({
                        "de": remetente,
                        "recebido": texto,
                        "respondido": resposta,
                        "status_envio": envio,
                    })

    except Exception as e:
        log.error(f"❌ Erro processando payload: {e}")

    return respostas