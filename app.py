
import json
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask, abort, flash, redirect, render_template, request,
    send_from_directory, session, url_for
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_FILE = DATA_DIR / "database.json"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
DEFAULT_AVATAR = "static/images/default_avatar.png"
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

# --------------------------------------------------
# CONFIGURAÇÃO DO FLASK
# --------------------------------------------------

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("Configure SECRET_KEY no arquivo .env")

# Configurações de sessão
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# O Codespaces utiliza HTTPS no navegador.
app.config["SESSION_COOKIE_SECURE"] = False

# Configurações CSRF
app.config["WTF_CSRF_TIME_LIMIT"] = timedelta(hours=1)

# Uploads
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

# Ativa proteção CSRF
csrf = CSRFProtect(app)



# -------------------------------------------------------------------
# PERSISTÊNCIA JSON
# -------------------------------------------------------------------

def inicializar_arquivos():
    """Garante que os diretórios e arquivos necessários existam."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "static" / "images").mkdir(parents=True, exist_ok=True)
    if not DATABASE_FILE.exists():
        salvar_usuarios([])
    if not (BASE_DIR / DEFAULT_AVATAR).is_file():
        app.logger.warning("Imagem padrão não encontrada: %s", BASE_DIR / DEFAULT_AVATAR)


def carregar_usuarios():
    inicializar_arquivos()
    try:
        with DATABASE_FILE.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (json.JSONDecodeError, OSError):
        app.logger.exception("Não foi possível ler data/database.json")
        raise
    if not isinstance(dados, list):
        raise ValueError("A estrutura de database.json deve ser uma lista.")
    return dados


def salvar_usuarios(usuarios):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporario = DATABASE_FILE.with_suffix(".tmp")
    with temporario.open("w", encoding="utf-8") as arquivo:
        json.dump(usuarios, arquivo, ensure_ascii=False, indent=4)
    temporario.replace(DATABASE_FILE)


def proximo_id(usuarios):
    return max((int(u.get("id", 0)) for u in usuarios), default=0) + 1


def buscar_por_id(user_id, incluir_excluidos=True):
    for usuario in carregar_usuarios():
        if int(usuario.get("id", -1)) == int(user_id):
            if incluir_excluidos or not usuario.get("excluido", False):
                return usuario
    return None


def buscar_por_email(email, ignorar_id=None):
    email = (email or "").strip().lower()
    for usuario in carregar_usuarios():
        if (usuario.get("email", "").lower() == email
                and int(usuario.get("id", -1)) != int(ignorar_id or -1)):
            return usuario
    return None


def usuario_publico(usuario):
    """Remove campos de autenticação antes de enviar dados ao template."""
    if not usuario:
        return None
    return {k: v for k, v in usuario.items() if k != "senha_hash"}


def usuario_atual():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    usuario = buscar_por_id(user_id, incluir_excluidos=False)
    if not usuario:
        session.clear()
        return None
    return usuario


# Cria um administrador inicial somente quando as credenciais são
# fornecidas explicitamente no ambiente (.env / configuração do Codespaces).
def criar_admin_inicial():
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    senha = os.getenv("ADMIN_PASSWORD", "")
    if not email or not senha:
        return
    usuarios = carregar_usuarios()
    if any(u.get("funcao") == "admin" for u in usuarios):
        return
    if buscar_por_email(email):
        return
    usuarios.append({
        "id": proximo_id(usuarios),
        "nome": os.getenv("ADMIN_NAME", "Administrador"),
        "email": email,
        "senha_hash": generate_password_hash(senha, method="pbkdf2:sha256"),
        "foto_perfil": DEFAULT_AVATAR,
        "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "funcao": "admin",
        "excluido": False
    })
    salvar_usuarios(usuarios)


inicializar_arquivos()
criar_admin_inicial()


# -------------------------------------------------------------------
# AUTORIZAÇÃO
# -------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not usuario_atual():
            if request.path.startswith("/api/"):
                abort(401)
            return render_template("error.html", codigo=401,
                                   titulo="Não autorizado",
                                   mensagem="Entre na sua conta para acessar esta página."), 401
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        usuario = usuario_atual()
        if not usuario:
            return render_template("error.html", codigo=401,
                                   titulo="Não autorizado",
                                   mensagem="Entre na sua conta para continuar."), 401
        if session.get("funcao") != "admin" or usuario.get("funcao") != "admin":
            return render_template("error.html", codigo=403,
                                   titulo="Acesso restrito a administradores",
                                   mensagem="Sua conta não possui permissão para acessar esta área."), 403
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def dados_globais():
    return {"usuario_logado": usuario_publico(usuario_atual())}


# -------------------------------------------------------------------
# PÁGINAS GERAIS
# -------------------------------------------------------------------

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(BASE_DIR / "static" / "icons", "favicon(1).ico")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


# -------------------------------------------------------------------
# CADASTRO / LOGIN / LOGOUT
# -------------------------------------------------------------------

@app.route("/cadastro", methods=["GET", "POST"])
@app.route("/register", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        confirmar = request.form.get("confirmar_senha", senha)

        if not nome or not email or not senha:
            return render_template("cadastro.html", erro="Preencha todos os campos.",
                                   nome=nome, email=email)
        if senha != confirmar:
            return render_template("cadastro.html", erro="As senhas não coincidem.",
                                   nome=nome, email=email)
        if len(senha) < 8:
            return render_template("cadastro.html", erro="A senha deve ter pelo menos 8 caracteres.",
                                   nome=nome, email=email)
        if buscar_por_email(email):
            return render_template("cadastro.html", erro="E-mail já cadastrado.",
                                   nome=nome, email=email)

        usuarios = carregar_usuarios()
        usuarios.append({
            "id": proximo_id(usuarios),
            "nome": nome,
            "email": email,
            "senha_hash": generate_password_hash(senha, method="pbkdf2:sha256"),
            "foto_perfil": DEFAULT_AVATAR,
            "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "funcao": "comum",
            "excluido": False
        })
        salvar_usuarios(usuarios)
        flash("Cadastro realizado. Faça login para continuar.", "success")
        return redirect(url_for("login"))
    return render_template("cadastro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        usuario = buscar_por_email(email)

        if (usuario and not usuario.get("excluido", False)
                and check_password_hash(usuario.get("senha_hash", ""), senha)):
            session.clear()
            session["user_id"] = usuario["id"]
            session["email"] = usuario["email"]
            session["funcao"] = usuario.get("funcao", "comum")
            session.permanent = bool(request.form.get("lembrar"))
            return redirect(url_for("index"))

        return render_template("login.html",
                               erro="E-mail ou senha incorretos, ou conta desativada.",
                               email=email)
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


# -------------------------------------------------------------------
# PERFIL E EDIÇÃO DA PRÓPRIA CONTA
# -------------------------------------------------------------------

@app.route("/profile")
@app.route("/perfil")
@login_required
def profile():
    return render_template("profile.html", usuario=usuario_publico(usuario_atual()))


def salvar_foto(file_obj, user_id):
    """Valida a extensão e salva a foto na pasta static/uploads."""
    if not file_obj or not file_obj.filename:
        return None

    nome_seguro = secure_filename(file_obj.filename)
    if not nome_seguro or "." not in nome_seguro:
        raise ValueError("Nome de arquivo inválido.")

    extensao = nome_seguro.rsplit(".", 1)[-1].lower()
    if extensao not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Formato de imagem não permitido. Use PNG, JPG ou WEBP.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    nome_arquivo = f"usuario_{int(user_id)}.{extensao}"
    destino = UPLOAD_DIR / nome_arquivo
    file_obj.save(destino)
    return f"static/uploads/{nome_arquivo}"


@app.route("/perfil/editar", methods=["GET", "POST"])
@app.route("/usuarios/<int:id_usuario>/editar", methods=["GET", "POST"])
@login_required
def editar(id_usuario=None):
    atual = usuario_atual()
    alvo_id = int(id_usuario or atual["id"])
    if alvo_id != int(atual["id"]) and atual.get("funcao") != "admin":
        abort(403)
    usuarios = carregar_usuarios()
    usuario = next((u for u in usuarios if int(u["id"]) == alvo_id), None)
    if not usuario or usuario.get("excluido", False):
        abort(404)

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        nova_senha = request.form.get("senha", "")
        if not nome or not email:
            return render_template("editar.html", usuario=usuario_publico(usuario),
                                   id_usuario=alvo_id, erro="Nome e e-mail são obrigatórios.")
        if buscar_por_email(email, ignorar_id=alvo_id):
            return render_template("editar.html", usuario=usuario_publico(usuario),
                                   id_usuario=alvo_id, erro="E-mail já cadastrado.")
        usuario["nome"] = nome
        usuario["email"] = email
        # data_cadastro não é alterada na edição.
        if nova_senha:
            if len(nova_senha) < 8:
                return render_template("editar.html", usuario=usuario_publico(usuario),
                                       id_usuario=alvo_id,
                                       erro="A nova senha deve ter pelo menos 8 caracteres.")
            usuario["senha_hash"] = generate_password_hash(
                nova_senha, method="pbkdf2:sha256"
            )
        foto = request.files.get("foto_perfil")
        if foto and foto.filename:
            try:
                caminho = salvar_foto(foto, alvo_id)
                if caminho:
                    usuario["foto_perfil"] = caminho
            except ValueError as erro:
                return render_template("editar.html", usuario=usuario_publico(usuario),
                                       id_usuario=alvo_id, erro=str(erro))
        salvar_usuarios(usuarios)
        if alvo_id == int(session["user_id"]):
            session["email"] = email
        flash("Dados atualizados com sucesso.", "success")
        return redirect(url_for("profile") if alvo_id == int(session["user_id"])
                        else url_for("admin_dashboard"))
    return render_template("editar.html", usuario=usuario_publico(usuario),
                           id_usuario=alvo_id)


@app.route("/perfil/excluir", methods=["POST"])
@login_required
def excluir_propria_conta():
    atual_id = int(session["user_id"])
    usuarios = carregar_usuarios()
    for usuario in usuarios:
        if int(usuario["id"]) == atual_id:
            usuario["excluido"] = True
            break
    salvar_usuarios(usuarios)
    session.clear()
    flash("Sua conta foi desativada.", "success")
    return redirect(url_for("index"))


# Compatibilidade com a rota de exclusão existente, agora com exclusão lógica.
@app.route("/usuarios/<int:id_usuario>/excluir", methods=["POST"])
@login_required
def excluir(id_usuario):
    if int(id_usuario) == int(session["user_id"]):
        return excluir_propria_conta()
    atual = usuario_atual()
    if not atual or atual.get("funcao") != "admin":
        abort(403)
    return alterar_status_usuario(id_usuario, True)


# -------------------------------------------------------------------
# ADMINISTRAÇÃO
# -------------------------------------------------------------------

def alterar_status_usuario(user_id, excluido):
    usuarios = carregar_usuarios()
    encontrado = False
    for usuario in usuarios:
        if int(usuario["id"]) == int(user_id):
            usuario["excluido"] = bool(excluido)
            encontrado = True
            break
    if not encontrado:
        abort(404)
    salvar_usuarios(usuarios)
    flash("Conta atualizada.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin")
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    usuarios = carregar_usuarios()
    ativos = [u for u in usuarios if not u.get("excluido", False)]
    return render_template(
        "admin_dashboard.html",
        usuarios=[usuario_publico(u) for u in usuarios],
        total=len(usuarios),
        ativos=len(ativos),
        excluidos=len(usuarios) - len(ativos),
        administradores=sum(1 for u in ativos if u.get("funcao") == "admin")
    )


@app.route("/admin/usuarios/novo", methods=["GET", "POST"])
@admin_required
def admin_novo_usuario():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        funcao = request.form.get("funcao", "comum")
        if funcao not in {"comum", "admin"}:
            funcao = "comum"
        if not nome or not email or len(senha) < 8:
            return render_template("admin_usuario.html",
                                   erro="Informe nome, e-mail e senha com pelo menos 8 caracteres.")
        if buscar_por_email(email):
            return render_template("admin_usuario.html", erro="E-mail já cadastrado.")
        usuarios = carregar_usuarios()
        usuarios.append({
            "id": proximo_id(usuarios), "nome": nome, "email": email,
            "senha_hash": generate_password_hash(senha, method="pbkdf2:sha256"),
            "foto_perfil": DEFAULT_AVATAR,
            "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "funcao": funcao, "excluido": False
        })
        salvar_usuarios(usuarios)
        flash("Usuário criado.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_usuario.html")


@app.route("/admin/usuarios/<int:user_id>/status", methods=["POST"])
@admin_required
def admin_status_usuario(user_id):
    usuario = buscar_por_id(user_id)
    if not usuario:
        abort(404)
    novo_status = request.form.get("excluido") == "true"
    if int(user_id) == int(session["user_id"]) and novo_status:
        flash("Você não pode desativar sua própria conta por esta tela.", "error")
        return redirect(url_for("admin_dashboard"))
    return alterar_status_usuario(user_id, novo_status)


@app.route("/admin/usuarios/<int:user_id>/funcao", methods=["POST"])
@admin_required
def admin_alterar_funcao(user_id):
    funcao = request.form.get("funcao")
    if funcao not in {"admin", "comum"}:
        abort(400)
    if int(user_id) == int(session["user_id"]) and funcao != "admin":
        flash("Não é permitido remover sua própria função administrativa.", "error")
        return redirect(url_for("admin_dashboard"))
    usuarios = carregar_usuarios()
    for usuario in usuarios:
        if int(usuario["id"]) == int(user_id):
            usuario["funcao"] = funcao
            salvar_usuarios(usuarios)
            flash("Função atualizada.", "success")
            return redirect(url_for("admin_dashboard"))
    abort(404)


# Rotas antigas de listagem/consulta permanecem, mas agora são exclusivas do admin.
@app.route("/usuarios")
@admin_required
def listar():
    return redirect(url_for("admin_dashboard"))


@app.route("/usuarios/<int:id_usuario>")
@admin_required
def consultar(id_usuario):
    usuario = buscar_por_id(id_usuario)
    if not usuario:
        abort(404)
    return render_template("usuario.html", id_usuario=id_usuario,
                           usuario=usuario_publico(usuario))


# -------------------------------------------------------------------
# CALCULADORA MATEMÁTICA (preservada)
# -------------------------------------------------------------------

@app.route("/calcular", methods=["POST"])
def calcular():
    try:
        op = request.form["op"]
        a = float(request.form["a"])
        b = float(request.form["b"])
    except (KeyError, ValueError):
        abort(400)
    return redirect(url_for("math", op=op, a=a, b=b))


@app.route("/math/<op>/<float(signed=True):a>/<float(signed=True):b>")
def math(op, a, b):
    operacoes = {
        "soma": (a + b, "Soma", "+"),
        "subtracao": (a - b, "Subtração", "-"),
        "multiplicacao": (a * b, "Multiplicação", "×")
    }
    if op == "divisao":
        resultado = "Não é possível dividir por zero." if b == 0 else a / b
        nome, simbolo = "Divisão", "÷"
    elif op in operacoes:
        resultado, nome, simbolo = operacoes[op]
    else:
        abort(400)
    return render_template("math.html", nome=nome, simbolo=simbolo,
                           a=a, b=b, resultado=resultado)


# -------------------------------------------------------------------
# CALCULADORA DE IMC (preservada e com persistência no perfil)
# -------------------------------------------------------------------

@app.route("/calcular-imc", methods=["POST"])
@login_required
def calcular_imc():
    try:
        peso = float(request.form["peso"])
        altura = float(request.form["altura"]) / 100
        idade = int(request.form["idade"])
        sexo = request.form["sexo"]
    except (KeyError, ValueError):
        abort(400)
    if peso <= 0 or not 0.5 <= altura <= 2.5 or idade <= 0 or sexo not in {"masculino", "feminino"}:
        abort(400)

    usuarios = carregar_usuarios()
    for usuario in usuarios:
        if int(usuario["id"]) == int(session["user_id"]):
            usuario.update({"peso": peso, "altura": altura, "idade": idade, "sexo": sexo})
            break
    salvar_usuarios(usuarios)
    return redirect(url_for("imc", peso=peso, altura=altura, idade=idade, sexo=sexo))


@app.route("/imc/<float:peso>/<float:altura>/<int:idade>/<sexo>")
@login_required
def imc(peso, altura, idade, sexo):
    if altura <= 0 or sexo not in {"masculino", "feminino"}:
        abort(400)
    valor_imc = peso / (altura ** 2)
    if valor_imc < 18.5:
        classificacao, cor = "Magreza", "azul"
    elif valor_imc < 25:
        classificacao, cor = "Normal", "verde"
    elif valor_imc < 30:
        classificacao, cor = "Sobrepeso", "amarelo"
    else:
        classificacao, cor = "Obesidade", "vermelho"

    minimo, maximo = 10, 40
    posicao = max(0, min(100, ((valor_imc - minimo) / (maximo - minimo)) * 100))
    peso_minimo = 18.5 * (altura ** 2)
    peso_maximo = 24.9 * (altura ** 2)
    gordura = (1.20 * valor_imc + 0.23 * idade -
               (16.2 if sexo == "masculino" else 5.4))

    if sexo == "masculino":
        limites = [(2, "Essencial"), (6, "Atlético"), (14, "Fitness"),
                   (25, "Aceitável")]
    else:
        limites = [(10, "Essencial"), (14, "Atlético"), (21, "Fitness"),
                   (32, "Aceitável")]
    gordura_classificacao = next((nome for limite, nome in limites if gordura < limite),
                                 "Obesidade")
    recomendacoes = {
        "Essencial": "Essa faixa representa uma quantidade mínima de gordura corporal necessária para funções do organismo.",
        "Atlético": "A estimativa está na faixa classificada como atlética pela referência utilizada.",
        "Fitness": "A estimativa está na faixa classificada como fitness pela referência utilizada.",
        "Aceitável": "A estimativa está dentro da faixa considerada aceitável pela referência utilizada.",
        "Obesidade": "A estimativa está acima da faixa considerada aceitável pela referência utilizada. Para uma avaliação real, procure orientação profissional."
    }
    return render_template(
        "imc.html", peso=peso, altura=altura, idade=idade, sexo=sexo,
        imc=valor_imc, classificacao=classificacao, cor=cor,
        peso_minimo=peso_minimo, peso_maximo=peso_maximo,
        gordura=gordura, gordura_classificacao=gordura_classificacao,
        recomendacao=recomendacoes[gordura_classificacao],
        posicao_ponteiro=posicao
    )


@app.errorhandler(404)
def pagina_nao_encontrada(_erro):
    return render_template("error.html", codigo=404,
                           titulo="Página não encontrada",
                           mensagem="A página solicitada não existe."), 404


@app.errorhandler(413)
def arquivo_muito_grande(_erro):
    return render_template("error.html", codigo=413,
                           titulo="Arquivo muito grande",
                           mensagem="A imagem deve ter no máximo 5 MB."), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")