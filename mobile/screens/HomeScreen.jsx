import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  StyleSheet, Text, View, TouchableOpacity,
  ScrollView, SafeAreaView, StatusBar, TextInput,
  Alert, ActivityIndicator,
} from 'react-native';
import { Pedometer, Accelerometer } from 'expo-sensors';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import {
  LogOut, Footprints, Flame, MapPin, CloudUpload,
  Cpu, User, RefreshCw, Activity, Camera, Sparkles
} from 'lucide-react-native';
import { Theme } from '../theme';
import { LogoMark } from '../components/Logo';

const STEP_KEY = 'nutrismart_steps_today';
const DATE_KEY = 'nutrismart_step_date';

export default function HomeScreen({ navigation, route }) {
  const backendIp = route?.params?.backendIp ?? '10.120.56.85';

  const [isPedometerAvailable, setIsPedometerAvailable] = useState('Đang khởi tạo...');
  const [stepCount, setStepCount] = useState(0);
  const [motionIntensity, setMotionIntensity] = useState(0);
  const [weight, setWeight] = useState('65');
  const [height, setHeight] = useState('170');
  const [syncStatus, setSyncStatus] = useState('Chưa đồng bộ');
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState(null);
  const [userEmail, setUserEmail] = useState('');

  const isPeak = useRef(false);
  const lastStepTime = useRef(Date.now());
  const stepCountRef = useRef(0);

  // ─── Load token & email, số bước đã lưu hôm nay ───
  useEffect(() => {
    async function init() {
      try {
        const token = await AsyncStorage.getItem('access_token');
        if (!token) {
          navigation.replace('Login', { backendIp });
          return;
        }
        try {
          const res = await axios.get(`http://${backendIp}:8000/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
            timeout: 5000,
          });
          setUserEmail(res.data?.email ?? '');
        } catch (_) {}

        const savedDate = await AsyncStorage.getItem(DATE_KEY);
        const today = new Date().toDateString();
        if (savedDate === today) {
          const saved = await AsyncStorage.getItem(STEP_KEY);
          if (saved) {
            const steps = parseInt(saved, 10);
            setStepCount(steps);
            stepCountRef.current = steps;
          }
        } else {
          await AsyncStorage.setItem(DATE_KEY, today);
          await AsyncStorage.setItem(STEP_KEY, '0');
        }
      } catch (e) {
        console.log('Init error:', e);
      }
    }
    init();
  }, [backendIp, navigation]);

  // ─── Lưu bước chân offline ───
  const saveSteps = useCallback(async (steps) => {
    try {
      await AsyncStorage.setItem(DATE_KEY, new Date().toDateString());
      await AsyncStorage.setItem(STEP_KEY, String(steps));
    } catch (_) {}
  }, []);

  // ─── Khởi tạo cảm biến ───
  useEffect(() => {
    let pedometerSub;
    let accelSub;

    async function setupSensors() {
      try {
        const available = await Pedometer.isAvailableAsync();
        if (available) {
          const perm = await Pedometer.requestPermissionsAsync();
          if (perm.granted) {
            setIsPedometerAvailable('Pedometer Native 🏃');
            pedometerSub = Pedometer.watchStepCount(() => {
              setStepCount((prev) => {
                const next = prev + 1;
                stepCountRef.current = next;
                saveSteps(next);
                return next;
              });
            });
            return;
          }
        }
      } catch (_) {}

      setIsPedometerAvailable('Accelerometer 📱');
      Accelerometer.setUpdateInterval(100);
      accelSub = Accelerometer.addListener(({ x, y, z }) => {
        const magnitude = Math.sqrt(x * x + y * y + z * z);
        setMotionIntensity(parseFloat(magnitude.toFixed(1)));
        const now = Date.now();
        if (magnitude > 1.28 && !isPeak.current && now - lastStepTime.current > 300) {
          isPeak.current = true;
          lastStepTime.current = now;
          setStepCount((prev) => {
            const next = prev + 1;
            stepCountRef.current = next;
            saveSteps(next);
            return next;
          });
        } else if (magnitude < 1.1) {
          isPeak.current = false;
        }
      });
    }

    setupSensors();
    return () => {
      if (pedometerSub) pedometerSub.remove();
      if (accelSub) accelSub.remove();
    };
  }, [saveSteps]);

  // ─── Tính calo & quãng đường ───
  const userHeight = parseFloat(height) || 170;
  const strideMeters = (userHeight * 0.414) / 100;
  const distanceKm = parseFloat(((stepCount * strideMeters) / 1000).toFixed(2));
  const userWeight = parseFloat(weight) || 65;
  const caloriesBurned = parseFloat((stepCount * 0.04 * (userWeight / 60)).toFixed(1));

  // ─── Đồng bộ lên Backend ───
  const handleSync = async () => {
    setIsSyncing(true);
    setSyncStatus('Đang gửi dữ liệu...');
    try {
      const token = await AsyncStorage.getItem('access_token');
      if (!token) {
        setSyncStatus('❌ Chưa đăng nhập');
        navigation.replace('Login', { backendIp });
        return;
      }

      const res = await axios.post(
        `http://${backendIp}:8000/api/v1/tracking/daily-activity`,
        { steps: stepCountRef.current, calories_burned: caloriesBurned, distance_km: distanceKm },
        { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, timeout: 8000 }
      );

      if (res.status === 200) {
        const now = new Date();
        const t = `${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}`;
        setSyncStatus(`✅ Đồng bộ thành công lúc ${t}`);
        setLastSyncTime(t);
      }
    } catch (err) {
      if (err.response?.status === 401) {
        setSyncStatus('❌ Token hết hạn — vui lòng đăng nhập lại');
        await AsyncStorage.removeItem('access_token');
        navigation.replace('Login', { backendIp });
      } else {
        setSyncStatus(`❌ ${err.message}`);
      }
    } finally {
      setIsSyncing(false);
    }
  };

  // ─── Đăng xuất ───
  const handleLogout = () => {
    Alert.alert('Đăng xuất', 'Bạn có muốn đăng xuất không?', [
      { text: 'Huỷ', style: 'cancel' },
      {
        text: 'Đăng xuất', style: 'destructive',
        onPress: async () => {
          await AsyncStorage.removeItem('access_token');
          navigation.replace('Login', { backendIp });
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor={Theme.colors.background} />
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>

        {/* Header */}
        <View style={styles.header}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <LogoMark size={36} />
            <View style={{ marginLeft: 10 }}>
              <Text style={styles.headerTitle}>NutriSmart</Text>
              {userEmail ? (
                <Text style={styles.headerEmail}>{userEmail}</Text>
              ) : null}
            </View>
          </View>
          <View style={{ alignItems: 'flex-end' }}>
            {lastSyncTime && (
              <View style={styles.syncBadgeContainer}>
                <RefreshCw size={10} color={Theme.colors.accentStrong} style={{ marginRight: 4 }} />
                <Text style={styles.syncBadge}>Đã sync lúc {lastSyncTime}</Text>
              </View>
            )}
          </View>
        </View>

        {/* Card Bước chân */}
        <View style={styles.mainCard}>
          <Footprints size={44} color={Theme.colors.accentStrong} style={styles.cardIcon} />
          <Text style={styles.cardLabel}>SỐ BƯỚC HÔM NAY</Text>
          <Text style={styles.stepNumber}>{stepCount.toLocaleString()}</Text>
          <Text style={styles.stepUnit}>bước chân</Text>
          
          <View style={styles.metricsRow}>
            <View style={styles.metricBox}>
              <View style={styles.metricHeader}>
                <Flame size={16} color={Theme.colors.warning} style={{ marginRight: 4 }} />
                <Text style={styles.metricLabel}>Calo tiêu hao</Text>
              </View>
              <Text style={[styles.metricValue, { color: Theme.colors.warning }]}>{caloriesBurned} <Text style={styles.metricUnit}>kcal</Text></Text>
            </View>
            
            <View style={styles.divider} />
            
            <View style={styles.metricBox}>
              <View style={styles.metricHeader}>
                <MapPin size={16} color="#38BDF8" style={{ marginRight: 4 }} />
                <Text style={styles.metricLabel}>Quãng đường</Text>
              </View>
              <Text style={[styles.metricValue, { color: '#0284C7' }]}>{distanceKm} <Text style={styles.metricUnit}>km</Text></Text>
            </View>
          </View>
        </View>

        {/* Banner Phân tích Món ăn AI Gemini */}
        <TouchableOpacity
          style={styles.aiScanBanner}
          onPress={() => navigation.navigate('FoodScan', { backendIp })}
          activeOpacity={0.85}
        >
          <View style={styles.aiScanIconBox}>
            <Camera size={24} color="#0F172A" />
          </View>
          <View style={{ flex: 1, marginLeft: 12 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <Sparkles size={14} color={Theme.colors.accentStrong} style={{ marginRight: 4 }} />
              <Text style={styles.aiScanTitle}>Phân tích Món ăn AI</Text>
            </View>
            <Text style={styles.aiScanSub}>Chụp ảnh đĩa thức ăn để Gemini AI tính Calo & Macros</Text>
          </View>
        </TouchableOpacity>

        {/* Nút Đồng bộ */}
        <View style={styles.syncCard}>
          <View style={styles.cardHeaderRow}>
            <CloudUpload size={20} color={Theme.colors.accentStrong} style={{ marginRight: 8 }} />
            <Text style={styles.syncTitle}>Đồng bộ lên Web Dashboard</Text>
          </View>
          <Text style={styles.syncDesc}>
            Gửi số bước & calo hôm nay. Web sẽ cập nhật mục "Đã tiêu hao" tức thì.
          </Text>
          <TouchableOpacity
            style={[styles.syncButton, isSyncing && styles.syncButtonDisabled]}
            onPress={handleSync}
            disabled={isSyncing}
            activeOpacity={0.8}
          >
            {isSyncing ? (
              <ActivityIndicator color="#FFFFFF" size="small" />
            ) : (
              <>
                <RefreshCw size={16} color="#FFFFFF" style={{ marginRight: 8 }} />
                <Text style={styles.syncButtonText}>Đồng bộ ngay</Text>
              </>
            )}
          </TouchableOpacity>
          {syncStatus ? <Text style={styles.syncStatusText}>{syncStatus}</Text> : null}
        </View>

        {/* Cảm biến */}
        <View style={styles.infoCard}>
          <View style={styles.cardHeaderRow}>
            <Cpu size={18} color={Theme.colors.text} style={{ marginRight: 8 }} />
            <Text style={styles.infoTitle}>Cảm biến: {isPedometerAvailable}</Text>
          </View>
          {motionIntensity > 0 && (
            <View style={styles.motionRow}>
              <Activity size={14} color="#38BDF8" style={{ marginRight: 6 }} />
              <Text style={styles.motionText}>Gia tốc thiết bị: {motionIntensity} G</Text>
            </View>
          )}
          <TouchableOpacity
            style={styles.simButton}
            onPress={() => {
              setStepCount((prev) => {
                const next = prev + 100;
                stepCountRef.current = next;
                saveSteps(next);
                return next;
              });
            }}
            activeOpacity={0.7}
          >
            <Text style={styles.simButtonText}>+ 100 bước (Test nhanh)</Text>
          </TouchableOpacity>
        </View>

        {/* Chỉ số cá nhân */}
        <View style={styles.configCard}>
          <View style={styles.cardHeaderRow}>
            <User size={18} color={Theme.colors.text} style={{ marginRight: 8 }} />
            <Text style={styles.configTitle}>Chỉ số cá nhân</Text>
          </View>
          <View style={styles.inputGroup}>
            <View style={styles.inputItem}>
              <Text style={styles.inputLabel}>Cân nặng (kg)</Text>
              <TextInput style={styles.textInput} value={weight} onChangeText={setWeight} keyboardType="numeric" />
            </View>
            <View style={styles.inputItem}>
              <Text style={styles.inputLabel}>Chiều cao (cm)</Text>
              <TextInput style={styles.textInput} value={height} onChangeText={setHeight} keyboardType="numeric" />
            </View>
          </View>
        </View>

        {/* Nút Đăng xuất ở dưới cùng bên phải */}
        <View style={styles.footerRow}>
          <TouchableOpacity onPress={handleLogout} style={styles.logoutBtnBottom} activeOpacity={0.7}>
            <LogOut size={14} color={Theme.colors.danger} style={{ marginRight: 6 }} />
            <Text style={styles.logoutTextBottom}>Đăng xuất</Text>
          </TouchableOpacity>
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Theme.colors.background },
  container: { padding: 20, paddingBottom: 40 },
  header: {
    flexDirection: 'row', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: 24, marginTop: 4,
  },
  headerTitle: { fontSize: 26, fontWeight: '800', color: Theme.colors.text, letterSpacing: -0.5 },
  headerEmail: { fontSize: 13, color: Theme.colors.textMuted, marginTop: 2, fontWeight: '500' },
  syncBadgeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 6,
    backgroundColor: Theme.colors.accentSoft,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: Theme.radius.full,
    alignSelf: 'flex-start',
  },
  syncBadge: {
    fontSize: 11, color: Theme.colors.accentStrong, fontWeight: '600'
  },
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Theme.colors.card,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: Theme.radius.sm,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  logoutText: { color: Theme.colors.textMuted, fontSize: 13, fontWeight: '600' },

  mainCard: {
    backgroundColor: Theme.colors.card,
    borderRadius: Theme.radius.lg,
    padding: 24,
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    shadowColor: '#10b981',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.05,
    shadowRadius: 16,
    elevation: 2,
  },
  cardIcon: {
    marginBottom: 12,
  },
  cardLabel: { fontSize: 12, fontWeight: '800', color: Theme.colors.accentStrong, letterSpacing: 1.5 },
  stepNumber: { fontSize: 56, fontWeight: '900', color: Theme.colors.text, marginVertical: 4, letterSpacing: -1 },
  stepUnit: { fontSize: 14, fontWeight: '600', color: Theme.colors.textMuted, marginBottom: 20 },
  metricsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: Theme.colors.border,
  },
  metricBox: { flex: 1, alignItems: 'center' },
  metricHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  divider: { width: 1, height: 40, backgroundColor: Theme.colors.border },
  metricValue: { fontSize: 20, fontWeight: '800' },
  metricUnit: { fontSize: 12, fontWeight: '500', color: Theme.colors.textMuted },
  metricLabel: { fontSize: 12, fontWeight: '600', color: Theme.colors.textMuted },

  syncCard: {
    backgroundColor: Theme.colors.card,
    borderRadius: Theme.radius.md,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    shadowColor: '#10b981',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 2,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  syncTitle: { color: Theme.colors.text, fontSize: 16, fontWeight: '700' },
  syncDesc: { color: Theme.colors.textMuted, fontSize: 13, marginBottom: 16, lineHeight: 18, fontWeight: '500' },
  syncButton: {
    backgroundColor: Theme.colors.accentStrong,
    paddingVertical: 13,
    borderRadius: Theme.radius.sm,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: Theme.colors.accentStrong,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 2,
  },
  syncButtonDisabled: { backgroundColor: '#A7F3D0' },
  syncButtonText: { color: '#FFFFFF', fontWeight: 'bold', fontSize: 15 },
  syncStatusText: { color: Theme.colors.textSecondary, fontSize: 13, marginTop: 12, textAlign: 'center', fontWeight: '600' },

  infoCard: {
    backgroundColor: Theme.colors.card,
    borderRadius: Theme.radius.md,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: Theme.colors.border,
  },
  infoTitle: { color: Theme.colors.text, fontSize: 14, fontWeight: '700' },
  motionRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  motionText: { color: '#0284C7', fontSize: 13, fontWeight: '600' },
  simButton: {
    backgroundColor: Theme.colors.cardSecondary,
    paddingVertical: 12,
    borderRadius: Theme.radius.sm,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Theme.colors.border,
  },
  simButtonText: { color: Theme.colors.accentStrong, fontWeight: '700', fontSize: 14 },

  configCard: {
    backgroundColor: Theme.colors.card,
    borderRadius: Theme.radius.md,
    padding: 18,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: Theme.colors.border,
  },
  configTitle: { color: Theme.colors.text, fontSize: 15, fontWeight: '700' },
  inputGroup: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 12 },
  inputItem: { width: '47%' },
  inputLabel: { color: Theme.colors.textSecondary, fontSize: 12, marginBottom: 6, fontWeight: '600' },
  textInput: {
    backgroundColor: '#FFFFFF', color: Theme.colors.text, borderRadius: Theme.radius.sm,
    paddingHorizontal: 12, paddingVertical: 10, fontSize: 16,
    borderWidth: 1, borderColor: Theme.colors.border,
    fontWeight: '600',
  },
  footerRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 8,
    marginBottom: 16,
  },
  logoutBtnBottom: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Theme.colors.card,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: Theme.radius.sm,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.2)', // light red outline
    shadowColor: '#EF4444',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  logoutTextBottom: {
    color: Theme.colors.danger,
    fontSize: 14,
    fontWeight: '700',
  },
  aiScanBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#10B98112',
    borderRadius: Theme.radius.md,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#10B98135',
  },
  aiScanIconBox: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: Theme.colors.accentStrong,
    alignItems: 'center',
    justifyContent: 'center',
  },
  aiScanTitle: {
    color: Theme.colors.text,
    fontSize: 16,
    fontWeight: '800',
  },
  aiScanSub: {
    color: Theme.colors.textSecondary,
    fontSize: 12,
    marginTop: 2,
  },
});


