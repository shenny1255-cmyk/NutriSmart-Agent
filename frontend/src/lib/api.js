const BASE = '/api/v1';

// Lỗi API mang theo status + detail để UI hiển thị đúng nguyên nhân.
// Lỗi mạng (backend không chạy) → status === undefined.
export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : `HTTP ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

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

  if (!res.ok) {
    let detail;
    try {
      detail = (await res.json()).detail;   // FastAPI: string, hoặc mảng lỗi 422
    } catch {
      /* body không phải JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  dailySummary: (days = 7) => request(`/tracking/summary?days=${days}`),
  activePlan: () => request('/plans/active'),
  generatePlan: () => request('/plans/generate', { method: 'POST' }),
  chat: (message) => request('/chat/messages', { method: 'POST', body: { message } }),
  chatHistory: () => request('/chat/messages'),
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
  // Admin
  adminUsers: (q = '') => request(`/admin/users${q ? `?q=${q}` : ''}`),
  updateUserRole: (id, role) => request(`/admin/users/${id}/role`, { method: 'PATCH', body: { role } }),
  deleteUser: (id) => request(`/admin/users/${id}`, { method: 'DELETE' }),
  adminDrugs: () => request('/admin/drugs'),
  createDrug: (payload) => request('/admin/drugs', { method: 'POST', body: payload }),
  setDrugRule: (id, payload) => request(`/admin/drugs/${id}/rules`, { method: 'PUT', body: payload }),
  auditLogs: () => request('/admin/audit'),
  // Expert
  pendingDocs: () => request('/expert/documents/pending'),
  reviewDoc: (id, status) => request(`/expert/documents/${id}/review`, { method: 'PATCH', body: { status } }),
  crawlDocs: (urls) => request('/expert/documents/crawl', { method: 'POST', body: { urls } }),
  crawlPresetDocs: (source = 'moh', limit = 10) => request('/expert/documents/crawl-preset', { method: 'POST', body: { source, limit } }),
  resetDocs: () => request('/expert/documents/reset', { method: 'POST' }),



  // lấy role người dùng hiện tại (đã có /auth/me)
  me: () => request('/auth/me'),
};