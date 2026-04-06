document.addEventListener("DOMContentLoaded", function() {
    
    // Pega todos os botões de rádio que usamos para avaliar as conquistas
    const triggerRadios = document.querySelectorAll('.trigger-radio');

    triggerRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            // Encontra o "Card" inteiro (o avô do botão) onde esse rádio foi clicado
            const cardBody = this.closest('.card-body');
            
            // Encontra a caixa de evidências específica deste Card
            const evidenceBox = cardBody.querySelector('.evidence-box');
            
            // Se o usuário marcou algo diferente de "OK" (ou seja, False ou No Trigger)
            if (this.value !== 'OK') {
                // Remove a classe que esconde (d-none) e mostra a caixa
                evidenceBox.classList.remove('d-none');
                
                // Opcional: muda a cor da borda da caixa dependendo do erro
                if (this.value === 'FALSE_TRIGGER') {
                    evidenceBox.classList.replace('border-warning', 'border-danger');
                    evidenceBox.classList.add('border-opacity-50');
                } else {
                    evidenceBox.classList.replace('border-danger', 'border-warning');
                    evidenceBox.classList.add('border-opacity-50');
                }
            } else {
                // Se marcou "OK", esconde a caixa de evidências de novo
                evidenceBox.classList.add('d-none');
                
                // Limpa os campos de texto para não enviar lixo pro banco de dados sem querer
                const noteInput = evidenceBox.querySelector('.trigger-note');
                const linkInput = evidenceBox.querySelector('.trigger-link');
                if (noteInput) noteInput.value = '';
                if (linkInput) linkInput.value = '';
            }
        });
    });
});