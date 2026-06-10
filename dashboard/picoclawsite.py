import os
import secrets
import random

from fastapi import FastAPI, Request, HTTPException
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


def salvar_conteudo(titulo: str, tipo: str, conteudo: str) -> dict:
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
#   URL:    https://seu-app.onrender.com/interno/gerar-automatico
#   Método: POST
#   Header: X-Cron-Token: <valor do CRON_SECRET no Render>
#   Horários: 09:00 / 12:00 / 15:00 (escolha o fuso)
# ─────────────────────────────────────────────
@app.post("/interno/gerar-automatico")
async def gerar_conteudo_automatico(request: Request):
    # Segurança: valida token para ninguém chamar externamente
    token = request.headers.get("X-Cron-Token", "")
    if not CRON_SECRET or not secrets.compare_digest(token, CRON_SECRET):
        raise HTTPException(status_code=401, detail="Não autorizado")

    # 1. Busca nichos TikTok do Supabase
    nichos = buscar_nichos_tiktok()

    # 2. PicoClaw sugere temas alinhados ao CoreGov
    temas = await sugerir_temas_automaticos(nichos)
    if not temas:
        return {"status": "erro", "detalhe": "PicoClaw não retornou temas válidos"}

    # 3. Gera roteiro TikTok + post LinkedIn + CTA para cada tema sugerido
    resultados = []
    for item in temas:
        tema  = item["tema"]
        nicho = item["nicho"]
        print(f"\n⏰ AUTO-GERANDO: [{nicho}] {tema}")

        # Roteiro TikTok
        try:
            r = gerar_roteiro_tiktok(tema, nicho, item["duracao"])
            if r.get("success"):
                salvar_conteudo(tema, "roteiro_tiktok", r["conteudo"])
                resultados.append({"tema": tema, "tipo": "roteiro_tiktok", "status": "ok"})
                print(f"  ✅ Roteiro TikTok salvo")
            else:
                resultados.append({"tema": tema, "tipo": "roteiro_tiktok",
                                   "status": "erro", "detalhe": r.get("erro")})
                print(f"  ❌ Roteiro TikTok falhou: {r.get('erro')}")
        except Exception as e:
            resultados.append({"tema": tema, "tipo": "roteiro_tiktok",
                               "status": "exceção", "detalhe": str(e)})

        # Post LinkedIn
        try:
            r = gerar_post(tema, "LinkedIn", "engajamento", nicho)
            if r.get("success"):
                salvar_conteudo(tema, "post", r["conteudo"])
                resultados.append({"tema": tema, "tipo": "post", "status": "ok"})
                print(f"  ✅ Post LinkedIn salvo")
            else:
                resultados.append({"tema": tema, "tipo": "post",
                                   "status": "erro", "detalhe": r.get("erro")})
                print(f"  ❌ Post LinkedIn falhou: {r.get('erro')}")
        except Exception as e:
            resultados.append({"tema": tema, "tipo": "post",
                               "status": "exceção", "detalhe": str(e)})

        # CTA
        try:
            r = gerar_cta(tema, nicho, "conversão", "site")
            if r.get("success"):
                salvar_conteudo(tema, "cta", r["conteudo"])
                resultados.append({"tema": tema, "tipo": "cta", "status": "ok"})
                print(f"  ✅ CTA salvo")
            else:
                resultados.append({"tema": tema, "tipo": "cta",
                                   "status": "erro", "detalhe": r.get("erro")})
                print(f"  ❌ CTA falhou: {r.get('erro')}")
        except Exception as e:
            resultados.append({"tema": tema, "tipo": "cta",
                               "status": "exceção", "detalhe": str(e)})

    total_ok    = sum(1 for r in resultados if r["status"] == "ok")
    total_erro  = sum(1 for r in resultados if r["status"] != "ok")
    print(f"\n✅ AUTO-GERAÇÃO CONCLUÍDA — {total_ok} ok / {total_erro} falhas")

    return {
        "status":      "concluido",
        "total_ok":    total_ok,
        "total_erro":  total_erro,
        "resultados":  resultados,
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
