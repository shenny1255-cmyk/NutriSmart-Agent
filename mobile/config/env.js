import Constants from 'expo-constants';

const API_PREFIX = '/api/v1';

function trimTrailingSlash(value) {
  return value.replace(/\/+$/, '');
}

function withApiPrefix(value) {
  const normalized = trimTrailingSlash(value.trim());
  return normalized.endsWith(API_PREFIX) ? normalized : `${normalized}${API_PREFIX}`;
}

function getExpoHost() {
  const hostUri = Constants.expoConfig?.hostUri || Constants.manifest?.debuggerHost;
  if (!hostUri) return '';

  const withoutProtocol = hostUri.replace(/^[a-z]+:\/\//i, '');
  return withoutProtocol.split(':')[0];
}

function getDevelopmentFallback() {
  if (!__DEV__) return '';
  const host = getExpoHost();
  return host ? `http://${host}:8000${API_PREFIX}` : '';
}

const configuredUrl = process.env.EXPO_PUBLIC_API_URL?.trim() || '';

export const API_BASE_URL = configuredUrl
  ? withApiPrefix(configuredUrl)
  : getDevelopmentFallback();

export function getApiConfigurationError() {
  if (!API_BASE_URL) {
    return 'Ứng dụng chưa được cấu hình máy chủ. Vui lòng liên hệ quản trị viên.';
  }

  if (!__DEV__ && !API_BASE_URL.toLowerCase().startsWith('https://')) {
    return 'Bản phát hành chỉ được phép kết nối tới máy chủ HTTPS.';
  }

  return '';
}
