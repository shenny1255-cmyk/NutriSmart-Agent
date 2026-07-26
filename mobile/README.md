# NutriSmart Agent - Mobile Application (React Native Expo)

Ung dung di dong ho tro theo doi van dong thoi gian thuc, dem buoc chan ngam, phan tich dinh duong dia thuc an bang AI Gemini Flash 2.0 va dong bo truc tiep voi CSDL PostgreSQL & Web Dashboard.

---

## Cac Tinh Nang Noi Bat Tren Mobile

### 1. Dem buoc chan ngam & Calo tieu hao (Step Tracker)
- Cam bien kep (Pedometer + Accelerometer): Tu dong dem buoc chan tren cac thiet bi Android/iOS ke ca khi di chuyen ngam.
- Tinh toan chi so sinh hoc: Tu dong tinh toan Calo tieu thu (kcal) va Quang duong di chuyen (km) dua tren can nang va chieu cao.
- Luu tru Offline: Luu tru du lieu ngam bang AsyncStorage va tu dong reset so buoc khi sang ngay moi (00:00).
- Dong bo 1 cham: Nut Dong bo ngay truyen du lieu dem buoc len Backend va cap nhat thang vao Card "Da tieu hao" tren Web Dashboard.

### 2. Phan tich Mon an AI Gemini Flash (AI Food Scanner)
- Chup anh / Chon tu Thu vien: Tich hop expo-image-picker chup anh truc tiep bang Camera hoac chon anh san co trong Album.
- Phan tich Multimodal Vision: Gui anh dia thuc an toi Gemini Flash 2.0 AI de tu dong nhan dien ten mon an, tinh tong Calo va phan tich 3 chi so Macros: Protein (Dam), Carbs (Duong), Fat (Beo).
- Thanh dieu chinh Khau phan (Portion Multiplier): Chon cac muc 0.5x, 1.0x, 1.5x, 2.0x - chi so Calo & Macros tu dong tinh toan lai theo ty le.
- Luu Nhat ky Bua an: Ghi nhan bua an vao CSDL PostgreSQL va cong don tu dong vao Card "Da nap" tren Web & Mobile.

### 3. Thanh Dieu Huong Bottom Navigation Bar (4 Tabs)
Thanh Tab Bar hien dai o day ung dung voi giao dien sac net, icon hoat hoa muot tu lucide-react-native:
- Tong quan (HomeScreen): Dem buoc chan, calo tieu hao, quang duong, dong bo du lieu.
- Quet AI (FoodScanScreen): Chup anh mon an & phan tich dinh duong AI.
- Lo trinh (PlanScreen): Theo doi Ke hoach Dinh duong ca nhan hoa, muc tieu Calo 2,000 kcal va phan bo 4 bua an.
- Ca nhan (ProfileScreen): Quan ly Thong tin tai khoan, Kiem tra dia chi may chu API va Dang xuat an toan.

### 4. Bao Mat & Xac Thuc JWT Token
- Luu tru JWT Token an toan trong AsyncStorage.
- Tu dong kiem tra token va chuyen thang vao ung dung ma khong can dang nhap lai.

---

## Huong Dan Cai Dat & Chay Ung Dung (Installation Guide)

### 1. Yeu cau moi truong (Prerequisites)
- Node.js: Phien ban >= 18.x
- Ung dung Expo Go: Tai san tren dien thoai Android (Google Play Store) hoac iOS (App Store).
- Backend & CSDL: Da khoi dong Backend Python (uvicorn app.main:app --host 0.0.0.0 --port 8000) va Docker PostgreSQL.

---

### 2. Cac buoc cai dat & Khoi dong

#### Buoc 1: Chuyen vao thu muc mobile
```powershell
cd mobile
```

#### Buoc 2: Cai dat cac goi phu thuoc (Dependencies)
```powershell
npm install
```

#### Buoc 3: Khoi dong Expo Dev Server o che do LAN
```powershell
npx expo start --clear --lan
```
*(Hoac dung npx expo start --clear --tunnel neu ban muan chay qua duong truyen dam may Tunnel)*.

#### Buoc 4: Trai nghiem tren dien thoai
- Mo ung dung Expo Go tren dien thoai.
- Dua camera quet ma QR hien thi trong cua so Terminal.
- Ung dung se nap giao dien va san sang su dung!

---

## Cau Truc Thu Muc (Directory Structure)

```text
mobile/
├── assets/                  # Hinh anh icon, splash screen
├── components/              # Cac UI Component chung (LogoMark...)
├── navigation/
│   └── MainTabNavigator.jsx # Thanh dieu huong Bottom Navigation 4 Tab
├── screens/
│   ├── LoginScreen.jsx      # Man hinh Dang nhap JWT Token
│   ├── HomeScreen.jsx       # Tab 1: Dem buoc chan & Calo tieu hao
│   ├── FoodScanScreen.jsx   # Tab 2: Chup anh & Phan tich Gemini AI
│   ├── PlanScreen.jsx       # Tab 3: Ke hoach Dinh duong
│   └── ProfileScreen.jsx    # Tab 4: Thong tin ca nhan & Dang xuat
├── theme.js                 # Token mau sac & Style chuan giao dien
├── App.js                   # Man hinh dieu huong goc (Root Navigator)
├── app.json                 # Cau hinh Expo, Camera & Permissions
├── babel.config.js          # Cau hinh Babel preset cho Expo SDK 54
├── metro.config.js          # Dang ky extension .jsx cho Metro
└── package.json             # Danh sach thu vien phu thuoc npm
```

---

## Luu Y Khi Chay Ung Dung
- Dam bao may tinh va dien thoai ket noi cung mot mang Wi-Fi khi chay che do --lan.
- Neu dia chi IP Wi-Fi cua may tinh bi thay doi, ban chi can cap nhat hang so BACKEND_IP trong App.js hoac nhap IP tren man hinh Dang nhap.
