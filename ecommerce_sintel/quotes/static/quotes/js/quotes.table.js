Sintel.Quotes.Table = {
    init(elementId) {
        return new Tabulator(`#${elementId}`, {
            ajaxURL: "/api/v1/quotes/",
            ajaxConfig: { headers: { 'Authorization': `Bearer ${localStorage.getItem('access')}` } },
            layout: "fitColumns",
            pagination: "remote",
            paginationSize: 20,
            columns: [
                {title: "Cliente", field: "client_name"},
                {title: "Total", field: "total_amount", formatter: "money", formatterParams: {symbol: "$"}},
                {title: "Estado", field: "status", formatter: (cell) => {
                    const status = cell.getValue();
                    const badgeClass = { 'DRAFT': 'bg-secondary', 'SENT': 'bg-primary', 'ACCEPTED': 'bg-success', 'REJECTED': 'bg-danger', 'EXPIRED': 'bg-warning' }[status] || 'bg-light text-dark';
                    return `<span class="badge ${badgeClass}">${status}</span>`;
                }},
                {title: "Fecha", field: "created_at", formatter: "datetime", formatterParams: {outputFormat: "DD/MM/YYYY"}},
                {title: "Acciones", field: "uuid", sortable: false, formatter: (cell) => {
                    const uuid = cell.getValue();
                    return `
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-light" onclick="Sintel.Quotes.UI.openOffcanvas('detalle', '${uuid}')"><i class="bi bi-eye"></i></button>
                            <a href="${Sintel.Quotes.API.pdf(uuid)}" target="_blank" class="btn btn-light"><i class="bi bi-file-earmark-pdf"></i></a>
                        </div>
                    `;
                }}
            ],
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('table-quotes')) {
        Sintel.Quotes.Table.init('table-quotes');
    }
});
