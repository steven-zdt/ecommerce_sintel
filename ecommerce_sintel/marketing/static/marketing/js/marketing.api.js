window.Sintel = window.Sintel || {};
window.Sintel.Marketing = window.Sintel.Marketing || {};

Sintel.Marketing.API = {
    campaigns: (params) => fetch(`/api/v1/marketing/campaigns/?${new URLSearchParams(params)}`, { headers: Sintel.Marketing.API.authHeaders() }),
    offers:    (params) => fetch(`/api/v1/marketing/flash-offers/?${new URLSearchParams(params)}`, { headers: Sintel.Marketing.API.authHeaders() }),
    runAgent:  ()       => fetch(`/api/v1/marketing/agent/run/`, { method: 'POST', headers: Sintel.Marketing.API.authHeaders() }),
    metrics:   ()       => fetch(`/api/v1/marketing/dashboard/metrics/`, { headers: Sintel.Marketing.API.authHeaders() }),
    agentStatus: (id)   => fetch(`/api/v1/marketing/agent/runs/${id}/`, { headers: Sintel.Marketing.API.authHeaders() }),
    
    authHeaders: () => ({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access')}`
    })
};
