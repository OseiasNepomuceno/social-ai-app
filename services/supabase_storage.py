import os
import uuid

from supabase import create_client
from werkzeug.utils import secure_filename

# ==========================================
# CONFIGURAÇÕES SUPABASE
# ==========================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# ==========================================
# CONFIG STORAGE
# ==========================================

BUCKET_NAME = "social-ai"

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp"
}

# ==========================================
# VALIDAR EXTENSÃO
# ==========================================

def allowed_file(filename):

    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )

# ==========================================
# UPLOAD IMAGEM
# ==========================================

def upload_image(file):

    try:

        if not file:
            return {
                "success": False,
                "error": "Nenhum arquivo enviado"
            }

        if file.filename == "":
            return {
                "success": False,
                "error": "Nome de arquivo inválido"
            }

        if not allowed_file(file.filename):
            return {
                "success": False,
                "error": "Formato não permitido"
            }

        # ==================================
        # NOME SEGURO
        # ==================================

        filename = secure_filename(
            file.filename
        )

        # ==================================
        # NOME ÚNICO
        # ==================================

        unique_filename = (
            f"{uuid.uuid4()}_{filename}"
        )

        # ==================================
        # UPLOAD SUPABASE
        # ==================================

        supabase.storage.from_(
            BUCKET_NAME
        ).upload(
            path=unique_filename,
            file=file.read(),
            file_options={
                "content-type": file.content_type
            }
        )

        # ==================================
        # URL PÚBLICA
        # ==================================

        public_url = supabase.storage.from_(
            BUCKET_NAME
        ).get_public_url(
            unique_filename
        )

        return {
            "success": True,
            "filename": unique_filename,
            "public_url": public_url
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }

# ==========================================
# DELETAR IMAGEM
# ==========================================

def delete_image(filename):

    try:

        supabase.storage.from_(
            BUCKET_NAME
        ).remove([filename])

        return {
            "success": True
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }
