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

    // Phiên đăng nhập hết hạn/không hợp lệ → dọn token và đưa về trang đăng nhập.
    // Chỉ áp dụng khi request CÓ gửi token; đăng nhập sai mật khẩu cũng trả 401
    // nhưng lúc đó chưa có token nên không được đá người dùng đi.
    if (res.status === 401 && token) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('role');
      if (!window.location.pathname.startsWith('/login')) {
        window.location.replace('/login?expired=1');
      }
    }

    throw new ApiError(res.status, detail);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  dailySummary: (days = 7) => request(`/tracking/summary?days=${days}`),
  activePlan: () => request('/plans/active'),
  generatePlan: () => request('/plans/generate', { method: 'POST' }),
  evaluatePlan: (force = false) =>
    request(`/plans/evaluate${force ? '?force=true' : ''}`, { method: 'POST' }),
  planEvaluations: (limit = 10) => request(`/plans/evaluations?limit=${limit}`),
  chat: (message) => request('/chat/messages', { method: 'POST', body: { message } }),
  streamChat: async (message, { onToken, onDone, onError }) => {
    const token = localStorage.getItem('access_token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;

    try {
      const res = await fetch(`${BASE}/chat/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message }),
      });

      if (!res.ok) {
        let detail;
        try { detail = (await res.json()).detail; } catch {}
        throw new ApiError(res.status, detail);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (!dataStr) continue;
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.error) {
                onError?.(parsed.error);
                return;
              }
              if (parsed.token) {
                onToken?.(parsed.token);
              }
              if (parsed.done) {
                onDone?.(parsed.citations || []);
              }
            } catch (e) {
              console.error('Lỗi parse SSE token:', e);
            }
          }
        }
      }
    } catch (e) {
      onError?.(e.message || 'Không thể kết nối stream');
    }
  },
  chatHistory: () => request('/chat/messages'),
  clearChatHistory: () => request('/chat/messages', { method: 'DELETE' }),
  analyzeMeal: (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return request('/vision/analyze-meal', { method: 'POST', body: fd, isForm: true });
  },
  logMeal: (payload) => request('/vision/log-meal', { method: 'POST', body: payload }),
  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  login: (email, password) => request('/auth/login', { method: 'POST', body: { email, password } }),
  verifyEmail: (token) => request(`/auth/verify?token=${encodeURIComponent(token)}`),
  resendVerification: () => request('/auth/resend-verification', { method: 'POST' }),

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

  // Activity từ Mobile (bước chân, calo tiêu hao)
  todayActivity: () => request('/tracking/today-activity'),
  syncActivity: (payload) => request('/tracking/daily-activity', { method: 'POST', body: payload }),
};