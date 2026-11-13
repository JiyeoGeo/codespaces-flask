from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session

app = Flask(__name__)

# Chave secreta: necessária para o Flask assinar o cookie da sessão
app.secret_key = "chave-secreta-do-portal"

# Tempo de vida da sessão quando ela é permanente ("Lembrar de mim")
app.permanent_session_lifetime = timedelta(minutes=30)

# FAVICON
@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        "static/icons",
        "favicon(1).ico"
    )


# =========================
# USUÁRIOS (DICIONÁRIO TEMPORÁRIO)
# =========================
# Os dados se perdem ao reiniciar o servidor.
# Os dados do IMC (peso, altura, idade, sexo) também
# ficam dentro do dicionário do próprio usuário.

usuarios = {}      # {id: {"nome": ..., "email": ..., "senha": ...}}
proximo_id = 1


def email_existe(email, ignorar_id=None):
    for id_usuario, dados in usuarios.items():
        if dados["email"] == email and id_usuario != ignorar_id:
            return True
    return False


def logado():
    return session.get("usuario_id") in usuarios


# =========================
# INÍCIO
# =========================

@app.route("/")
def index():
    return render_template("index.html")


# =========================
# SOBRE
# =========================

@app.route("/about")
def about():
    return render_template("about.html")


# =========================
# CREATE - CADASTRAR
# =========================

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    global proximo_id

    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]

        if email_existe(email):
            return render_template("cadastro.html", erro="E-mail já cadastrado.")

        usuarios[proximo_id] = {"nome": nome, "email": email, "senha": senha}
        proximo_id += 1

        return redirect(url_for("login"))

    return render_template("cadastro.html")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        for id_usuario, dados in usuarios.items():
            if dados["email"] == email and dados["senha"] == senha:

                # Guarda dados na sessão
                session["usuario_id"] = id_usuario
                session["usuario_nome"] = dados["nome"]

                # Sessão permanente (expira em 30 min) ou temporária
                # (termina ao fechar o navegador), conforme a caixa marcada
                if request.form.get("lembrar"):
                    session.permanent = True
                else:
                    session.permanent = False

                return redirect(url_for("profile"))

        return render_template("login.html", erro="E-mail ou senha incorretos.")

    return render_template("login.html")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():
    # Remove apenas as chaves do login
    session.pop("usuario_id", None)
    session.pop("usuario_nome", None)
    return redirect(url_for("login"))


# =========================
# PERFIL
# =========================

@app.route("/profile")
def profile():

    if not logado():
        return redirect(url_for("login"))

    return render_template(
        "profile.html",
        usuario=usuarios[session["usuario_id"]]
    )


# =========================
# READ - LISTAR USUÁRIOS
# =========================

@app.route("/usuarios")
def listar():
    if not logado():
        return redirect(url_for("login"))

    return render_template("usuarios.html", usuarios=usuarios)


# =========================
# READ - CONSULTAR UM USUÁRIO
# =========================

@app.route("/usuarios/<int:id_usuario>")
def consultar(id_usuario):
    if not logado():
        return redirect(url_for("login"))

    if id_usuario not in usuarios:
        return redirect(url_for("listar"))

    return render_template("usuario.html", id_usuario=id_usuario,
                           usuario=usuarios[id_usuario])


# =========================
# UPDATE - EDITAR USUÁRIO
# =========================

@app.route("/usuarios/<int:id_usuario>/editar", methods=["GET", "POST"])
def editar(id_usuario):
    if not logado():
        return redirect(url_for("login"))

    if id_usuario not in usuarios:
        return redirect(url_for("listar"))

    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]

        if email_existe(email, ignorar_id=id_usuario):
            return render_template("editar.html", id_usuario=id_usuario,
                                   usuario=usuarios[id_usuario],
                                   erro="E-mail já cadastrado.")

        # Atualiza só estes campos (os dados do IMC são mantidos)
        usuarios[id_usuario]["nome"] = nome
        usuarios[id_usuario]["email"] = email
        usuarios[id_usuario]["senha"] = senha

        # Se editou o próprio usuário, atualiza o nome guardado na sessão
        if id_usuario == session.get("usuario_id"):
            session["usuario_nome"] = nome

        return redirect(url_for("listar"))

    return render_template("editar.html", id_usuario=id_usuario,
                           usuario=usuarios[id_usuario])


# =========================
# DELETE - EXCLUIR USUÁRIO
# =========================

@app.route("/usuarios/<int:id_usuario>/excluir", methods=["POST"])
def excluir(id_usuario):
    if not logado():
        return redirect(url_for("login"))

    usuarios.pop(id_usuario, None)

    # Se excluiu a própria conta, encerra toda a sessão
    if id_usuario == session.get("usuario_id"):
        session.clear()
        return redirect(url_for("login"))

    return redirect(url_for("listar"))


# =========================
# CALCULADORA MATEMÁTICA
# =========================

@app.route("/calcular", methods=["POST"])
def calcular():

    op = request.form["op"]
    a = request.form["a"]
    b = request.form["b"]

    return redirect(
        url_for(
            "math",
            op=op,
            a=a,
            b=b
        )
    )


@app.route("/math/<op>/<float(signed=True):a>/<float(signed=True):b>")
def math(op, a, b):

    if op == "soma":

        resultado = a + b
        nome = "Soma"
        simbolo = "+"

    elif op == "subtracao":

        resultado = a - b
        nome = "Subtração"
        simbolo = "-"

    elif op == "multiplicacao":

        resultado = a * b
        nome = "Multiplicação"
        simbolo = "×"

    elif op == "divisao":

        nome = "Divisão"
        simbolo = "÷"

        if b == 0:
            resultado = "Não é possível dividir por zero."
        else:
            resultado = a / b

    else:

        return "Operação inválida."

    return render_template(
        "math.html",
        nome=nome,
        simbolo=simbolo,
        a=a,
        b=b,
        resultado=resultado
    )


# =========================
# RECEBE OS DADOS DO IMC
# =========================

@app.route("/calcular-imc", methods=["POST"])
def calcular_imc():

    if not logado():
        return redirect(url_for("login"))

    peso = float(request.form["peso"])

    # O formulário recebe centímetros.
    # O cálculo utiliza metros.
    altura = float(request.form["altura"]) / 100

    idade = int(request.form["idade"])
    sexo = request.form["sexo"]

    # Atualiza os dados do usuário logado
    usuario = usuarios[session["usuario_id"]]
    usuario["peso"] = peso
    usuario["altura"] = altura
    usuario["idade"] = idade
    usuario["sexo"] = sexo

    return redirect(
        url_for(
            "imc",
            peso=peso,
            altura=altura,
            idade=idade,
            sexo=sexo
        )
    )


# =========================
# RESULTADO DO IMC
# =========================

@app.route("/imc/<float:peso>/<float:altura>/<int:idade>/<sexo>")
def imc(peso, altura, idade, sexo):

    if not logado():
        return redirect(url_for("login"))

    # =========================
    # CÁLCULO DO IMC
    # =========================

    valor_imc = peso / (altura ** 2)

    # =========================
    # CLASSIFICAÇÃO
    # =========================

    if valor_imc < 18.5:

        classificacao = "Magreza"
        cor = "azul"

    elif valor_imc < 25:

        classificacao = "Normal"
        cor = "verde"

    elif valor_imc < 30:

        classificacao = "Sobrepeso"
        cor = "amarelo"

    else:

        classificacao = "Obesidade"
        cor = "vermelho"

    # =========================
    # POSIÇÃO DO PONTEIRO
    # =========================
    #
    # A régua visual representa
    # IMC de 10 até 40.
    #
    # Valores abaixo de 10 ficam
    # no início.
    #
    # Valores acima de 40 ficam
    # no final.
    # =========================

    IMC_MINIMO_REGUA = 10
    IMC_MAXIMO_REGUA = 40

    if valor_imc <= IMC_MINIMO_REGUA:
        posicao_ponteiro = 0

    elif valor_imc >= IMC_MAXIMO_REGUA:
        posicao_ponteiro = 100

    else:
        posicao_ponteiro = (
            (valor_imc - IMC_MINIMO_REGUA)
            / (IMC_MAXIMO_REGUA - IMC_MINIMO_REGUA)
            ) * 100

    # =========================
    # PESO DE REFERÊNCIA
    # =========================

    peso_minimo = 18.5 * (altura ** 2)
    peso_maximo = 24.9 * (altura ** 2)

    # =========================
    # FÓRMULA DE DEURENBERG
    # =========================

    if sexo == "masculino":

        gordura = (
            1.20 * valor_imc
            + 0.23 * idade
            - 16.2
        )

    else:

        gordura = (
            1.20 * valor_imc
            + 0.23 * idade
            - 5.4
        )

    # =========================
    # CLASSIFICAÇÃO DA GORDURA
    # =========================

    if sexo == "masculino":

        if gordura < 2:

            gordura_classificacao = "Essencial"

        elif gordura < 6:

            gordura_classificacao = "Atlético"

        elif gordura < 14:

            gordura_classificacao = "Fitness"

        elif gordura < 25:

            gordura_classificacao = "Aceitável"

        else:

            gordura_classificacao = "Obesidade"

    else:

        if gordura < 10:

            gordura_classificacao = "Essencial"

        elif gordura < 14:

            gordura_classificacao = "Atlético"

        elif gordura < 21:

            gordura_classificacao = "Fitness"

        elif gordura < 32:

            gordura_classificacao = "Aceitável"

        else:

            gordura_classificacao = "Obesidade"

    # =========================
    # RECOMENDAÇÕES
    # =========================

    recomendacoes = {

        "Essencial":
            "Essa faixa representa uma quantidade mínima de gordura corporal necessária para funções do organismo.",

        "Atlético":
            "A estimativa está na faixa classificada como atlética pela referência utilizada.",

        "Fitness":
            "A estimativa está na faixa classificada como fitness pela referência utilizada.",

        "Aceitável":
            "A estimativa está dentro da faixa considerada aceitável pela referência utilizada.",

        "Obesidade":
            "A estimativa está acima da faixa considerada aceitável pela referência utilizada. Para uma avaliação real, deve-se procurar orientação de um profissional de saúde."
    }

    recomendacao = recomendacoes[gordura_classificacao]

    return render_template(
        "imc.html",

        peso=peso,
        altura=altura,
        idade=idade,
        sexo=sexo,

        imc=valor_imc,
        classificacao=classificacao,
        cor=cor,

        peso_minimo=peso_minimo,
        peso_maximo=peso_maximo,

        gordura=gordura,
        gordura_classificacao=gordura_classificacao,
        recomendacao=recomendacao,

        posicao_ponteiro=posicao_ponteiro
    )


# =========================
# EXECUÇÃO
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)