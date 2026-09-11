from flask import Flask, render_template, send_from_directory, request

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/sobre')
def sobre():
    return render_template('sobre.html')


@app.route('/calculadora')
def calculadora():
    return render_template('calculadora.html')


@app.route('/resultado')
def resultado():
    resultado = request.args.get('resultado')
    return render_template('resultado.html', resultado=resultado)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')


if __name__ == '__main__':
    app.run(debug=True)