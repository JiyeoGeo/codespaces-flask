console.log("MEU LOGIN.JS FOI CARREGADO!");

function mostrarSenha() {

    const senha = document.getElementById("senha");

    if (senha.type === "password") {

        senha.type = "text";

    } else {

        senha.type = "password";

    }
}


const senha = document.getElementById("senha");
const aviso = document.getElementById("caps-lock");


function atualizarCapsLock(event) {

    if (event.getModifierState("CapsLock")) {

        aviso.style.display = "block";

    } else {

        aviso.style.display = "none";

    }
}


/*
 * Verifica quando uma tecla é pressionada.
 */
senha.addEventListener(
    "keydown",
    atualizarCapsLock
);


/*
 * Verifica quando a tecla é solta.
 *
 * Isso é especialmente importante para
 * detectar quando o Caps Lock foi desligado.
 */
senha.addEventListener(
    "keyup",
    atualizarCapsLock
);


/*
 * Se o usuário sair do campo de senha,
 * o aviso desaparece.
 */
senha.addEventListener(
    "blur",
    function () {
        aviso.style.display = "none";
    }
);


/*
 * Ao voltar para o campo, o aviso começa
 * oculto e será atualizado novamente
 * quando uma tecla for pressionada.
 */
senha.addEventListener(
    "focus",
    function () {
        aviso.style.display = "none";
    }
);