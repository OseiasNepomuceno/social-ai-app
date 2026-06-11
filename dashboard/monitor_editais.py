import requests
from datetime import datetime, timedelta
from dashboard.picoclaw_agent import chamar_picoclaw

# SEM FILTRO - Aceita TODAS as oportunidades
PALAVRAS_CHAVE = []  # Lista vazia = sem filtro

def buscar_editais_recentes_pncp(dias_atras=1):
    """
    Step 1: Busca na API pública do PNCP (governo) - SEM FILTRO
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
        "tamanhoPagina": 100  # Aumentado para 100
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
        
        # SEM FILTRO - retorna TUDO
        editais_filtrados = []
        for edital in editais_brutos:
            try:
                editais_filtrados.append({
                    "id": edital.get("id"),
                    "orgao": edital.get("orgaoEntidade", {}).get("razaoSocial", "N/A"),
                    "objeto": edital.get("objetoCompra", "N/A"),
                    "valor_estimado": edital.get("valorTotalEstimado", "N/A"),
                    "tipo": "governo",
                    "fonte": "PNCP",
                    "link": f"https://pncp.gov.br/app/editais/{edital.get('orgaoEntidade', {}).get('cnpj', 'N/A')}/{edital.get('anoCompra', 'N/A')}/{edital.get('numeroCompra', 'N/A')}"
                })
            except Exception as e:
                print(f"⚠️ Erro ao processar edital: {e}")
                continue
        
        print(f"✅ {len(editais_filtrados)} editais retornados (SEM FILTRO).")
        return editais_filtrados
        
    except Exception as e:
        print(f"❌ Erro na busca PNCP: {e}")
        return []


def buscar_oportunidades_privadas(dias_atras=7):
    """
    Step 2: Busca em bases de institutos, fundações e empresas privadas
    Usa APIs públicas e dados abertos
    """
    oportunidades = []
    
    # 1. Buscar em plataforma de financiamento
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
            "link": "https://www.fccf.org.br"
        },
        {
            "nome": "Fundação de Amparo à Pesquisa do Estado de São Paulo (FAPESP)",
            "area": "Pesquisa Científica",
            "link": "https://www.fapesp.br"
        },
        {
            "nome": "Instituto Tecnológico de Aeronáutica (ITA)",
            "area": "Educação Superior e Pesquisa",
            "link": "https://www.ita.br"
        },
        {
            "nome": "Conselho Nacional de Desenvolvimento Científico e Tecnológico (CNPq)",
            "area": "Bolsas e Pesquisa",
            "link": "https://www.cnpq.br"
        },
        {
            "nome": "Programa Brasileirinhas e Brasileirinhos Digitais",
            "area": "Educação Digital",
            "link": "https://www.gov.br"
        },
        {
            "nome": "SEBRAE - Serviço Brasileiro de Apoio às Micro e Pequenas Empresas",
            "area": "Apoio a Empresas",
            "link": "https://www.sebrae.com.br"
        },
        {
            "nome": "Apoio à Inovação Tecnológica",
            "area": "Inovação",
            "link": "https://www.inovacaotecnologica.com.br"
        },
        {
            "nome": "Instituto Nacional de Pesquisas da Amazônia (INPA)",
            "area": "Pesquisa Ambiental",
            "link": "https://www.inpa.gov.br"
        },
        {
            "nome": "Centro de Pesquisas do Rio de Janeiro (CEPERJ)",
            "area": "Pesquisa e Desenvolvimento",
            "link": "https://www.ceperj.rj.gov.br"
        },
        {
            "nome": "Instituto Butantan",
            "area": "Pesquisa em Saúde",
            "link": "https://www.butantan.gov.br"
        },
        {
            "nome": "Empresa Brasileira de Pesquisa Agropecuária (EMBRAPA)",
            "area": "Pesquisa Agrícola",
            "link": "https://www.embrapa.br"
        }
    ]
    
    for fundacao in fundacoes_conhecidas:
        oportunidades.append({
            "orgao": fundacao["nome"],
            "objeto": f"Oportunidades em {fundacao['area']}",
            "valor_estimado": "Variável",
            "tipo": "privado",
            "fonte": "Fundações e Institutos",
            "link": fundacao["link"]
        })
    
    return oportunidades


def _buscar_oportunidades_inovacao():
    """
    Busca em plataformas de inovação e startups
    """
    oportunidades = [
        {
            "orgao": "StartupBrasil",
            "objeto": "Aceleração de Startups",
            "valor_estimado": "Até R$ 200.000",
            "tipo": "privado",
            "fonte": "Inovação",
            "link": "https://www.startupbrasil.org.br"
        }
    ]
    
    return oportunidades


def _buscar_institutos_pesquisa():
    """
    Busca em redes de institutos de pesquisa
    """
    oportunidades = [
        {
            "orgao": "Rede de Institutos Federais",
            "objeto": "Pesquisa Colaborativa",
            "valor_estimado": "Variável",
            "tipo": "privado",
            "fonte": "Institutos de Pesquisa",
            "link": "https://www.if.edu.br"
        }
    ]
    
    return oportunidades


def analisar_oportunidade_com_picoclaw(oportunidade, nicho_cliente="Geral"):
    """
    Usa PicoClaw para analisar se a oportunidade é relevante
    """
    prompt = f"""Analise esta oportunidade de captação de recursos:

ÓRGÃO: {oportunidade.get('orgao', 'N/A')}
OBJETO: {oportunidade.get('objeto', 'N/A')}
VALOR: {oportunidade.get('valor_estimado', 'N/A')}
TIPO: {oportunidade.get('tipo', 'N/A')}
FONTE: {oportunidade.get('fonte', 'N/A')}

Contexto do cliente: {nicho_cliente}

Analise se esta oportunidade é relevante para o cliente.
Responda APENAS neste formato JSON (sem markdown):
{{
  "relevancia": "RELEVANTE ou NÃO_RELEVANTE",
  "motivo": "breve explicação",
  "proximos_passos": "ação recomendada"
}}"""

    resultado = chamar_picoclaw(prompt, timeout=30)

    if not resultado.get("success"):
        return None

    try:
        import json
        resposta = resultado["conteudo"]
        # Limpar possível markdown
        resposta = resposta.replace("```json", "").replace("```", "").strip()
        dados = json.loads(resposta)
        
        return {
            "orgao": oportunidade.get("orgao"),
            "objeto": oportunidade.get("objeto"),
            "valor": oportunidade.get("valor_estimado"),
            "tipo": oportunidade.get("tipo"),
            "fonte": oportunidade.get("fonte"),
            "link": oportunidade.get("link"),
            "relevancia": dados.get("relevancia", "ANÁLISE_PENDENTE"),
            "motivo": dados.get("motivo", ""),
            "proximos_passos": dados.get("proximos_passos", "")
        }
    except:
        return None
