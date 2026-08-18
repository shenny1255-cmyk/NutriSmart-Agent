import axios from 'axios';
import NetInfo from '@react-native-community/netinfo';

import { API_BASE_URL, getApiConfigurationError } from '../config/env';
import { clearAccessToken, getAccessToken } from './session';

const DEFAULT_TIMEOUT_MS = 12000;
const VISION_TIMEOUT_MS = 180000;

let unauthorizedHandler = null;
let unauthorizedPromise = null;

export class ApiError extends Error {
  constructor({ status, code, detail, message }) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.detail = detail;
    this.userMessage = message;
  }
}

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

function detailFromResponse(data) {
  if (typeof data?.detail === 'string') return data.detail;
  if (Array.isArray(data?.detail)) {
    return data.detail.map((item) => item?.msg).filter(Boolean).join('. ');
  }
  return '';
}

async function networkError(error) {
  const state = await NetInfo.fetch().catch(() => null);
  const offline = state?.isConnected === false;
  return new ApiError({
    code: offline ? 'OFFLINE' : 'NETWORK',
    message: offline
      ? 'Bạn đang ngoại tuyến. Hãy kiểm tra kết nối mạng rồi thử lại.'
      : 'Không thể kết nối máy chủ. Vui lòng thử lại sau.',
    detail: error.message,
  });
}

async function normalizeError(error) {
  if (error instanceof ApiError) return error;

  if (axios.isCancel(error) || error.code === 'ERR_CANCELED') {
    return new ApiError({ code: 'CANCELLED', message: 'Yêu cầu đã được hủy.' });
  }

  if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
    return new ApiError({
      code: 'TIMEOUT',
      message: 'Máy chủ phản hồi quá lâu. Vui lòng thử lại.',
      detail: error.message,
    });
  }

  if (!error.response) return networkError(error);

  const status = error.response.status;
  const detail = detailFromResponse(error.response.data);
  let code = 'HTTP_ERROR';
  let message = detail || 'Không thể hoàn tất yêu cầu. Vui lòng thử lại.';

  if (status === 401) {
    code = 'UNAUTHORIZED';
    message = error.config?._hadAccessToken
      ? 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.'
      : 'Email hoặc mật khẩu không đúng.';
  } else if (status === 404) {
    code = 'NOT_FOUND';
  } else if (status === 422) {
    code = 'VALIDATION';
    message = detail || 'Dữ liệu chưa hợp lệ. Vui lòng kiểm tra lại.';
  } else if (status === 503) {
    code = 'SERVICE_UNAVAILABLE';
    message = 'Dịch vụ tạm thời không khả dụng. Vui lòng thử lại sau.';
  } else if (status >= 500) {
    code = 'SERVER_ERROR';
    message = 'Máy chủ đang gặp sự cố. Vui lòng thử lại sau.';
  }

  return new ApiError({ status, code, detail, message });
}

async function expireSession() {
  if (unauthorizedPromise) return unauthorizedPromise;

  unauthorizedPromise = (async () => {
    try {
      if (unauthorizedHandler) {
        await unauthorizedHandler();
      } else {
        await clearAccessToken();
      }
    } finally {
      unauthorizedPromise = null;
    }
  })();

  return unauthorizedPromise;
}

const client = axios.create({
  baseURL: API_BASE_URL || undefined,
  timeout: DEFAULT_TIMEOUT_MS,
  headers: { Accept: 'application/json' },
});

client.interceptors.request.use(async (config) => {
  const configurationError = getApiConfigurationError();
  if (configurationError) {
    throw new ApiError({ code: 'CONFIG', message: configurationError });
  }

  const token = await getAccessToken();
  config._hadAccessToken = Boolean(token);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const normalized = await normalizeError(error);
    if (normalized.status === 401 && error.config?._hadAccessToken) {
      await expireSession();
    }
    return Promise.reject(normalized);
  }
);

async function request(path, options = {}) {
  try {
    const response = await client.request({ url: path, ...options });
    return response.status === 204 ? null : response.data;
  } catch (error) {
    throw await normalizeError(error);
  }
}

function imageFile(asset) {
  const extension = asset.fileName?.split('.').pop()?.toLowerCase();
  const inferredType = extension === 'png' ? 'image/png'
    : extension === 'webp' ? 'image/webp'
      : 'image/jpeg';

  return {
    uri: asset.uri,
    name: asset.fileName || `mon-an.${extension || 'jpg'}`,
    type: asset.mimeType || inferredType,
  };
}

export const api = {
  login: (email, password) => request('/auth/login', {
    method: 'POST',
    data: { email, password },
  }),
  me: () => request('/auth/me'),
  updateProfile: (payload) => request('/auth/me', {
    method: 'PUT',
    data: payload,
  }),
  conditions: () => request('/catalog/conditions'),
  allergens: () => request('/catalog/allergens'),
  foods: (query = '') => request(`/catalog/foods${query ? `?q=${encodeURIComponent(query)}` : ''}`),
  exercises: () => request('/catalog/exercises'),
  dailySummary: (days = 1) => request(`/tracking/summary?days=${days}`),
  syncActivity: (payload) => request('/tracking/daily-activity', {
    method: 'POST',
    data: payload,
  }),
  activePlan: () => request('/plans/active'),
  activeCheckin: () => request('/plans/active/checkin'),
  checkinHistory: (limit = 10) => request(`/plans/checkins/history?limit=${limit}`),
  submitCheckin: (id, payload) => request(`/plans/checkins/${id}/submit`, {
    method: 'POST',
    data: payload,
  }),
  reopenCheckin: (id) => request(`/plans/checkins/${id}/reopen`, {
    method: 'POST',
  }),
  decideCheckin: (id, action) => request(`/plans/checkins/${id}/decision`, {
    method: 'POST',
    data: { action },
  }),
  notifications: (limit = 20) => request(`/notifications?limit=${limit}`),
  markNotificationRead: (id) => request(`/notifications/${id}/read`, {
    method: 'PUT',
  }),
  chatHistory: () => request('/chat/messages'),
  sendChat: (message) => request('/chat/messages', {
    method: 'POST',
    data: { message },
    timeout: VISION_TIMEOUT_MS,
  }),
  clearChatHistory: () => request('/chat/messages', { method: 'DELETE' }),
  meals: (date) => request(`/tracking/meals${date ? `?d=${encodeURIComponent(date)}` : ''}`),
  addMeal: (payload) => request('/tracking/meals', {
    method: 'POST',
    data: payload,
  }),
  deleteMeal: (id) => request(`/tracking/meals/${id}`, { method: 'DELETE' }),
  activities: (date) => request(`/tracking/activities${date ? `?d=${encodeURIComponent(date)}` : ''}`),
  addActivity: (payload) => request('/tracking/activities', {
    method: 'POST',
    data: payload,
  }),
  deleteActivity: (id) => request(`/tracking/activities/${id}`, { method: 'DELETE' }),
  weightHistory: (days = 90) => request(`/tracking/weight?days=${days}`),
  updateWeight: (payload) => request('/tracking/weight', {
    method: 'PUT',
    data: payload,
  }),
  analyzeMeal: (asset) => {
    const formData = new FormData();
    formData.append('file', imageFile(asset));
    return request('/vision/analyze-meal', {
      method: 'POST',
      data: formData,
      timeout: VISION_TIMEOUT_MS,
    });
  },
  logMeal: (payload) => request('/vision/log-meal', {
    method: 'POST',
    data: payload,
  }),
};
