from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from supabase import create_client
import os
import schedule
import time
import threading
import requests

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

# Função para gerar roteiro TikTok
def gerar_roteiro_tiktok(tema: str):
    # Aqui você chama o Picoclaw (pode ser API ou função interna)
    roteiro = f"Roteiro TikTok sobre {tema}: introdução rápida, 3 dicas, CTA final."
    
    # Salva no Supabase
    supabase.table("conteudos").insert({
        "titulo": tema,
        "tipo": "roteiro_tiktok",
        "conteudo": roteiro,
        "status": "rascunho"
    }).execute()
    
    print(f"Roteiro gerado e salvo: {tema}")
    return roteiro

# CTAs
@app.get("/ctas", response_class=HTMLResponse)
def listar_ctas(request: Request):
    response = supabase.table("conteudos").select("*").eq("tipo", "cta").eq("status", "publicado").execute()
    return templates.TemplateResponse("ctas.html", {"request": request, "ctas": response.data})

# E-books
@app.get("/e-books", response_class=HTMLResponse)
def listar_ebooks(request: Request):
    response = supabase.table("conteudos").select("*").eq("tipo", "ebook").eq("status", "publicado").execute()
    return templates.TemplateResponse("e-books.html", {"request": request, "ebooks": response.data})

# Infográficos
@app.get("/infografico", response_class=HTMLResponse)
def listar_infograficos(request: Request):
    response = supabase.table("conteudos").select("*").eq("tipo", "infografico").eq("status", "publicado").execute()
    return templates.TemplateResponse("infografico.html", {"request": request, "infograficos": response.data})

# Posts
@app.get("/posts", response_class=HTMLResponse)
def listar_posts(request: Request):
    response = supabase.table("conteudos").select("*").eq("tipo", "post").eq("status", "publicado").execute()
    return templates.TemplateResponse("posts.html", {"request": request, "posts": response.data})



@app.get("/roteiros-tiktok")
def listar_roteiros():
    # Busca todos os roteiros publicados no Supabase
    response = supabase.table("conteudos") \
        .select("*") \
        .eq("tipo", "roteiro_tiktok") \
        .eq("status", "publicado") \
        .execute()
    
    roteiros = response.data
    return {"roteiros": roteiros}


# Endpoint manual (se quiser chamar via API)
@app.post("/gerar-roteiro-tiktok")
def gerar_roteiro_endpoint(tema: str):
    roteiro = gerar_roteiro_tiktok(tema)
    return {"status": "ok", "roteiro": roteiro}

# Scheduler para rodar automaticamente
def job_scheduler():
    schedule.every().day.at("09:00").do(gerar_roteiro_tiktok, tema="Automação às 9h")
    schedule.every().day.at("12:00").do(gerar_roteiro_tiktok, tema="Automação às 12h")
    schedule.every().day.at("15:00").do(gerar_roteiro_tiktok, tema="Automação às 15h")

    while True:
        schedule.run_pending()
        time.sleep(60)

# Thread para rodar o scheduler junto com FastAPI
threading.Thread(target=job_scheduler, daemon=True).start()
