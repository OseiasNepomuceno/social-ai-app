from flask import (
    Flask,
    render_template,
    redirect,
    request,
    session,
    jsonify
)

import os
import mercadopago

from datetime import timedelta
 
from dashboard.agents.analisador_media import gerar_relatorio_completo

from supabase import create_client

from services.supabase_storage import upload_image

from dashboard.agents.media_selector import (
    selecionar_imagem
)

from dashboard.ia_engine import (
    gerar_conteudo
)

from apscheduler.schedulers.background import (
    BackgroundScheduler
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
# SESSÃO
# =========================

app.permanent_session_lifetime = timedelta(days=30)

# =========================
# MONITORAMENTO
# =========================

app = Flask(__name__)

@app.route('/monitoramento')
def monitoramento():
    # Chama o agente de análise
    relatorio = gerar_relatorio_dados()
    return render_template('monitoramento.html', data=relatorio)

# Rota para executar via botão (AJAX) sem dar refresh na página
@app.route('/api/executar-analise')
def api_analise():
    resultado = gerar_relatorio_dados()
    return jsonify(resultado)

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
# FUNÇÃO: VERIFICAR PAGAMENTOS
# =========================

def verificar_e_atualizar_pagamento(user_id):
    """
    Verifica pagamentos pendentes no Mercado Pago
    e atualiza o plano do usuário se aprovado.
    
    Args:
        user_id (str): ID do usuário
        
    Returns:
        dict: {'success': bool, 'message': str}
    """
    
    try:

        print("\n========================")
        print(f"🔎 VERIFICANDO PAGAMENTOS - USER: {user_id}")
        print("========================")

        if not mp:

            print("❌ MERCADO PAGO NÃO CONFIGURADO")

            return {
                "success": False,
                "message": "Mercado Pago não configurado"
            }

        # =========================
        # BUSCAR PAGAMENTOS
        # =========================

        pagamentos_response = (
            mp.payment().search({

                "external_reference": user_id

            })
        )

        results = pagamentos_response.get(
            "response",
            {}
        ).get(
            "results",
            []
        )

        print(f"PAGAMENTOS ENCONTRADOS: {len(results)}")

        if not results:

            print("⚠️ NENHUM PAGAMENTO ENCONTRADO")

            return {
                "success": False,
                "message": "Nenhum pagamento encontrado"
            }

        # =========================
        # VERIFICAR STATUS
        # =========================

        for pagamento in results:

            status = pagamento.get("status")

            payment_id = pagamento.get("id")

            print(f"PAGAMENTO ID: {payment_id} | STATUS: {status}")

            if status == "approved":

                print(f"✅ PAGAMENTO APROVADO - {payment_id}")

                # =========================
                # ATUALIZAR PLANO
                # =========================

                supabase.table(
                    "users"
                ).update({

                    "plano": "pro",

                    "posts_limite": 999999

                }).eq(

                    "id",
                    user_id

                ).execute()

                print(f"🚀 PLANO PRO ATIVADO - {user_id}")

                return {
                    "success": True,
                    "message": "Plano atualizado com sucesso",
                    "payment_id": payment_id
                }

        print("⚠️ NENHUM PAGAMENTO APROVADO")

        return {
            "success": False,
            "message": "Nenhum pagamento em status aprovado"
        }

    except Exception as e:

        print(f"❌ ERRO NA VERIFICAÇÃO: {str(e)}")

        return {
            "success": False,
            "message": str(e)
        }

# =========================
# TAREFA AGENDADA: VERIFICAR PAGAMENTOS
# =========================

def verificar_pagamentos_todos_usuarios():
    """
    Verifica pagamentos pendentes de TODOS os usuários.
    Executada automaticamente a cada X minutos.
    """

    try:

        print("\n" + "="*50)
        print("🔄 VERIFICAÇÃO AUTOMÁTICA DE PAGAMENTOS")
        print("="*50)

        # Buscar usuários com plano "free"
        usuarios_free = supabase.table(
            "users"
        ).select("id").eq(
            "plano",
            "free"
        ).execute()

        usuarios = usuarios_free.data

        print(f"USUÁRIOS FREE: {len(usuarios)}")

        if not usuarios:

            print("✅ NENHUM USUÁRIO PARA VERIFICAR")

            return

        # Verificar cada usuário
        for usuario in usuarios:

            user_id = usuario["id"]

            resultado = verificar_e_atualizar_pagamento(
                user_id
            )

            if resultado["success"]:

                print(
                    f"✅ {user_id}: {resultado['message']}"
                )

            else:

                print(
                    f"⚠️ {user_id}: {resultado['message']}"
                )

    except Exception as e:

        print(f"❌ ERRO NA TAREFA AGENDADA: {str(e)}")

# =========================
# CONFIGURAR SCHEDULER
# =========================

scheduler = BackgroundScheduler()

scheduler.add_job(

    func=verificar_pagamentos_todos_usuarios,

    trigger="interval",

    minutes=15,  # A cada 15 minutos

    id="verificar_pagamentos",

    name="Verificar pagamentos pendentes",

    replace_existing=True

)

scheduler.start()

print("✅ SCHEDULER INICIADO - Verificação a cada 15 minutos")

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

            session.permanent = True

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
# REGISTER
# =========================

@app.route(
    "/register",
    methods=["GET", "POST"]
)

def register():

    if request.method == "POST":

        nome = request.form["nome"]

        email = request.form["email"]

        senha = request.form["senha"]

        try:

            resposta = (
                supabase.auth
                .sign_up({

                    "email": email,

                    "password": senha

                })
            )

            user = resposta.user

            if not user:

                return render_template(

                    "register.html",

                    erro="Erro ao criar conta"

                )

            supabase.table(
                "users"
            ).upsert({

                "id": user.id,

                "nome": nome,

                "email": email,

                "plano": "free",

                "posts_limite": 10,

                "posts_usados": 0

            }).execute()

            session.permanent = True

            session["user_id"] = user.id

            session["email"] = email

            print("✅ USUÁRIO CRIADO")

            return redirect("/")

        except Exception as e:

            print("REGISTER ERROR:")
            print(str(e))

            return render_template(

                "register.html",

                erro="Erro ao criar conta"

            )

    return render_template(
        "register.html"
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

            if rede == "instagram":

                status_post = "pronto_instagram"

            else:

                status_post = "pendente"

            print("STATUS POST:")
            print(status_post)

            imagem_url = None

            file = request.files.get(
                "image"
            )

            print("REQUEST FILES:")
            print(request.files)

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

            payload = {

                "tema": tema,

                "rede": rede,

                "conteudo": conteudo,

                "modo": modo,

                "nicho": nicho,

                "imagem_url": imagem_url,

                "data_postagem": data_postagem,

                "hora_postagem": hora_postagem,

                "status": status_post,

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

        supabase.table(
            "posts"
        ).delete().eq(
            "id",
            post_id
        ).eq(
            "user_id",
            session["user_id"]
        ).execute()

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
        ).in_(
            "status",
            [
                "executado",
                "pronto_instagram"
            ]
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

    try:

        user_id = session["user_id"]

        # =========================
        # VERIFICAR PAGAMENTO MANUAL
        # =========================

        resultado = verificar_e_atualizar_pagamento(
            user_id
        )

        if resultado["success"]:

            print(
                f"✅ PAGAMENTO RECUPERADO: {resultado['message']}"
            )

        return render_template(

            "planos.html",

            planos=PLANOS

        )

    except Exception as e:

        print("PLANOS ERROR:")
        print(str(e))

        return str(e)

# =========================
# CHECKOUT PRO
# =========================

@app.route("/checkout/pro")
def checkout_pro():

    if "user_id" not in session:

        return redirect("/login")

    try:

        user_id = session["user_id"]

        email = session["email"]

        preference_data = {

            "items": [

                {

                    "title":
                    "Social AI Pro",

                    "quantity": 1,

                    "currency_id":
                    "BRL",

                    "unit_price": 49.90

                }

            ],

            "payer": {

                "email": email

            },

            "back_urls": {

                "success":
                "https://app.coregov.com.br/planos",

                "failure":
                "https://app.coregov.com.br/planos",

                "pending":
                "https://app.coregov.com.br/planos"

            },

            "auto_return":
            "approved",

            "external_reference":
            user_id

        }

        preference_response = (
            mp.preference().create(
                preference_data
            )
        )

        preference = (
            preference_response[
                "response"
            ]
        )

        checkout_url = preference[
            "init_point"
        ]

        print("✅ CHECKOUT GERADO")

        print(checkout_url)

        return redirect(
            checkout_url
        )

    except Exception as e:

        print("❌ ERRO CHECKOUT")

        print(str(e))

        return str(e)

# =========================
# WEBHOOK MERCADO PAGO
# =========================

@app.route(
    "/webhook/mercadopago",
    methods=["POST"]
)

def webhook_mercadopago():

    try:

        data = request.json

        print("\n========================")
        print("🚀 WEBHOOK MERCADO PAGO")
        print("========================")

        print(data)

        if not data:

            return {
                "success": False
            }, 400

        payment_type = (
            data.get("type")
            or data.get("topic")
        )

        print("PAYMENT TYPE:")
        print(payment_type)

        if payment_type != "payment":

            return {
                "success": True
            }, 200

        payment_id = None

        if "data" in data:

            payment_id = (
                data["data"].get("id")
            )

        elif "id" in data:

            payment_id = data.get(
                "id"
            )

        if not payment_id:

            print(
                "❌ PAYMENT ID NÃO ENCONTRADO"
            )

            return {
                "success": False
            }, 400

        print("PAYMENT ID:")
        print(payment_id)

        payment_info = (
            mp.payment().get(
                payment_id
            )
        )

        payment = payment_info[
            "response"
        ]

        print("\n========================")
        print("💰 PAYMENT COMPLETO")
        print("========================")

        print(payment)

        status = payment.get(
            "status"
        )

        print("STATUS:")
        print(status)

        if status != "approved":

            print(
                "⚠️ PAGAMENTO NÃO APROVADO"
            )

            return {
                "success": True
            }, 200

        user_id = payment.get(
            "external_reference"
        )

        print("USER ID:")
        print(user_id)

        if not user_id:

            print(
                "❌ USER ID NÃO ENCONTRADO"
            )

            return {
                "success": False
            }, 400

        supabase.table(
            "users"
        ).update({

            "plano": "pro",

            "posts_limite": 999999

        }).eq(

            "id",
            user_id

        ).execute()

        print(
            "✅ PLANO PRO ATIVADO"
        )

        return {
            "success": True
        }, 200

    except Exception as e:

        print("\n========================")
        print("❌ WEBHOOK ERROR")
        print("========================")

        print(str(e))

        return {

            "success": False,

            "error": str(e)

        }, 500

# =========================
# START
# =========================

if __name__ == "__main__":

    app.run(
        debug=True
    )
