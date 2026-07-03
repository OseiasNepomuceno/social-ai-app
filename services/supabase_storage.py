"""
Storage adaptável: Supabase (nuvem) ou local (SQLite mode).
Usa o db_adapter para escolher automaticamente.
"""
import os
import uuid

from werkzeug.utils import secure_filename

# ==========================================
# VERIFICAR MODO
# ==========================================
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() in ("true", "1", "yes")

if USE_SQLITE:
    BUCKET_NAME = "coregov-local"
    STORAGE_BASE = os.environ.get("STORAGE_DIR", "/data/storage")
else:
    from supabase import create_client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    BUCKET_NAME = "social-ai"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_EXTENSIONS_FILE = {"pdf", "doc", "docx", "txt"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_image(file):
    """Upload de imagem - compatível com Supabase e local"""
    try:
        if not file or file.filename == "":
            return {"success": False, "error": "Arquivo inválido"}

        if not allowed_file(file.filename):
            return {"success": False, "error": "Formato não permitido (use PNG, JPG, GIF, WebP)"}

        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"

        if USE_SQLITE:
            # Salvar localmente
            upload_dir = os.path.join(STORAGE_BASE, BUCKET_NAME)
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, unique_filename)
            file.save(filepath)
            public_url = f"/storage/{BUCKET_NAME}/{unique_filename}"
        else:
            # Upload no Supabase Storage
            supabase.storage.from_(BUCKET_NAME).upload(
                path=unique_filename,
                file=file.read(),
                file_options={"content-type": file.content_type}
            )
            public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(unique_filename)

        return {"success": True, "filename": unique_filename, "public_url": public_url}

    except Exception as e:
        return {"success": False, "error": str(e)}


def upload_file(filepath, destination_path):
    """Upload de arquivo genérico (PDF, etc.) - retorna {public_url}"""
    try:
        if USE_SQLITE:
            upload_dir = os.path.join(STORAGE_BASE, BUCKET_NAME, os.path.dirname(destination_path))
            os.makedirs(upload_dir, exist_ok=True)
            dest = os.path.join(upload_dir, os.path.basename(destination_path))
            
            import shutil
            shutil.copy2(filepath, dest)
            public_url = f"/storage/{BUCKET_NAME}/{destination_path}"
        else:
            from supabase import create_client as cc
            s = cc(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
            with open(filepath, "rb") as f:
                s.storage.from_(BUCKET_NAME).upload(
                    path=destination_path,
                    file=f.read(),
                    file_options={"content-type": "application/pdf"}
                )
            public_url = s.storage.from_(BUCKET_NAME).get_public_url(destination_path)

        return {"success": True, "public_url": public_url}

    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_image(filename):
    """Deletar imagem"""
    try:
        if USE_SQLITE:
            filepath = os.path.join(STORAGE_BASE, BUCKET_NAME, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        else:
            supabase.storage.from_(BUCKET_NAME).remove([filename])
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
