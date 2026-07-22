Sintel.Services.Table = {
    init(elementId) {
        return new Tabulator(`#${elementId}`, {
            ajaxURL: "/api/v1/services/",
            ajaxConfig: { headers: { 'Authorization': `Bearer ${localStorage.getItem('access')}` } },
            layout: "fitColumns",
            pagination: "remote",
            paginationSize: 20,
            columns: [
                {title: "Servicio", field: "name"},
                {title: "Categoría", field: "category_name"},
                {title: "Tarifa Base", field: "base_price", formatter: "money", formatterParams: {symbol: "$"}},
                {title: "Activo", field: "is_active", hozAlign: "center", formatter: "tickCross"},
                {title: "Acciones", field: "uuid", sortable: false, formatter: (cell) => {
                    const uuid = cell.getValue();
                    return `
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-light" onclick="Sintel.Services.UI.openOffcanvas('detalle', '${uuid}')"><i class="bi bi-eye"></i></button>
                            <button class="btn btn-light" onclick="Sintel.Services.UI.openOffcanvas('editar', '${uuid}')"><i class="bi bi-pencil"></i></button>
                        </div>
                    `;
                }}
            ],
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('table-services')) {
        Sintel.Services.Table.init('table-services');
    }
});
