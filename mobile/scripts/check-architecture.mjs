import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const sourceFiles = [
  join(root, 'App.js'),
  join(root, 'navigation', 'MainTabNavigator.jsx'),
  ...readdirSync(join(root, 'screens')).map((name) => join(root, 'screens', name)),
];

const rules = [
  { pattern: /\baxios\b|\bfetch\s*\(/, message: 'Màn hình không được tự gọi HTTP.' },
  { pattern: /https?:\/\//, message: 'Màn hình không được chứa URL API.' },
  { pattern: /\b(?:\d{1,3}\.){3}\d{1,3}\b/, message: 'Màn hình không được chứa IP viết cứng.' },
  { pattern: /AsyncStorage[\s\S]{0,100}access_token|access_token[\s\S]{0,100}AsyncStorage/, message: 'JWT không được lưu bằng AsyncStorage.' },
];

const failures = [];
for (const file of sourceFiles) {
  const source = readFileSync(file, 'utf8');
  for (const rule of rules) {
    if (rule.pattern.test(source)) failures.push(`${file}: ${rule.message}`);
  }
}

const sessionSource = readFileSync(join(root, 'services', 'session.js'), 'utf8');
if (!sessionSource.includes('SecureStore.setItemAsync')) {
  failures.push('services/session.js: Thiếu lưu token bằng SecureStore.');
}

const apiSource = readFileSync(join(root, 'services', 'api.js'), 'utf8');
if (!apiSource.includes('interceptors.response') || !apiSource.includes('status === 401')) {
  failures.push('services/api.js: Thiếu xử lý HTTP 401 tập trung.');
}

if (failures.length) {
  console.error(failures.join('\n'));
  process.exitCode = 1;
} else {
  console.log('Kiểm tra kiến trúc mobile đạt yêu cầu.');
}
