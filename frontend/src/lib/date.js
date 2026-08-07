function toLocalDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const today = new Date();
const oldestBirthDate = new Date(today);
oldestBirthDate.setFullYear(today.getFullYear() - 120);

export const MAX_BIRTH_DATE = toLocalDateInputValue(today);
export const MIN_BIRTH_DATE = toLocalDateInputValue(oldestBirthDate);

export function isValidBirthDate(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value)
    && value >= MIN_BIRTH_DATE
    && value <= MAX_BIRTH_DATE;
}
