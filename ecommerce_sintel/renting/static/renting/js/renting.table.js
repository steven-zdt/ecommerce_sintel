Sintel.Renting.Table = {
    init(elementId) {
        return new Tabulator(`#${elementId}`, {
            ajaxURL: "/api/v1/renting/",
            ajaxConfig: { headers: { 'Authorization': `Bearer ${localStorage.getItem('access')}` } },
            layout: "fitColumns",
            pagination: "remote",
            paginationSize: 20,
            columns: [
                {title: "Equipo", field: "name"},
                {title: "Marca", field: "brand_name"},
                {title: "Tarifa Hora", field: "hourly_rate", formatter: "money", formatterParams: {symbol: "$"}},
                {title: "Disponible", field: "is_available", hozAlign: "center", formatter: "tickCross"},
                {title: "Acciones", field: "uuid", sortable: false, formatter: (cell) => {
                    const uuid = cell.getValue();
                    return `
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-light" onclick="Sintel.Renting.UI.openOffcanvas('detalle', '${uuid}')"><i class="bi bi-eye"></i></button>
                            <button class="btn btn-light" onclick="Sintel.Renting.UI.openOffcanvas('editar', '${uuid}')"><i class="bi bi-pencil"></i></button>
                        </div>
                    `;
                }}
            ],
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('table-renting')) {
        Sintel.Renting.Table.init('table-renting');
    }
});
