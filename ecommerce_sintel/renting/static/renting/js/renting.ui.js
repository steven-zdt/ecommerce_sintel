Sintel.Renting.UI = {
    openOffcanvas(accion, uuid = null) {
        const url = uuid
            ? `/panel/renta/offcanvas/${accion}/${uuid}/`
            : `/panel/renta/offcanvas/${accion}/`;
        
        htmx.ajax('GET', url, { target: '#offcanvas-body', swap: 'innerHTML' });
        
        const titleMap = { 'crear': 'Nuevo Equipo', 'editar': 'Editar Equipo', 'detalle': 'Detalle de Equipo' };
        document.getElementById('offcanvas-title').textContent = titleMap[accion] || 'Equipo';
        
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(document.getElementById('panel-offcanvas'));
        offcanvas.show();
    }
};
