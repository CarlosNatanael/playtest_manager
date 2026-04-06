document.addEventListener("DOMContentLoaded", function() {
    console.log("JS Carregado!");

    // Seleciona todos os botões de rádio das conquistas
    const triggerRadios = document.querySelectorAll('.trigger-radio');

    triggerRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            // Sobe até o card da conquista e procura a evidence-box
            const cardBody = this.closest('.card-body');
            const evidenceBox = cardBody.querySelector('.evidence-box');

            if (this.value === 'ERROR') {
                evidenceBox.classList.remove('d-none');
            } else {
                evidenceBox.classList.add('d-none');
            }
        });
    });
});