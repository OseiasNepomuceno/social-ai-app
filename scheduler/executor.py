import os
import time
from supabase import create_client
from linkedin.postar import publicar_linkedin

print("🚀 EXECUTOR SAAS INICIANDO")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

print("SUPABASE_URL:", bool(SUPABASE_URL))
print("SUPABASE_KEY:", bool(SUPABASE_KEY))

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Variáveis Supabase ausentes")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

print("✅ SUPABASE CONECTADO")


# =========================
# VERIFICAR LIMITE
# =========================

def pode_publicar(user):

    plano = user.get("plano", "gratuito")
    usados = user.get("posts_usados", 0)
    limite = user.get("posts_limite", 10)

    if plano == "business":
        return True

    return usados < limite


# =========================
# EXECUTAR POST
# =========================

def executar_post(post, user):

    try:

        print("\n🚀 EXECUTANDO POST")
        print("Usuário:", user.get("email"))
        print("Tema:", post.get("tema"))
        print("Rede:", post.get("rede"))

        conteudo = post.get("conteudo", "")

        print("\n===== CONTEÚDO =====")
        print(conteudo)

        # =========================
        # LINKEDIN
        # =========================

        if post.get("rede") == "linkedin":

            print("🚀 Publicando no LinkedIn...")

            sucesso = publicar_linkedin(
                user["id"],
                conteudo
            )

            if not sucesso:

                print("❌ Falha publicação LinkedIn")

                supabase.table("posts").update({
                "status": "erro"
                }).eq(
                "id",
                post["id"]
                ).execute()

                return

        # =========================
        # INSTAGRAM
        # =========================

        elif post.get("rede") == "instagram":

            print("🚀 Instagram em integração")

        else:

            print("❌ Rede social inválida")

        # =========================
        # ALTERAR STATUS
        # =========================

        supabase.table("posts").update({
            "status": "executado"
        }).eq(
            "id",
            post["id"]
        ).execute()

        # =========================
        # INCREMENTAR USO
        # =========================

        usuario = supabase.table("users") \
            .select("*") \
            .eq("id", user["id"]) \
            .execute()

        if usuario.data:

            u = usuario.data[0]

            novo_total = u.get(
                "posts_usados",
                0
            ) + 1

            supabase.table("users").update({
                "posts_usados": novo_total
            }).eq(
                "id",
                user["id"]
            ).execute()

        print("✅ Post executado")

    except Exception as e:

        print("❌ ERRO EXECUTANDO POST:", str(e))

        # salva erro no banco
        supabase.table("posts").update({
            "status": "erro"
        }).eq(
            "id",
            post["id"]
        ).execute()


# =========================
# LOOP PRINCIPAL
# =========================

def loop_executor():

    while True:

        try:

            print("\n⏰ Verificando posts pendentes...")

            # =========================
            # BUSCAR POSTS
            # =========================

            posts = supabase.table("posts") \
                .select("*") \
                .eq("status", "pendente") \
                .execute()

            posts = posts.data

            if not posts:

                print("Nenhum post pendente")

                time.sleep(10)

                continue

            # =========================
            # LOOP POSTS
            # =========================

            for post in posts:

                try:

                    user_id = post.get("user_id")

                    if not user_id:

                        print("❌ Post sem user_id")
                        continue

                    # =========================
                    # BUSCAR USER
                    # =========================

                    user_res = supabase.table("users") \
                        .select("*") \
                        .eq("id", user_id) \
                        .execute()

                    if not user_res.data:

                        print("❌ Usuário não encontrado")
                        continue

                    user = user_res.data[0]

                    # =========================
                    # VALIDAR LIMITE
                    # =========================

                    permitido = pode_publicar(user)

                    if not permitido:

                        print("🚫 Limite atingido:", user.get("email"))

                        supabase.table("posts").update({
                            "status": "bloqueado"
                        }).eq(
                            "id",
                            post["id"]
                        ).execute()

                        continue

                    # =========================
                    # EVITAR DUPLICAÇÃO
                    # =========================

                    supabase.table("posts").update({
                        "status": "processando"
                    }).eq(
                        "id",
                        post["id"]
                    ).execute()

                    # =========================
                    # EXECUTAR
                    # =========================

                    executar_post(
                        post,
                        user
                    )

                except Exception as e:

                    print("❌ Erro no loop do post:", str(e))

        except Exception as e:

            print("❌ ERRO GERAL:", str(e))

        # =========================
        # INTERVALO
        # =========================

        time.sleep(10)


# =========================
# START
# =========================

if __name__ == "__main__":

    loop_executor()


