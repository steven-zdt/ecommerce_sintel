/**
 * users.table.js — Tabla de usuarios con Tabulator
 */
Sintel.Users.Table = {
    instance: null,

    init(elementId) {
        this.instance = new Tabulator(`#${elementId}`, {
            ajaxURL: '/api/v1/users/',
            ajaxConfig: {
                headers: {
                    'X-CSRFToken': Sintel.Users.API._csrfToken(),
                }
            },
            ajaxResponse(url, params, response) {
                // Soporte para listas planas o paginadas por DRF
                return Array.isArray(response) ? response : (response.results || []);
            },
            layout: 'fitColumns',
            responsiveLayout: 'collapse',
            pagination: true,
            paginationMode: 'remote',
            paginationSize: 20,
            sortMode: 'remote',
            columns: [
                { title: 'Nombre',  field: 'full_name',  widthGrow: 2 },
                { title: 'Email',   field: 'email',      widthGrow: 3 },
                {
                    title: 'Rol', field: 'role',
                    widthGrow: 1,
                    formatter: (cell) => {
                        const labels = { 1: 'Admin', 2: 'Customer', 3: 'Vendor' };
                        return labels[cell.getValue()] || cell.getValue();
                    }
                },
                {
                    title: 'Activo', field: 'is_active',
                    hozAlign: 'center', widthGrow: 1,
                    formatter: (cell) => cell.getValue()
                        ? '<span class="badge bg-success-subtle text-success">Sí</span>'
                        : '<span class="badge bg-danger-subtle text-danger">No</span>'
                },
                {
                    title: 'Acciones', field: 'id',
                    hozAlign: 'center', sortable: false, widthGrow: 1,
                    formatter: (cell) => {
                        const id   = cell.getValue();
                        const uuid = cell.getRow().getData().uuid;
                        return `
                            <div class="d-flex gap-1 justify-content-center">
                                <button class="btn btn-sm btn-light border"
                                    title="Ver detalle"
                                    onclick="Sintel.Users.UI.openDetail('${uuid}')">
                                    <i class="bi bi-eye"></i>
                                </button>
                                <button class="btn btn-sm btn-light border"
                                    title="Editar"
                                    onclick="Sintel.Users.UI.openEdit(${id})">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button class="btn btn-sm btn-danger border-0"
                                    title="Desactivar"
                                    onclick="Sintel.Users.UI.confirmDeactivate(${id})">
                                    <i class="bi bi-trash3"></i>
                                </button>
                            </div>`;
                    }
                },
            ],
        });
        return this.instance;
    },

    reload() {
        if (this.instance) this.instance.replaceData();
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('table-users')) {
        Sintel.Users.Table.init('table-users');
    }
});
