from flask import (
    Flask,
    render_template,
    redirect,
    request,
    session
)

import os
import mercadopago

from supabase import create_client

from services.supabase_storage import upload_image

from dashboard.agents.media_selector import (
    selecionar_imagem
)

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

            supabase.table(
                "users"
            ).upsert({

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

            print("\n========================")
            print("🚀 NOVO POST")
            print("========================")

            print("TEMA:")
            print(tema)

            print("NICHO:")
            print(nicho)

            print("REDE:")
            print(rede)

            print("MODO:")
            print(modo)

            # =========================
            # IMAGEM
            # =========================

            imagem_url = None

            file = request.files.get(
                "image"
            )

            print("REQUEST FILES:")
            print(request.files)

            # =========================
            # UPLOAD MANUAL
            # =========================

            if file and file.filename != "":

                print(
                    "🖼️ Upload manual detectado"
                )

                upload_result = upload_image(
                    file
                )

                print("UPLOAD RESULT:")
                print(upload_result)

                if upload_result["success"]:

                    imagem_url = upload_result[
                        "public_url"
                    ]

                    print(
                        "✅ Upload manual OK"
                    )

                    print(imagem_url)

            # =========================
            # IMAGEM AUTOMÁTICA
            # =========================

            if not imagem_url:

                print(
                    "🖼️ BUSCANDO IMAGEM AUTOMÁTICA"
                )

                imagem_url = selecionar_imagem(

                    nicho=nicho,

                    rede=rede,

                    estilo="premium"

                )

                print(
                    "✅ IMAGEM ENCONTRADA:"
                )

                print(imagem_url)

            # =========================
            # GERAR CONTEÚDO
            # =========================

            resultado = gerar_conteudo(

                tema,

                rede,

                modo,

                nicho

            )

            print("RESULTADO IA:")
            print(resultado)

            if not resultado["success"]:

                return render_template(

                    "ia.html",

                    erro=resultado["erro"]

                )

            conteudo = resultado["conteudo"]

            print("CONTEÚDO GERADO:")
            print(conteudo)

            # =========================
            # SALVAR POST
            # =========================

            payload = {

                "tema": tema,

                "rede": rede,

                "conteudo": conteudo,

                "modo": modo,

                "nicho": nicho,

                "imagem_url": imagem_url,

                "data_postagem": data_postagem,

                "hora_postagem": hora_postagem,

                "status": "pendente",

                "user_id": session["user_id"]

            }

            print("\n===== PAYLOAD POST =====")
            print(payload)

            response = supabase.table(
                "posts"
            ).insert(
                payload
            ).execute()

            print("\n===== RESPONSE POST =====")
            print(response)

            print("✅ POST SALVO")

            return render_template(

                "ia.html",

                sucesso=True,

                conteudo=conteudo,

                imagem_url=imagem_url

            )

        except Exception as e:

            print("ERRO IA:")
            print(str(e))

            return render_template(

                "ia.html",

                erro=str(e)

            )

    return render_template(
        "ia.html"
    )

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
# DELETAR POST
# =========================

@app.route(
    "/deletar/<int:post_id>"
)
def deletar_post(post_id):

    if "user_id" not in session:

        return redirect("/login")

    try:

        print("\n========================")
        print("🗑️ DELETANDO POST")
        print("========================")

        print("POST ID:")
        print(post_id)

        print("USER:")
        print(session["user_id"])

        response = supabase.table(
            "posts"
        ).delete().eq(
            "id",
            post_id
        ).eq(
            "user_id",
            session["user_id"]
        ).execute()

        print("RESPONSE DELETE:")
        print(response)

        print("✅ POST DELETADO")

        return redirect(
            "/agendamentos"
        )

    except Exception as e:

        print("❌ ERRO DELETE")

        print(str(e))

        return str(e)

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
# START
# =========================

if __name__ == "__main__":

    app.run(
        debug=True
    )
