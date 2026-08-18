import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator, Alert, RefreshControl, ScrollView, StatusBar, StyleSheet,
  Text, TextInput, TouchableOpacity, View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from '@react-navigation/native';
import { Accelerometer, Pedometer } from 'expo-sensors';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  Activity, Bell, BookOpenText, CalendarCheck, Camera, CloudUpload, Cpu, Flame,
  Footprints, LogOut, MapPin, MessageCircle, RefreshCw, Sparkles, User,
} from 'lucide-react-native';

import { Theme } from '../theme';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { ErrorState, LoadingSkeleton } from '../components/AsyncState';
import { OfflineBanner } from '../components/OfflineBanner';
import { LogoMark } from '../components/Logo';

const STEP_KEY = 'nutrismart_steps_today';
const DATE_KEY = 'nutrismart_step_date';

export default function HomeScreen({ navigation }) {
  const { signOut } = useAuth();
  const [dataStatus, setDataStatus] = useState('loading');
  const [dataError, setDataError] = useState('');
  const [userData, setUserData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [unreadCount, setUnreadCount] = useState(0);

  const [stepsReady, setStepsReady] = useState(false);
  const [sensorStatus, setSensorStatus] = useState('Đang khởi tạo...');
  const [stepCount, setStepCount] = useState(0);
  const [motionIntensity, setMotionIntensity] = useState(0);
  const [weight, setWeight] = useState('65');
  const [height, setHeight] = useState('170');
  const [syncStatus, setSyncStatus] = useState('Chưa đồng bộ');
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState(null);

  const isPeak = useRef(false);
  const lastStepTime = useRef(Date.now());
  const stepCountRef = useRef(0);

  const saveSteps = useCallback(async (steps) => {
    try {
      await AsyncStorage.multiSet([
        [DATE_KEY, new Date().toDateString()],
        [STEP_KEY, String(steps)],
      ]);
    } catch {
      // Cache bước chân không được làm gián đoạn trải nghiệm chính.
    }
  }, []);

  useEffect(() => {
    let active = true;
    async function loadCachedSteps() {
      try {
        const [[, savedDate], [, savedSteps]] = await AsyncStorage.multiGet([DATE_KEY, STEP_KEY]);
        const today = new Date().toDateString();
        const steps = savedDate === today ? Number.parseInt(savedSteps || '0', 10) || 0 : 0;
        if (active) {
          stepCountRef.current = steps;
          setStepCount(steps);
        }
        if (savedDate !== today) await saveSteps(0);
      } finally {
        if (active) setStepsReady(true);
      }
    }
    loadCachedSteps();
    return () => {
      active = false;
    };
  }, [saveSteps]);

  useEffect(() => {
    if (!stepsReady) return undefined;

    let cancelled = false;
    let pedometerSubscription;
    let accelerometerSubscription;

    function updateSteps(next) {
      stepCountRef.current = next;
      setStepCount(next);
      saveSteps(next);
    }

    function startAccelerometer() {
      setSensorStatus('Ước tính bằng gia tốc kế');
      Accelerometer.setUpdateInterval(100);
      accelerometerSubscription = Accelerometer.addListener(({ x, y, z }) => {
        const magnitude = Math.sqrt(x * x + y * y + z * z);
        setMotionIntensity(Number(magnitude.toFixed(1)));
        const now = Date.now();
        if (magnitude > 1.28 && !isPeak.current && now - lastStepTime.current > 300) {
          isPeak.current = true;
          lastStepTime.current = now;
          updateSteps(stepCountRef.current + 1);
        } else if (magnitude < 1.1) {
          isPeak.current = false;
        }
      });
    }

    async function setupSensors() {
      try {
        const available = await Pedometer.isAvailableAsync();
        if (available) {
          const permission = await Pedometer.requestPermissionsAsync();
          if (permission.granted) {
            const baseSteps = stepCountRef.current;
            setSensorStatus('Cảm biến bước chân');
            const subscription = Pedometer.watchStepCount(({ steps }) => {
              updateSteps(baseSteps + Number(steps || 0));
            });
            if (cancelled) subscription.remove();
            else pedometerSubscription = subscription;
            return;
          }
        }
      } catch {
        // Thiết bị không hỗ trợ Pedometer sẽ dùng gia tốc kế.
      }
      if (!cancelled) startAccelerometer();
    }

    setupSensors();
    return () => {
      cancelled = true;
      pedometerSubscription?.remove();
      accelerometerSubscription?.remove();
    };
  }, [saveSteps, stepsReady]);

  const loadDashboard = useCallback(async () => {
    setDataStatus((current) => (current === 'success' ? 'refreshing' : 'loading'));
    setDataError('');
    try {
      const [me, rows, notifications] = await Promise.all([
        api.me(), api.dailySummary(1), api.notifications(20).catch(() => []),
      ]);
      const today = rows?.[rows.length - 1] || null;
      setUserData(me);
      setSummary(today);
      setUnreadCount(notifications.filter((item) => !item.is_read).length);
      if (me?.profile?.weight_kg) setWeight(String(me.profile.weight_kg));
      if (me?.profile?.height_cm) setHeight(String(me.profile.height_cm));
      setDataStatus('success');
    } catch (error) {
      setDataError(error.userMessage || 'Không thể tải dữ liệu tổng quan.');
      setDataStatus('error');
    }
  }, []);

  useFocusEffect(useCallback(() => {
    loadDashboard();
  }, [loadDashboard]));

  const userHeight = Number.parseFloat(height) || 170;
  const userWeight = Number.parseFloat(weight) || 65;
  const strideMeters = (userHeight * 0.414) / 100;
  const distanceKm = Number(((stepCount * strideMeters) / 1000).toFixed(2));
  const caloriesBurned = Number((stepCount * 0.04 * (userWeight / 60)).toFixed(1));

  const handleSync = async () => {
    if (isSyncing) return;
    setIsSyncing(true);
    setSyncStatus('Đang gửi dữ liệu...');
    try {
      await api.syncActivity({
        steps: stepCountRef.current,
        calories_burned: caloriesBurned,
        distance_km: distanceKm,
      });
      const now = new Date();
      const time = `${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}`;
      setSyncStatus(`Đồng bộ thành công lúc ${time}`);
      setLastSyncTime(time);
      await loadDashboard();
    } catch (error) {
      setSyncStatus(error.userMessage || 'Chưa thể đồng bộ. Vui lòng thử lại.');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleLogout = () => {
    Alert.alert('Đăng xuất', 'Bạn có muốn đăng xuất không?', [
      { text: 'Huỷ', style: 'cancel' },
      { text: 'Đăng xuất', style: 'destructive', onPress: signOut },
    ]);
  };

  const openRootScreen = (name) => navigation.getParent()?.navigate(name);

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor={Theme.colors.background} />
      <ScrollView
        contentContainerStyle={styles.container}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={dataStatus === 'refreshing'} onRefresh={loadDashboard} />}
      >
        <OfflineBanner />
        <View style={styles.header}>
          <View style={styles.identity}>
            <LogoMark size={36} />
            <View style={styles.identityText}>
              <Text style={styles.headerTitle}>NutriSmart</Text>
              <Text style={styles.headerEmail}>{userData?.email || 'Tổng quan hôm nay'}</Text>
            </View>
          </View>
          {lastSyncTime ? <Text style={styles.syncBadge}>Đã sync {lastSyncTime}</Text> : null}
        </View>

        {dataStatus === 'loading' && !userData ? <LoadingSkeleton rows={1} /> : null}
        {dataStatus === 'error' && !userData ? <ErrorState message={dataError} onRetry={loadDashboard} /> : null}
        {dataStatus === 'error' && userData ? (
          <ErrorState message={`${dataError} Số liệu bên dưới có thể là dữ liệu cũ.`} onRetry={loadDashboard} />
        ) : null}

        {summary ? (
          <View style={styles.summaryCard}>
            <SummaryMetric label="Đã nạp" value={summary.kcal_intake} color="#F97316" />
            <View style={styles.verticalDivider} />
            <SummaryMetric label="Đã tiêu hao" value={summary.kcal_burned} color="#0284C7" />
            <View style={styles.verticalDivider} />
            <SummaryMetric label="Còn lại" value={summary.kcal_remaining} color={Theme.colors.accentStrong} />
          </View>
        ) : null}

        <Text style={styles.quickTitle}>Truy cập nhanh</Text>
        <View style={styles.quickGrid}>
          <QuickAction icon={BookOpenText} label="Nhật ký" onPress={() => openRootScreen('Journal')} />
          <QuickAction icon={CalendarCheck} label="Check-in" onPress={() => openRootScreen('Checkin')} />
          <QuickAction icon={Bell} label="Thông báo" badge={unreadCount} onPress={() => openRootScreen('Notifications')} />
          <QuickAction icon={MessageCircle} label="Trợ lý AI" onPress={() => openRootScreen('Chat')} />
        </View>

        <View style={styles.mainCard}>
          <Footprints size={44} color={Theme.colors.accentStrong} />
          <Text style={styles.cardLabel}>SỐ BƯỚC HÔM NAY</Text>
          <Text style={styles.stepNumber}>{stepCount.toLocaleString()}</Text>
          <Text style={styles.stepUnit}>bước chân</Text>
          <View style={styles.metricsRow}>
            <Metric icon={<Flame size={16} color={Theme.colors.warning} />} label="Calo tiêu hao" value={`${caloriesBurned} kcal`} />
            <View style={styles.verticalDivider} />
            <Metric icon={<MapPin size={16} color="#0284C7" />} label="Quãng đường" value={`${distanceKm} km`} />
          </View>
        </View>

        <TouchableOpacity style={styles.aiBanner} onPress={() => navigation.navigate('TabFoodScan')} activeOpacity={0.85}>
          <View style={styles.aiIcon}><Camera size={24} color="#0F172A" /></View>
          <View style={styles.aiContent}>
            <View style={styles.inlineRow}>
              <Sparkles size={14} color={Theme.colors.accentStrong} />
              <Text style={styles.aiTitle}>Phân tích món ăn AI</Text>
            </View>
            <Text style={styles.aiSubtitle}>Chụp ảnh món ăn để ước tính năng lượng và dinh dưỡng</Text>
          </View>
        </TouchableOpacity>

        <View style={styles.syncCard}>
          <View style={styles.inlineRow}>
            <CloudUpload size={20} color={Theme.colors.accentStrong} />
            <Text style={styles.sectionHeading}>Đồng bộ hoạt động</Text>
          </View>
          <Text style={styles.sectionDescription}>Gửi số bước và calo tiêu hao hôm nay lên tài khoản của bạn.</Text>
          <TouchableOpacity style={[styles.primaryButton, isSyncing && styles.buttonDisabled]} onPress={handleSync} disabled={isSyncing}>
            {isSyncing ? <ActivityIndicator color="#FFFFFF" /> : (
              <><RefreshCw size={16} color="#FFFFFF" /><Text style={styles.primaryButtonText}>Đồng bộ ngay</Text></>
            )}
          </TouchableOpacity>
          <Text style={styles.syncStatus}>{syncStatus}</Text>
        </View>

        <View style={styles.infoCard}>
          <View style={styles.inlineRow}>
            <Cpu size={18} color={Theme.colors.text} />
            <Text style={styles.sectionHeading}>Cảm biến: {sensorStatus}</Text>
          </View>
          <Text style={styles.sensorNote}>Bước chân chỉ được cập nhật khi ứng dụng đang mở.</Text>
          {motionIntensity > 0 ? (
            <View style={styles.inlineRow}>
              <Activity size={14} color="#0284C7" />
              <Text style={styles.motionText}>Gia tốc thiết bị: {motionIntensity} G</Text>
            </View>
          ) : null}
          {__DEV__ ? (
            <TouchableOpacity style={styles.testButton} onPress={() => {
              const next = stepCountRef.current + 100;
              stepCountRef.current = next;
              setStepCount(next);
              saveSteps(next);
            }}>
              <Text style={styles.testButtonText}>+ 100 bước (kiểm thử)</Text>
            </TouchableOpacity>
          ) : null}
        </View>

        <View style={styles.configCard}>
          <View style={styles.inlineRow}>
            <User size={18} color={Theme.colors.text} />
            <Text style={styles.sectionHeading}>Chỉ số dùng để ước tính</Text>
          </View>
          <View style={styles.inputGroup}>
            <MetricInput label="Cân nặng (kg)" value={weight} onChangeText={setWeight} />
            <MetricInput label="Chiều cao (cm)" value={height} onChangeText={setHeight} />
          </View>
        </View>

        <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}>
          <LogOut size={15} color={Theme.colors.danger} />
          <Text style={styles.logoutText}>Đăng xuất</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

function SummaryMetric({ label, value, color }) {
  return (
    <View style={styles.summaryMetric}>
      <Text style={styles.summaryLabel}>{label}</Text>
      <Text style={[styles.summaryValue, { color }]}>{Math.round(Number(value || 0)).toLocaleString()}</Text>
      <Text style={styles.summaryUnit}>kcal</Text>
    </View>
  );
}

function Metric({ icon, label, value }) {
  return (
    <View style={styles.metricBox}>
      <View style={styles.inlineRow}>{icon}<Text style={styles.metricLabel}>{label}</Text></View>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

function MetricInput({ label, value, onChangeText }) {
  return (
    <View style={styles.inputItem}>
      <Text style={styles.inputLabel}>{label}</Text>
      <TextInput style={styles.textInput} value={value} onChangeText={onChangeText} keyboardType="decimal-pad" />
    </View>
  );
}

function QuickAction({ icon: Icon, label, onPress, badge = 0 }) {
  return (
    <TouchableOpacity style={styles.quickAction} onPress={onPress} activeOpacity={0.8}>
      <View style={styles.quickIcon}>
        <Icon size={20} color={Theme.colors.accentStrong} />
        {badge ? <View style={styles.quickBadge}><Text style={styles.quickBadgeText}>{badge > 9 ? '9+' : badge}</Text></View> : null}
      </View>
      <Text style={styles.quickLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Theme.colors.background },
  container: { padding: 20, paddingBottom: 40 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 },
  identity: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  identityText: { marginLeft: 10, flex: 1 },
  headerTitle: { fontSize: 25, fontWeight: '900', color: Theme.colors.text },
  headerEmail: { color: Theme.colors.textMuted, fontSize: 12, marginTop: 2 },
  syncBadge: { color: Theme.colors.accentStrong, fontSize: 10, fontWeight: '800', backgroundColor: Theme.colors.accentSoft, padding: 6, borderRadius: 12 },
  summaryCard: { flexDirection: 'row', backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md, borderWidth: 1, borderColor: Theme.colors.border, padding: 14, marginBottom: 16 },
  summaryMetric: { flex: 1, alignItems: 'center' },
  summaryLabel: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '700' },
  summaryValue: { fontSize: 18, fontWeight: '900', marginTop: 4 },
  summaryUnit: { color: Theme.colors.textMuted, fontSize: 10 },
  quickTitle: { color: Theme.colors.text, fontSize: 14, fontWeight: '900', marginBottom: 9 },
  quickGrid: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  quickAction: { flex: 1, alignItems: 'center', backgroundColor: Theme.colors.card, borderWidth: 1, borderColor: Theme.colors.border, borderRadius: Theme.radius.md, paddingVertical: 12, paddingHorizontal: 3 },
  quickIcon: { width: 38, height: 38, borderRadius: 19, backgroundColor: Theme.colors.accentSoft, alignItems: 'center', justifyContent: 'center' },
  quickBadge: { position: 'absolute', right: -5, top: -5, minWidth: 17, height: 17, borderRadius: 9, backgroundColor: Theme.colors.danger, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 3 },
  quickBadgeText: { color: '#FFFFFF', fontSize: 9, fontWeight: '900' },
  quickLabel: { color: Theme.colors.textSecondary, fontSize: 10, fontWeight: '800', marginTop: 7, textAlign: 'center' },
  mainCard: { backgroundColor: Theme.colors.card, borderRadius: Theme.radius.lg, padding: 24, alignItems: 'center', marginBottom: 16, borderWidth: 1, borderColor: Theme.colors.border },
  cardLabel: { fontSize: 12, fontWeight: '800', color: Theme.colors.accentStrong, letterSpacing: 1.4, marginTop: 10 },
  stepNumber: { fontSize: 54, fontWeight: '900', color: Theme.colors.text, marginTop: 3 },
  stepUnit: { color: Theme.colors.textMuted, fontSize: 13, marginBottom: 18 },
  metricsRow: { flexDirection: 'row', alignItems: 'center', width: '100%', borderTopWidth: 1, borderTopColor: Theme.colors.border, paddingTop: 17 },
  metricBox: { flex: 1, alignItems: 'center' },
  metricLabel: { color: Theme.colors.textMuted, fontSize: 11, marginLeft: 4 },
  metricValue: { color: Theme.colors.text, fontSize: 17, fontWeight: '900', marginTop: 5 },
  verticalDivider: { width: 1, height: 38, backgroundColor: Theme.colors.border },
  aiBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#10B98112', borderRadius: Theme.radius.md, padding: 16, marginBottom: 16, borderWidth: 1, borderColor: '#10B98135' },
  aiIcon: { width: 46, height: 46, borderRadius: 23, backgroundColor: Theme.colors.accentStrong, alignItems: 'center', justifyContent: 'center' },
  aiContent: { flex: 1, marginLeft: 12 },
  aiTitle: { color: Theme.colors.text, fontSize: 16, fontWeight: '800', marginLeft: 5 },
  aiSubtitle: { color: Theme.colors.textSecondary, fontSize: 12, marginTop: 3 },
  syncCard: { backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md, padding: 18, borderWidth: 1, borderColor: Theme.colors.border, marginBottom: 16 },
  infoCard: { backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md, padding: 16, borderWidth: 1, borderColor: Theme.colors.border, marginBottom: 16 },
  configCard: { backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md, padding: 16, borderWidth: 1, borderColor: Theme.colors.border, marginBottom: 16 },
  inlineRow: { flexDirection: 'row', alignItems: 'center' },
  sectionHeading: { color: Theme.colors.text, fontSize: 15, fontWeight: '800', marginLeft: 7 },
  sectionDescription: { color: Theme.colors.textMuted, fontSize: 12, lineHeight: 18, marginVertical: 10 },
  primaryButton: { flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: Theme.colors.accentStrong, borderRadius: Theme.radius.sm, paddingVertical: 13 },
  buttonDisabled: { opacity: 0.55 },
  primaryButtonText: { color: '#FFFFFF', fontWeight: '800', fontSize: 14 },
  syncStatus: { color: Theme.colors.textSecondary, fontSize: 12, textAlign: 'center', marginTop: 9 },
  sensorNote: { color: Theme.colors.textMuted, fontSize: 11, lineHeight: 17, marginVertical: 8 },
  motionText: { color: '#0284C7', fontSize: 12, fontWeight: '700', marginLeft: 5 },
  testButton: { backgroundColor: Theme.colors.cardSecondary, paddingVertical: 10, borderRadius: Theme.radius.sm, alignItems: 'center', marginTop: 12 },
  testButtonText: { color: Theme.colors.accentStrong, fontWeight: '800', fontSize: 12 },
  inputGroup: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 12 },
  inputItem: { width: '47%' },
  inputLabel: { color: Theme.colors.textMuted, fontSize: 11, marginBottom: 6 },
  textInput: { backgroundColor: '#FFFFFF', borderRadius: Theme.radius.sm, borderWidth: 1, borderColor: Theme.colors.border, paddingHorizontal: 12, paddingVertical: 9, color: Theme.colors.text, fontWeight: '700' },
  logoutButton: { flexDirection: 'row', gap: 6, alignItems: 'center', alignSelf: 'flex-end', padding: 10 },
  logoutText: { color: Theme.colors.danger, fontSize: 13, fontWeight: '700' },
});
