window.Sintel = window.Sintel || {};
window.Sintel.Cart = window.Sintel.Cart || {};

Sintel.Cart.API = {
    list: (params) => fetch(`/api/v1/cart/?${new URLSearchParams(params)}`, { headers: Sintel.Cart.API.authHeaders() }),
    get:  (uuid)   => fetch(`/api/v1/cart/${uuid}/`,         { headers: Sintel.Cart.API.authHeaders() }),
    clear: ()      => fetch(`/api/v1/cart/clear/`,         { method: 'DELETE', headers: Sintel.Cart.API.authHeaders() }),
    
    authHeaders: () => ({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access')}`
    })
};
