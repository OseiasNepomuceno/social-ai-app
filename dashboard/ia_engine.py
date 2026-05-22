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
        # LOGICA DO CTA DINÂMICO
        # =========================
        if modo_nome in ["autoridade", "viral"]:
            cta_instrucao = (
                "Crie um fechamento estimulando o engajamento direto na publicação. "
                "Termine obrigatoriamente a última linha do texto com a frase exata: "
                "'Quer aprender como acelerar esse processo? Comente \"EU QUERO\" abaixo que te envio o material completo!'"
            )
        else:
            cta_instrucao = (
                "Direcione o leitor para tomar uma ação imediata de contato. "
                "Termine obrigatoriamente a última linha do texto com a frase exata: "
                "'Quer entender como aplicar isso no seu cenário? Clique no link da minha bio ou me envie uma mensagem no inbox para conversarmos!'"
            )

        # =========================
        # PROMPT FINAL OTIMIZADO
        # =========================

        prompt = f"""
{prompt_base}

{prompt_modo}

{prompt_nicho}

Você é um especialista em {rede.capitalize()} e copywriting profissional de alta conversão.
Seu objetivo é criar um post HUMANIZADO, moderno, persuasivo e adaptado exatamente para o nicho de: {nicho_nome}.

REGRAS OBRIGATÓRIAS E ESTRITAS:
- NÃO explique o que está fazendo, não dê introduções nem conclusões textuais adicionais.
- NUNCA use rótulos explicativos como "Título:", "Desenvolvimento:", "CTA:" ou "Hashtags:".
- Entregue apenas o texto final do post pronto para copiar e colar.
- Texto humano, natural, gerando conexão emocional e foco em autoridade.
- Use storytelling curto e espaçamento profissional (linhas em branco entre parágrafos curtos para leitura escaneável).
- NÃO criar textos longos demais, respeite o limite técnico da rede social.
- Inserir emojis relacionados ao tema de forma sutil e corporativa.
- O texto deve parecer escrito por um especialista humano e nativo da área de {nicho_nome}.

ESTRUTURA DO POST:
1. Gancho Forte: Uma frase impactante na primeira linha que gere curiosidade ou toque numa dor do segmento.
2. Desenvolvimento: História curta, dado relevante ou reflexão prática sobre o tema: {tema}.
3. Autoridade: Posicionamento que demonstre domínio técnico sobre o assunto.
4. Chamada para Ação (CTA) Obrigatória: {cta_instrucao}
5. Hashtags: Insira de 3 a 5 hashtags altamente estratégicas e contextualizadas, separadas por espaço simples.

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
        # IA (LLAMA 3.3 VIA GROQ)
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
