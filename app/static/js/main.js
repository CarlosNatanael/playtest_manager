document.addEventListener("DOMContentLoaded", function() {

    const isSessionPage = window.location.pathname.includes('/session/');
    const sessionId = window.location.pathname.split('/').pop();

    let globalPill = null;
    let pillTimer = null;
    let pendingRequests = 0;

    function setGlobalStatus(state) {
        if (!isSessionPage) return;
        if (!globalPill) {
            globalPill = document.createElement('div');
            globalPill.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:2000;padding:6px 14px;border-radius:20px;font-size:0.8rem;font-weight:600;display:none;box-shadow:0 2px 8px rgba(0,0,0,.5);';
            document.body.appendChild(globalPill);
        }
        clearTimeout(pillTimer);
        globalPill.style.display = 'block';
        if (state === 'saving') {
            globalPill.style.background = '#0dcaf0'; globalPill.style.color = '#000';
            globalPill.textContent = 'Saving...';
        } else if (state === 'saved') {
            globalPill.style.background = '#198754'; globalPill.style.color = '#fff';
            globalPill.textContent = 'All changes saved \u2713';
            pillTimer = setTimeout(() => { globalPill.style.display = 'none'; }, 2500);
        } else {
            globalPill.style.background = '#dc3545'; globalPill.style.color = '#fff';
            globalPill.textContent = 'Error saving! Click Save to try again.';
        }
    }

    function sendData(payload) {
        if (!isSessionPage) return Promise.resolve(false);
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

        pendingRequests++;
        setGlobalStatus('saving');

        return fetch(`/dashboard/session/autosave/${sessionId}`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        })
        .then(res => {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        })
        .then(data => {
            if (data.status !== 'success') throw new Error(data.message || 'Save failed');
            pendingRequests--;
            if (pendingRequests === 0) setGlobalStatus('saved');
            return true;
        })
        .catch(err => {
            pendingRequests--;
            console.error('Erro ao salvar:', err, payload);
            setGlobalStatus('error');
            return false;
        });
    }

    const saveUnits = [];

    function createSaveUnit(fields, anchor, getPayload, opts) {
        opts = opts || {};
        fields = fields.filter(Boolean);
        if (!fields.length || !anchor) return;

        const bar = document.createElement('div');
        bar.className = 'd-flex align-items-center justify-content-end gap-2 mt-2' + (opts.pad ? ' px-3 pb-2' : '');
        const status = document.createElement('span');
        status.className = 'small text-muted';
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-sm btn-outline-secondary fw-bold';
        btn.innerHTML = '<i class="bi bi-save"></i> Save';
        bar.appendChild(status);
        bar.appendChild(btn);
        anchor.insertAdjacentElement('afterend', bar);

        const unit = { dirty: false, saving: false };
        saveUnits.push(unit);

        function setState(state) {
            btn.classList.remove('btn-outline-secondary', 'btn-warning', 'btn-danger', 'btn-success');
            if (state === 'dirty') {
                unit.dirty = true;
                btn.classList.add('btn-warning'); status.className = 'small text-warning';
                status.textContent = 'Unsaved changes';
            } else if (state === 'saving') {
                btn.classList.add('btn-outline-secondary'); status.className = 'small text-info';
                status.textContent = 'Saving...';
            } else if (state === 'saved') {
                unit.dirty = false;
                btn.classList.add('btn-success'); status.className = 'small text-success';
                status.textContent = 'Saved \u2713';
            } else if (state === 'error') {
                unit.dirty = true;
                btn.classList.add('btn-danger'); status.className = 'small text-danger';
                status.textContent = 'Error saving - try again';
            } else {
                btn.classList.add('btn-outline-secondary'); status.className = 'small text-muted';
                status.textContent = '';
            }
        }
        setState('clean');

        function save() {
            if (unit.saving) return;
            unit.saving = true;
            setState('saving');
            sendData(getPayload()).then(ok => {
                unit.saving = false;
                setState(ok ? 'saved' : 'error');
            });
        }

        fields.forEach(f => {
            f.addEventListener('input', () => setState('dirty'));
            // Autosave de segurança ao sair do campo (só se houver mudanças)
            f.addEventListener('blur', () => { if (unit.dirty) save(); });
            // Enter em campos de uma linha também salva
            if (f.tagName === 'INPUT') {
                f.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); save(); } });
            }
        });
        btn.addEventListener('click', save);
    }

    // Avisa se o tester tentar sair com texto não salvo
    window.addEventListener('beforeunload', function(e) {
        if (saveUnits.some(u => u.dirty || u.saving) || pendingRequests > 0) {
            e.preventDefault();
            e.returnValue = '';
        }
    });

    if (isSessionPage) {
        // Emulator, Core, Hash (cada um com seu botão Save)
        document.querySelectorAll('input.autosave-global[type="text"]').forEach(el => {
            const anchor = el.closest('.input-group') || el;
            createSaveUnit([el], anchor, () => ({ [el.name]: el.value }));
        });

        // Notas + link de cada conquista (um botão Save por card)
        document.querySelectorAll('.achievement-card').forEach(card => {
            const radio = card.querySelector('.trigger-radio');
            const note = card.querySelector('.trigger-note');
            const link = card.querySelector('.trigger-link');
            const box = card.querySelector('.evidence-box');
            if (!radio || !note || !link || !box) return;
            const achId = radio.name.split('_')[1];
            // Insere o controle logo depois do campo de link
            createSaveUnit([note, link], link, () => ({
                achievement_id: achId, note: note.value, link: link.value
            }));
        });

        // Observações do checklist (salvam o checklist inteiro)
        document.querySelectorAll('textarea.autosave-checklist').forEach(el => {
            createSaveUnit([el], el, collectChecklistPayload);
        });

        // Set Impressions
        const impressions = document.querySelector('textarea[name="set_impressions"]');
        if (impressions) {
            createSaveUnit([impressions], impressions, () => ({ set_impressions: impressions.value }), { pad: true });
        }
    }

    function collectChecklistPayload() {
        const payload = {};
        document.querySelectorAll('.autosave-checklist').forEach(input => {
            payload[input.name] = input.type === 'checkbox' ? input.checked : input.value;
        });
        return { checklist_data: JSON.stringify(payload) };
    }

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

    // 3. Checklist (checkboxes salvam na hora; observações têm botão Save próprio)
    document.querySelectorAll('.autosave-checklist').forEach(el => {
        if (el.tagName === 'TEXTAREA') return;
        el.addEventListener('change', function() {
            sendData(collectChecklistPayload());
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
            
            const controller = new AbortController();
            const abortTimer = setTimeout(() => controller.abort(), 15000);

            fetch(`/dashboard/session/validate_hash/${sessionId}`, {
                signal: controller.signal,
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken // CRACHÁ ESTÁ AQUI
                },
                body: JSON.stringify({ hash: hashValue })
            })
            .then(res => {
                clearTimeout(abortTimer);
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