import os
from openai import OpenAI
from agents.image_agent import gerar_imagem


# =========================
# CLIENTE IA
# =========================

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

print("🚀 IA ENGINE INICIADA")


# =========================
# GERAR CONTEÚDO
# =========================

def gerar_conteudo(
    tema,
    rede,
    modo_escolha,
    nicho_escolha
):

    try:

        # =========================
        # MODOS
        # =========================

        modos = {
            "1": "viral",
            "2": "autoridade",
            "3": "vendas",
            "4": "storytelling"
        }

        modo_nome = modos.get(
            str(modo_escolha),
            "viral"
        )

        # =========================
        # NICHOS
        # =========================

        nichos = {
            "1": "contabilidade",
            "2": "advocacia",
            "3": "saude",
            "4": "marketing",
            "5": "imobiliaria",
            "6": "politica",
            "7": "gestao_negocios"
        }

        nicho_nome = nichos.get(
            str(nicho_escolha),
            "marketing"
        )

               # =========================
        # BASE DIR
        # =========================

        BASE_DIR = os.path.dirname(
            os.path.dirname(__file__)
        )

        # =========================
        # ARQUIVOS
        # =========================

        arquivo_prompt = os.path.join(
            BASE_DIR,
            "prompts",
            f"{rede}.txt"
        )

        arquivo_modo = os.path.join(
            BASE_DIR,
            "modes",
            f"{modo_nome}.txt"
        )

        arquivo_nicho = os.path.join(
            BASE_DIR,
            "nichos",
            f"{nicho_nome}.txt"
        )
        # =========================
        # LER PROMPTS
        # =========================

        with open(
            arquivo_prompt,
            "r",
            encoding="utf-8"
        ) as file:

            prompt_base = file.read()

        with open(
            arquivo_modo,
            "r",
            encoding="utf-8"
        ) as file:

            prompt_modo = file.read()

        with open(
            arquivo_nicho,
            "r",
            encoding="utf-8"
        ) as file:

            prompt_nicho = file.read()

        # =========================
        # PROMPT FINAL
        # =========================

        prompt = f"""
{prompt_base}

{prompt_modo}

{prompt_nicho}

Tema do conteúdo:
{tema}
"""

        # =========================
        # IA
        # =========================

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        resultado = response.choices[0].message.content
        imagem_url = gerar_imagem(tema)

        print("✅ Conteúdo IA gerado")

        return {
            "success": True,
            "conteudo": resultado,
            "imagem_url": imagem_url,
            "modo": modo_nome,
            "nicho": nicho_nome
        }

    except Exception as e:

        print("❌ ERRO IA ENGINE")

        print(str(e))

        return {
            "success": False,
            "erro": str(e)
        }
