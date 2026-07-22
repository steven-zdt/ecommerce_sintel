Sintel.Quotes.UI = {
    openOffcanvas(accion, uuid = null) {
        const url = uuid
            ? `/panel/cotizaciones/offcanvas/${accion}/${uuid}/`
            : `/panel/cotizaciones/offcanvas/${accion}/`;
        
        htmx.ajax('GET', url, { target: '#offcanvas-body', swap: 'innerHTML' });
        
        const titleMap = { 'crear': 'Nueva Cotización', 'editar': 'Editar Cotización', 'detalle': 'Detalle de Cotización' };
        document.getElementById('offcanvas-title').textContent = titleMap[accion] || 'Cotización';
        
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(document.getElementById('panel-offcanvas'));
        offcanvas.show();
    }
};
