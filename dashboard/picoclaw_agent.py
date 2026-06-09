import re
import difflib
import unicodedata
import requests
import os

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"


def chamar_deepseek(prompt: str, timeout: int = 90, max_tokens: int = 1500) -> dict:
    """Chama a API DeepSeek e retorna o conteúdo gerado."""
    print(f"🤖 DEEPSEEK ACIONADO — {len(prompt)} chars no prompt")

    if not DEEPSEEK_API_KEY:
        return {"success": False, "erro": "DEEPSEEK_API_KEY não configurada"}

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()

        conteudo = data["choices"][0]["message"]["content"].strip()

        # Limpa marcações desnecessárias
        conteudo = re.sub(r"\*\*(.*?)\*\*", r"\1", conteudo)  # remove **negrito**
        conteudo = re.sub(r"\*(.*?)\*", r"\1", conteudo)       # remove *itálico*
        conteudo = conteudo.strip()

        print(f"✅ DEEPSEEK RESPONDEU: {len(conteudo)} caracteres")
        return {"success": True, "conteudo": conteudo}

    except requests.exceptions.Timeout:
        print("⏱️ DEEPSEEK TIMEOUT")
        return {"success": False, "erro": "Timeout: DeepSeek demorou demais para responder"}
    except requests.exceptions.HTTPError as e:
        print(f"❌ DEEPSEEK HTTP ERRO: {e}")
        return {"success": False, "erro": f"Erro HTTP: {str(e)}"}
    except Exception as e:
        print(f"❌ DEEPSEEK EXCEÇÃO: {str(e)}")
        return {"success": False, "erro": str(e)}


def normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    ).lower()


def inferir_nicho(tema: str, lista_nichos: list) -> str:
    """Infere o nicho mais adequado para o tema dado."""
    prompt = f"""Com base no tema abaixo, identifique qual é o nicho/segmento mais adequado.
Tema: {tema}
Nichos disponíveis: {', '.join(lista_nichos)}
Responda APENAS com o nome exato do nicho da lista, sem explicações."""

    resultado = chamar_deepseek(prompt, timeout=30, max_tokens=50)
    if resultado.get("success"):
        nicho_inferido = resultado["conteudo"].strip()
        nicho_inferido_norm = normalize(nicho_inferido)
        lista_norm = [normalize(n) for n in lista_nichos]

        for i, n_norm in enumerate(lista_norm):
            if n_norm == nicho_inferido_norm:
                return lista_nichos[i]

        match = difflib.get_close_matches(nicho_inferido_norm, lista_norm, n=1, cutoff=0.6)
        if match:
            idx = lista_norm.index(match[0])
            return lista_nichos[idx]

    return lista_nichos[0]


# ─────────────────────────────────────────────
# GERAÇÃO DE POST
# ─────────────────────────────────────────────
def gerar_post(tema: str, rede: str, modo: str, nicho: str) -> dict:
    """Gera post para redes sociais (LinkedIn, Instagram, Facebook, etc.)."""
    print(f"📝 GERANDO POST: tema='{tema}' rede='{rede}' modo='{modo}' nicho='{nicho}'")

    prompt = f"""Crie um post profissional para {rede} sobre: {tema}
Nicho: {nicho}
Objetivo: {modo}
Idioma: Português do Brasil

FORMATAÇÃO OBRIGATÓRIA:
- Título impactante na primeira linha
- Uma linha em branco entre cada parágrafo
- Máximo 3 parágrafos curtos e diretos
- Emoji no início de cada parágrafo
- Hashtags relevantes na última linha (mínimo 5)
- SEM markdown como ** ou *
- Texto humanizado e conversacional
- Tom de autoridade no nicho"""

    return chamar_deepseek(prompt)


# ─────────────────────────────────────────────
# GERAÇÃO DE ROTEIRO TIKTOK
# ─────────────────────────────────────────────
def gerar_roteiro_tiktok(tema: str, nicho: str = "geral", duracao: int = 60) -> dict:
    """Gera roteiro para vídeo no TikTok."""
    print(f"🎬 GERANDO ROTEIRO TIKTOK: tema='{tema}' nicho='{nicho}' duração={duracao}s")

    prompt = f"""Crie um roteiro de vídeo para TikTok sobre: {tema}
Nicho: {nicho}
Duração alvo: {duracao} segundos
Idioma: Português do Brasil

ESTRUTURA OBRIGATÓRIA:
[GANCHO - 0 a 3s]
(frase de impacto que prende atenção imediatamente)

[PROBLEMA/CONTEXTO - 3 a 15s]
(apresente o problema ou situação que o espectador se identifica)

[DESENVOLVIMENTO - 15 a 45s]
(3 dicas ou pontos principais, cada um em 1-2 frases diretas)

[CTA FINAL - 45 a {duracao}s]
(chamada para ação: curtir, seguir, comentar ou acessar link na bio)

REGRAS:
- Linguagem informal e direta
- Frases curtas (máximo 15 palavras cada)
- SEM markdown
- Inclua sugestão de legenda e 5 hashtags no final"""

    return chamar_deepseek(prompt, max_tokens=1200)


# ─────────────────────────────────────────────
# GERAÇÃO DE CTA
# ─────────────────────────────────────────────
def gerar_cta(tema: str, nicho: str, objetivo: str, canal: str = "site") -> dict:
    """Gera Call To Action para diferentes canais."""
    print(f"📣 GERANDO CTA: tema='{tema}' nicho='{nicho}' objetivo='{objetivo}' canal='{canal}'")

    prompt = f"""Crie 5 variações de Call To Action (CTA) para: {tema}
Nicho: {nicho}
Objetivo do CTA: {objetivo}
Canal: {canal}
Idioma: Português do Brasil

PARA CADA CTA ENTREGUE:
- Título curto (máximo 8 palavras) — linha 1
- Subtítulo de apoio (máximo 15 palavras) — linha 2
- Texto do botão (máximo 4 palavras) — linha 3
- Separador: ---

REGRAS:
- Linguagem persuasiva e orientada à ação
- Use verbos de ação no imperativo
- Gere urgência ou benefício claro
- SEM markdown"""

    return chamar_deepseek(prompt, max_tokens=800)


# ─────────────────────────────────────────────
# GERAÇÃO DE E-BOOK
# ─────────────────────────────────────────────
def gerar_ebook(tema: str, nicho: str, publico_alvo: str, num_capitulos: int = 5) -> dict:
    """Gera estrutura completa e conteúdo de e-book."""
    print(f"📚 GERANDO E-BOOK: tema='{tema}' nicho='{nicho}' público='{publico_alvo}'")

    prompt = f"""Crie um e-book completo sobre: {tema}
Nicho: {nicho}
Público-alvo: {publico_alvo}
Número de capítulos: {num_capitulos}
Idioma: Português do Brasil

ESTRUTURA OBRIGATÓRIA:

TÍTULO DO E-BOOK:
(título chamativo e orientado ao benefício)

SUBTÍTULO:
(complemento que reforça o valor)

INTRODUÇÃO:
(2 parágrafos apresentando o problema e a promessa do e-book)

{"".join([f"CAPÍTULO {i+1}: [título do capítulo]{chr(10)}(3 parágrafos com conteúdo relevante, dicas práticas e exemplos){chr(10)}{chr(10)}" for i in range(num_capitulos)])}

CONCLUSÃO:
(1 parágrafo com recapitulação e CTA final)

REGRAS:
- Linguagem profissional mas acessível
- Conteúdo prático e acionável
- SEM markdown como ** ou *
- Cada capítulo com conteúdo real, não resumo"""

    return chamar_deepseek(prompt, max_tokens=3000, timeout=120)


# ─────────────────────────────────────────────
# GERAÇÃO DE INFOGRÁFICO (roteiro/texto)
# ─────────────────────────────────────────────
def gerar_infografico(tema: str, nicho: str, formato: str = "lista") -> dict:
    """Gera o conteúdo textual/roteiro para infográfico."""
    print(f"📊 GERANDO INFOGRÁFICO: tema='{tema}' nicho='{nicho}' formato='{formato}'")

    prompt = f"""Crie o conteúdo para um infográfico sobre: {tema}
Nicho: {nicho}
Formato: {formato} (pode ser: lista, processo, comparação, estatísticas, timeline)
Idioma: Português do Brasil

ESTRUTURA OBRIGATÓRIA:

TÍTULO PRINCIPAL:
(título curto e impactante, máximo 8 palavras)

SUBTÍTULO:
(complemento explicativo, máximo 12 palavras)

BLOCOS DE CONTEÚDO (mínimo 5, máximo 8):
BLOCO 1:
- Ícone sugerido: (emoji representativo)
- Título do bloco: (3-5 palavras)
- Texto: (máximo 2 frases diretas)

(repita o padrão para cada bloco)

RODAPÉ:
- Fonte/crédito sugerido
- CTA curto (máximo 6 palavras)

REGRAS:
- Informações factuais e verificáveis
- Linguagem direta e escaneável
- SEM markdown"""

    return chamar_deepseek(prompt, max_tokens=1200)


# ─────────────────────────────────────────────
# GERAÇÃO DE TEMPLATE
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# ALIASES DE COMPATIBILIDADE (legado)
# ─────────────────────────────────────────────
gerar_post_picoclaw = gerar_post
chamar_picoclaw = chamar_deepseek


def gerar_template(tipo: str, nicho: str, tema: str) -> dict:
    """Gera template reutilizável de conteúdo (post, email, legenda, etc.)."""
    print(f"📋 GERANDO TEMPLATE: tipo='{tipo}' nicho='{nicho}' tema='{tema}'")

    prompt = f"""Crie um template reutilizável de {tipo} para o nicho: {nicho}
Tema base: {tema}
Idioma: Português do Brasil

O template deve ter variáveis entre colchetes como [TEMA], [BENEFÍCIO], [NÚMERO], etc.
para que possa ser reutilizado facilmente.

ENTREGUE:
1. O template completo com variáveis
2. Exemplo preenchido com dados fictícios do nicho
3. Dicas de personalização (3 sugestões)

REGRAS:
- Template prático e profissional
- Variáveis claramente identificadas com [COLCHETES]
- SEM markdown"""

    return chamar_deepseek(prompt, max_tokens=1000)
