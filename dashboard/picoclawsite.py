from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from supabase import create_client
import os
import schedule
import time
import threading

from picoclaw_agent import (
    gerar_post,
    gerar_roteiro_tiktok,
    gerar_cta,
    gerar_ebook,
    gerar_infografico,
    gerar_template,
    inferir_nicho,
)

# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="PicoClawSite — Gerador de Conteúdo")
templates = Jinja2Templates(directory="templates")

# ─────────────────────────────────────────────
# NICHOS DISPONÍVEIS
# ─────────────────────────────────────────────
NICHOS = [
    "Gestão Pública",
    "Tecnologia",
    "Saúde",
    "Educação",
    "Empreendedorismo",
    "Marketing Digital",
    "Direito",
    "Finanças",
    "Sustentabilidade",
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
    publico_alvo: str = "gestores públicos"
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
# HELPER: salvar no Supabase
# ─────────────────────────────────────────────
def salvar_conteudo(titulo: str, tipo: str, conteudo: str, status: str = "rascunho") -> dict:
    try:
        response = supabase.table("conteudos").insert({
            "titulo": titulo,
            "tipo": tipo,
            "conteudo": conteudo,
            "status": status,
        }).execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"❌ Erro ao salvar no Supabase: {e}")
        return {}

# ─────────────────────────────────────────────
# ROTAS HTML (listagem)
# ─────────────────────────────────────────────
@app.get("/posts", response_class=HTMLResponse)
def listar_posts(request: Request):
    response = supabase.table("conteudos").select("*").eq("tipo", "post").eq("status", "publicado").execute()
    return templates.TemplateResponse("posts.html", {"request": request, "posts": response.data})

@app.get("/roteiros-tiktok", response_class=HTMLResponse)
def listar_roteiros(request: Request):
    response = supabase.table("conteudos").select("*").eq("tipo", "roteiro_tiktok").eq("status", "publicado").execute()
    return templates.TemplateResponse("roteiros.html", {"request": request, "roteiros": response.data})

@app.get("/ctas", response_class=HTMLResponse)
def listar_ctas(request: Request):
    response = supabase.table("conteudos").select("*").eq("tipo", "cta").eq("status", "publicado").execute()
    return templates.TemplateResponse("ctas.html", {"request": request, "ctas": response.data})

@app.get("/e-books", response_class=HTMLResponse)
def listar_ebooks(request: Request):
    response = supabase.table("conteudos").select("*").eq("tipo", "ebook").eq("status", "publicado").execute()
    return templates.TemplateResponse("e-books.html", {"request": request, "ebooks": response.data})

@app.get("/infograficos", response_class=HTMLResponse)
def listar_infograficos(request: Request):
    response = supabase.table("conteudos").select("*").eq("tipo", "infografico").eq("status", "publicado").execute()
    return templates.TemplateResponse("infografico.html", {"request": request, "infograficos": response.data})

# ─────────────────────────────────────────────
# ROTAS DE GERAÇÃO (POST → DeepSeek → Supabase)
# ─────────────────────────────────────────────
@app.post("/gerar/post")
def endpoint_gerar_post(body: PostRequest):
    nicho = body.nicho or inferir_nicho(body.tema, NICHOS)
    resultado = gerar_post(body.tema, body.rede, body.modo, nicho)

    if not resultado.get("success"):
        raise HTTPException(status_code=500, detail=resultado.get("erro"))

    salvo = salvar_conteudo(body.tema, "post", resultado["conteudo"])
    return {"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo}


@app.post("/gerar/roteiro-tiktok")
def endpoint_gerar_roteiro(body: RoteiroRequest):
    nicho = body.nicho or inferir_nicho(body.tema, NICHOS)
    resultado = gerar_roteiro_tiktok(body.tema, nicho, body.duracao)

    if not resultado.get("success"):
        raise HTTPException(status_code=500, detail=resultado.get("erro"))

    salvo = salvar_conteudo(body.tema, "roteiro_tiktok", resultado["conteudo"])
    return {"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo}


@app.post("/gerar/cta")
def endpoint_gerar_cta(body: CTARequest):
    nicho = body.nicho or inferir_nicho(body.tema, NICHOS)
    resultado = gerar_cta(body.tema, nicho, body.objetivo, body.canal)

    if not resultado.get("success"):
        raise HTTPException(status_code=500, detail=resultado.get("erro"))

    salvo = salvar_conteudo(body.tema, "cta", resultado["conteudo"])
    return {"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo}


@app.post("/gerar/ebook")
def endpoint_gerar_ebook(body: EbookRequest):
    nicho = body.nicho or inferir_nicho(body.tema, NICHOS)
    resultado = gerar_ebook(body.tema, nicho, body.publico_alvo, body.num_capitulos)

    if not resultado.get("success"):
        raise HTTPException(status_code=500, detail=resultado.get("erro"))

    salvo = salvar_conteudo(body.tema, "ebook", resultado["conteudo"])
    return {"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo}


@app.post("/gerar/infografico")
def endpoint_gerar_infografico(body: InfograficRequest):
    nicho = body.nicho or inferir_nicho(body.tema, NICHOS)
    resultado = gerar_infografico(body.tema, nicho, body.formato)

    if not resultado.get("success"):
        raise HTTPException(status_code=500, detail=resultado.get("erro"))

    salvo = salvar_conteudo(body.tema, "infografico", resultado["conteudo"])
    return {"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo}


@app.post("/gerar/template")
def endpoint_gerar_template(body: TemplateRequest):
    nicho = body.nicho or inferir_nicho(body.tema, NICHOS)
    resultado = gerar_template(body.tipo, nicho, body.tema)

    if not resultado.get("success"):
        raise HTTPException(status_code=500, detail=resultado.get("erro"))

    salvo = salvar_conteudo(body.tema, "template", resultado["conteudo"])
    return {"status": "ok", "nicho": nicho, "conteudo": resultado["conteudo"], "salvo": salvo}


# ─────────────────────────────────────────────
# ROTA DE STATUS
# ─────────────────────────────────────────────
@app.get("/status")
def status():
    return {"status": "online", "modelo": "deepseek-v4-flash", "nichos": NICHOS}


# ─────────────────────────────────────────────
# SCHEDULER AUTOMÁTICO
# ─────────────────────────────────────────────
TEMAS_AUTOMATICOS = [
    "Transparência na gestão pública municipal",
    "Como usar tecnologia para melhorar serviços públicos",
    "Gestão de equipes no setor público",
    "Licitações: erros mais comuns e como evitar",
    "Inovação em prefeituras pequenas",
]

_tema_index = 0

def job_gerar_conteudo_automatico():
    """Gera roteiro TikTok + post automaticamente no horário agendado."""
    global _tema_index
    tema = TEMAS_AUTOMATICOS[_tema_index % len(TEMAS_AUTOMATICOS)]
    _tema_index += 1

    nicho = inferir_nicho(tema, NICHOS)
    print(f"\n⏰ SCHEDULER — tema: '{tema}' | nicho: '{nicho}'")

    # Roteiro TikTok
    r_tiktok = gerar_roteiro_tiktok(tema, nicho)
    if r_tiktok.get("success"):
        salvar_conteudo(tema, "roteiro_tiktok", r_tiktok["conteudo"])
        print(f"✅ Roteiro TikTok salvo: {tema}")
    else:
        print(f"❌ Falha roteiro TikTok: {r_tiktok.get('erro')}")

    # Post LinkedIn
    r_post = gerar_post(tema, "LinkedIn", "engajamento", nicho)
    if r_post.get("success"):
        salvar_conteudo(tema, "post", r_post["conteudo"])
        print(f"✅ Post LinkedIn salvo: {tema}")
    else:
        print(f"❌ Falha post: {r_post.get('erro')}")


def job_scheduler():
    schedule.every().day.at("09:00").do(job_gerar_conteudo_automatico)
    schedule.every().day.at("12:00").do(job_gerar_conteudo_automatico)
    schedule.every().day.at("15:00").do(job_gerar_conteudo_automatico)
    while True:
        schedule.run_pending()
        time.sleep(60)


# Inicia o scheduler em thread separada
threading.Thread(target=job_scheduler, daemon=True).start()
