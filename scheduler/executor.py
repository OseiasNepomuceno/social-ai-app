import os
import time
from datetime import datetime
from supabase import create_client

# =========================
# SUPABASE
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🚀 Executor SaaS iniciado (multiusuário)")

# =========================
# FUNÇÃO: VERIFICAR LIMITE
# =========================

def pode_publicar(user):
    plano = user.get("plano", "gratuito")
    usados = user.get("posts_usados", 0)
    limite = user.get("posts_limite", 10)

    if plano == "business":
        return True

    return usados < limite


# =========================
# FUNÇÃO: EXECUTAR POST
# =========================

def executar_post(post, user):

    print("\n🚀 Executando post SaaS")
    print("Usuário:", user["email"])
    print("Tema:", post["tema"])
    print("Rede:", post["rede"])

    # =========================
    # LER CONTEÚDO DO ARQUIVO
    # =========================

    try:
        with open(post["arquivo"], "r", encoding="utf-8") as file:
            conteudo = file.read()
    except Exception as e:
        print("Erro ao ler arquivo:", e)
        return

    print("\n===== CONTEÚDO =====")
    print(conteudo)

    # =========================
    # PUBLICAÇÃO (LINKEDIN / INSTAGRAM FUTURO)
    # =========================

    if post["rede"] == "linkedin":
        os.system("python linkedin/postar.py")

    if post["rede"] == "instagram":
        print("Instagram ainda em integração")

    # =========================
    # ATUALIZAR POST
    # =========================

    supabase.table("posts").update({
        "status": "executado"
    }).eq("id", post["id"]).execute()

    # =========================
    # INCREMENTAR USO DO USUÁRIO
    # =========================

    usuario = supabase.table("users") \
        .select("*") \
        .eq("id", user["id"]) \
        .execute()

    if usuario.data:
        u = usuario.data[0]

        supabase.table("users").update({
            "posts_usados": u.get("posts_usados", 0) + 1
        }).eq("id", user["id"]).execute()

    print("✅ Post executado com sucesso")


# =========================
# LOOP SAAS (MOTOR PRINCIPAL)
# =========================

def loop_executor():

    while True:

        try:

            print("\n⏰ Verificando posts...")

            # =========================
            # BUSCAR POSTS PENDENTES
            # =========================

            posts = supabase.table("posts") \
                .select("*") \
                .eq("status", "pendente") \
                .execute().data

            if not posts:
                print("Nenhum post pendente.")
                time.sleep(10)
                continue

            for post in posts:

                # =========================
                # BUSCAR USUÁRIO
                # =========================

                user_res = supabase.table("users") \
                    .select("*") \
                    .eq("id", post["user_id"]) \
                    .execute()

                if not user_res.data:
                    print("Usuário não encontrado:", post["user_id"])
                    continue

                user = user_res.data[0]

                # =========================
                # VERIFICAR LIMITE DE PLANO
                # =========================

                if not pode_publicar(user):
                    print("🚫 Limite atingido:", user["email"])
                    continue

                # =========================
                # EXECUTAR POST
                # =========================

                executar_post(post, user)

        except Exception as e:
            print("Erro no executor:", e)

        # roda a cada 10 segundos
        time.sleep(10)


# =========================
# START
# =========================

if __name__ == "__main__":
    loop_executor()
