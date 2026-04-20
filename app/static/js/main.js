document.addEventListener("DOMContentLoaded", function() {


    if (window.location.pathname.includes('/session/')) {
        const sessionId = window.location.pathname.split('/').pop();
        function sendData(payload) {
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

            fetch(`/dashboard/session/autosave/${sessionId}`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(payload)
            }).then(res => console.log("Auto-saved:", payload));
        }
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

    // 5. Monitorar o Cadeado (Lock Team)
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
            
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            
            fetch(`/dashboard/session/validate_hash/${sessionId}`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken // CRACHÁ ESTÁ AQUI
                },
                body: JSON.stringify({ hash: hashValue })
            })
            .then(res => {
                if(!res.ok) throw new Error("Erro de comunicação com o servidor");
                return res.json();
            })
            .then(data => {
                
                if (data.empty) {
                    hashStatus.innerHTML = '<i class="bi bi-question-circle text-muted"></i>';
                } else if (data.valid === true) {
                    hashStatus.innerHTML = '<span class="text-success fw-bold me-1"></span><i class="bi bi-check-lg text-success"></i>';
                } else {
                    hashStatus.innerHTML = '<span class="text-danger fw-bold me-1"></span><i class="bi bi-x-lg text-danger"></i>';
                }
            })
            .catch(err => {
                console.error("Erro no Javascript:", err);
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

    // 7. Filtro de Pesquisa Universal para Tabelas
    const searchInputs = document.querySelectorAll('.table-search');
    searchInputs.forEach(input => {
        input.addEventListener('input', function() {
            const term = this.value.toLowerCase();
            const targetTable = document.querySelector(this.getAttribute('data-target'));
            if (!targetTable) return;

            const rows = targetTable.querySelectorAll('tbody tr');
            rows.forEach(row => {
                if (row.querySelector('td') && row.querySelector('td').colSpan > 1) return; 
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(term) ? '' : 'none';
            });
        });
    });

    // 8. Auto-expandir as caixas de texto
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        const autoResize = function() {
            this.style.height = 'auto'; 
            this.style.height = this.scrollHeight + 'px'; 
        };

        textarea.addEventListener('input', autoResize);
        setTimeout(() => autoResize.call(textarea), 0);
    });

});