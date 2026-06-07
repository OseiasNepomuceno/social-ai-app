import os
import requests

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def enviar_alerta(mensagem: str, emoji: str = "🔔") -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram não configurado — alerta não enviado")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"{emoji} *CoreGov Alertas*\n\n{mensagem}",
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"✅ Alerta Telegram enviado: {mensagem[:50]}")
            return True
        else:
            print(f"❌ Erro ao enviar Telegram: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exceção no Telegram: {str(e)}")
        return False


def alerta_ataque(ip: str, rota: str):
    enviar_alerta(
        f"🚨 *TENTATIVA DE ATAQUE*\n\nIP: `{ip}`\nRota: `{rota}`",
        emoji="🚨"
    )

def alerta_rate_limit(ip: str, rota: str):
    enviar_alerta(
        f"⚠️ *RATE LIMIT ATINGIDO*\n\nIP: `{ip}`\nRota: `{rota}`",
        emoji="⚠️"
    )

def alerta_picoclaw_falhou(erro: str):
    enviar_alerta(
        f"❌ *PICOCLAW FALHOU*\n\nErro: `{erro}`\nFallback: ia\\_engine ativado",
        emoji="❌"
    )

def alerta_pagamento_aprovado(user_id: str):
    enviar_alerta(
        f"💳 *PAGAMENTO APROVADO*\n\nUsuário: `{user_id}`\nPlano PRO ativado!",
        emoji="💳"
    )

def alerta_erro_critico(rota: str, erro: str):
    enviar_alerta(
        f"🔴 *ERRO CRÍTICO*\n\nRota: `{rota}`\nErro: `{erro[:200]}`",
        emoji="🔴"
    )
