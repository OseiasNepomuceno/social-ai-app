import os
import unicodedata
from openai import OpenAI

from dashboard.agents.image_agent import gerar_imagem

print("🚀 IA ENGINE INICIADA")

def normalizar_texto(texto):
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = texto.replace(" ", "")
    return texto

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
        nicho_norm = normalizar_texto(nicho)
        dist = distancia_levenshtein(entrada_norm, nicho_norm)
        if dist < menor_distancia:
            menor_distancia = dist
            melhor_nicho = nicho
    return melhor_nicho

def mapear_nicho_escolhido(nicho_escolha, lista_nichos):
    if isinstance(nicho_escolha, int) or (isinstance(nicho_escolha, str) and nicho_escolha.isdigit()):
        idx = int(nicho_escolha) - 1
        if 0 <= idx < len(lista_nichos):
            return lista_nichos[idx]
    return encontrar_nicho_mais_proximo(str(nicho_escolha), lista_nichos)

def gerar_conteudo(tema, rede, modo_escolha, nicho_escolha):
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise Exception("GROQ_API_KEY não configurada")

        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

        # Mapeamento modos e lista completa de nichos
        modos = {
            "1": "viral",
            "2": "autoridade",
            "3": "vendas",
            "4": "storytelling",
            "5": "educacional"
        }
        modo_nome = modos.get(str(modo_escolha), "viral")

        lista_nichos = [
            "limpeza",
            "marketing",
            "psicologia",
            "negocios",
            "engenharia",
            "financeiro",
            "tecnologia",
            "contabilidade",
            "vendas",
            "empreendedorismo",
            "saude",
            "fotografiadealimentos",
            "fitnessbem-estar",
            "diversidadeerepresentacao",
            "viagenseturismo",
            "saudementalemindfulness",
            "alimentacao",
            "familiaerelacionamentos",
            "arquiteturaedesigndeinteriores",
            "tecnologiamergente",
            "moda",
            "educacao"
        ]

        nicho_nome = mapear_nicho_escolhido(nicho_escolha, lista_nichos)

        rede_valida = str(rede).lower()
        
        if "instagram" in rede_valida:
            persona_regra = f"Você é um especialista em Instagram, engajamento e viralização profissional. Crie um post altamente envolvente para o nicho de {nicho_nome}."
            diretrizes_rede = (
                "- Use frases curtas, dinâmicas e com forte apelo emocional.\n"
                "- Foque em gerar salvamentos, compartilhamentos e alta retenção.\n"
                "- Adote tom adequado ao modo selecionado: dinâmico e orientado ao comportamento do usuário do Instagram."
            )
            if modo_nome == "educacional":
                cta_instrucao = (
                    "Inclua a frase final: 'Quer aprender como acelerar esse processo? Comente \"EU QUERO\" abaixo que te envio o material completo direto no seu direct!'"
                )
            else:
                cta_instrucao = (
                    "Inclua a frase final: 'Quer aprender como aplicar isso no seu cenário? O link está na minha bio, clica lá para saber mais!'"
                )
        else:
            # Padrão LinkedIn
            persona_regra = f"Você é um especialista em LinkedIn e copywriting profissional de alta conversão. Faça um post para o nicho de: {nicho_nome}."
            diretrizes_rede = (
                "- Utilize linguagem natural com conexão emocional e construção de autoridade.\n"
                "- Use storytelling curto e espaçamento profissional.\n"
                "- Adapte o vocabulário ao ambiente corporativo B2B."
            )
            if modo_nome == "educacional":
                cta_instrucao = (
                    "Inclua o encerramento: 'Quer aprender como acelerar esse processo? Comente \"EU QUERO\" abaixo que te envio o material completo!'"
                )
            else:
                cta_instrucao = (
                    "Inclua o encerramento: 'Quer entender como aplicar isso no seu cenário? Clique no link da minha bio ou me envie uma mensagem no inbox para conversarmos!'"
                )

        prompt = f"""{persona_regra}

Você está criando um conteúdo no estilo '{modo_nome}'.

REGRAS:
- Não explique o que está fazendo.
- Não use rótulos como 'Título:', 'CTA:', ou 'Hashtags:'.
- Entregue o post final pronto, natural, persuasivo e humanizado.
{diretrizes_rede}
- Não faça textos excessivamente longos.
- Insira emojis estratégicos relacionados ao tema.
- O conteúdo deve parecer escrito por um especialista humano experiente em {nicho_nome}.

ESTRUTURA:
1. Gancho inicial marcante.
2. Desenvolvimento que agrega valor e conecta com a dor e solução.
3. Chamada para ação (CTA), conforme: {cta_instrucao}
4. De 3 a 5 hashtags relevantes e estratégicas para o nicho, modo e tema.

Tema do post: {tema}
Rede social: {rede}
Modo/Estilo: {modo_nome}
Nicho: {nicho_nome}
"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )

        resultado = response.choices[0].message.content.strip()

        # Formatar espaçamento profissional com parágrafos separados por linha em branco
        conteudo_formatado = "\n\n".join(
            [paragrafo.strip() for paragrafo in resultado.split("\n") if paragrafo.strip() != ""]
        )

        # Gerar imagem automática (tratamento de erro incluso)
        try:
            imagem_url = gerar_imagem(tema)
        except Exception as e:
            print(f"ERRO AO GERAR IMAGEM: {str(e)}")
            imagem_url = None

        print("✅ Conteúdo IA gerado com sucesso!")

        return {
            "success": True,
            "conteudo": conteudo_formatado,
            "imagem_url": imagem_url,
            "modo": modo_nome,
            "nicho": nicho_nome
        }

    except Exception as e:
        print(f"❌ ERRO IA ENGINE: {str(e)}")
        return {
            "success": False,
            "erro": str(e)
        }
