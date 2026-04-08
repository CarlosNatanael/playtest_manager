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
                hashStatus.innerHTML = '<i class="bi bi-question-circle text-muted"></i>';
                return;
            }
            
            hashStatus.innerHTML = '<div class="spinner-border spinner-border-sm text-info" role="status"></div>';
            
            fetch(`/dashboard/session/validate_hash/${sessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hash: hashValue })
            })
            .then(res => {
                if(!res.ok) throw new Error("Erro de comunicação com o servidor");
                return res.json();
            })
            .then(data => {
                console.log("Resposta da API Hash:", data); // Olhe o F12 no navegador!
                
                if (data.empty) {
                    hashStatus.innerHTML = '<i class="bi bi-question-circle text-muted"></i>';
                } else if (data.valid === true) {
                    // Texto Verde + Ícone
                    hashStatus.innerHTML = '<span class="text-success fw-bold me-1">OK</span><i class="bi bi-check-lg text-success"></i>';
                } else {
                    // Texto Vermelho + Ícone
                    hashStatus.innerHTML = '<span class="text-danger fw-bold me-1">X</span><i class="bi bi-x-lg text-danger"></i>';
                }
            })
            .catch(err => {
                console.error("Erro no Javascript:", err);
                // Texto Amarelo
                hashStatus.innerHTML = '<span class="text-warning fw-bold small">ERR</span>';
            });
        }

        checkHash(hashInput.value);

        let typingTimer;
        hashInput.addEventListener('input', function() {
            clearTimeout(typingTimer);
            typingTimer = setTimeout(() => { checkHash(this.value); }, 800); 
        });
    }


});