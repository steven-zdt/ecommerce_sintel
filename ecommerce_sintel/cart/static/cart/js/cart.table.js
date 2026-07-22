Sintel.Cart.Table = {
    init(elementId) {
        return new Tabulator(`#${elementId}`, {
            ajaxURL: "/api/v1/cart/",
            ajaxConfig: { headers: { 'Authorization': `Bearer ${localStorage.getItem('access')}` } },
            layout: "fitColumns",
            columns: [
                {title: "Usuario", field: "user_email", formatter: (cell) => cell.getValue() || "Invitado"},
                {title: "Guest ID", field: "guest_id", visible: false},
                {title: "Ítems", field: "items_count", hozAlign: "center"},
                {title: "Total", field: "total", formatter: "money", formatterParams: {symbol: "$"}},
                {title: "Creado", field: "created_at", formatter: "datetime", formatterParams: {outputFormat: "DD/MM/YYYY"}},
                {title: "Acciones", field: "uuid", sortable: false, formatter: (cell) => {
                    const uuid = cell.getValue();
                    return `<button class="btn btn-sm btn-light" onclick="Sintel.Cart.UI.openOffcanvas('detalle', '${uuid}')"><i class="bi bi-eye"></i></button>`;
                }}
            ],
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('table-cart')) {
        Sintel.Cart.Table.init('table-cart');
    }
});
