Sintel.Inventory.Table = {
    init(elementId) {
        return new Tabulator(`#${elementId}`, {
            ajaxURL: "/api/v1/inventory/",
            ajaxConfig: { headers: { 'Authorization': `Bearer ${localStorage.getItem('access')}` } },
            layout: "fitColumns",
            pagination: "remote",
            paginationSize: 20,
            columns: [
                {title: "Fecha", field: "created_at", formatter: "datetime", formatterParams: {outputFormat: "DD/MM/YYYY HH:mm"}},
                {title: "SKU", field: "sku"},
                {title: "Tipo", field: "movement_type", formatter: (cell) => {
                    const type = cell.getValue();
                    const badgeClass = { 'ENTRY': 'bg-success', 'EXIT': 'bg-danger', 'RESERVE': 'bg-warning' }[type] || 'bg-secondary';
                    return `<span class="badge ${badgeClass}">${type}</span>`;
                }},
                {title: "Cantidad", field: "quantity", hozAlign: "right"},
                {title: "Stock Nuevo", field: "balance_after", hozAlign: "right"},
                {title: "Referencia", field: "reference"},
                {title: "Acciones", field: "sku", sortable: false, formatter: (cell) => {
                    const sku = cell.getValue();
                    return `<button class="btn btn-sm btn-light" onclick="Sintel.Inventory.UI.openOffcanvas('detalle', '${sku}')"><i class="bi bi-eye"></i></button>`;
                }}
            ],
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('table-inventory')) {
        Sintel.Inventory.Table.init('table-inventory');
    }
});
