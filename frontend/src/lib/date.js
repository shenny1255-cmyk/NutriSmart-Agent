function toLocalDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const today = new Date();
export const TODAY = toLocalDateInputValue(today);

export const MIN_BIRTH_DATE = '1920-01-01';

export function calculateMaxBirthDate(base = new Date()) {
  const d = new Date(base);
  d.setFullYear(d.getFullYear() - 15);
  return toLocalDateInputValue(d);
}

export const MAX_BIRTH_DATE = calculateMaxBirthDate();

export function calculateAge(birthDateString) {
  if (!birthDateString || !/^\d{4}-\d{2}-\d{2}$/.test(birthDateString)) return null;
  const [y, m, d] = birthDateString.split('-').map(Number);
  const now = new Date();
  let age = now.getFullYear() - y;
  const monthDiff = (now.getMonth() + 1) - m;
  if (monthDiff < 0 || (monthDiff === 0 && now.getDate() < d)) {
    age -= 1;
  }
  return age;
}

export function isValidBirthDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  if (value < MIN_BIRTH_DATE) return false;
  const age = calculateAge(value);
  if (age === null) return false;
  return age >= 15 && age <= 100;
}

export function getBirthDateValidationError(value) {
  if (!value) return '';
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return 'Định dạng ngày sinh không hợp lệ.';
  if (value < MIN_BIRTH_DATE) return 'Ngày sinh không được trước ngày 1920-01-01.';
  const age = calculateAge(value);
  if (age === null) return 'Ngày sinh không hợp lệ.';
  if (age < 0) return 'Ngày sinh không được ở trong tương lai.';
  if (age < 15) return 'Người dùng phải từ 15 tuổi trở lên (độ tuổi tối thiểu là 15).';
  if (age > 100) return 'Độ tuổi không được vượt quá 100 tuổi.';
  return '';
}
