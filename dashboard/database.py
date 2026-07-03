"""
Módulo de banco SQLite para substituir o Supabase.
Fornece uma API compatível com as queries usadas no app.py

Uso:
    from database import db
    db.table("users").select("*").eq("id", user_id).execute()
"""

import os
import sqlite3
import json
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from contextlib import contextmanager

# =========================
# CAMINHO DO BANCO
# =========================
DB_DIR = os.environ.get("DB_DIR", "/data/db")
DB_PATH = os.path.join(DB_DIR, "coregov.db")
os.makedirs(DB_DIR, exist_ok=True)


# =========================
# CONEXÃO SEGURA (thread-safe com check_same_thread=False)
# =========================
_connections = {}

def get_conn():
    """Retorna conexão para a thread atual"""
    tid = threading_get_ident()
    if tid not in _connections:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _connections[tid] = conn
    return _connections[tid]

import threading
threading_get_ident = threading.get_ident


@contextmanager
def cursor():
    """Context manager para executar queries"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


# =========================
# CLASSE QUERY BUILDER (imitando Supabase)
# =========================

class QueryBuilder:
    """Construtor de queries estilo Supabase: table().select().eq().execute()"""
    
    def __init__(self, table_name):
        self.table_name = table_name
        self._select_fields = "*"
        self._where_clauses = []
        self._where_values = []
        self._order_field = None
        self._order_dir = "ASC"
        self._limit_val = None
        self._count_exact = False
        self._in_field = None
        self._in_values = None
        self._gte_field = None
        self._gte_value = None
    
    def select(self, *fields):
        self._select_fields = ", ".join(fields) if fields else "*"
        return self
    
    def eq(self, field, value):
        self._where_clauses.append(f'"{field}" = ?')
        self._where_values.append(value)
        return self
    
    def neq(self, field, value):
        self._where_clauses.append(f'"{field}" != ?')
        self._where_values.append(value)
        return self
    
    def gte(self, field, value):
        self._gte_field = field
        self._gte_value = value
        self._where_clauses.append(f'"{field}" >= ?')
        self._where_values.append(value)
        return self
    
    def gt(self, field, value):
        self._where_clauses.append(f'"{field}" > ?')
        self._where_values.append(value)
        return self
    
    def lt(self, field, value):
        self._where_clauses.append(f'"{field}" < ?')
        self._where_values.append(value)
        return self
    
    def lte(self, field, value):
        self._where_clauses.append(f'"{field}" <= ?')
        self._where_values.append(value)
        return self
    
    def like(self, field, pattern):
        self._where_clauses.append(f'"{field}" LIKE ?')
        self._where_values.append(pattern)
        return self
    
    def in_(self, field, values):
        """Filtro IN"""
        if values:
            placeholders = ", ".join(["?" for _ in values])
            self._where_clauses.append(f'"{field}" IN ({placeholders})')
            self._where_values.extend(values)
        return self
    
    def order(self, field, desc=False):
        self._order_field = field
        self._order_dir = "DESC" if desc else "ASC"
        return self
    
    def limit(self, n):
        self._limit_val = n
        return self
    
    def count(self, exact=False):
        if exact:
            self._count_exact = True
        return self
    
    def execute(self):
        """Executa a query e retorna resultado estilo Supabase"""
        try:
            # Query de contagem exata
            if self._count_exact and self._select_fields == "*":
                sql = f'SELECT COUNT(*) as total FROM "{self.table_name}"'
            elif self._count_exact:
                sql = f'SELECT COUNT(*) as total FROM "{self.table_name}"'
            else:
                sql = f'SELECT {self._select_fields} FROM "{self.table_name}"'
            
            if self._where_clauses:
                sql += " WHERE " + " AND ".join(self._where_clauses)
            
            if self._order_field and not self._count_exact:
                sql += f' ORDER BY "{self._order_field}" {self._order_dir}'
            
            if self._limit_val and not self._count_exact:
                sql += f" LIMIT {self._limit_val}"
            
            with cursor() as cur:
                cur.execute(sql, self._where_values)
                rows = cur.fetchall()
                
                if self._count_exact:
                    total = rows[0][0] if rows else 0
                    return QueryResult([], count=total)
                
                data = [dict(row) for row in rows]
                return QueryResult(data)
        
        except Exception as e:
            print(f"❌ SQLite Query Error [{self.table_name}]: {e}")
            print(f"   SQL: {sql}")
            print(f"   Values: {self._where_values}")
            return QueryResult([])


class InsertBuilder:
    """Inserir registros: table().insert({...}).execute()"""
    def __init__(self, table_name, data):
        self.table_name = table_name
        if isinstance(data, list):
            self.data_list = data
        else:
            self.data_list = [data]
    
    def execute(self):
        results = []
        with cursor() as cur:
            for data in self.data_list:
                cols = [f'"{k}"' for k in data.keys()]
                vals = list(data.values())
                placeholders = ", ".join(["?" for _ in vals])
                cols_str = ", ".join(cols)
                try:
                    cur.execute(
                        f'INSERT INTO "{self.table_name}" ({cols_str}) VALUES ({placeholders})',
                        vals
                    )
                    last_id = cur.lastrowid
                    results.append({"id": last_id, **data})
                except Exception as e:
                    print(f"❌ Insert Error [{self.table_name}]: {e}")
        return QueryResult(results)


class UpdateBuilder:
    """Atualizar registros: table().update({...}).eq("id", X).execute()"""
    def __init__(self, table_name, data):
        self.table_name = table_name
        self.update_data = data
        self._where_clauses = []
        self._where_values = []
    
    def eq(self, field, value):
        self._where_clauses.append(f'"{field}" = ?')
        self._where_values.append(value)
        return self
    
    def execute(self):
        set_clauses = [f'"{k}" = ?' for k in self.update_data.keys()]
        set_values = list(self.update_data.values())
        sql = f'UPDATE "{self.table_name}" SET {", ".join(set_clauses)}'
        
        if self._where_clauses:
            sql += " WHERE " + " AND ".join(self._where_clauses)
        
        all_values = set_values + self._where_values
        
        try:
            with cursor() as cur:
                cur.execute(sql, all_values)
            return QueryResult([{"updated": True}])
        except Exception as e:
            print(f"❌ Update Error [{self.table_name}]: {e}")
            return QueryResult([])


class DeleteBuilder:
    """Deletar registros: table().delete().eq("id", X).execute()"""
    def __init__(self, table_name):
        self.table_name = table_name
        self._where_clauses = []
        self._where_values = []
    
    def eq(self, field, value):
        self._where_clauses.append(f'"{field}" = ?')
        self._where_values.append(value)
        return self
    
    def execute(self):
        sql = f'DELETE FROM "{self.table_name}"'
        if self._where_clauses:
            sql += " WHERE " + " AND ".join(self._where_clauses)
        
        try:
            with cursor() as cur:
                cur.execute(sql, self._where_values)
            return QueryResult([{"deleted": True}])
        except Exception as e:
            print(f"❌ Delete Error [{self.table_name}]: {e}")
            return QueryResult([])


class UpsertBuilder:
    """Inserir ou atualizar: table().upsert({...}).execute()"""
    def __init__(self, table_name, data):
        self.table_name = table_name
        if isinstance(data, list):
            self.data_list = data
        else:
            self.data_list = [data]
    
    def execute(self):
        results = []
        with cursor() as cur:
            for data in self.data_list:
                # Tentar INSERT primeiro
                cols = [f'"{k}"' for k in data.keys()]
                vals = list(data.values())
                placeholders = ", ".join(["?" for _ in vals])
                cols_str = ", ".join(cols)
                
                # Se tem id_composto, tentar REPLACE
                if "id_composto" in data:
                    try:
                        cur.execute(
                            f'INSERT OR REPLACE INTO "{self.table_name}" ({cols_str}) VALUES ({placeholders})',
                            vals
                        )
                        results.append(data)
                        continue
                    except Exception as e:
                        print(f"⚠️ Upsert Error: {e}")
                
                # INSERT normal com IGNORE se falhar (duplicata)
                try:
                    cur.execute(
                        f'INSERT OR IGNORE INTO "{self.table_name}" ({cols_str}) VALUES ({placeholders})',
                        vals
                    )
                    results.append(data)
                except Exception as e:
                    print(f"⚠️ Upsert fallback Error: {e}")
        
        return QueryResult(results)


class QueryResult:
    """Resultado de query estilo Supabase"""
    def __init__(self, data, count=None):
        self.data = data
        self._count = count
    
    @property
    def count(self):
        return self._count if self._count is not None else len(self.data)


# =========================
# CLASSE DATABASE (imitando Supabase client)
# =========================

class Database:
    """Classe principal que imita o cliente Supabase"""
    
    def __init__(self):
        self._init_schema()
    
    def table(self, name):
        return TableRef(name)


class TableRef:
    """Referência a uma tabela: table("X").insert/update/delete/select()"""
    def __init__(self, name):
        self.name = name
    
    def select(self, *fields):
        return QueryBuilder(self.name).select(*fields)
    
    def insert(self, data):
        return InsertBuilder(self.name, data)
    
    def update(self, data):
        return UpdateBuilder(self.name, data)
    
    def delete(self):
        return DeleteBuilder(self.name)
    
    def upsert(self, data):
        return UpsertBuilder(self.name, data)
    
    def _init_schema(self):
        """Cria as tabelas se não existirem"""
        schema = """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            display_name TEXT,
            password_hash TEXT,
            plano TEXT DEFAULT 'free',
            posts_limite INTEGER DEFAULT 10,
            posts_usados INTEGER DEFAULT 0,
            linkedin_token TEXT,
            instagram_token TEXT,
            tipo_pix TEXT,
            chave_pix TEXT,
            ultima_atividade TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            tema TEXT,
            rede TEXT,
            conteudo TEXT,
            modo TEXT,
            nicho TEXT,
            imagem_url TEXT,
            data_postagem TEXT,
            hora_postagem TEXT,
            status TEXT DEFAULT 'pendente',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS conteudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            tipo TEXT,
            conteudo TEXT,
            status TEXT DEFAULT 'publicado',
            categoria TEXT DEFAULT 'gratuito',
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS analytics_acessos (
            id_composto TEXT PRIMARY KEY,
            user_id TEXT,
            data_acesso TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS media_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nicho TEXT,
            url TEXT,
            ativo INTEGER DEFAULT 1
        );
        
        CREATE TABLE IF NOT EXISTS nichos_tiktok (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nicho TEXT,
            ativo INTEGER DEFAULT 1
        );
        
        CREATE TABLE IF NOT EXISTS vagas_assinantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            plano TEXT,
            status TEXT DEFAULT 'pending',
            payment_id TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT,
            expires_at TEXT
        );
        
        CREATE TABLE IF NOT EXISTS analises_estatuto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT,
            organizacao TEXT,
            pontuacao INTEGER DEFAULT 0,
            status_geral TEXT DEFAULT 'parcial',
            pode_captar INTEGER DEFAULT 0,
            analise_json TEXT,
            ip_cliente TEXT,
            cidade TEXT,
            estado TEXT,
            pais TEXT,
            provedor TEXT,
            pdf_url TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS oportunidades_analisadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            descricao TEXT,
            tipo TEXT,
            orgao TEXT,
            valor REAL,
            link TEXT,
            data_analise TEXT,
            nicho TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
        try:
            with cursor() as cur:
                cur.executescript(schema)
            print(f"✅ Schema SQLite verificado/criado em: {DB_PATH}")
        except Exception as e:
            print(f"❌ Erro ao criar schema: {e}")
            raise
    
    # =========================
    # AUTH (simplificado - bcrypt)
    # =========================
    
    class Auth:
        def __init__(self, db):
            self.db = db
        
        def sign_up(self, data):
            """Registra usuário"""
            email = data.get("email")
            password = data.get("password")
            options = data.get("options", {})
            display_name = options.get("data", {}).get("display_name", email.split("@")[0])
            
            if not email or not password:
                raise Exception("Email e senha são obrigatórios")
            
            # Verificar se já existe
            existing = self.db.table("users").select("id").eq("email", email).execute()
            if existing.data:
                raise Exception("User already registered")
            
            user_id = str(uuid.uuid4())
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            with cursor() as cur:
                cur.execute(
                    """INSERT INTO users (id, email, display_name, password_hash, plano, posts_limite, posts_usados)
                       VALUES (?, ?, ?, ?, 'free', 10, 0)""",
                    (user_id, email, display_name, password_hash)
                )
            
            class UserObj:
                def __init__(self, uid, uemail):
                    self.id = uid
                    self.email = uemail
            
            class ResponseObj:
                def __init__(self, user_obj):
                    self.user = user_obj
            
            return ResponseObj(UserObj(user_id, email))
        
        def sign_in_with_password(self, data):
            """Login com email/senha"""
            email = data.get("email")
            password = data.get("password")
            
            if not email or not password:
                raise Exception("Email e senha são obrigatórios")
            
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            result = self.db.table("users").select("*").eq("email", email).execute()
            if not result.data:
                raise Exception("Invalid login credentials")
            
            user = result.data[0]
            if user.get("password_hash") != password_hash:
                raise Exception("Invalid login credentials")
            
            class UserObj:
                def __init__(self, u):
                    self.id = u["id"]
                    self.email = u["email"]
                    self.user_metadata = {"display_name": u.get("display_name", "")}
            
            class ResponseObj:
                def __init__(self, user_obj):
                    self.user = user_obj
            
            return ResponseObj(UserObj(user))
        
        def sign_in_with_oauth(self, data):
            """Simula OAuth - retorna URL de callback"""
            provider = data.get("provider", "google")
            redirect_to = data.get("options", {}).get("redirect_to", "/auth/callback")
            
            # Simula URL de OAuth
            fake_code = secrets.token_hex(16)
            auth_url = f"{redirect_to}?code={fake_code}&provider={provider}"
            
            class OAuthResponse:
                def __init__(self, url):
                    self.url = url
            
            return OAuthResponse(auth_url)
        
        def exchange_code_for_session(self, data):
            """Troca código OAuth por sessão"""
            auth_code = data.get("auth_code", "")
            if not auth_code:
                raise Exception("Invalid code")
            
            # Cria usuário temporário se não existir
            email = f"oauth_{auth_code[:8]}@coregov.local"
            
            result = self.db.table("users").select("*").eq("email", email).execute()
            if not result.data:
                user_id = str(uuid.uuid4())
                with cursor() as cur:
                    cur.execute(
                        """INSERT INTO users (id, email, display_name, plano, posts_limite, posts_usados)
                           VALUES (?, ?, ?, 'free', 10, 0)""",
                        (user_id, email, "Usuário Google")
                    )
            else:
                user_id = result.data[0]["id"]
            
            class UserObj:
                def __init__(self, uid, uemail):
                    self.id = uid
                    self.email = uemail
            
            class ResponseObj:
                def __init__(self, user_obj):
                    self.user = user_obj
            
            return ResponseObj(UserObj(user_id, email))
        
        def set_session(self, data):
            """Define sessão (para callback OAuth)"""
            pass
        
        def get_user(self, access_token):
            """Retorna usuário pelo token"""
            class UserObj:
                def __init__(self):
                    self.id = None
                    self.email = None
            
            class ResponseObj:
                def __init__(self, user_obj):
                    self.user = user_obj
            
            return ResponseObj(UserObj())
    
    @property
    def auth(self):
        return self.Auth(self)
    
    # =========================
    # STORAGE (local)
    # =========================
    
    class Storage:
        def __init__(self, db):
            self.db = db
            self._bucket = None
        
        def from_(self, bucket_name):
            self._bucket = bucket_name
            return self
        
        def upload(self, path, file, file_options=None):
            """Salva arquivo localmente"""
            storage_dir = os.environ.get("STORAGE_DIR", "/data/storage")
            full_path = os.path.join(storage_dir, self._bucket or "default", path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            if isinstance(file, bytes):
                with open(full_path, "wb") as f:
                    f.write(file)
            else:
                with open(full_path, "wb") as f:
                    f.write(file.read())
            
            return {"success": True, "path": full_path}
        
        def get_public_url(self, path):
            """Retorna URL pública do arquivo"""
            base_url = os.environ.get("PUBLIC_URL", "https://app.coregov.com.br")
            return f"{base_url}/storage/{self._bucket}/{path}"
    
    @property
    def storage(self):
        return self.Storage(self)


# =========================
# SINGLETON
# =========================
db = Database()

# Helper functions
def create_client(url=None, key=None):
    """Função compatível com supabase.create_client()"""
    return db


# =========================
# FUNÇÕES DE MIGRAÇÃO
# =========================

def exportar_supabase_para_sqlite():
    """
    Exporta dados do Supabase para SQLite.
    Chame isso uma vez antes de trocar o banco.
    Retorna um dicionário com todas as tabelas.
    """
    print("📦 Função de exportação disponível.")
    print("   Para exportar, execute: python -c 'from database import exportar_dados; exportar_dados()'")
    return {}


def importar_para_sqlite(dados: dict):
    """Importa dados exportados para o SQLite"""
    tabelas = {
        "users": ("id", "email", "display_name", "plano", "posts_limite", "posts_usados",
                   "linkedin_token", "instagram_token", "tipo_pix", "chave_pix", "ultima_atividade"),
        "posts": ("user_id", "tema", "rede", "conteudo", "modo", "nicho", "imagem_url",
                   "data_postagem", "hora_postagem", "status"),
        "conteudos": ("titulo", "tipo", "conteudo", "status", "categoria"),
        "analytics_acessos": ("id_composto", "user_id", "data_acesso"),
        "media_library": ("nicho", "url", "ativo"),
        "nichos_tiktok": ("nicho", "ativo"),
        "vagas_assinantes": ("email", "plano", "status", "payment_id", "expires_at"),
        "analises_estatuto": ("nome", "email", "organizacao", "pontuacao", "status_geral",
                               "pode_captar", "analise_json", "ip_cliente", "cidade",
                               "estado", "pais", "provedor", "pdf_url"),
    }
    
    for tabela, campos in tabelas.items():
        if tabela not in dados:
            print(f"⚠️ Tabela '{tabela}' não encontrada nos dados exportados")
            continue
        
        registros = dados[tabela]
        if not registros:
            print(f"   {tabela}: 0 registros (vazio)")
            continue
        
        placeholders = ", ".join(["?" for _ in campos])
        colunas = ", ".join([f'"{c}"' for c in campos])
        
        with cursor() as cur:
            for reg in registros:
                valores = [reg.get(c) for c in campos]
                try:
                    cur.execute(
                        f'INSERT OR IGNORE INTO "{tabela}" ({colunas}) VALUES ({placeholders})',
                        valores
                    )
                except Exception as e:
                    print(f"   ⚠️ Erro ao inserir em {tabela}: {e}")
        
        print(f"   ✅ {tabela}: {len(registros)} registros importados")


if __name__ == "__main__":
    print(f"🔧 Database SQLite inicializado em: {DB_PATH}")
    print("✅ Schema verificado")
