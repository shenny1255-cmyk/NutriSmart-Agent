/**
 * Quản lý lưu trữ ảnh thực tế của người dùng chụp/tải lên khi phân tích món ăn.
 * Nén ảnh thành thumbnail chất lượng cao (~40KB) để lưu vào localStorage
 * và hiển thị chuẩn xác trong trang Nhật ký (thay vì fallback ảnh mẫu).
 */

const STORAGE_KEY = 'nutrismart_scanned_meal_images';

export async function compressImageToThumbnail(dataUrl, maxDim = 600) {
  if (!dataUrl || typeof dataUrl !== 'string') return dataUrl;
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      let w = img.width;
      let h = img.height;
      if (w > maxDim || h > maxDim) {
        if (w > h) {
          h = Math.round((h * maxDim) / w);
          w = maxDim;
        } else {
          w = Math.round((w * maxDim) / h);
          h = maxDim;
        }
      }
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext('2d');
      if (!ctx) return resolve(dataUrl);
      ctx.drawImage(img, 0, 0, w, h);
      resolve(canvas.toDataURL('image/jpeg', 0.8));
    };
    img.onerror = () => resolve(dataUrl);
    img.src = dataUrl;
  });
}

export async function saveScannedMealImage(foodName, dataUrl) {
  if (!foodName || !dataUrl) return;
  try {
    const thumb = await compressImageToThumbnail(dataUrl, 600);
    const raw = localStorage.getItem(STORAGE_KEY) || '{}';
    const map = JSON.parse(raw);
    const key = foodName.trim().toLowerCase();
    map[key] = thumb;

    // Giữ tối đa 30 ảnh gần nhất để không chiếm dụng bộ nhớ
    const keys = Object.keys(map);
    if (keys.length > 30) {
      delete map[keys[0]];
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch (e) {
    console.warn('Could not save meal thumbnail to localStorage', e);
  }
}

export function getCustomMealImage(foodName) {
  if (!foodName || typeof foodName !== 'string') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const map = JSON.parse(raw);
    const key = foodName.trim().toLowerCase();
    if (map[key]) return map[key];

    // So khớp gần đúng nếu tên món có chứa nhau
    for (const [k, v] of Object.entries(map)) {
      if (key.includes(k) || k.includes(key)) {
        return v;
      }
    }
  } catch {
    return null;
  }
  return null;
}
