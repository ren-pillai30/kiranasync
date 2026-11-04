const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? (window.location.port === '5173' ? 'http://127.0.0.1:5000' : '')
  : '';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    credentials: 'include',
    cache: 'no-store',
    ...options,
  });
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
  getAuthSession: () => request('/api/auth/session'),
  login: (email, password) =>
    request('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }),
  registerOwner: (payload) =>
    request('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  logout: () =>
    request('/api/auth/logout', {
      method: 'POST',
    }),
  completeStoreSetup: (data) =>
    request('/api/store/setup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  // Dashboard & Ledger
  getDashboard: () => request('/api/dashboard'),
  getLedger: () => request('/api/ledger'),
  getArchives: () => request('/api/archives'),
  getHisaab: () => request('/api/analytics/hisaab'),

  // Inventory Mutations
  addInventory: (data) =>
    request('/api/inventory/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  editInventory: (itemId, newItemName, newItemNameHindi) =>
    request('/api/inventory/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ItemID: itemId, NewItemName: newItemName, NewItemNameHindi: newItemNameHindi }),
    }),

  confirmInventoryCommand: (data) =>
    request('/api/inventory/confirm-command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  confirmTransaction: (data) =>
    request('/api/transactions/confirm', {
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

  editCustomer: (customerId, newCustomerName, newCustomerNameHindi) =>
    request('/api/credit/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ CustomerID: customerId, NewCustomerName: newCustomerName, NewCustomerNameHindi: newCustomerNameHindi }),
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
      credentials: 'include',
      body: formData,
    }).then(async (res) => {
      const contentType = res.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) {
        const text = await res.text();
        if (/^\s*<!doctype html/i.test(text) || /<html/i.test(text)) {
          throw new Error(`Server error (${res.status}). Please check the deployment logs.`);
        }
        throw new Error(text.slice(0, 200) || `HTTP ${res.status}`);
      }
      return res.json();
    }),

  synthesizeVoice: (text, languageCode, entityNames = []) =>
    fetch(`${API_BASE}/api/voice/synthesize`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, language_code: languageCode, entity_names: entityNames }),
    }),

  // Barcode Scanning
  lookupBarcode: (code) => request(`/api/barcode/lookup?code=${encodeURIComponent(code)}`),
  linkBarcode: (itemId, barcode) =>
    request('/api/barcode/link', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ItemID: itemId, Barcode: barcode }),
    }),

  // Feedback
  getFeedback: () => request('/api/feedback'),
  submitFeedback: (payload) =>
    request('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
};
