/**
 * users.utils.js — Utilidades compartidas del módulo de usuarios
 */
window.Sintel = window.Sintel || {};
window.Sintel.Users = window.Sintel.Users || {};

Sintel.Users.Utils = {
    /**
     * Muestra un toast de Bootstrap en la esquina superior derecha.
     * @param {string} message - Mensaje a mostrar
     * @param {string} type - 'success' | 'danger' | 'warning' | 'info'
     */
    toast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const id = `toast-${Date.now()}`;
        const icons = {
            success: 'bi-check-circle-fill text-success',
            danger:  'bi-x-circle-fill text-danger',
            warning: 'bi-exclamation-triangle-fill text-warning',
            info:    'bi-info-circle-fill text-primary',
        };
        const icon = icons[type] || icons.info;

        container.insertAdjacentHTML('beforeend', `
            <div id="${id}" class="toast align-items-center border-0 shadow-sm" role="alert" aria-live="assertive">
                <div class="d-flex">
                    <div class="toast-body d-flex align-items-center gap-2">
                        <i class="bi ${icon}"></i> ${message}
                    </div>
                    <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>`);

        const el = document.getElementById(id);
        const t  = new bootstrap.Toast(el, { delay: 4000 });
        t.show();
        el.addEventListener('hidden.bs.toast', () => el.remove());
    }
};
