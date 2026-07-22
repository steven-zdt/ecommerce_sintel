window.Sintel = window.Sintel || {};
window.Sintel.Renting = window.Sintel.Renting || {};

Sintel.Renting.API = {
    list: (params) => fetch(`/api/v1/renting/?${new URLSearchParams(params)}`, { headers: Sintel.Renting.API.authHeaders() }),
    get:  (uuid)   => fetch(`/api/v1/renting/${uuid}/`,         { headers: Sintel.Renting.API.authHeaders() }),
    
    authHeaders: () => ({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access')}`
    })
};
