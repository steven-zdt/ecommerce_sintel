Sintel.Marketing.UI = {
    runAgent() {
        console.log("Marketing Agent triggered...");
        Sintel.showToast('info', 'Agente IA iniciado. Analizando datos...');
        // logic for polling agent status would go here
    },
    openOffcanvas(accion, uuid = null) {
        const url = uuid
            ? `/panel/marketing/offcanvas/${accion}/${uuid}/`
            : `/panel/marketing/offcanvas/${accion}/`;
        htmx.ajax('GET', url, { target: '#offcanvas-body', swap: 'innerHTML' });
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(document.getElementById('panel-offcanvas'));
        offcanvas.show();
    }
};
