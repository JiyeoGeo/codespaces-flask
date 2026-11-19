document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-toggle-password]").forEach((botao) => {
        botao.addEventListener("click", () => {
            const campo = document.getElementById(botao.dataset.togglePassword);
            if (!campo) return;
            campo.type = campo.type === "password" ? "text" : "password";
            botao.setAttribute("aria-label",
                campo.type === "password" ? "Exibir senha" : "Ocultar senha");
        });
    });

    const campoSenha = document.getElementById("senha");
    const aviso = document.getElementById("caps-lock");
    if (!campoSenha || !aviso) return;

    let capsLockAtivo = false;
    const atualizarEstado = (evento) => {
        if (evento.getModifierState) {
            capsLockAtivo = evento.getModifierState("CapsLock");
        }
        aviso.hidden = !capsLockAtivo;
    };

    // Acompanha o estado mesmo quando Caps Lock é acionado antes do foco no campo.
    document.addEventListener("keydown", atualizarEstado);
    document.addEventListener("keyup", atualizarEstado);
    campoSenha.addEventListener("keydown", atualizarEstado);
    campoSenha.addEventListener("keyup", atualizarEstado);
    campoSenha.addEventListener("focus", () => {
        aviso.hidden = !capsLockAtivo;
    });
    campoSenha.addEventListener("blur", () => {
        aviso.hidden = true;
    });
});
