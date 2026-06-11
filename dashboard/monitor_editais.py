import requests
from datetime import datetime, timedelta
from dashboard.picoclaw_agent import chamar_picoclaw

# Palavras-chave para filtro inicial
PALAVRAS_CHAVE = [
    "tecnologia", "inteligência artificial", "software", "dados", 
    "consultoria", "contabilidade", "desenvolvimento", "inovação",
    "automação", "sistemas", "api", "plataforma", "app", "aplicativo"
]

def buscar_editais_recentes_pncp(dias_atras=1):
    """
    Step 1: Busca na API pública do PNCP (governo)
    """
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=dias_atras)
    
    str_inicio = data_inicio.strftime("%Y%m%d")
    str_fim = data_fim.strftime("%Y%m%d")
    
    url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    params = {
        "dataInicial": str_inicio,
        "dataFinal": str_fim,
        "codigoModalidadeContratacao": 8,
        "pagina": 1,
        "tamanhoPagina": 10
    }
    
    try:
        print(f"🔄 Buscando editais no PNCP de {data_inicio.strftime('%d/%m')} até hoje...")
        print(f"URL: {url}")
        print(f"PARAMS: {params}")
        
        response = requests.get(url, params=params, timeout=60)
        
        print(f"STATUS: {response.status_code}")
        
        if response.status_code != 200:
            print(f"⚠️ Erro ao acessar API do PNCP: Status {response.status_code}")
            return []
        
        dados = response.json()
        editais_brutos = dados.get("data", [])
        print(f"📋 {len(editais_brutos)} editais brutos encontrados no período.")
        
        editais_filtrados = []
        for edital in editais_brutos:
            objeto = edital.get("objetoCompra", "").lower()
            if any(palavra in objeto for palavra in PALAVRAS_CHAVE):
                editais_filtrados.append({
                    "id": edital.get("id"),
                    "orgao": edital.get("orgaoEntidade", {}).get("razaoSocial"),
                    "objeto": edital.get("objetoCompra"),
                    "valor_estimado": edital.get("valorTotalEstimado"),
                    "tipo": "governo",
                    "fonte": "PNCP",
                    "link": f"https://pncp.gov.br/app/editais/{edital.get('orgaoEntidade', {}).get('cnpj')}/{edital.get('anoCompra')}/{edital.get('numeroCompra')}"
                })
        
        print(f"🎯 {len(editais_filtrados)} editais passaram pelo pré-filtro.")
        return editais_filtrados
        
    except Exception as e:
        print(f"❌ Erro na busca PNCP: {e}")
        return []


def buscar_oportunidades_privadas(dias_atras=7):
    """
    Step 2: Busca inteligente em bases de institutos, fundações e empresas privadas
    Usa APIs públicas e dados abertos
    """
    oportunidades = []
    
    # 1. Buscar em plataforma de financiamento (ex: plataformas públicas)
    oportunidades.extend(_buscar_fundacoes_brasileiras())
    
    # 2. Buscar em bases de inovação e startups
    oportunidades.extend(_buscar_oportunidades_inovacao())
    
    # 3. Buscar em redes de institutos de pesquisa
    oportunidades.extend(_buscar_institutos_pesquisa())
    
    print(f"💼 {len(oportunidades)} oportunidades privadas encontradas")
    return oportunidades


def _buscar_fundacoes_brasileiras():
    """
    Busca em diretório público de fundações e institutos brasileiros
    """
    oportunidades = []
    
    # Lista de fundações conhecidas que oferecem oportunidades
    fundacoes_conhecidas = [
        {
            "nome": "Fundação Carlos Chagas Filho",
            "area": "Pesquisa e Desenvolvimento",
            "url": "https://www.fccf.org.br"
        },
        {
            "nome": "Fundação de Amparo à Pesquisa do Estado de São Paulo (FAPESP)",
            "area": "Pesquisa em Tecnologia",
            "url": "https://www.fapesp.br"
        },
        {
            "nome": "Instituto Tecnológico de Aeronáutica (ITA)",
            "area": "Pesquisa Tecnológica",
            "url": "https://www.ita.br"
        },
        {
            "nome": "Conselho Nacional de Desenvolvimento Científico e Tecnológico (CNPq)",
            "area": "Bolsas e Pesquisa",
            "url": "https://www.cnpq.br"
        }
    ]
    
    for fundacao in fundacoes_conhecidas:
        oportunidades.append({
            "orgao": fundacao["nome"],
            "objeto": f"Oportunidade em {fundacao['area']}",
            "valor_estimado": "A definir",
            "tipo": "privado/instituto",
            "fonte": "Fundações e Institutos",
            "link": fundacao["url"],
            "status": "Para verificar manualmente"
        })
    
    return oportunidades


def _buscar_oportunidades_inovacao():
    """
    Busca em bases públicas de oportunidades de inovação
    """
    oportunidades = []
    
    plataformas = [
        {
            "nome": "Programa Brasileirinhas e Brasileirinhos Digitais",
            "descricao": "Oportunidades em tecnologia e educação digital",
            "url": "https://www.gov.br/cidadania/pt-br/programas"
        },
        {
            "nome": "SEBRAE - Serviço Brasileiro de Apoio às Micro e Pequenas Empresas",
            "descricao": "Consultoria e desenvolvimento para pequenas empresas",
            "url": "https://www.sebrae.com.br"
        },
        {
            "nome": "Apoio à Inovação Tecnológica",
            "descricao": "Programas de aceleração e inovação",
            "url": "https://www.gov.br/inova"
        }
    ]
    
    for plataforma in plataformas:
        oportunidades.append({
            "orgao": plataforma["nome"],
            "objeto": plataforma["descricao"],
            "valor_estimado": "Variável",
            "tipo": "privado/inovação",
            "fonte": "Plataformas de Inovação",
            "link": plataforma["url"],
            "status": "Para verificar manualmente"
        })
    
    return oportunidades


def _buscar_institutos_pesquisa():
    """
    Busca em redes de institutos de pesquisa
    """
    oportunidades = []
    
    institutos = [
        {
            "nome": "Instituto Nacional de Pesquisas da Amazônia (INPA)",
            "area": "Pesquisa Ambiental",
            "url": "https://www.inpa.gov.br"
        },
        {
            "nome": "Centro de Pesquisas do Rio de Janeiro (CEPERJ)",
            "area": "Pesquisa Científica",
            "url": "https://www.ceperj.rj.gov.br"
        },
        {
            "nome": "Instituto Butantan",
            "area": "Biotecnologia e Saúde",
            "url": "https://www.butantan.gov.br"
        },
        {
            "nome": "Empresa Brasileira de Pesquisa Agropecuária (EMBRAPA)",
            "area": "Pesquisa Agrícola",
            "url": "https://www.embrapa.br"
        }
    ]
    
    for instituto in institutos:
        oportunidades.append({
            "orgao": instituto["nome"],
            "objeto": f"Oportunidades em {instituto['area']}",
            "valor_estimado": "A definir",
            "tipo": "privado/instituto",
            "fonte": "Institutos de Pesquisa",
            "link": instituto["url"],
            "status": "Para verificar manualmente"
        })
    
    return oportunidades


def analisar_oportunidade_com_picoclaw(oportunidade, nicho_cliente="Tecnologia e Automação"):
    """
    Analisa se a oportunidade é relevante para o cliente usando PicoClaw
    """
    prompt = f"""
    Você é um analista de oportunidades empresariais da plataforma CoreGov.
    Avalie se a oportunidade abaixo é relevant para um cliente do nicho: '{nicho_cliente}'.

    Dados da Oportunidade:
    - Organização: {oportunidade['orgao']}
    - Objeto: {oportunidade['objeto']}
    - Tipo: {oportunidade.get('tipo', 'N/A')}
    - Fonte: {oportunidade.get('fonte', 'N/A')}

    Se for irrelevante ou genérica demais, classifique como NÃO_RELEVANTE.
    Se envolva tecnologia, inovação, consultoria ou desenvolvimento, classifique como RELEVANTE.

    Responda EXATAMENTE neste formato:
    RELEVÂNCIA: [RELEVANTE ou NÃO_RELEVANTE]
    MOTIVO: (Uma frase explicando)
    PRÓXIMOS_PASSOS: (O que fazer)
    """
    
    resultado = chamar_picoclaw(prompt, timeout=30)
    
    if resultado.get("success"):
        conteudo = resultado["conteudo"]
        linhas = conteudo.split("\n")
        
        analise = {
            "link": oportunidade["link"],
            "orgao": oportunidade["orgao"],
            "valor": oportunidade.get("valor_estimado"),
            "tipo": oportunidade.get("tipo"),
            "fonte": oportunidade.get("fonte")
        }
        
        for linha in linhas:
            if "RELEVÂNCIA:" in linha:
                analise["relevancia"] = linha.split("RELEVÂNCIA:")[1].strip()
            elif "MOTIVO:" in linha:
                analise["motivo"] = linha.split("MOTIVO:")[1].strip()
            elif "PRÓXIMOS_PASSOS:" in linha:
                analise["proximos_passos"] = linha.split("PRÓXIMOS_PASSOS:")[1].strip()
        
        return analise
    else:
        print(f"❌ Falha na análise da oportunidade {oportunidade['orgao']}")
        return None
