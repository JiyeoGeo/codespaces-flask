from flask import Flask, render_template, request, redirect, url_for, send_from_directory

app = Flask(__name__)

# FAVICON
@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        "static/icons",
        "favicon(1).ico"
    )


# Dados do usuário durante a execução
usuario = {}


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
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    global usuario

    if request.method == "POST":

        usuario = {
            "nome": request.form["nome"],
            "email": request.form["email"],
            "senha": request.form["senha"]
        }

        return redirect(url_for("profile"))

    return render_template("login.html")


# =========================
# PERFIL
# =========================

@app.route("/profile")
def profile():

    if not usuario:
        return redirect(url_for("login"))

    return render_template(
        "profile.html",
        usuario=usuario
    )


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


@app.route("/math/<op>/<float:a>/<float:b>")
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

    global usuario

    peso = float(request.form["peso"])

    # O formulário recebe centímetros.
    # O cálculo utiliza metros.
    altura = float(request.form["altura"]) / 100

    idade = int(request.form["idade"])
    sexo = request.form["sexo"]

    # Atualiza os dados do usuário
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

    if not usuario:
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
    app.run(debug=True)