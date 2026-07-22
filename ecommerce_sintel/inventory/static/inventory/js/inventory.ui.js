Sintel.Inventory.UI = {
    openOffcanvas(accion, sku = null) {
        const url = sku
            ? `/panel/inventario/offcanvas/${accion}/${sku}/`
            : `/panel/inventario/offcanvas/${accion}/`;
        
        htmx.ajax('GET', url, { target: '#offcanvas-body', swap: 'innerHTML' });
        
        const titleMap = { 'entrada': 'Registrar Entrada', 'salida': 'Registrar Salida', 'detalle': 'Detalle de Stock' };
        document.getElementById('offcanvas-title').textContent = titleMap[accion] || 'Inventario';
        
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(document.getElementById('panel-offcanvas'));
        offcanvas.show();
    }
};
