window.Sintel = window.Sintel || {};
window.Sintel.Inventory = window.Sintel.Inventory || {};

Sintel.Inventory.API = {
    list: (params) => fetch(`/api/v1/inventory/?${new URLSearchParams(params)}`, { headers: Sintel.Inventory.API.authHeaders() }),
    stock: (sku)    => fetch(`/api/v1/inventory/stock-level/${sku}/`,          { headers: Sintel.Inventory.API.authHeaders() }),
    entry: (data)   => fetch(`/api/v1/inventory/entry/`,                       { method: 'POST',  headers: Sintel.Inventory.API.authHeaders(), body: JSON.stringify(data) }),
    exit:  (data)   => fetch(`/api/v1/inventory/exit/`,                        { method: 'POST',  headers: Sintel.Inventory.API.authHeaders(), body: JSON.stringify(data) }),
    
    authHeaders: () => ({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access')}`
    })
};
