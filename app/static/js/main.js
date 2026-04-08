document.addEventListener("DOMContentLoaded", function() {
    const sessionId = window.location.pathname.split('/').pop();

    function sendData(payload) {
        fetch(`/dashboard/session/autosave/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(res => console.log("Auto-saved:", payload));
    }

    // 1. Campos Globais (Textos)
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

    // 3. Checklist
    document.querySelectorAll('.autosave-checklist').forEach(el => {
        el.addEventListener('change', function() {
            const payload = {};
            document.querySelectorAll('.autosave-checklist').forEach(input => {
                payload[input.name] = input.type === 'checkbox' ? input.checked : input.value;
            });
            sendData({ checklist_data: JSON.stringify(payload) });
        });
    });

    // 4. Monitorar o Switch de Collab
    const collabSwitch = document.getElementById('is_collab');
    if (collabSwitch) {
        collabSwitch.addEventListener('change', function() {
            sendData({ is_collab: this.checked });
        });
    }

    // 5. NOVO: Monitorar o Cadeado (Lock Team)
    const lockCollabSwitch = document.getElementById('lockCollab');
    if (lockCollabSwitch) {
        lockCollabSwitch.addEventListener('change', function() {
            sendData({ collab_locked: this.checked });
        });
    }

    // 6. Validador de Hash em Tempo Real
    const hashInput = document.getElementById('hash_input');
    const hashStatus = document.getElementById('hash_status');
    
    if (hashInput && hashStatus) {
        function checkHash(hashValue) {
            if (!hashValue.trim()) {
                hashStatus.innerHTML = '<i class="bi bi-question-circle text-muted" title="Waiting for hash..."></i>';
                return;
            }
            
            // Coloca um ícone a girar a dizer "a carregar"
            hashStatus.innerHTML = '<div class="spinner-border spinner-border-sm text-info" role="status"></div>';
            
            fetch(`/dashboard/session/validate_hash/${sessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hash: hashValue })
            })
            .then(res => res.json())
            .then(data => {
                if (data.empty) {
                    hashStatus.innerHTML = '<i class="bi bi-question-circle text-muted"></i>';
                } else if (data.valid) {
                    hashStatus.innerHTML = '<i class="bi bi-check-circle-fill text-success fs-5" title="Valid Hash!"></i>';
                } else {
                    hashStatus.innerHTML = '<i class="bi bi-x-circle-fill text-danger fs-5" title="Hash not linked to this game!"></i>';
                }
            })
            .catch(() => {
                hashStatus.innerHTML = '<i class="bi bi-exclamation-triangle-fill text-warning fs-5" title="API Error"></i>';
            });
        }

        // Valida assim que a página abre, caso já haja um hash salvo
        checkHash(hashInput.value);

        // Valida quando o tester cola ou escreve
        let typingTimer;
        hashInput.addEventListener('input', function() {
            clearTimeout(typingTimer);
            // Aguarda 800ms depois de parar de digitar para não bombardear a API
            typingTimer = setTimeout(() => {
                checkHash(this.value);
            }, 800); 
        });
    }


});