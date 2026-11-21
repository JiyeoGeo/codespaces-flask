
document.addEventListener("DOMContentLoaded", () => {

    // Mostrar ou ocultar senha
    document.querySelectorAll("[data-toggle-password]").forEach((botao) => {
        botao.addEventListener("click", () => {
            const campo = document.getElementById(
                botao.dataset.togglePassword
            );

            if (!campo) return;

            campo.type =
                campo.type === "password" ? "text" : "password";

            botao.setAttribute(
                "aria-label",
                campo.type === "password"
                    ? "Exibir senha"
                    : "Ocultar senha"
            );
        });
    });

    // Detecção do Caps Lock
    const campoSenha = document.getElementById("senha");
    const aviso = document.getElementById("caps-lock");

    if (!campoSenha || !aviso) return;

    let campoEmFoco = false;
    let capsLockAtivo = false;

    function atualizarAviso() {
        aviso.hidden = !(campoEmFoco && capsLockAtivo);
    }

    function verificarCapsLock(evento) {
        if (evento.key === "CapsLock") {
            capsLockAtivo = evento.type === "keydown"
                ? !capsLockAtivo
                : capsLockAtivo;

            atualizarAviso();
            return;
        }

        if (typeof evento.getModifierState === "function") {
            capsLockAtivo = evento.getModifierState("CapsLock");
            atualizarAviso();
        }
    }

    document.addEventListener("keydown", verificarCapsLock);

    campoSenha.addEventListener("focus", () => {
        campoEmFoco = true;
        atualizarAviso();
    });

    campoSenha.addEventListener("blur", () => {
        campoEmFoco = false;
        atualizarAviso();
    });

});
