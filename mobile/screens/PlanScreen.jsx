import React, { useEffect, useState } from 'react';
import {
  StyleSheet, Text, View, ScrollView, SafeAreaView, StatusBar, ActivityIndicator, TouchableOpacity,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { Target, Flame, Calendar, Sparkles, RefreshCw, CheckCircle2, ChevronRight, Scale } from 'lucide-react-native';
import { Theme } from '../theme';
import { LogoMark } from '../components/Logo';

export default function PlanScreen({ route }) {
  let rawIp = route?.params?.backendIp ?? '10.120.56.85';
  if (rawIp === '172.16.162' || rawIp === '172.16.1.162') rawIp = '10.120.56.85';
  const backendIp = rawIp.trim();

  const [loading, setLoading] = useState(true);
  const [plan, setPlan] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchPlan = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      if (!token) return;

      const res = await axios.get(`http://${backendIp}:8000/api/v1/plans/active`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 8000,
      });

      if (res.data) {
        setPlan(res.data);
      }
    } catch (e) {
      console.log('Lỗi fetch plan:', e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPlan();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchPlan();
  };

  const targetKcal = plan?.daily_calorie_target ?? 2000;
  const targetProtein = Math.round((targetKcal * 0.25) / 4);
  const targetCarbs = Math.round((targetKcal * 0.50) / 4);
  const targetFat = Math.round((targetKcal * 0.25) / 9);

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor={Theme.colors.background} />
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>

        {/* Header */}
        <View style={styles.header}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <LogoMark size={36} />
            <View style={{ marginLeft: 10 }}>
              <Text style={styles.headerTitle}>Lộ trình Dinh dưỡng</Text>
              <Text style={styles.headerSub}>Kế hoạch ăn uống AI cá nhân hóa</Text>
            </View>
          </View>
          <TouchableOpacity onPress={handleRefresh} style={styles.refreshBtn} activeOpacity={0.7}>
            <RefreshCw size={18} color={Theme.colors.accentStrong} />
          </TouchableOpacity>
        </View>

        {loading ? (
          <View style={styles.loadingBox}>
            <ActivityIndicator size="large" color={Theme.colors.accentStrong} />
            <Text style={styles.loadingText}>Đang tải lộ trình dinh dưỡng...</Text>
          </View>
        ) : (
          <>
            {/* Banner Mục tiêu Calo */}
            <View style={styles.targetCard}>
              <View style={styles.targetHeader}>
                <Target size={24} color={Theme.colors.accentStrong} />
                <Text style={styles.targetLabel}>MỤC TIÊU HÀNG NGÀY</Text>
              </View>
              <View style={styles.targetValRow}>
                <Text style={styles.targetVal}>{targetKcal.toLocaleString()}</Text>
                <Text style={styles.targetUnit}>kcal / ngày</Text>
              </View>
              <Text style={styles.targetHint}>Mức năng lượng tối ưu được AI tính toán cho cơ thể bạn.</Text>
            </View>

            {/* Phân bổ Macros mục tiêu */}
            <Text style={styles.sectionTitle}>Phân bổ Macros mục tiêu</Text>
            <View style={styles.macrosGrid}>
              <View style={[styles.macroCard, { borderLeftColor: '#38BDF8' }]}>
                <Text style={[styles.macroValue, { color: '#0284C7' }]}>{targetProtein}g</Text>
                <Text style={styles.macroLabel}>Protein (25%)</Text>
                <Text style={styles.macroDesc}>Phát triển cơ bắp</Text>
              </View>

              <View style={[styles.macroCard, { borderLeftColor: '#EAB308' }]}>
                <Text style={[styles.macroValue, { color: '#CA8A04' }]}>{targetCarbs}g</Text>
                <Text style={styles.macroLabel}>Carbs (50%)</Text>
                <Text style={styles.macroDesc}>Cung cấp năng lượng</Text>
              </View>

              <View style={[styles.macroCard, { borderLeftColor: '#EF4444' }]}>
                <Text style={[styles.macroValue, { color: '#DC2626' }]}>{targetFat}g</Text>
                <Text style={styles.macroLabel}>Fat (25%)</Text>
                <Text style={styles.macroDesc}>Hấp thu Vitamin</Text>
              </View>
            </View>

            {/* Lịch trình Bữa ăn gợi ý */}
            <Text style={styles.sectionTitle}>Gợi ý phân bổ bữa ăn</Text>
            <View style={styles.mealList}>
              <View style={styles.mealItem}>
                <View style={[styles.mealIconCircle, { backgroundColor: '#F59E0B20' }]}>
                  <Flame size={20} color="#D97706" />
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={styles.mealTitle}>Bữa sáng (25%)</Text>
                  <Text style={styles.mealDesc}>Phở bò, Trứng cuộn, Cơm tấm hoặc Bánh mì yến mạch</Text>
                </View>
                <Text style={styles.mealKcal}>{Math.round(targetKcal * 0.25)} kcal</Text>
              </View>

              <View style={styles.mealItem}>
                <View style={[styles.mealIconCircle, { backgroundColor: '#10B98120' }]}>
                  <Flame size={20} color={Theme.colors.accentStrong} />
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={styles.mealTitle}>Bữa trưa (40%)</Text>
                  <Text style={styles.mealDesc}>Cơm cá thu sốt cà, Salad ức gà nướng, Thịt luộc</Text>
                </View>
                <Text style={styles.mealKcal}>{Math.round(targetKcal * 0.40)} kcal</Text>
              </View>

              <View style={styles.mealItem}>
                <View style={[styles.mealIconCircle, { backgroundColor: '#38BDF820' }]}>
                  <Flame size={20} color="#0284C7" />
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={styles.mealTitle}>Bữa tối (25%)</Text>
                  <Text style={styles.mealDesc}>Canh rau củ, Thịt nạc hấp, Trái cây tươi thanh mát</Text>
                </View>
                <Text style={styles.mealKcal}>{Math.round(targetKcal * 0.25)} kcal</Text>
              </View>

              <View style={styles.mealItem}>
                <View style={[styles.mealIconCircle, { backgroundColor: '#8B5CF620' }]}>
                  <Flame size={20} color="#7C3AED" />
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={styles.mealTitle}>Bữa phụ (10%)</Text>
                  <Text style={styles.mealDesc}>Sữa chua không đường, Hạt óc chó, Táo tây</Text>
                </View>
                <Text style={styles.mealKcal}>{Math.round(targetKcal * 0.10)} kcal</Text>
              </View>
            </View>

          </>
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Theme.colors.background },
  container: { padding: 20, paddingBottom: 40 },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    marginBottom: 20, marginTop: 4,
  },
  headerTitle: { fontSize: 20, fontWeight: '800', color: Theme.colors.text },
  headerSub: { fontSize: 12, color: Theme.colors.textMuted, marginTop: 1 },
  refreshBtn: {
    width: 38, height: 38, borderRadius: 19, backgroundColor: Theme.colors.card,
    alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: Theme.colors.border,
  },
  loadingBox: { paddingVertical: 60, alignItems: 'center' },
  loadingText: { color: Theme.colors.textMuted, marginTop: 12, fontSize: 14 },

  targetCard: {
    backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md,
    padding: 20, borderWidth: 1, borderColor: Theme.colors.border, marginBottom: 24,
  },
  targetHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  targetLabel: { fontSize: 12, fontWeight: '800', color: Theme.colors.accentStrong, marginLeft: 8, letterSpacing: 0.5 },
  targetValRow: { flexDirection: 'row', alignItems: 'baseline', marginBottom: 6 },
  targetVal: { fontSize: 36, fontWeight: '900', color: Theme.colors.text },
  targetUnit: { fontSize: 16, fontWeight: '600', color: Theme.colors.textMuted, marginLeft: 8 },
  targetHint: { fontSize: 12, color: Theme.colors.textMuted, lineHeight: 18 },

  sectionTitle: { fontSize: 15, fontWeight: '700', color: Theme.colors.text, marginBottom: 12 },

  macrosGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 24 },
  macroCard: {
    width: '31%', backgroundColor: Theme.colors.card, borderRadius: Theme.radius.sm,
    padding: 12, borderWidth: 1, borderColor: Theme.colors.border, borderLeftWidth: 4,
  },
  macroValue: { fontSize: 18, fontWeight: '800' },
  macroLabel: { fontSize: 11, fontWeight: '700', color: Theme.colors.text, marginTop: 4 },
  macroDesc: { fontSize: 10, color: Theme.colors.textMuted, marginTop: 2 },

  mealList: { backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md, padding: 16, borderWidth: 1, borderColor: Theme.colors.border },
  mealItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: Theme.colors.border },
  mealIconCircle: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' },
  mealTitle: { fontSize: 14, fontWeight: '700', color: Theme.colors.text },
  mealDesc: { fontSize: 11, color: Theme.colors.textMuted, marginTop: 2 },
  mealKcal: { fontSize: 14, fontWeight: '800', color: Theme.colors.text },
});
