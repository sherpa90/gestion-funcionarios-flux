/**
 * Funcionalidad de acordeón para las liquidaciones por año
 * Usado en mis_liquidaciones.html y admin_funcionario_liquidaciones.html
 */

document.addEventListener('DOMContentLoaded', function () {
    // Inicializar: primer año expandido, los demás colapsados
    const years = document.querySelectorAll('[data-year]');
    years.forEach(function (year, index) {
        const yearKey = year.dataset.year;
        const content = document.getElementById('year-' + yearKey);
        const icon = document.getElementById('icon-' + yearKey);
        if (index > 0 && content) {
            content.style.display = 'none';
        } else if (icon) {
            icon.classList.add('rotate-90');
        }
    });
});

/**
 * Alterna la visibilidad de un año específico
 * @param {string} anio - El año a mostrar/ocultar
 */
function toggleYear(anio) {
    const content = document.getElementById('year-' + anio);
    const icon = document.getElementById('icon-' + anio);
    if (content.style.display === 'none') {
        content.style.display = 'block';
        icon.classList.add('rotate-90');
    } else {
        content.style.display = 'none';
        icon.classList.remove('rotate-90');
    }
}
