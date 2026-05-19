import os
from openai import OpenAI

from dashboard.agents.image_agent import (
    gerar_imagem
)

# =========================
# IA ENGINE
# =========================

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
        # API KEY
        # =========================

        api_key = os.getenv(
            "GROQ_API_KEY"
        )

        if not api_key:

            raise Exception(
                "GROQ_API_KEY não configurada"
            )

        # =========================
        # CLIENTE IA
        # =========================

        client = OpenAI(

            api_key=api_key,

            base_url="https://api.groq.com/openai/v1"

        )

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
        # VALIDAR ARQUIVOS
        # =========================

        arquivos = [

            arquivo_prompt,

            arquivo_modo,

            arquivo_nicho

        ]

        for arquivo in arquivos:

            if not os.path.exists(arquivo):

                raise Exception(
                    f"Arquivo não encontrado: {arquivo}"
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

REGRAS OBRIGATÓRIAS:

- Criar conteúdo profissional para LinkedIn
- Máximo de 2 parágrafos curtos
- Texto humano e persuasivo
- Linguagem natural
- NÃO criar textos longos
- NÃO ultrapassar 1200 caracteres
- Inserir emojis relacionados ao tema
- Criar título forte e chamativo
- Adicionar CTA curto no final
- Adicionar hashtags relevantes
- Separar bem os blocos do texto
- Aparência premium de marketing
- Foco em engajamento
- Foco em autoridade profissional
- Foco em conversão
- O texto deve parecer escrito por especialista humano

ESTRUTURA OBRIGATÓRIA:

[TÍTULO]

Parágrafo curto 1

Parágrafo curto 2

CTA curto

Hashtags

REGRAS DA IMAGEM:

- A imagem deve ser totalmente relacionada ao tema
- SEMPRE gerar uma imagem diferente
- NÃO reutilizar layouts
- NÃO reutilizar cores
- NÃO reutilizar composição
- NÃO reutilizar enquadramento
- NÃO reutilizar estilo visual
- NÃO reutilizar elementos gráficos
- Estilo premium corporativo
- Visual moderno
- Alta qualidade
- Formato ideal para LinkedIn
- Sem textos na imagem
- Aparência cinematográfica
- Aparência profissional
- Visual de marketing empresarial

Tema do conteúdo:
{tema}

Rede social:
{rede}

Modo:
{modo_nome}

Nicho:
{nicho_nome}
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

        resultado = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        # =========================
        # GERAR IMAGEM
        # =========================

        try:

            imagem_url = gerar_imagem(
                tema
            )

        except Exception as image_error:

            print(
                "ERRO IMAGEM:"
            )

            print(
                str(image_error)
            )

            imagem_url = None

        print(
            "✅ Conteúdo IA gerado"
        )

        return {

            "success": True,

            "conteudo": resultado,

            "imagem_url": imagem_url,

            "modo": modo_nome,

            "nicho": nicho_nome

        }

    except Exception as e:

        print(
            "❌ ERRO IA ENGINE"
        )

        print(str(e))

        return {

            "success": False,

            "erro": str(e)

        }
