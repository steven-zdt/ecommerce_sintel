Sintel.Cart.UI = {
    openOffcanvas(accion, uuid = null) {
        const url = `/panel/carritos/offcanvas/${accion}/${uuid}/`;
        htmx.ajax('GET', url, { target: '#offcanvas-body', swap: 'innerHTML' });
        document.getElementById('offcanvas-title').textContent = 'Detalle de Carrito';
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(document.getElementById('panel-offcanvas'));
        offcanvas.show();
    }
};
