const FULL_NAME_PATTERN = /^\p{L}+(?:[ '\-’]\p{L}+)*$/u;

export function isValidFullName(value) {
  const normalized = (value || '').trim().replace(/\s+/g, ' ');
  return normalized.length >= 2
    && normalized.length <= 100
    && FULL_NAME_PATTERN.test(normalized);
}

export function isEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((value || '').trim());
}

export function bodyMetricsBmi(heightCm, weightKg) {
  const height = Number(heightCm);
  const weight = Number(weightKg);
  if (!Number.isFinite(height) || !Number.isFinite(weight) || height <= 0 || weight <= 0) return null;
  return weight / (height / 100) ** 2;
}

export function areBodyMetricsPlausible(heightCm, weightKg) {
  const bmi = bodyMetricsBmi(heightCm, weightKg);
  return bmi !== null && bmi >= 10 && bmi <= 80;
}

const HEALTH_TERM_PATTERN = /^[\p{L}\p{N}\s\-'’()/&.,]+$/u;

export function customHealthTermError(value) {
  const normalized = (value || '').trim().replace(/\s+/g, ' ');
  if (normalized.length < 2 || normalized.length > 80) return 'Tên phải có từ 2–80 ký tự.';
  const letters = normalized.match(/\p{L}/gu) || [];
  if (letters.length < 2) return 'Tên phải chứa ít nhất 2 chữ cái.';
  if (!HEALTH_TERM_PATTERN.test(normalized)) return 'Không được chứa emoji, email, đường dẫn hoặc ký tự đặc biệt.';
  if (new Set(letters.map((char) => char.toLocaleLowerCase('vi'))).size < 2) return 'Nội dung lặp không hợp lệ.';
  return '';
}

const CATEGORY_NAME_PATTERN = /^[\p{L}\p{N}\s&/().,'’+%\-]+$/u;

export function categoryNameError(value) {
  const normalized = (value || '').trim().replace(/\s+/g, ' ');
  if (normalized.length < 2 || normalized.length > 100) return 'Tên danh mục phải có từ 2–100 ký tự.';
  if (!/\p{L}/u.test(normalized)) return 'Tên danh mục phải chứa chữ cái.';
  if (!CATEGORY_NAME_PATTERN.test(normalized)) return 'Tên danh mục không được chứa emoji hoặc ký tự đặc biệt.';
  return '';
}

const FOOD_NAME_PATTERN = /^[\p{L}\p{N}\s&/().,'’+%\-]+$/u;

export function isValidFoodName(value) {
  const normalized = (value || '').trim().replace(/\s+/g, ' ');
  const letterCount = normalized.match(/\p{L}/gu)?.length ?? 0;
  return normalized.length >= 2
    && normalized.length <= 100
    && letterCount >= 2
    && FOOD_NAME_PATTERN.test(normalized);
}
