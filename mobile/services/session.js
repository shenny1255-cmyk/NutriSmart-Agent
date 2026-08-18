import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';

const ACCESS_TOKEN_KEY = 'access_token';
const LEGACY_SERVER_KEY = 'backend_ip';

function getWebStorage() {
  if (typeof globalThis.sessionStorage === 'undefined') return null;
  return globalThis.sessionStorage;
}

async function secureStoreAvailable() {
  return Platform.OS !== 'web' && SecureStore.isAvailableAsync();
}

export async function getAccessToken() {
  if (Platform.OS === 'web') {
    return getWebStorage()?.getItem(ACCESS_TOKEN_KEY) || null;
  }

  if (!(await secureStoreAvailable())) return null;

  const secureToken = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
  if (secureToken) return secureToken;

  // Di chuyển phiên cũ một lần rồi xóa bản JWT không an toàn.
  const legacyToken = await AsyncStorage.getItem(ACCESS_TOKEN_KEY);
  if (!legacyToken) return null;

  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, legacyToken);
  await AsyncStorage.multiRemove([ACCESS_TOKEN_KEY, LEGACY_SERVER_KEY]);
  return legacyToken;
}

export async function saveAccessToken(token) {
  if (!token || typeof token !== 'string') {
    throw new Error('Access token không hợp lệ');
  }

  if (Platform.OS === 'web') {
    getWebStorage()?.setItem(ACCESS_TOKEN_KEY, token);
    return;
  }

  if (!(await secureStoreAvailable())) {
    throw new Error('Thiết bị không hỗ trợ kho lưu trữ bảo mật');
  }

  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, token);
  await AsyncStorage.multiRemove([ACCESS_TOKEN_KEY, LEGACY_SERVER_KEY]);
}

export async function clearAccessToken() {
  if (Platform.OS === 'web') {
    getWebStorage()?.removeItem(ACCESS_TOKEN_KEY);
  } else if (await secureStoreAvailable()) {
    await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
  }

  await AsyncStorage.multiRemove([ACCESS_TOKEN_KEY, LEGACY_SERVER_KEY]);
}
