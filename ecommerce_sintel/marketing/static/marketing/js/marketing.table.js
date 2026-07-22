Sintel.Marketing.Table = {
    initCampaigns(elementId) {
        return new Tabulator(`#${elementId}`, {
            ajaxURL: "/api/v1/marketing/campaigns/",
            ajaxConfig: { headers: { 'Authorization': `Bearer ${localStorage.getItem('access')}` } },
            layout: "fitColumns",
            columns: [
                {title: "Campaña", field: "title"},
                {title: "Estado", field: "status"},
                {title: "Canales", field: "channels"},
                {title: "Acciones", field: "uuid", sortable: false, formatter: () => `<button class="btn btn-sm btn-light"><i class="bi bi-eye"></i></button>`}
            ],
        });
    },
    initOffers(elementId) {
        return new Tabulator(`#${elementId}`, {
            ajaxURL: "/api/v1/marketing/flash-offers/",
            ajaxConfig: { headers: { 'Authorization': `Bearer ${localStorage.getItem('access')}` } },
            layout: "fitColumns",
            columns: [
                {title: "Oferta", field: "name"},
                {title: "Descuento", field: "discount_percent", formatter: (cell) => `${cell.getValue()}%`},
                {title: "Fin", field: "end_date", formatter: "datetime"}
            ],
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('table-marketing-campaigns')) {
        Sintel.Marketing.Table.initCampaigns('table-marketing-campaigns');
    }
    if (document.getElementById('table-marketing-offers')) {
        Sintel.Marketing.Table.initOffers('table-marketing-offers');
    }
});
