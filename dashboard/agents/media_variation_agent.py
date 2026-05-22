import os
import io
from PIL import Image, ImageEnhance
from supabase import create_client

# Configurações do Supabase obtidas do ambiente
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_variacao_para_supabase(buffer_imagem, nome_arquivo_variacao):
    """Envia o arquivo diretamente da memória para o Supabase Storage"""
    try:
        # Envia para o bucket que você já usa para guardar as mídias (ex: 'midias_ia' ou 'public')
        bucket_name = "media_library_bucket" 
        
        # Faz o upload dos bytes da imagem
        supabase.storage.from_(bucket_name).upload(
            path=f"variacoes/{nome_arquivo_variacao}",
            file=buffer_imagem.getvalue(),
            file_options={"content-type": "image/jpeg"}
        )
        
        # Pega a URL pública gerada
        public_url = supabase.storage.from_(bucket_name).get_public_url(f"variacoes/{nome_arquivo_variacao}")
        return public_url
    except Exception as e:
        print(f"❌ Erro no upload da variação para o Storage: {str(e)}")
        return None

def criar_e_salvar_variacoes_no_supabase(imagem_original_banco):
    """
    Pega o registro de uma imagem original vinda do banco, baixa,
    gera as variações e insere os novos links na mesma tabela.
    """
    try:
        id_pai = imagem_original_banco["id"]
        url_original = imagem_original_banco["imagem_url"]
        nicho = imagem_original_banco["nicho"]
        rede = imagem_original_banco["rede"]
        
        # Como o Pillow precisa abrir a imagem, você pode baixá-la usando a URL
        import requests
        response = requests.get(url_original)
        if response.status_code != 200:
            return 0
            
        img_original = Image.open(io.BytesIO(response.content))
        nome_base = f"img_{id_pai}"
        ext = ".jpg"
        
        variacoes = [
            {"tipo": "variacao_flip", "transform": lambda img: img.transpose(Image.FLIP_LEFT_RIGHT)},
            {"tipo": "variacao_filtro", "transform": lambda img: ImageEnhance.Contrast(img).enhance(1.15)},
        ]
        
        geradas = 0
        for i, var in enumerate(variacoes, 1):
            # Aplica a transformação de IA/Mídia
            img_alterada = var["transform"](img_original)
            
            # Salva o resultado em um buffer de memória (sem ocupar espaço no Render)
            buffer = io.BytesIO()
            img_alterada.convert('RGB').save(buffer, format="JPEG", quality=85)
            buffer.seek(0)
            
            # Envia para o Storage
            nome_arquivo = f"{nome_base}_v{i}_{var['tipo']}{ext}"
            url_publica_nova = upload_variacao_para_supabase(buffer, nome_arquivo)
            
            if url_publica_nova:
                # Salva o novo registro na MESMA tabela do banco de dados
                payload = {
                    "tema": imagem_original_banco.get("tema", "Variação Automatizada"),
                    "rede": rede,
                    "nicho": nicho,
                    "imagem_url": url_publica_nova,
                    "tipo_midia": var["tipo"],
                    "id_imagem_pai": id_pai
                }
                supabase.table("media_library").insert(payload).execute()
                geradas += 1
                
        return geradas
    except Exception as e:
        print(f"❌ Erro ao processar variações para ID {imagem_original_banco.get('id')}: {str(e)}")
        return 0
