/**
 * users.ui.js — Offcanvas/modal UI para CRUD de usuarios
 */
Sintel.Users.UI = {

    /** Abre el offcanvas de detalle (solo lectura) */
    async openDetail(uuid) {
        const res = await fetch(`/panel/usuarios/offcanvas/detalle/${uuid}/`);
        if (!res.ok) return;
        const html = await res.text();
        const container = document.getElementById('offcanvas-container');
        if (container) {
            container.innerHTML = html;
            const el = document.getElementById('offcanvas-panel');
            if (el) new bootstrap.Offcanvas(el).show();
        }
    },

    /** Abre modal de edición para el usuario con `id` */
    async openEdit(id) {
        const res = await Sintel.Users.API.get(id);
        if (!res.ok) return Sintel.Users.Utils.toast('Error al cargar usuario', 'danger');
        const user = await res.json();

        const modal = new bootstrap.Modal(document.getElementById('modal-user-edit'));
        document.getElementById('edit-user-id').value         = user.id;
        document.getElementById('edit-first-name').value      = user.first_name || '';
        document.getElementById('edit-last-name').value       = user.last_name  || '';
        document.getElementById('edit-role').value            = user.role;
        document.getElementById('edit-is-active').checked     = user.is_active;
        modal.show();
    },

    /** Guarda cambios del usuario editado */
    async saveEdit() {
        const id = parseInt(document.getElementById('edit-user-id').value);
        const data = {
            first_name: document.getElementById('edit-first-name').value,
            last_name:  document.getElementById('edit-last-name').value,
            role:       parseInt(document.getElementById('edit-role').value),
            is_active:  document.getElementById('edit-is-active').checked,
        };
        const res = await Sintel.Users.API.update(id, data);
        if (res.ok) {
            Sintel.Users.Utils.toast('Usuario actualizado correctamente.', 'success');
            bootstrap.Modal.getInstance(document.getElementById('modal-user-edit'))?.hide();
            Sintel.Users.Table.reload();
        } else {
            const err = await res.json();
            Sintel.Users.Utils.toast(JSON.stringify(err), 'danger');
        }
    },

    /** Solicita confirmación y desactiva el usuario */
    async confirmDeactivate(id) {
        if (!confirm('¿Deseas desactivar este usuario? El usuario no podrá iniciar sesión.')) return;
        const res = await Sintel.Users.API.destroy(id);
        if (res.ok || res.status === 204) {
            Sintel.Users.Utils.toast('Usuario desactivado.', 'warning');
            Sintel.Users.Table.reload();
        } else {
            const err = await res.json();
            Sintel.Users.Utils.toast(err.detail || 'Error al desactivar.', 'danger');
        }
    },

    /** Abre modal de creación */
    openCreate() {
        document.getElementById('form-create-user')?.reset();
        const modal = new bootstrap.Modal(document.getElementById('modal-user-create'));
        modal.show();
    },

    /** Guarda nuevo usuario */
    async saveCreate() {
        const form = document.getElementById('form-create-user');
        const data = {
            email:            form.querySelector('[name=email]').value,
            first_name:       form.querySelector('[name=first_name]').value,
            last_name:        form.querySelector('[name=last_name]').value,
            phone_number:     form.querySelector('[name=phone_number]').value,
            role:             parseInt(form.querySelector('[name=role]').value),
            password:         form.querySelector('[name=password]').value,
            password_confirm: form.querySelector('[name=password_confirm]').value,
        };
        const res = await Sintel.Users.API.create(data);
        const payload = await res.json();
        if (res.ok) {
            Sintel.Users.Utils.toast(`Usuario ${payload.email} creado.`, 'success');
            bootstrap.Modal.getInstance(document.getElementById('modal-user-create'))?.hide();
            Sintel.Users.Table.reload();
        } else {
            Sintel.Users.Utils.toast(JSON.stringify(payload), 'danger');
        }
    },
};
