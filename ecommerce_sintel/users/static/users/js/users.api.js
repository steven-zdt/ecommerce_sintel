/**
 * users.api.js — Sintel Users CRUD API Client
 * Usa sesión Django (cookie) — sin JWT en localStorage.
 */
window.Sintel = window.Sintel || {};
window.Sintel.Users = window.Sintel.Users || {};

Sintel.Users.API = {
    BASE: '/api/v1/users/',

    _csrfToken() {
        return document.cookie.split(';')
            .map(c => c.trim())
            .find(c => c.startsWith('csrftoken='))
            ?.split('=')[1] || '';
    },

    _headers(contentType = 'application/json') {
        return {
            'Content-Type': contentType,
            'X-CSRFToken': this._csrfToken(),
        };
    },

    list(params = {}) {
        const qs = new URLSearchParams(params).toString();
        return fetch(`${this.BASE}?${qs}`, { headers: this._headers() });
    },

    get(id) {
        return fetch(`${this.BASE}${id}/`, { headers: this._headers() });
    },

    create(data) {
        return fetch(this.BASE, {
            method: 'POST',
            headers: this._headers(),
            body: JSON.stringify(data),
        });
    },

    update(id, data) {
        return fetch(`${this.BASE}${id}/`, {
            method: 'PATCH',
            headers: this._headers(),
            body: JSON.stringify(data),
        });
    },

    destroy(id) {
        return fetch(`${this.BASE}${id}/`, {
            method: 'DELETE',
            headers: this._headers(),
        });
    },

    profile() {
        return fetch(`${this.BASE}profile/`, { headers: this._headers() });
    },
};
