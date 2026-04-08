// Remova o código que estava isolado fora e use apenas esta estrutura:

document.addEventListener("DOMContentLoaded", function() {
    const sessionId = window.location.pathname.split('/').pop();

    function sendData(payload) {
        fetch(`/dashboard/session/autosave/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(res => console.log("Auto-saved:", payload));
    }

    // 1. Campos Globais
    document.querySelectorAll('input[type="text"], textarea').forEach(el => {
        el.addEventListener('blur', function() { 
            const achCard = this.closest('.achievement-card');
            if (achCard) {
                const achId = achCard.querySelector('.trigger-radio').name.split('_')[1];
                sendData({ 
                    achievement_id: achId, 
                    note: achCard.querySelector('.trigger-note').value,
                    link: achCard.querySelector('.trigger-link').value 
                });
            } else if (!this.classList.contains('autosave-checklist')) {
                // Salva Emulator, Core, Hash
                sendData({ [this.name]: this.value });
            }
        });
    });

    // 2. Rádios de Conquista
    document.querySelectorAll('.trigger-radio').forEach(radio => {
        radio.addEventListener('change', function() {
            const achId = this.name.split('_')[1];
            sendData({ achievement_id: achId, status: this.value });
            
            const box = this.closest('.card-body').querySelector('.evidence-box');
            if (this.value !== 'OK') box.classList.remove('d-none');
            else box.classList.add('d-none');
        });
    });

    // 3. O CHECKLIST AGORA DENTRO DO BLOCO PRINCIPAL
    document.querySelectorAll('.autosave-checklist').forEach(el => {
        el.addEventListener('change', function() {
            const payload = {};
            document.querySelectorAll('.autosave-checklist').forEach(input => {
                payload[input.name] = input.type === 'checkbox' ? input.checked : input.value;
            });
            sendData({ checklist_data: JSON.stringify(payload) });
        });
    });

    // Monitorar o Switch de Collab
    const collabSwitch = document.getElementById('is_collab');
    if (collabSwitch) {
        collabSwitch.addEventListener('change', function() {
            sendData({ is_collab: this.checked });
        });
    }

});