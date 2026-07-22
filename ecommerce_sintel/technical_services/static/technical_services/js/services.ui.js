Sintel.Services.UI = {
    openOffcanvas(accion, uuid = null) {
        const url = uuid
            ? `/panel/servicios/offcanvas/${accion}/${uuid}/`
            : `/panel/servicios/offcanvas/${accion}/`;
        
        htmx.ajax('GET', url, { target: '#offcanvas-body', swap: 'innerHTML' });
        
        const titleMap = { 'crear': 'Nuevo Servicio', 'editar': 'Editar Servicio', 'detalle': 'Detalle de Servicio' };
        document.getElementById('offcanvas-title').textContent = titleMap[accion] || 'Servicio';
        
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(document.getElementById('panel-offcanvas'));
        offcanvas.show();
    }
};
