window.Sintel = window.Sintel || {};
window.Sintel.Quotes = window.Sintel.Quotes || {};

Sintel.Quotes.API = {
    list: (params) => fetch(`/api/v1/quotes/?${new URLSearchParams(params)}`, { headers: Sintel.Quotes.API.authHeaders() }),
    get:  (uuid)   => fetch(`/api/v1/quotes/${uuid}/`,         { headers: Sintel.Quotes.API.authHeaders() }),
    send: (uuid)   => fetch(`/api/v1/quotes/${uuid}/send/`,    { method: 'POST',  headers: Sintel.Quotes.API.authHeaders() }),
    pdf:  (uuid)   => `/api/v1/quotes/${uuid}/pdf/`, // Direct link
    
    authHeaders: () => ({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access')}`
    })
};
