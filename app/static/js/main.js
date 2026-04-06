document.addEventListener("DOMContentLoaded", function() {
    console.log("Sistema de Auto-save ativo!");

    // Pega o ID da sessão da URL (ex: /dashboard/session/5 -> 5)
    const sessionId = window.location.pathname.split('/').pop();

    function sendData(payload) {
        fetch(`/dashboard/session/autosave/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => console.log("Dados salvos:", payload))
        .catch(error => console.error("Erro ao salvar:", error));
    }

    // 1. Monitorar campos globais (Core, Hash)
    document.querySelectorAll('.row.g-3 input').forEach(input => {
        input.addEventListener('blur', function() {
            // O nome do campo no input deve ser 'core' ou 'hash_used' no HTML
            sendData({ [this.name]: this.value });
        });
    });

    // 2. Monitorar o Switch de Collab
    const collabSwitch = document.getElementById('is_collab');
    if (collabSwitch) {
        collabSwitch.addEventListener('change', function() {
            sendData({ is_collab: this.checked });
        });
    }

    // 3. Monitorar Conquistas (Rádios, Notas e Links)
    document.querySelectorAll('.achievement-card').forEach(card => {
        const achId = card.querySelector('.trigger-radio').name.split('_')[1];

        // Rádios
        card.querySelectorAll('.trigger-radio').forEach(radio => {
            radio.addEventListener('change', function() {
                sendData({ 
                    achievement_id: achId, 
                    status: this.value 
                });
                
                // Mostrar/esconder caixa de evidência
                const evidenceBox = card.querySelector('.evidence-box');
                if (this.value !== 'OK') evidenceBox.classList.remove('d-none');
                else evidenceBox.classList.add('d-none');
            });
        });

        // Notas e Links (salva ao sair do campo)
        card.querySelectorAll('.trigger-note, .trigger-link').forEach(input => {
            input.addEventListener('blur', function() {
                const note = card.querySelector('.trigger-note').value;
                const link = card.querySelector('.trigger-link').value;
                sendData({ 
                    achievement_id: achId, 
                    note: note, 
                    link: link 
                });
            });
        });
    });
});

// Monitorar mudanças no Checklist
document.querySelectorAll('.autosave-checklist').forEach(el => {
    el.addEventListener('change', function() {
        const payload = {};
        // Captura todos os estados do checklist de uma vez
        document.querySelectorAll('.autosave-checklist').forEach(input => {
            payload[input.name] = input.type === 'checkbox' ? input.checked : input.value;
        });
        sendData({ checklist_data: JSON.stringify(payload) });
    });
});