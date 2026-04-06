document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM carregado e pronto.");

    // Seleciona todos os inputs de rádio da página
    const inputs = document.querySelectorAll('.trigger-radio');

    inputs.forEach(radio => {
        radio.onclick = function() {
            // Encontra o container da conquista (o card)
            const card = this.closest('.card-body');
            const box = card.querySelector('.evidence-box');

            console.log("Clicou em: " + this.value);

            // Se NÃO for OK, mostra a caixa vermelha
            if (this.value !== 'OK') {
                box.classList.remove('d-none');
            } else {
                box.classList.add('d-none');
                // Limpa os campos
                box.querySelector('textarea').value = '';
                box.querySelector('input').value = '';
            }
        };
    });
});

// Exemplo simples: Salvar ao clicar em "Conclude" ou periodicamente
document.querySelector('form').addEventListener('change', function() {
    console.log("Alteração detectada, progresso pronto para ser salvo.");
    // Você pode implementar um fetch aqui para salvar em background
});

document.addEventListener("DOMContentLoaded", function() {
    const sessionId = window.location.pathname.split('/').pop(); // Pega o ID da URL

    function sendData(payload) {
        fetch(`/dashboard/session/autosave/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(res => console.log("Auto-saved"));
    }

    // Salva mudanças nos inputs de texto (Core, Hash, Emulator)
    document.querySelectorAll('input[type="text"], textarea').forEach(el => {
        el.addEventListener('blur', function() { // Salva ao sair do campo (igual Excel)
            const achCard = this.closest('.achievement-card');
            if (achCard) {
                const achId = achCard.querySelector('.trigger-radio').name.split('_')[1];
                sendData({ 
                    achievement_id: achId, 
                    note: achCard.querySelector('.trigger-note').value,
                    link: achCard.querySelector('.trigger-link').value 
                });
            } else {
                sendData({ [this.name]: this.value });
            }
        });
    });

    // Salva mudanças nos botões de rádio (Status)
    document.querySelectorAll('.trigger-radio').forEach(radio => {
        radio.addEventListener('change', function() {
            const achId = this.name.split('_')[1];
            sendData({ achievement_id: achId, status: this.value });
            
            // Lógica visual de mostrar/esconder a caixa (que já tínhamos)
            const box = this.closest('.card-body').querySelector('.evidence-box');
            if (this.value !== 'OK') box.classList.remove('d-none');
            else box.classList.add('d-none');
        });
    });
});