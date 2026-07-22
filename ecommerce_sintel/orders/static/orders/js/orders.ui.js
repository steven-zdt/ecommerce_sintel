Sintel.Orders.UI = {
    openOffcanvas(accion, uuid = null) {
        const url = uuid
            ? `/panel/ordenes/offcanvas/${accion}/${uuid}/`
            : `/panel/ordenes/offcanvas/${accion}/`;
        
        htmx.ajax('GET', url, { target: '#offcanvas-body', swap: 'innerHTML' });
        
        const titleMap = { 'detalle': 'Detalle de Orden', 'direccion': 'Dirección de Envío' };
        document.getElementById('offcanvas-title').textContent = titleMap[accion] || 'Orden';
        
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(document.getElementById('panel-offcanvas'));
        offcanvas.show();
    }
};
