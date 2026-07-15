const BASE = '/api/v1';

async function request(path, { method = 'GET', body, isForm } = {}) {
  const token = localStorage.getItem('access_token');
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (!isForm) headers['Content-Type'] = 'application/json';

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.status === 204 ? null : res.json();
}

export const api = {
  dailySummary: (days = 7) => request(`/tracking/summary?days=${days}`),
  activePlan: () => request('/plans/active'),
  chat: (message) => request('/chat/messages', { method: 'POST', body: { message } }),
  analyzeMeal: (file) => {
    const fd = new FormData();
    fd.append('image', file);
    return request('/vision/meals/analyze', { method: 'POST', body: fd, isForm: true });
  },
  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  login: (email, password) => request('/auth/login', { method: 'POST', body: { email, password } }),

  // dữ liệu cho dropdown/checkbox — lấy từ bảng countries, medical_conditions, allergens
  countries: () => request('/catalog/countries'),
  conditions: () => request('/catalog/conditions'),
  allergens: () => request('/catalog/allergens'),
  seedDemo: () => request('/demo/seed', { method: 'POST' }),
};