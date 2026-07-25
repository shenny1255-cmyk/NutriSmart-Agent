import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  StatusBar,
  TextInput,
} from 'react-native';
import { Pedometer, Accelerometer } from 'expo-sensors';
import axios from 'axios';

export default function App() {
  const [isPedometerAvailable, setIsPedometerAvailable] = useState('Đang khởi tạo...');
  const [stepCount, setStepCount] = useState(0);
  const [motionIntensity, setMotionIntensity] = useState(0);
  const [weight, setWeight] = useState('65'); // kg
  const [height, setHeight] = useState('170'); // cm
  const [backendIp, setBackendIp] = useState('192.168.1.8'); // IP máy tính
  const [backendStatus, setBackendStatus] = useState('Chưa kiểm tra');

  // Ref dùng cho thuật toán đếm bước từ Cảm biến gia tốc (Accelerometer Fallback)
  const lastMagnitude = useRef(0);
  const isPeak = useRef(false);
  const lastStepTime = useRef(Date.now());

  useEffect(() => {
    let pedometerSub;
    let accelSub;

    async function setupSensors() {
      // 1. Thử dùng Pedometer Native trước
      try {
        const pedometerAvailable = await Pedometer.isAvailableAsync();
        if (pedometerAvailable) {
          const perm = await Pedometer.requestPermissionsAsync();
          if (perm.granted) {
            setIsPedometerAvailable('Đang dùng Cảm biến Pedometer Native 🏃');

            // Đọc lịch sử từ đầu ngày
            const now = new Date();
            const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
            try {
              const history = await Pedometer.getStepCountAsync(startOfDay, now);
              if (history && history.steps > 0) {
                setStepCount(history.steps);
              }
            } catch (e) {}

            pedometerSub = Pedometer.watchStepCount((res) => {
              setStepCount((prev) => prev + 1);
            });
            return;
          }
        }
      } catch (err) {}

      // 2. Nếu Pedometer không khả dụng hoặc bị giới hạn quyền -> Chuyển sang Accelerometer đếm bước thông minh
      setIsPedometerAvailable('Đang dùng Cảm biến Gia tốc (Accelerometer) 📱');
      Accelerometer.setUpdateInterval(100); // Đọc mỗi 100ms

      accelSub = Accelerometer.addListener(({ x, y, z }) => {
        // Tính tổng gia tốc 3 trục: M = sqrt(x^2 + y^2 + z^2)
        const magnitude = Math.sqrt(x * x + y * y + z * z);
        setMotionIntensity(magnitude.toFixed(1));

        const now = Date.now();
        const deltaM = magnitude - lastMagnitude.current;
        lastMagnitude.current = magnitude;

        // Đi bộ tạo ra gia tốc dao động từ 1.2G đến 1.8G (ngưỡng bước đi)
        const STEP_THRESHOLD = 1.28;
        const MIN_STEP_DELAY = 300; // Tối thiểu 300ms giữa 2 bước chân

        if (magnitude > STEP_THRESHOLD && !isPeak.current) {
          if (now - lastStepTime.current > MIN_STEP_DELAY) {
            isPeak.current = true;
            lastStepTime.current = now;
            setStepCount((prev) => prev + 1);
          }
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
  }, []);

  // Tính toán số km: Sải chân = height * 0.414 (cm)
  const userHeight = parseFloat(height) || 170;
  const strideMeters = (userHeight * 0.414) / 100;
  const distanceKm = ((stepCount * strideMeters) / 1000).toFixed(2);

  // Tính toán Calo đã đốt: Kcal = steps * 0.04 * (weight / 60)
  const userWeight = parseFloat(weight) || 65;
  const caloriesBurned = (stepCount * 0.04 * (userWeight / 60)).toFixed(1);

  // Nút cộng bước thủ công khi test
  const handleSimulateSteps = () => {
    setStepCount((prev) => prev + 100);
  };

  // Test kết nối Backend Python
  const testBackendConnection = async () => {
    try {
      setBackendStatus('Đang kết nối...');
      const url = `http://${backendIp.trim()}:8000/health`;
      const response = await axios.get(url, { timeout: 5000 });
      if (response.data && response.data.status === 'ok') {
        setBackendStatus('Kết nối thành công! ✅ (Backend OK)');
      } else {
        setBackendStatus('Kết nối thành công nhưng phản hồi lạ');
      }
    } catch (err) {
      setBackendStatus(`Lỗi kết nối: ${err.message}`);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor="#0F172A" />
      <ScrollView contentContainerStyle={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>NutriSmart Mobile 🥗</Text>
          <Text style={styles.headerSubtitle}>Theo dõi bước chân & Calo tiêu thụ</Text>
        </View>

        {/* Card Đếm Bước Chân */}
        <View style={styles.mainCard}>
          <Text style={styles.cardLabel}>SỐ BƯỚC HÔM NAY</Text>
          <Text style={styles.stepNumber}>{stepCount.toLocaleString()}</Text>
          <Text style={styles.stepUnit}>bước</Text>

          {/* Hàng chỉ số phụ */}
          <View style={styles.metricsRow}>
            <View style={styles.metricBox}>
              <Text style={styles.metricValue}>{caloriesBurned}</Text>
              <Text style={styles.metricLabel}>🔥 Calo (kcal)</Text>
            </View>

            <View style={styles.divider} />

            <View style={styles.metricBox}>
              <Text style={styles.metricValue}>{distanceKm}</Text>
              <Text style={styles.metricLabel}>📍 Quãng đường (km)</Text>
            </View>
          </View>
        </View>

        {/* Trạng thái cảm biến */}
        <View style={styles.infoCard}>
          <Text style={styles.infoTitle}>⚙️ Chế độ cảm biến:</Text>
          <Text style={styles.infoText}>{isPedometerAvailable}</Text>
          {motionIntensity > 0 && (
            <Text style={styles.motionText}>⚡ Đang nhận diện gia tốc bước: {motionIntensity} G</Text>
          )}

          <TouchableOpacity style={styles.simButton} onPress={handleSimulateSteps}>
            <Text style={styles.simButtonText}>+ 100 bước (Nút Test nhanh)</Text>
          </TouchableOpacity>
        </View>

        {/* Cấu hình chỉ số cơ thể */}
        <View style={styles.configCard}>
          <Text style={styles.configTitle}>👤 Chỉ số cá nhân</Text>
          <View style={styles.inputGroup}>
            <View style={styles.inputItem}>
              <Text style={styles.inputLabel}>Cân nặng (kg):</Text>
              <TextInput
                style={styles.textInput}
                value={weight}
                onChangeText={setWeight}
                keyboardType="numeric"
              />
            </View>
            <View style={styles.inputItem}>
              <Text style={styles.inputLabel}>Chiều cao (cm):</Text>
              <TextInput
                style={styles.textInput}
                value={height}
                onChangeText={setHeight}
                keyboardType="numeric"
              />
            </View>
          </View>
        </View>

        {/* Test kết nối Backend Python */}
        <View style={styles.configCard}>
          <Text style={styles.configTitle}>🌐 Kết nối Backend Python</Text>
          <Text style={styles.inputLabel}>Nhập IP máy tính (Wi-Fi):</Text>
          <TextInput
            style={styles.textInputFull}
            value={backendIp}
            onChangeText={setBackendIp}
            placeholder="Ví dụ: 192.168.1.8"
            placeholderTextColor="#64748B"
          />

          <TouchableOpacity style={styles.connectButton} onPress={testBackendConnection}>
            <Text style={styles.connectButtonText}>Kiểm tra kết nối BE (/health)</Text>
          </TouchableOpacity>

          <Text style={styles.statusText}>{backendStatus}</Text>
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  container: {
    padding: 20,
    paddingBottom: 40,
  },
  header: {
    marginBottom: 20,
    marginTop: 10,
  },
  headerTitle: {
    fontSize: 26,
    fontWeight: 'bold',
    color: '#F8FAFC',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#94A3B8',
    marginTop: 4,
  },
  mainCard: {
    backgroundColor: '#1E293B',
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#334155',
    shadowColor: '#10B981',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 12,
    elevation: 8,
  },
  cardLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#10B981',
    letterSpacing: 1.2,
  },
  stepNumber: {
    fontSize: 54,
    fontWeight: '900',
    color: '#F8FAFC',
    marginVertical: 4,
  },
  stepUnit: {
    fontSize: 16,
    color: '#64748B',
    marginBottom: 20,
  },
  metricsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#334155',
  },
  metricBox: {
    flex: 1,
    alignItems: 'center',
  },
  divider: {
    width: 1,
    height: 30,
    backgroundColor: '#334155',
  },
  metricValue: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#38BDF8',
  },
  metricLabel: {
    fontSize: 12,
    color: '#94A3B8',
    marginTop: 4,
  },
  infoCard: {
    backgroundColor: '#1E293B',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#334155',
  },
  infoTitle: {
    color: '#94A3B8',
    fontSize: 13,
    marginBottom: 4,
  },
  infoText: {
    color: '#F8FAFC',
    fontSize: 15,
    fontWeight: '600',
    marginBottom: 8,
  },
  motionText: {
    color: '#38BDF8',
    fontSize: 13,
    marginBottom: 12,
    fontWeight: '500',
  },
  simButton: {
    backgroundColor: '#334155',
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: 'center',
  },
  simButtonText: {
    color: '#38BDF8',
    fontWeight: '600',
    fontSize: 14,
  },
  configCard: {
    backgroundColor: '#1E293B',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#334155',
  },
  configTitle: {
    color: '#F8FAFC',
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  inputGroup: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  inputItem: {
    width: '48%',
  },
  inputLabel: {
    color: '#94A3B8',
    fontSize: 12,
    marginBottom: 6,
  },
  textInput: {
    backgroundColor: '#0F172A',
    color: '#F8FAFC',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#334155',
  },
  textInputFull: {
    backgroundColor: '#0F172A',
    color: '#F8FAFC',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    borderWidth: 1,
    borderColor: '#334155',
    marginBottom: 12,
  },
  connectButton: {
    backgroundColor: '#10B981',
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  connectButtonText: {
    color: '#0F172A',
    fontWeight: 'bold',
    fontSize: 15,
  },
  statusText: {
    color: '#F1F5F9',
    fontSize: 13,
    marginTop: 10,
    textAlign: 'center',
  },
});
