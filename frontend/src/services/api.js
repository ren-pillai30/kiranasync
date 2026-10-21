const API_BASE = 'http://127.0.0.1:5000';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, options);
  const contentType = response.headers.get('content-type') || '';

  if (!contentType.includes('application/json')) {
    const text = await response.text();
    const detail = text.trim().toLowerCase().startsWith('<!doctype')
      ? 'The backend returned an HTML page instead of JSON. Ensure the backend server is running.'
      : text.slice(0, 200) || `Request failed with HTTP status ${response.status}`;
    throw new Error(detail);
  }

  const data = await response.json();
  if (!response.ok || data.status === 'error') {
    throw new Error(data.error || `Request failed with HTTP status ${response.status}`);
  }
  return data;
}

export const api = {
  // Dashboard & Ledger
  getDashboard: () => request('/api/dashboard'),
  getLedger: () => request('/api/ledger'),
  getArchives: () => request('/api/archives'),
  getHisaab: () => request('/api/analytics/hisaab'),
  getBenchmark: () => request('/api/evaluation/benchmark'),

  // Inventory Mutations
  addInventory: (data) =>
    request('/api/inventory/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  editInventory: (itemId, newItemName) =>
    request('/api/inventory/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ItemID: itemId, NewItemName: newItemName }),
    }),

  confirmInventoryCommand: (data) =>
    request('/api/inventory/confirm-command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  confirmRestock: (data) =>
    request('/api/inventory/confirm-restock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  lookupProduct: (itemName) =>
    request('/api/product-lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ItemName: itemName }),
    }),

  // Customer Credit Mutations
  addCustomer: (data) =>
    request('/api/credit/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  editCustomer: (customerId, newCustomerName) =>
    request('/api/credit/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ CustomerID: customerId, NewCustomerName: newCustomerName }),
    }),

  // Entity Archiving / Removal
  archiveEntity: (data) =>
    request('/api/entities/archive', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  // Voice Processing
  processAudio: (formData) =>
    fetch(`${API_BASE}/api/process-audio`, {
      method: 'POST',
      body: formData,
    }).then(async (res) => {
      const contentType = res.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) {
        const text = await res.text();
        throw new Error(text.slice(0, 200) || `HTTP ${res.status}`);
      }
      return res.json();
    }),

  synthesizeVoice: (text, languageCode) =>
    fetch(`${API_BASE}/api/voice/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, language_code: languageCode }),
    }),
};

