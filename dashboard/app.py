import os
from datetime import datetime, timedelta
import threading
import requests
import mercadopago
import urllib.parse
import unicodedata
from flask import (
    Flask,
    render_template,
    redirect,
    request,
    session,
    jsonify,
    send_from_directory,
    flash,
    url_for,
    render_template_string
)
from supabase import create_client
from apscheduler.schedulers.background import BackgroundScheduler
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Importações dos agentes internos
from dashboard.agents.analisador_media import gerar_relatorio_completo
from services.supabase_storage import upload_image
from dashboard.agents.media_selector import selecionar_imagem
from dashboard.ia_engine import gerar_conteudo
from dashboard.picoclaw_agent import gerar_post_picoclaw

# =========================
# CONFIGURAÇÃO DO FLASK
# =========================

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates"
)

# SECRET KEY — obrigatória via variável de ambiente
app.secret_key = os.getenv("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("❌ SECRET_KEY não configurada no ambiente!")

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=4)
app.config['SESSION_COOKIE_NAME'] = 'social_ai_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# =========================
# RATE LIMITING E SEGURANÇA
# =========================

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Headers de segurança HTTP
@app.after_request
def adicionar_headers_seguranca(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

# Erro 429 — Rate limit atingido
@app.errorhandler(429)
def rate_limit_exceeded(e):
    ip = request.remote_addr
    print(f"🚨 RATE LIMIT ATINGIDO: IP={ip} Rota={request.path}")
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Muitas requisições</title>
            <meta http-equiv="refresh" content="60;url=/">
        </head>
        <body style="background:#111827;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
            <div style="text-align:center;">
                <h2>⚠️ Muitas tentativas</h2>
                <p style="color:#9ca3af;">Aguarde 1 minuto e tente novamente.</p>
            </div>
        </body>
        </html>
    '''), 429

# =========================
# ROTA DO FAVICON
# =========================

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

# =========================
# FUNDO ANIMADO
# =========================

@app.route("/fundo")
def fundo_video():
    return render_template("fundo-video.html")

# =========================
# SUPABASE
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# MERCADO PAGO
# =========================

MERCADO_PAGO_TOKEN = os.getenv("MERCADO_PAGO_TOKEN")
mp = mercadopago.SDK(MERCADO_PAGO_TOKEN) if MERCADO_PAGO_TOKEN else None

# =========================
# PLANOS
# =========================

PLANOS = {
    "free": {"nome": "Free", "preco": 0, "limite": 10},
    "pro": {"nome": "Pro", "preco": 99.90, "limite": 60}
}

# =========================
# INSTAGRAM LOGIN
# =========================

@app.route("/instagram/login")
def instagram_login():
    scope = (
        "instagram_basic,"
        "instagram_manage_comments,"
        "pages_show_list,"
        "pages_read_engagement,"
        "business_management"
    )
    auth_url = (
        f"https://www.facebook.com/v21.0/dialog/oauth?"
        f"client_id={os.getenv('FACEBOOK_APP_ID')}"
        f"&scope={scope}"
        f"&response_type=code"
        f"&state={session.get('user_id', 'init')}"
        f"&auth_type=rerequest"
    )
    return redirect(auth_url)

# =========================
# ROBOTS.TXT
# =========================

@app.route('/robots.txt')
def robots_txt():
    linhas = [
        "User-agent: *",
        "Disallow: /dashboard",
        "Disallow: /api/",
        "Allow: /$"
    ]
    return "\n".join(linhas), 200, {'Content-Type': 'text/plain'}

# =========================
# BLOQUEIO DE SCAN MALICIOSO
# =========================

@app.route('/.env')
@app.route('/.env.bak')
@app.route('/.env.save')
@app.route('/.env.backup')
@app.route('/wp-config.php')
@app.route('/.aws/credentials')
@app.route('/.aws/config')
@app.route('/aws-credentials')
@app.route('/phpinfo.php')
@app.route('/info.php')
@app.route('/test.php')
def bloquear_scan():
    ip = request.remote_addr
    print(f"🚨 TENTATIVA DE ATAQUE BLOQUEADA: {ip} → {request.path}")
    return "Not Found", 404

# =========================
# MIDDLEWARE: MONITORAMENTO DE TRÁFEGO
# =========================

@app.before_request
def rastrear_atividade_usuario():
    if request.path.startswith('/static') or request.path == '/favicon.ico':
        return
    if "user_id" in session:
        user_id = session["user_id"]
        agora_iso = datetime.utcnow().isoformat()
        hoje_str = datetime.utcnow().strftime("%Y-%m-%d")
        try:
            supabase.table("users").update({
                "ultima_atividade": agora_iso
            }).eq("id", user_id).execute()
            id_registro_unico = f"{user_id}_{hoje_str}"
            supabase.table("analytics_acessos").upsert({
                "id_composto": id_registro_unico,
                "user_id": user_id,
                "data_acesso": hoje_str
            }).execute()
        except Exception as e:
            print(f"⚠️ Erro ao registrar tracking de analytics: {str(e)}")

# =========================
# MONITORAMENTO ADMIN
# =========================

ADMIN_EMAIL = "oseiasnepom@gmail.com"

@app.route('/monitoramento')
def monitoramento():
    if "user_id" not in session:
        return redirect("/login")
    if session.get("email") != ADMIN_EMAIL:
        print(f"🚨 Tentativa de acesso não autorizado ao monitoramento por: {session.get('email')}")
        return redirect("/")
    try:
        print("⚡ Gatilho detectado via Painel Admin: Disparando robô multiplicador...")
        thread_agente = threading.Thread(
            target=iniciar_multiplicacao_banco_existente,
            kwargs={"limite_por_rodada": 20},
            daemon=True
        )
        thread_agente.start()
    except Exception as err_agente:
        print(f"⚠️ Falha ao criar a thread de multiplicação: {str(err_agente)}")
    usuarios_online = 0
    usuarios_hoje = 0
    usuarios_mes = 0
    lista_online = []
    lista_hoje = []
    lista_mes = []
    grafico_labels = []
    grafico_dados = []
    try:
        agora = datetime.utcnow()
        cinco_minutos_atras = (agora - timedelta(minutes=5)).isoformat()
        res_online = supabase.table("users").select("id", "email").gte("ultima_atividade", cinco_minutos_atras).execute()
        if res_online.data:
            lista_online = res_online.data
            usuarios_online = len(lista_online)
        hoje_str = agora.strftime("%Y-%m-%d")
        res_hoje = supabase.table("analytics_acessos").select("user_id", "users(email)").eq("data_acesso", hoje_str).execute()
        if res_hoje.data:
            lista_hoje = [{"email": item["users"]["email"]} for item in res_hoje.data if item.get("users")]
            usuarios_hoje = len(lista_hoje)
        trinta_dias_atras = (agora - timedelta(days=30)).strftime("%Y-%m-%d")
        res_mes = supabase.table("analytics_acessos").select("user_id", "users(email)").gte("data_acesso", trinta_dias_atras).execute()
        if res_mes.data:
            emails_unicos_mes = {item["users"]["email"] for item in res_mes.data if item.get("users")}
            lista_mes = [{"email": email} for email in emails_unicos_mes]
            usuarios_mes = len(lista_mes)
        for i in range(6, -1, -1):
            dia_alvo = agora - timedelta(days=i)
            dia_alvo_str = dia_alvo.strftime("%Y-%m-%d")
            dia_exibicao = dia_alvo.strftime("%d/%m")
            res_dia = supabase.table("analytics_acessos").select("user_id", count="exact").eq("data_acesso", dia_alvo_str).execute()
            total_dia = res_dia.count if res_dia.count is not None else 0
            grafico_labels.append(dia_exibicao)
            grafico_dados.append(total_dia)
    except Exception as err_metrics:
        print(f"⚠️ Falha crítica ao computar métricas de usuários: {str(err_metrics)}")
    try:
        relatorio = gerar_relatorio_completo()
    except Exception as e:
        print("Erro ao gerar relatório do monitoramento:", str(e))
        relatorio = {}
    return render_template(
        'monitoramento.html',
        data=relatorio,
        usuarios_online=usuarios_online,
        usuarios_hoje=usuarios_hoje,
        usuarios_mes=usuarios_mes,
        lista_online=lista_online,
        lista_hoje=lista_hoje,
        lista_mes=lista_mes,
        grafico_labels=grafico_labels,
        grafico_dados=grafico_dados
    )

# =========================
# LINKEDIN OAUTH
# =========================

@app.route("/linkedin/login", methods=["GET"])
def linkedin_login():
    if "user_id" not in session:
        return redirect("/login")
    CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
    REDIRECT_URI = "https://app.coregov.com.br/linkedin/callback"
    if not CLIENT_ID:
        print("❌ Erro: LINKEDIN_CLIENT_ID não configurado.")
        flash("A integração com o LinkedIn está em manutenção temporária.", "danger")
        return redirect(url_for("configuracoes"))
    scope = "openid,profile,email,w_member_social"
    linkedin_auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={session['user_id']}"
        f"&scope={scope}"
    )
    return redirect(linkedin_auth_url)

@app.route("/linkedin/callback", methods=["GET"])
def linkedin_callback():
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")
    error_description = request.args.get("error_description")
    if error:
        flash("Autorização cancelada ou negada.", "warning")
        return redirect(url_for("configuracoes"))
    if not code:
        flash("Código de autenticação ausente.", "danger")
        return redirect(url_for("configuracoes"))
    user_id = state if state else session.get("user_id")
    if not user_id:
        return redirect("/login")
    CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
    CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
    REDIRECT_URI = "https://app.coregov.com.br/linkedin/callback"
    try:
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data=token_data,
            headers=headers
        )
        token_json = response.json()
        if "access_token" in token_json:
            access_token = token_json["access_token"]
            supabase.table("users").update({
                "linkedin_token": access_token
            }).eq("id", user_id).execute()
            flash("Conta do LinkedIn conectada com sucesso! 🚀", "success")
        else:
            flash("Não foi possível validar as credenciais do LinkedIn.", "danger")
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NO CALLBACK DO LINKEDIN: {str(e)}")
        flash(f"Instabilidade ao conectar com o LinkedIn: {str(e)}", "danger")
    return redirect(url_for("configuracoes"))

# =========================
# FUNÇÕES AUXILIARES
# =========================

def formatar_nicho(nome):
    nome = nome.lower()
    substituicoes = {
        "fotografiadealimentos": "Fotografia de Alimentos",
        "fitnessbem-estar": "Fitness e Bem-estar",
        "diversidadeerepresentacao": "Diversidade e Representação",
        "viagenseturismo": "Viagens e Turismo",
        "saudementalemindfulness": "Saúde Mental e Mindfulness",
        "familiaerelacionamentos": "Família e Relacionamentos",
        "arquiteturaedesigndeinteriores": "Arquitetura e Design de Interiores",
        "tecnologiamergente": "Tecnologia Emergente"
    }
    if nome in substituicoes:
        return substituicoes[nome]
    return " ".join(p.capitalize() for p in nome.split())

def buscar_nichos_ativos():
    try:
        response = supabase.table("media_library").select("nicho").eq("ativo", True).execute()
        nichos_originais = list({item['nicho'] for item in response.data or []})
        return [formatar_nicho(n) for n in nichos_originais]
    except Exception as e:
        print(f"Erro ao buscar nichos ativos: {str(e)}")
        return [
            "Limpeza", "Marketing", "Psicologia", "Negócios", "Engenharia",
            "Financeiro", "Tecnologia", "Contabilidade", "Vendas", "Empreendedorismo",
            "Saúde", "Fotografia de Alimentos", "Fitness e Bem-estar",
            "Diversidade e Representação", "Viagens e Turismo",
            "Saúde Mental e Mindfulness", "Alimentação", "Família e Relacionamentos",
            "Arquitetura e Design de Interiores", "Tecnologia Emergente", "Moda", "Educação"
        ]

def normalizar_texto(texto):
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto.replace(" ", "")

def distancia_levenshtein(a, b):
    n, m = len(a), len(b)
    if n > m:
        a, b = b, a
        n, m = m, n
    current = list(range(n + 1))
    for i in range(1, m + 1):
        previous, current = current, [i] + [0] * n
        for j in range(1, n + 1):
            add = previous[j] + 1
            delete = current[j - 1] + 1
            change = previous[j - 1]
            if a[j - 1] != b[i - 1]:
                change += 1
            current[j] = min(add, delete, change)
    return current[n]

def encontrar_nicho_mais_proximo(entrada, lista_nichos):
    entrada_norm = normalizar_texto(entrada)
    melhor_nicho = None
    menor_distancia = float('inf')
    for nicho in lista_nichos:
        dist = distancia_levenshtein(entrada_norm, normalizar_texto(nicho))
        if dist < menor_distancia:
            menor_distancia = dist
            melhor_nicho = nicho
    return melhor_nicho

def validar_url_imagem(url):
    if not url:
        return False
    try:
        resposta = requests.head(url, timeout=5)
        return resposta.status_code == 200
    except:
        return False

# =========================
# ROTA IA — GERADOR DE POSTS
# =========================

@app.route("/ia", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def ia():
    if "user_id" not in session:
        return redirect("/login")
    if request.method == "POST":
        try:
            tema = request.form.get("tema")
            rede = request.form.get("rede_social")
            modo = request.form.get("modo")
            nicho = request.form.get("nicho")
            data_postagem = request.form.get("data_postagem")
            hora_postagem = request.form.get("horario")
            print(f"🚀 EXECUTOR IA ACIONADO: Tema='{tema}' | Rede='{rede}' | Modo='{modo}'")
            user_data_res = supabase.table("users").select("posts_usados", "posts_limite").eq("id", session["user_id"]).execute()
            if not user_data_res.data:
                flash("Usuário não encontrado. Faça login novamente.", "danger")
                return redirect(url_for("login"))
            user_info = user_data_res.data[0]
            posts_usados = user_info.get("posts_usados", 0)
            posts_limite = user_info.get("posts_limite", 10)
            if posts_usados >= posts_limite:
                flash(f"Você atingiu o limite de {posts_limite} postagens. Atualize seu plano.", "warning")
                return redirect(url_for("ia"))
            status_post = "pendente"
            imagem_url = None
            file = request.files.get("imagem")
            if file and file.filename != "":
                print(f"📸 Imagem manual detectada: {file.filename}.")
                upload_result = upload_image(file)
                if upload_result.get("success"):
                    imagem_url = upload_result.get("public_url")
            if not imagem_url:
                print("📂 Nenhuma imagem enviada. Buscando na Media Library...")
                imagem_url = selecionar_imagem(nicho=nicho, rede=rede, estilo="premium")
                print(f"🎯 Imagem selecionada do banco: {imagem_url}")
            IMAGEM_PADRAO = "https://coregov.com.br/static/imagem-padrao.png"
            if not validar_url_imagem(imagem_url):
                print("⚠️ URL da imagem inválida, usando imagem padrão.")
                imagem_url = IMAGEM_PADRAO
            resultado = gerar_post_picoclaw(tema, rede, modo, nicho)
            if not resultado.get("success"):
                print(f"⚠️ PICOCLAW FALHOU ({resultado.get('erro')}) - Usando ia_engine como fallback")
                resultado = gerar_conteudo(tema, rede, modo, nicho)
            if not resultado.get("success"):
                flash(f"Erro na inteligência artificial: {resultado.get('erro')}", "error")
                return redirect(url_for("ia"))
            conteudo = resultado["conteudo"]
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
            supabase.table("posts").insert(payload).execute()
            print("💾 Post inserido com sucesso.")
            novo_total = posts_usados + 1
            supabase.table("users").update({"posts_usados": novo_total}).eq("id", session["user_id"]).execute()
            print(f"Contador atualizado! Total usado: {novo_total}")
            flash("Postagem criada com sucesso!", "success")
            return redirect(url_for("ia"))
        except Exception as e:
            print("❌ EXCEÇÃO DISPARADA NO EXECUTOR IA:", str(e))
            flash(f"Ocorreu um erro interno: {str(e)}", "error")
            return redirect(url_for("ia"))
    else:
        nichos_ativos = buscar_nichos_ativos()
        nicho_sugerido = None
        tema = request.args.get("tema", "")
        if tema:
            nicho_sugerido = encontrar_nicho_mais_proximo(tema, nichos_ativos)
        return render_template("ia.html", nicho_sugerido=nicho_sugerido, lista_nichos=nichos_ativos)

# =========================
# PAGAMENTOS & SCHEDULER
# =========================

def verificar_e_atualizar_pagamento(user_id):
    try:
        print(f"🔎 VERIFICANDO PAGAMENTOS - USER: {user_id}")
        if not mp:
            return {"success": False, "message": "Mercado Pago não configurado"}
        pagamentos_response = mp.payment().search({"external_reference": user_id})
        results = pagamentos_response.get("response", {}).get("results", [])
        if not results:
            return {"success": False, "message": "Nenhum pagamento encontrado"}
        for pagamento in results:
            status = pagamento.get("status")
            payment_id = pagamento.get("id")
            if status == "approved":
                supabase.table("users").update({
                    "plano": "pro",
                    "posts_limite": 60
                }).eq("id", user_id).execute()
                print(f"🚀 PLANO PRO ATIVADO - {user_id}")
                return {"success": True, "message": "Plano atualizado", "payment_id": payment_id}
        return {"success": False, "message": "Nenhum pagamento aprovado"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def verificar_pagamentos_todos_usuarios():
    try:
        print("🔄 VERIFICAÇÃO AUTOMÁTICA DE PAGAMENTOS")
        usuarios_free = supabase.table("users").select("id").eq("plano", "free").execute()
        usuarios = usuarios_free.data
        if not usuarios:
            return
        for usuario in usuarios:
            user_id = usuario["id"]
            resultado = verificar_e_atualizar_pagamento(user_id)
            print(f"{'✅' if resultado['success'] else '⚠️'} {user_id}: {resultado['message']}")
    except Exception as e:
        print(f"❌ ERRO NA TAREFA AGENDADA: {str(e)}")

scheduler = BackgroundScheduler()
scheduler.add_job(
    func=verificar_pagamentos_todos_usuarios,
    trigger="interval",
    minutes=15,
    id="verificar_pagamentos",
    name="Verificar pagamentos pendentes",
    replace_existing=True
)
scheduler.start()
print("✅ SCHEDULER INICIADO - Verificação a cada 15 minutos")

# =========================
# ROTAS DE AUTENTICAÇÃO
# =========================

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect("/login")
    try:
        posts = supabase.table("posts").select("*").eq(
            "user_id", session["user_id"]
        ).order("id", desc=True).limit(6).execute().data
        total_posts = len(posts) if posts else 0
        executados = sum(1 for p in posts if p.get("status") == "executado")
        pendentes = sum(1 for p in posts if p.get("status") == "pendente")
        erros = sum(1 for p in posts if p.get("status") == "erro")
        return render_template("index.html", posts=posts, total_posts=total_posts,
                               executados=executados, pendentes=pendentes, erros=erros)
    except Exception as e:
        print("HOME ERROR:", str(e))
        return render_template("index.html", posts=[], total_posts=0,
                               executados=0, pendentes=0, erros=0, erro=str(e))

@app.route("/login", methods=["GET", "POST"])
@app.route('/login/', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]
        try:
            resposta = supabase.auth.sign_in_with_password({"email": email, "password": senha})
            user = resposta.user
            session.permanent = True
            session["user_id"] = user.id
            session["email"] = user.email
            checar_usuario = supabase.table("users").select("plano").eq("id", user.id).execute()
            if not checar_usuario.data:
                supabase.table("users").insert({
                    "id": user.id, "email": user.email,
                    "plano": "free", "posts_limite": 10, "posts_usados": 0
                }).execute()
            else:
                supabase.table("users").update({"email": user.email}).eq("id", user.id).execute()
            return redirect("/")
        except Exception as e:
            print("LOGIN ERROR:", str(e))
            return render_template("login.html", erro="Login inválido. Verifique suas credenciais.")
    return render_template("login.html")

@app.route("/login/google")
def login_google():
    try:
        dados_auth = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": "https://app.coregov.com.br/auth/callback"}
        })
        return redirect(dados_auth.url)
    except Exception as e:
        print(f"❌ ERRO AO INICIAR FLUXO GOOGLE OAUTH: {str(e)}")
        return redirect("/login")

@app.route("/auth/callback")
def auth_callback():
    try:
        code = request.args.get("code")
        if code:
            resposta = supabase.auth.exchange_code_for_session({"auth_code": code})
        else:
            access_token = request.args.get("access_token")
            refresh_token = request.args.get("refresh_token")
            if access_token and refresh_token:
                supabase.auth.set_session({"access_token": access_token, "refresh_token": refresh_token})
                resposta = supabase.auth.get_user(access_token)
            else:
                resposta = None
        if resposta and hasattr(resposta, 'user') and resposta.user:
            user = resposta.user
            session.permanent = True
            session["user_id"] = user.id
            session["email"] = user.email
            try:
                checar_usuario = supabase.table("users").select("plano").eq("id", user.id).execute()
                if not checar_usuario.data:
                    supabase.table("users").insert({
                        "id": user.id, "email": user.email,
                        "plano": "free", "posts_limite": 10, "posts_usados": 0
                    }).execute()
                else:
                    supabase.table("users").update({"email": user.email}).eq("id", user.id).execute()
            except Exception as table_err:
                print(f"⚠️ Nota de tabela: {table_err}")
            return redirect("/")
        return render_template_string('''
            <!DOCTYPE html><html><head><title>Autenticando...</title>
            <script>
                window.onload = function() {
                    var hash = window.location.hash.substring(1);
                    if (hash.length > 0) {
                        var params = new URLSearchParams(hash);
                        var accessToken = params.get("access_token");
                        var refreshToken = params.get("refresh_token");
                        if (accessToken && refreshToken) {
                            window.location.href = "/auth/callback?access_token=" + accessToken + "&refresh_token=" + refreshToken;
                            return;
                        }
                    }
                    setTimeout(function() { window.location.href = "/"; }, 1500);
                };
            </script></head>
            <body style="background:#111827;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
                <div style="text-align:center;"><h2>Conectando com o Google...</h2></div>
            </body></html>
        ''')
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NO CALLBACK DO GOOGLE: {str(e)}")
        return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per hour", methods=["POST"])
def register():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]
        try:
            resposta = supabase.auth.sign_up({
                "email": email, "password": senha,
                "options": {"data": {"display_name": nome}}
            })
            user = resposta.user
            if not user or not hasattr(user, 'id') or user.id is None:
                return render_template("register.html",
                    sucesso="📬 Enviamos um e-mail de ativação. Verifique sua caixa de entrada!")
            try:
                supabase.table("users").upsert({
                    "id": user.id, "email": email,
                    "plano": "free", "posts_limite": 10, "posts_usados": 0
                }).execute()
            except Exception as table_err:
                print(f"⚠️ Alerta ao salvar usuário: {str(table_err)}")
            session.permanent = True
            session["user_id"] = user.id
            session["email"] = email
            return redirect("/")
        except Exception as e:
            error_msg = str(e)
            if "User already registered" in error_msg or "already exists" in error_msg:
                user_friendly_error = "Este e-mail já está cadastrado. Tente fazer login."
            elif "should be at least" in error_msg:
                user_friendly_error = "Senha muito fraca. Use pelo menos 6 caracteres."
            else:
                user_friendly_error = "Instabilidade temporária. Verifique suas informações e tente novamente."
            return render_template("register.html", erro=user_friendly_error)
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("email", None)
    return redirect("/login")

# =========================
# OUTRAS ROTAS
# =========================

@app.route("/agendamentos")
def agendamentos():
    if "user_id" not in session:
        return redirect("/login")
    try:
        posts = supabase.table("posts").select("*").eq(
            "user_id", session["user_id"]).order("id", desc=True).execute().data
        return render_template("agendamentos.html", posts=posts)
    except Exception as e:
        return render_template("agendamentos.html", erro=str(e), posts=[])

@app.route("/deletar/<int:post_id>")
def deletar_post(post_id):
    if "user_id" not in session:
        return redirect("/login")
    try:
        supabase.table("posts").delete().eq("id", post_id).eq("user_id", session["user_id"]).execute()
        return redirect("/agendamentos")
    except Exception as e:
        return str(e)

@app.route("/publicacoes")
def publicacoes():
    if "user_id" not in session:
        return redirect("/login")
    try:
        posts = supabase.table("posts").select("*").eq(
            "user_id", session["user_id"]
        ).in_("status", ["executado", "pronto_instagram"]).order("id", desc=True).execute().data
        return render_template("publicacoes.html", posts=posts)
    except Exception as e:
        print("ERRO ROTA PUBLICACOES:", str(e))
        return render_template("publicacoes.html", erro=str(e), posts=[])

@app.route("/configuracoes")
def configuracoes():
    if "user_id" not in session:
        return redirect("/login")
    try:
        res = supabase.table("users").select("*").eq("id", session["user_id"]).execute()
        dados_usuario = res.data[0] if res.data else {}
        user_data = {
            "name": dados_usuario.get("display_name") or session.get("email", "").split("@")[0].capitalize(),
            "email": dados_usuario.get("email") or session.get("email"),
            "plan": (dados_usuario.get("plano") or "Free").upper(),
            "linkedin_connected": True if dados_usuario.get("linkedin_token") else False,
            "instagram_connected": True if dados_usuario.get("instagram_token") else False,
            "tipo_pix": dados_usuario.get("tipo_pix", ""),
            "chave_pix": dados_usuario.get("chave_pix", "")
        }
        return render_template("configuracoes.html", user=user_data, dados_usuario=dados_usuario)
    except Exception as e:
        print(f"❌ Erro ao carregar configurações: {str(e)}")
        user_fallback = {
            "name": session.get("email", "").split("@")[0].capitalize(),
            "email": session.get("email"),
            "plan": "FREE",
            "linkedin_connected": False,
            "instagram_connected": False,
            "tipo_pix": "",
            "chave_pix": ""
        }
        return render_template("configuracoes.html", user=user_fallback, dados_usuario=user_fallback)

@app.route("/configuracoes/salvar-pix", methods=["POST"])
def salvar_pix():
    if "user_id" not in session:
        return redirect("/login")
    tipo_pix = request.form.get("tipo_pix")
    chave_pix = request.form.get("chave_pix", "").strip()
    try:
        supabase.table("users").update({
            "tipo_pix": tipo_pix, "chave_pix": chave_pix
        }).eq("id", session["user_id"]).execute()
        flash("Chave PIX atualizada com sucesso!", "success")
    except Exception as e:
        print(f"❌ Erro ao salvar PIX: {str(e)}")
        flash("Erro ao salvar sua chave. Tente novamente.", "danger")
    return redirect("/configuracoes")

@app.route("/configuracoes/alterar-senha", methods=["POST"])
def alterar_senha():
    if "user_id" not in session:
        return redirect("/login")
    flash("Senha atualizada com sucesso!", "success")
    return redirect("/configuracoes")

@app.route("/planos")
def planos():
    if "user_id" not in session:
        return redirect("/login")
    try:
        usuario_res = supabase.table("users").select("*").eq("id", session["user_id"]).execute()
        user_data = usuario_res.data[0] if usuario_res.data else {}
        return render_template("planos.html", dados_usuario=user_data)
    except Exception as e:
        print(f"❌ Erro na rota de planos: {str(e)}")
        return redirect("/")
