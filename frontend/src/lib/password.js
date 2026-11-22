// Chính sách mật khẩu phía client - phải khớp _validate_strong_password trong backend/app/schemas.py.
export const PASSWORD_SPECIALS = '!@#$%^&*()_+-=[]{}|;:,.<>?';

const COMMON = new Set([
  '12345678', '123456789', '1234567890', '87654321', '11111111', '00000000', '12341234',
  'password', 'password1', 'password123', 'password@123', 'passw0rd', 'p@ssw0rd', 'p@ssword1',
  'admin123', 'admin1234', 'admin@123', 'administrator', 'qwerty123', 'qwertyuiop', 'abc12345',
  'abcd1234', 'iloveyou', 'letmein1', 'welcome1', 'welcome123', 'matkhau123', 'nutrismart',
  'nutrismart123', 'nutrismart@123', 'demo1234', 'changeme', 'test1234',
]);

export function passwordChecks(pw = '') {
  return {
    length: pw.length >= 8 && pw.length <= 64,
    mixedCase: /[a-z]/.test(pw) && /[A-Z]/.test(pw),
    digit: /\d/.test(pw),
    special: [...pw].some((c) => PASSWORD_SPECIALS.includes(c)),
  };
}

export function isCommonPassword(pw = '') {
  return COMMON.has(pw.toLowerCase());
}

export function isStrongPassword(pw = '') {
  const c = passwordChecks(pw);
  return c.length && c.mixedCase && c.digit && c.special && !/\s/.test(pw) && !isCommonPassword(pw);
}

// 0 = chưa nhập, 1 = Yếu, 2 = Trung bình, 3 = Mạnh
export function passwordStrength(pw = '') {
  if (!pw) return 0;
  if (isCommonPassword(pw) || /\s/.test(pw)) return 1;
  const met = Object.values(passwordChecks(pw)).filter(Boolean).length;
  if (met <= 2) return 1;
  if (met === 3 || pw.length < 12) return 2;
  return 3;
}

function randomIndex(max) {
  const buf = new Uint32Array(1);
  // Loại bỏ phần dư để mọi ký tự có xác suất như nhau
  const limit = Math.floor(0x100000000 / max) * max;
  do { crypto.getRandomValues(buf); } while (buf[0] >= limit);
  return buf[0] % max;
}

// Sinh mật khẩu ngẫu nhiên bằng crypto.getRandomValues, luôn đủ 4 nhóm ký tự.
export function generateStrongPassword(length = 12) {
  const groups = [
    'ABCDEFGHJKLMNPQRSTUVWXYZ',   // bỏ I, O dễ nhầm
    'abcdefghijkmnpqrstuvwxyz',   // bỏ l, o
    '23456789',                   // bỏ 0, 1
    '!@#$%^&*?-_+=',
  ];
  const all = groups.join('');
  let chars;
  do {
    chars = groups.map((g) => g[randomIndex(g.length)]);
    while (chars.length < length) chars.push(all[randomIndex(all.length)]);
    for (let i = chars.length - 1; i > 0; i -= 1) {
      const j = randomIndex(i + 1);
      [chars[i], chars[j]] = [chars[j], chars[i]];
    }
  } while (!isStrongPassword(chars.join('')));
  return chars.join('');
}
