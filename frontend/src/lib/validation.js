const FULL_NAME_PATTERN = /^\p{L}+(?:[ '\-’]\p{L}+)*$/u;

export function isValidFullName(value) {
  const normalized = (value || '').trim().replace(/\s+/g, ' ');
  return normalized.length >= 2
    && normalized.length <= 100
    && FULL_NAME_PATTERN.test(normalized);
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
