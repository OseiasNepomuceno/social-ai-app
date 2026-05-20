from flask import (
    Flask,
    render_template,
    redirect,
    request,
    session,
    url_for
)

import os
import mercadopago

from supabase import create_client
from services.supabase_storage import upload_image
from dashboard.image_agent import gerar_imagem

from dashboard.ia_engine import (
    gerar_conteudo
)

# =========================
# FLASK
# =========================

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates"
)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "social_ai_secret"
)

# =========================
# SUPABASE
# =========================

SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY"
)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# =========================
# MERCADO PAGO
# =========================

MERCADO_PAGO_TOKEN = os.getenv(
    "MERCADO_PAGO_TOKEN"
)

mp = (
    mercadopago.SDK(MERCADO_PAGO_TOKEN)
    if MERCADO_PAGO_TOKEN
    else None
)

# =========================
# PLANOS
# =========================

PLANOS = {

    "free": {

        "nome": "Free",

        "preco": 0,

        "limite": 10

    },

    "pro": {

        "nome": "Pro",

        "preco": 49.90,

        "limite": 999999

    }

}

# =========================
# HOME
# =========================

@app.route("/")
def home():

    if "user_id" not in session:
        return redirect("/login")

    try:

        posts = supabase.table(
            "posts"
        ).select("*").eq(
            "user_id",
            session["user_id"]
        ).order(
            "id",
            desc=True
        ).limit(6).execute().data

        total_posts = len(posts)

        executados = len([
            p for p in posts
            if p["status"] == "executado"
        ])

        pendentes = len([
            p for p in posts
            if p["status"] == "pendente"
        ])

        erros = len([
            p for p in posts
            if p["status"] == "erro"
        ])

        return render_template(

            "index.html",

            posts=posts,

            total_posts=total_posts,

            executados=executados,

            pendentes=pendentes,

            erros=erros

        )

    except Exception as e:

        print("HOME ERROR:")

        print(str(e))

        return str(e)

# =========================
# LOGIN
# =========================

@app.route(
    "/login",
    methods=["GET", "POST"]
)

def login():

    if request.method == "POST":

        email = request.form["email"]

        senha = request.form["senha"]

        try:

            resposta = (
                supabase.auth
                .sign_in_with_password({

                    "email": email,

                    "password": senha

                })
            )

            user = resposta.user

            session["user_id"] = user.id

            session["email"] = user.email

            supabase.table("users").upsert({

                "id": user.id,

                "email": user.email,

                "plano": "free",

                "posts_limite": 10,

                "posts_usados": 0

            }).execute()

            return redirect("/")

        except Exception as e:

            print("LOGIN ERROR:")

            print(str(e))

            return render_template(

                "login.html",

                erro="Login inválido"

            )

    return render_template(
        "login.html"
    )

# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.pop(
        "user_id",
        None
    )

    session.pop(
        "email",
        None
    )

    return redirect("/login")

# =========================
# IA
# =========================

@app.route(
    "/ia",
    methods=["GET", "POST"]
)

def ia():

    if "user_id" not in session:
        return redirect("/login")

if request.method == "POST":

    try:
            tema = request.form["tema"]

            rede = request.form["rede"]

            modo = request.form["modo"]

            nicho = request.form["nicho"]

            data_postagem = request.form["data"]

            hora_postagem = request.form["hora"]

            # =========================
            # IMAGEM
            # =========================

            imagem_url = None
        
            # =========================
            # UPLOAD MANUAL
            # =========================
            
            if "image" in request.files:
            
                file = request.files["image"]
            
                if file.filename != "":
            
                    print("🖼️ Upload manual detectado")
            
                    upload_result = upload_image(file)
            
                    if upload_result["success"]:
            
                        imagem_url = upload_result["public_url"]
    
            # =========================
            # FAL AI AUTOMÁTICO
            # =========================
            
            if not imagem_url:
            
                print("🤖 Gerando imagem com FAL AI")
            
                imagem_url = gerar_imagem(tema)
            
            # =========================
            # GERAR CONTEÚDO
            # =========================            
            
           resultado = gerar_conteudo(
               tema,
            
               rede,
            
               modo,
            
              nicho
            
        ) 
                            
        if not resultado["success"]:
            
            return render_template(
            
                "ia.html",
            
                erro=resultado["erro"]
            
          )
            
      conteudo = resultado["conteudo"]      


      # =========================
      # SALVAR POST
      # =========================
             

       supabase.table(
           "posts"
       ).insert({
            
      "tema": tema,
            
                            "rede": rede,
            
                            "conteudo": conteudo,
            
                            "modo": resultado["modo"],
            
                            "nicho": resultado["nicho"],
            
                            "imagem_url": imagem_url,
            
                            "data_postagem": data_postagem,
            
                            "hora_postagem": hora_postagem,
            
                            "status": "pendente",
            
                            "user_id": session["user_id"]                      
            
                        }).execute()                
                       
            
                        return render_template(
            
                            "ia.html",
            
                            sucesso=True,
            
                            conteudo=conteudo
            
                        )
            
                    except Exception as e:
            
                        print("ERRO IA:")
            
                        print(str(e))
            
                        return render_template(
            
                            "ia.html",
            
                            erro=str(e)
        
# =========================
# AGENDAMENTOS
# =========================

@app.route("/agendamentos")
def agendamentos():

    if "user_id" not in session:
        return redirect("/login")

    try:

        posts = supabase.table(
            "posts"
        ).select("*").eq(
            "user_id",
            session["user_id"]
        ).order(
            "id",
            desc=True
        ).execute().data

        return render_template(

            "agendamentos.html",

            posts=posts

        )

    except Exception as e:

        return render_template(

            "agendamentos.html",

            erro=str(e),

            posts=[]

        )

# =========================
# UPLOAD
# =========================

@app.route("/upload", methods=["POST"])
def upload():

    if "image" not in request.files:

        return {
            "success": False,
            "error": "Nenhuma imagem enviada"
        }, 400

    file = request.files["image"]

    result = upload_image(file)

    if not result["success"]:

        return result, 400

    return result


# =========================
# PUBLICAÇÕES
# =========================

@app.route("/publicacoes")
def publicacoes():

    if "user_id" not in session:
        return redirect("/login")

    try:

        posts = supabase.table(
            "posts"
        ).select("*").eq(
            "user_id",
            session["user_id"]
        ).eq(
            "status",
            "executado"
        ).order(
            "id",
            desc=True
        ).execute().data

        return render_template(

            "publicacoes.html",

            posts=posts

        )

    except Exception as e:

        return render_template(

            "publicacoes.html",

            erro=str(e),

            posts=[]

        )

# =========================
# CONFIGURAÇÕES
# =========================

@app.route("/configuracoes")
def configuracoes():

    if "user_id" not in session:
        return redirect("/login")

    try:

        usuario = supabase.table(
            "users"
        ).select("*").eq(
            "id",
            session["user_id"]
        ).execute()

        if not usuario.data:

            return render_template(

                "configuracoes.html",

                erro="Usuário não encontrado",

                user=None,

                linkedin_conectado=False

            )

        user = usuario.data[0]

        linkedin_conectado = bool(
            user.get("linkedin_token")
        )

        return render_template(

            "configuracoes.html",

            user=user,

            linkedin_conectado=linkedin_conectado

        )

    except Exception as e:

        print("ERRO CONFIG:")

        print(str(e))

        return render_template(

            "configuracoes.html",

            erro=str(e),

            user=None,

            linkedin_conectado=False

        )

# =========================
# PLANOS
# =========================

@app.route("/planos")
def planos():

    if "user_id" not in session:
        return redirect("/login")

    return render_template(
        "planos.html",
        planos=PLANOS
    )

# =========================
# DELETE POST
# =========================

@app.route("/delete_post/<int:post_id>")
def delete_post(post_id):

    if "user_id" not in session:
        return redirect("/login")

    try:

        supabase.table(
            "posts"
        ).delete().eq(
            "id",
            post_id
        ).eq(
            "user_id",
            session["user_id"]
        ).execute()

        return redirect("/agendamentos")

    except Exception as e:

        print("DELETE ERROR:")

        print(str(e))

        return redirect("/agendamentos")

# =========================
# PUBLICAR
# =========================

@app.route("/publicar/<int:post_id>")
def publicar(post_id):

    if "user_id" not in session:
        return redirect("/login")

    # =========================
    # PUBLICAÇÃO MANUAL
    # DESATIVADA
    # =========================

    return redirect("/agendamentos")
    
# =========================
# START
# =========================

if __name__ == "__main__":

    app.run(
        debug=True
    )
