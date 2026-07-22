window.Sintel = window.Sintel || {};
window.Sintel.Services = window.Sintel.Services || {};

Sintel.Services.API = {
    list: (params) => fetch(`/api/v1/services/?${new URLSearchParams(params)}`, { headers: Sintel.Services.API.authHeaders() }),
    get:  (uuid)   => fetch(`/api/v1/services/${uuid}/`,         { headers: Sintel.Services.API.authHeaders() }),
    
    authHeaders: () => ({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access')}`
    })
};
