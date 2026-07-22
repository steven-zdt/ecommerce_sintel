Sintel.Orders.Table = {
    init(elementId) {
        return new Tabulator(`#${elementId}`, {
            ajaxURL: "/api/v1/orders/",
            ajaxConfig: { headers: { 'Authorization': `Bearer ${localStorage.getItem('access')}` } },
            layout: "fitColumns",
            pagination: "remote",
            paginationSize: 20,
            columns: [
                {title: "Número", field: "uuid", formatter: (cell) => cell.getValue().substring(0, 8).toUpperCase()},
                {title: "Cliente", field: "user_email"},
                {title: "Total", field: "total_amount", formatter: "money", formatterParams: {symbol: "$"}},
                {title: "Estado", field: "status", formatter: (cell) => {
                    const status = cell.getValue();
                    const badgeClass = { 'PENDING': 'bg-warning', 'PAID': 'bg-success', 'SHIPPED': 'bg-info', 'CANCELLED': 'bg-danger' }[status] || 'bg-secondary';
                    return `<span class="badge ${badgeClass}">${status}</span>`;
                }},
                {title: "Fecha", field: "created_at", formatter: "datetime", formatterParams: {outputFormat: "DD/MM/YYYY"}},
                {title: "Acciones", field: "uuid", sortable: false, formatter: (cell) => {
                    const uuid = cell.getValue();
                    return `<button class="btn btn-sm btn-light" onclick="Sintel.Orders.UI.openOffcanvas('detalle', '${uuid}')"><i class="bi bi-eye"></i></button>`;
                }}
            ],
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('table-orders')) {
        Sintel.Orders.Table.init('table-orders');
    }
});
