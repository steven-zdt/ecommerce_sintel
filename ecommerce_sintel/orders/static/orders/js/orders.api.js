window.Sintel = window.Sintel || {};
window.Sintel.Orders = window.Sintel.Orders || {};

Sintel.Orders.API = {
    list: (params) => fetch(`/api/v1/orders/?${new URLSearchParams(params)}`, { headers: Sintel.Orders.API.authHeaders() }),
    get:  (uuid)   => fetch(`/api/v1/orders/${uuid}/`,         { headers: Sintel.Orders.API.authHeaders() }),
    
    authHeaders: () => ({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access')}`
    })
};
