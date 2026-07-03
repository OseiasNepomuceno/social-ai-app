import os
import secrets
import random
import asyncio
import logging

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from supabase import create_client

from picoclaw_agent import (
    gerar_post,
    gerar_roteiro_tiktok,
    gerar_cta,
    gerar_ebook,
    gerar_infografico,
    gerar_template,
    inferir_nicho,
    chamar_picoclaw,
)
from whatsapp_webhook import (
    verificar_webhook,
    processar_payload,
    enviar_mensagem,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("picoclawsite")


# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────
SUPABASE_URL  = os.getenv("SUPABASE_URL")
SUPABASE_KEY  = os.getenv("SUPABASE_KEY")
CRON_SECRET   = os.getenv("CRON_SECRET", "")

supabase  = create_client(SUPABASE_URL, SUPABASE_KEY)
app       = FastAPI(title="PicoClawSite — Gerador de Conteúdo CoreGov")
templates = Jinja2Templates(directory="templates")

# ─────────────────────────────────────────────
# NICHOS — fallback local caso o Supabase falhe
# ─────────────────────────────────────────────
NICHOS_FALLBACK = [
    "Automação",
    "Dados",
    "Gestão",
    "Fiscal",
    "Produtividade",
    "Tecnologia",
    "Empreendedorismo",
    "Marketing Digital",
    "Finanças",
    "Recursos Humanos",
]

# ─────────────────────────────────────────────
# SCHEMAS (Pydantic)
# ─────────────────────────────────────────────
class PostRequest(BaseModel):
    tema: str
    rede: str = "LinkedIn"
    modo: str = "engajamento"
    nicho: str = ""

class RoteiroRequest(BaseModel):
    tema: str
    nicho: str = ""
    duracao: int = 60

class CTARequest(BaseModel):
    tema: str
    nicho: str = ""
    objetivo: str = "conversão"
    canal: str = "site"

class EbookRequest(BaseModel):
    tema: str
    nicho: str = ""
    publico_alvo: str = "gestores e empresários"
    num_capitulos: int = 5

class InfograficRequest(BaseModel):
    tema: str
    nicho: str = ""
    formato: str = "lista"

class TemplateRequest(BaseModel):
    tipo: str = "post"
    nicho: str = ""
    tema: str


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def buscar_nichos_tiktok() -> list:
    """Busca nichos da tabela nichos_tiktok no Supabase (apenas ativos)."""
    try:
        response = (
            supabase.table("nichos_tiktok")
            .select("nicho")
            .eq("ativo", True)
            .execute()
        )
        nichos = [row["nicho"] for row in response.data if row.get("nicho")]
        if nichos:
            return nichos
        print("⚠️ Nenhum nicho TikTok encontrado no Supabase — usando fallback")
        return NICHOS_FALLBACK
    except Exception as e:
        print(f"❌ ERRO ao buscar nichos TikTok: {e} — usando fallback")
        return NICHOS_FALLBACK


def salvar_conteudo(titulo: str, tipo: str, conteudo: str, categoria: str = "gratuito") -> dict:
    """Salva conteúdo diretamente como publicado — fluxo 100% automático."""
    try:
        if not conteudo or len(conteudo.strip()) < 50:
            print(f"⚠️ Conteúdo muito curto para '{titulo}' — descartado")
            return {}
        response = supabase.table("conteudos").insert({
            "titulo":   titulo,
            "tipo":     tipo,
            "conteudo": conteudo.strip(),
            "status":   "publicado",
            "categoria": categoria,
        }).execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"❌ Erro ao salvar no Supabase: {e}")
        return {}


async def sugerir_temas_automaticos(nichos: list) -> list:
    """PicoClaw sugere temas aleatórios alinhados ao contexto CoreGov."""
    nichos_sorteados = random.sample(nichos, min(3, len(nichos)))

    prompt = f"""Você é um especialista em conteúdo para redes sociais voltado ao mercado empresarial e de gestão.

O CoreGov é uma plataforma de consultoria e automação para empresas privadas, com foco em:
- Automação inteligente com Python e IA
- Tratamento e análise de dados empresariais
- Otimização de processos fiscais e administrativos
- Redução de erros manuais e aumento de produtividade
- Estratégia de gestão orientada a dados
- Transformação digital para crescimento e inovação

Público-alvo: gestores, empresários e decisores que querem eliminar gargalos
operacionais e transformar dados complexos em decisões lucrativas.

Com base nos nichos abaixo, sugira 1 tema criativo e relevante para um vídeo TikTok
para CADA nicho. Os temas devem educar, gerar valor real e despertar interesse
em empresários e gestores que ainda não automatizaram seus processos.

Nichos: {', '.join(nichos_sorteados)}

Responda APENAS neste formato exato, uma linha por nicho:
NICHO: tema sugerido"""

    resultado = chamar_picoclaw(prompt, timeout=60)
    if not resultado.get("success"):
        print(f"❌ PicoClaw não retornou temas: {resultado.get('erro')}")
        return []

    temas = []
    for linha in resultado["conteudo"].split('\n'):
        if ':' in linha:
            partes = linha.split(':', 1)
            nicho = partes[0].strip()
            tema  = partes[1].strip()
            if nicho and tema:
                temas.append({"tema": tema, "nicho": nicho, "duracao": 60})

    print(f"✅ PicoClaw sugeriu {len(temas)} temas: {[t['tema'] for t in temas]}")
    return temas


# ─────────────────────────────────────────────
# ROTAS HTML (listagem)
# ─────────────────────────────────────────────
@app.get("/posts", response_class=HTMLResponse)
def listar_posts(request: Request):
    response = (
        supabase.table("conteudos")
        .select("*")
        .eq("tipo", "post")
        .eq("status", "publicado")
        .execute()
    )
    return templates.TemplateResponse("posts.html", {
        "request": request, "posts": response.data
    })

@app.get("/roteiros-tiktok", response_class=HTMLResponse)
def listar_roteiros(request: Request):
    response = (
        supabase.table("conteudos")
        .select("*")
        .eq("tipo", "roteiro_tiktok")
        .eq("status", "publicado")
        .execute()
    )
    return templates.TemplateResponse("roteiros.html", {
        "request": request, "roteiros": response.data
    })

@app.get("/ctas", response_class=HTMLResponse)
def listar_ctas(request: Request):
    response = (
        supabase.table("conteudos")
        .select("*")
        .eq("tipo", "cta")
        .eq("status", "publicado")
        .execute()
    )
    return templates.TemplateResponse("ctas.html", {
        "request": request, "ctas": response.data
    })

@app.get("/e-books", response_class=HTMLResponse)
def listar_ebooks(request: Request):
    response = (
        supabase.table("conteudos")
        .select("*")
        .eq("tipo", "ebook")
        .eq("status", "publicado")
        .execute()
    )
    return templates.TemplateResponse("e-books.html", {
        "request": request, "ebooks": response.data
    })

@app.get("/infograficos", response_class=HTMLResponse)
def listar_infograficos(request: Request):
    response = (
        supabase.table("conteudos")
        .select("*")
        .eq("tipo", "infografico")
        .eq("status", "publicado")
        .execute()
    )
    return templates.TemplateResponse("infografico.html", {
        "request": request, "infograficos": response.data
    })


# ─────────────────────────────────────────────
# ROTAS DE GERAÇÃO MANUAL (POST → PicoClaw → Supabase)
# ─────────────────────────────────────────────
@app.post("/gerar/post")
def endpoint_gerar_post(body: PostRequest):
    nicho = body.nicho or inferir_nicho(body.tema, NICHOS_FALLBACK)
    resultado = gerar_post(body.tema, body.rede, body.modo, nicho)
    if not resultado.get("success"):
        raise HTTPException(status_code=500, detail=resultado.get("erro"))
    salvo = salvar_conteudo(body.tema, "post", resultado["conteudo"])
    if not salvo:
        print(f"⚠️ Post gerado mas NÃO salvo — tema: {body.tema}")
    return {"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo}

@app.post("/gerar/roteiro-tiktok")
def endpoint_gerar_roteiro(body: RoteiroRequest):
    nicho = body.nicho or inferir_nicho(body.tema, NICHOS_FALLBACK)
    resultado = gerar_roteiro_tiktok(body.tema, nicho, body.duracao)
    if not resultado.get("success"):
        raise HTTPException(status_code=500, detail=resultado.get("erro"))
    salvo = salvar_conteudo(body.tema, "roteiro_tiktok", resultado["conteudo"])
    if not salvo:
        print(f"⚠️ Roteiro gerado mas NÃO salvo — tema: {body.tema}")
    return {"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo}

@app.post("/gerar/cta")
def endpoint_gerar_cta(body: CTARequest):
    nicho = body.nicho or inferir_nicho(body.tema, NICHOS_FALLBACK)
    resultado = gerar_cta(body.tema, nicho, body.objetivo, body.canal)
    if not resultado.get("success"):
        raise HTTPException(status_code=500, detail=resultado.get("erro"))
    salvo = salvar_conteudo(body.tema, "cta", resultado["conteudo"])
    if not salvo:
        print(f"⚠️ CTA gerado mas NÃO salvo — tema: {body.tema}")
    return {"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo}

@app.post("/gerar/ebook")
def endpoint_gerar_ebook(body: EbookRequest):
    nicho = body.nicho or inferir_nicho(body.tema, NICHOS_FALLBACK)
    resultado = gerar_ebook(body.tema, nicho, body.publico_alvo, body.num_capitulos)
    if not resultado.get("success"):
        raise HTTPException(status_code=500, detail=resultado.get("erro"))
    salvo = salvar_conteudo(body.tema, "ebook", resultado["conteudo"])
    if not salvo:
        print(f"⚠️ E-book gerado mas NÃO salvo — tema: {body.tema}")
    return {"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo}

@app.post("/gerar/infografico")
def endpoint_gerar_infografico(body: InfograficRequest):
    nicho = body.nicho or inferir_nicho(body.tema, NICHOS_FALLBACK)
    resultado = gerar_infografico(body.tema, nicho, body.formato)
    if not resultado.get("success"):
        raise HTTPException(status_code=500, detail=resultado.get("erro"))
    salvo = salvar_conteudo(body.tema, "infografico", resultado["conteudo"])
    if not salvo:
        print(f"⚠️ Infográfico gerado mas NÃO salvo — tema: {body.tema}")
    return {"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo}

@app.post("/gerar/template")
def endpoint_gerar_template(body: TemplateRequest):
    nicho = body.nicho or inferir_nicho(body.tema, NICHOS_FALLBACK)
    resultado = gerar_template(body.tipo, nicho, body.tema)
    if not resultado.get("success"):
        raise HTTPException(status_code=500, detail=resultado.get("erro"))
    salvo = salvar_conteudo(body.tema, "template", resultado["conteudo"])
    if not salvo:
        print(f"⚠️ Template gerado mas NÃO salvo — tema: {body.tema}")
    return {"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo}


# ─────────────────────────────────────────────
# ROTA DE GERAÇÃO AUTOMÁTICA — acionada pelo cron-job.org
#
# Configure no cron-job.org:
#   URL:     https://app.coregov.com.br/interno/gerar-automatico
#   Método:  POST
#   Header:  X-Cron-Token: <valor do CRON_SECRET no Render>
#   Crontab: 0 9,12,15 * * *  (9h, 12h, 15h — America/Sao_Paulo)
#   Timeout: 30s (responde imediato — processamento ocorre em background)
# ─────────────────────────────────────────────
async def _processar_conteudo_background(nichos: list):
    """Tarefa em background — executa após o endpoint já ter respondido 202."""
    print("\n🔄 BACKGROUND — iniciando geração automática de conteúdo")

    # 1. PicoClaw sugere temas alinhados ao CoreGov
    temas = await sugerir_temas_automaticos(nichos)
    if not temas:
        print("❌ BACKGROUND — PicoClaw não retornou temas válidos")
        return

    # 2. Gera roteiro TikTok + post LinkedIn + CTA para cada tema sugerido
    total_ok   = 0
    total_erro = 0

    for item in temas:
        tema  = item["tema"]
        nicho = item["nicho"]
        print(f"\n⏰ BACKGROUND AUTO-GERANDO: [{nicho}] {tema}")

        # Roteiro TikTok
        try:
            r = gerar_roteiro_tiktok(tema, nicho, item["duracao"])
            if r.get("success"):
                salvar_conteudo(tema, "roteiro_tiktok", r["conteudo"])
                total_ok += 1
                print(f"  ✅ Roteiro TikTok salvo")
            else:
                total_erro += 1
                print(f"  ❌ Roteiro TikTok falhou: {r.get('erro')}")
        except Exception as e:
            total_erro += 1
            print(f"  ❌ Roteiro TikTok exceção: {e}")

        # Post LinkedIn
        try:
            r = gerar_post(tema, "LinkedIn", "engajamento", nicho)
            if r.get("success"):
                salvar_conteudo(tema, "post", r["conteudo"])
                total_ok += 1
                print(f"  ✅ Post LinkedIn salvo")
            else:
                total_erro += 1
                print(f"  ❌ Post LinkedIn falhou: {r.get('erro')}")
        except Exception as e:
            total_erro += 1
            print(f"  ❌ Post LinkedIn exceção: {e}")

        # CTA
        try:
            r = gerar_cta(tema, nicho, "conversão", "site")
            if r.get("success"):
                salvar_conteudo(tema, "cta", r["conteudo"])
                total_ok += 1
                print(f"  ✅ CTA salvo")
            else:
                total_erro += 1
                print(f"  ❌ CTA falhou: {r.get('erro')}")
        except Exception as e:
            total_erro += 1
            print(f"  ❌ CTA exceção: {e}")

    print(f"\n✅ BACKGROUND CONCLUÍDO — {total_ok} ok / {total_erro} falhas")


@app.post("/interno/gerar-automatico", status_code=202)
async def gerar_conteudo_automatico(request: Request, background_tasks: BackgroundTasks):
    """
    Responde imediatamente 202 Accepted ao cron-job.org.
    O processamento real (PicoClaw → Supabase) ocorre em background,
    sem risco de timeout nos 30s do plano gratuito do cron-job.org.
    """
    # Segurança: valida token para ninguém chamar externamente
    token = request.headers.get("X-Cron-Token", "")
    if not CRON_SECRET or not secrets.compare_digest(token, CRON_SECRET):
        raise HTTPException(status_code=401, detail="Não autorizado")

    # Busca nichos antes de soltar o background (falha rápida se Supabase estiver fora)
    nichos = buscar_nichos_tiktok()

    # Agenda o processamento em background e responde imediatamente
    background_tasks.add_task(_processar_conteudo_background, nichos)

    print("✅ /interno/gerar-automatico — 202 enviado, background iniciado")
    return {
        "status":   "aceito",
        "mensagem": "Geração iniciada em background",
        "nichos":   len(nichos),
    }


# ─────────────────────────────────────────────
# WEBHOOK WHATSAPP — Health IA Agent
# ─────────────────────────────────────────────
@app.get("/webhook/whatsapp")
def whatsapp_webhook_verificar(request: Request):
    """
    Meta envia GET para verificar o webhook.
    Parâmetros: hub.mode, hub.verify_token, hub.challenge
    """
    modo     = request.query_params.get("hub.mode", "")
    token    = request.query_params.get("hub.verify_token", "")
    desafio  = request.query_params.get("hub.challenge", "")

    resultado = verificar_webhook(modo, token, desafio)
    if resultado:
        return int(resultado)  # Meta espera o challenge como texto puro

    raise HTTPException(status_code=403, detail="Token de verificação inválido")


@app.post("/webhook/whatsapp")
async def whatsapp_webhook_receber(payload: dict, background_tasks: BackgroundTasks):
    """
    Meta envia POST com as mensagens recebidas.
    Processa em background para não travar o webhook.
    """
    log.info("📩 Webhook WhatsApp acionado")
    background_tasks.add_task(processar_payload, payload)
    return {"status": "ok"}


@app.get("/webhook/whatsapp/status")
def whatsapp_status():
    """Status da integração WhatsApp."""
    token_configurado = bool(os.getenv("WHATSAPP_TOKEN", ""))
    phone_configurado = bool(os.getenv("WHATSAPP_PHONE_ID", ""))
    return {
        "whatsapp_api": "configurado" if (token_configurado and phone_configurado) else "pendente",
        "token": "✅" if token_configurado else "❌",
        "phone_id": "✅" if phone_configurado else "❌",
        "verify_token": os.getenv("WHATSAPP_VERIFY_TOKEN", "COREGOV_HEALTH_2026"),
    }


# ─────────────────────────────────────────────
# ROTA DE STATUS
# ─────────────────────────────────────────────
@app.get("/status")
def status():
    nichos = buscar_nichos_tiktok()
    return {
        "status":          "online",
        "modelo":          "picoclaw",
        "nichos_tiktok":   nichos,
        "total_nichos":    len(nichos),
        "automatico":      "via cron-job.org → /interno/gerar-automatico",
    }
