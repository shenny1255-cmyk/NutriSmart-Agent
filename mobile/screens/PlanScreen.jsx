import React, { useCallback, useMemo, useState } from 'react';
import {
  RefreshControl, ScrollView, StatusBar, StyleSheet, Text, TouchableOpacity, View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from '@react-navigation/native';
import { Calendar, CalendarCheck, Dumbbell, Flame, RefreshCw, Target, Utensils } from 'lucide-react-native';

import { Theme } from '../theme';
import { api } from '../services/api';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/AsyncState';
import { OfflineBanner } from '../components/OfflineBanner';
import { LogoMark } from '../components/Logo';

export default function PlanScreen({ navigation }) {
  const [status, setStatus] = useState('loading');
  const [plan, setPlan] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [selectedDay, setSelectedDay] = useState(0);

  const fetchPlan = useCallback(async () => {
    setStatus((current) => (current === 'success' ? 'refreshing' : 'loading'));
    setErrorMessage('');
    try {
      const data = await api.activePlan();
      setPlan(data);
      setSelectedDay((day) => Math.min(day, Math.max((data?.content?.days?.length || 1) - 1, 0)));
      setStatus('success');
    } catch (error) {
      if (error.status === 404) {
        setPlan(null);
        setStatus('empty');
      } else {
        setErrorMessage(error.userMessage || 'Không thể tải lộ trình.');
        setStatus('error');
      }
    }
  }, []);

  useFocusEffect(useCallback(() => {
    fetchPlan();
  }, [fetchPlan]));

  const days = plan?.content?.days || [];
  const day = days[selectedDay];
  const targetKcal = Number(plan?.daily_kcal_target || 0);
  const macros = useMemo(() => ({
    protein: Math.round((targetKcal * 0.25) / 4),
    carbs: Math.round((targetKcal * 0.50) / 4),
    fat: Math.round((targetKcal * 0.25) / 9),
  }), [targetKcal]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor={Theme.colors.background} />
      <ScrollView
        contentContainerStyle={styles.container}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={status === 'refreshing'} onRefresh={fetchPlan} />}
      >
        <OfflineBanner />
        <View style={styles.header}>
          <View style={styles.headerIdentity}>
            <LogoMark size={36} />
            <View style={styles.headerText}>
              <Text style={styles.headerTitle}>Lộ trình Dinh dưỡng</Text>
              <Text style={styles.headerSub}>Kế hoạch ăn uống cá nhân hóa</Text>
            </View>
          </View>
          <TouchableOpacity onPress={fetchPlan} style={styles.refreshBtn} disabled={status === 'refreshing'}>
            <RefreshCw size={18} color={Theme.colors.accentStrong} />
          </TouchableOpacity>
        </View>

        {status === 'loading' ? <LoadingSkeleton rows={3} /> : null}
        {status === 'empty' ? (
          <EmptyState title="Chưa có lộ trình" message="Hãy tạo lộ trình trên NutriSmart Web rồi quay lại thử lại." />
        ) : null}
        {status === 'error' && !plan ? <ErrorState message={errorMessage} onRetry={fetchPlan} /> : null}
        {status === 'error' && plan ? (
          <ErrorState message={`${errorMessage} Đang hiển thị dữ liệu đã tải trước đó.`} onRetry={fetchPlan} />
        ) : null}

        {plan ? (
          <>
            <View style={styles.targetCard}>
              <View style={styles.targetHeader}>
                <Target size={24} color={Theme.colors.accentStrong} />
                <Text style={styles.targetLabel}>MỤC TIÊU HÀNG NGÀY</Text>
              </View>
              <View style={styles.targetValueRow}>
                <Text style={styles.targetValue}>{targetKcal.toLocaleString()}</Text>
                <Text style={styles.targetUnit}>kcal / ngày</Text>
              </View>
              <Text style={styles.targetHint}>Phiên bản lộ trình {plan.version} · {plan.start_date} đến {plan.end_date}</Text>
            </View>

            <TouchableOpacity style={styles.checkinButton} onPress={() => navigation.getParent()?.navigate('Checkin')} activeOpacity={0.8}>
              <CalendarCheck size={18} color={Theme.colors.accentStrong} />
              <View style={styles.checkinText}>
                <Text style={styles.checkinTitle}>Check-in tiến độ 14 ngày</Text>
                <Text style={styles.checkinSubtitle}>Xem hạn báo cáo và đề xuất cho kỳ hiện tại</Text>
              </View>
              <Text style={styles.checkinArrow}>›</Text>
            </TouchableOpacity>

            <Text style={styles.sectionTitle}>Phân bổ dinh dưỡng tham khảo</Text>
            <View style={styles.macrosGrid}>
              <MacroCard value={`${macros.protein}g`} label="Protein" color="#0284C7" />
              <MacroCard value={`${macros.carbs}g`} label="Carb" color="#CA8A04" />
              <MacroCard value={`${macros.fat}g`} label="Chất béo" color="#DC2626" />
            </View>

            {days.length ? (
              <>
                <Text style={styles.sectionTitle}>Thực đơn từng ngày</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.dayRow}>
                  {days.map((_, index) => (
                    <TouchableOpacity
                      key={index}
                      style={[styles.dayChip, selectedDay === index && styles.dayChipActive]}
                      onPress={() => setSelectedDay(index)}
                    >
                      <Calendar size={14} color={selectedDay === index ? '#FFFFFF' : Theme.colors.textMuted} />
                      <Text style={[styles.dayChipText, selectedDay === index && styles.dayChipTextActive]}>
                        Ngày {index + 1}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </ScrollView>

                <View style={styles.scheduleCard}>
                  {(day?.meals || []).map((meal, index) => (
                    <View key={`${meal.type}-${index}`} style={styles.scheduleRow}>
                      <View style={styles.scheduleIcon}>
                        <Utensils size={18} color={Theme.colors.accentStrong} />
                      </View>
                      <View style={styles.scheduleContent}>
                        <Text style={styles.mealType}>{meal.type || `Bữa ${index + 1}`}</Text>
                        <Text style={styles.mealName}>{meal.name}</Text>
                      </View>
                      <Text style={styles.mealKcal}>{Number(meal.kcal || 0).toLocaleString()} kcal</Text>
                    </View>
                  ))}

                  {day?.exercise ? (
                    <View style={styles.exerciseRow}>
                      <Dumbbell size={20} color="#7C3AED" />
                      <View style={styles.exerciseContent}>
                        <Text style={styles.exerciseTitle}>Vận động</Text>
                        <Text style={styles.exerciseText}>{day.exercise}</Text>
                      </View>
                    </View>
                  ) : null}
                </View>
              </>
            ) : (
              <EmptyState title="Lộ trình chưa có thực đơn" message="Dữ liệu lộ trình chưa đầy đủ. Vui lòng tạo lại trên web." />
            )}
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function MacroCard({ value, label, color }) {
  return (
    <View style={[styles.macroCard, { borderLeftColor: color }]}>
      <Flame size={16} color={color} />
      <Text style={[styles.macroValue, { color }]}>{value}</Text>
      <Text style={styles.macroLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Theme.colors.background },
  container: { padding: 20, paddingBottom: 40 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 },
  headerIdentity: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  headerText: { marginLeft: 10, flex: 1 },
  headerTitle: { fontSize: 20, fontWeight: '800', color: Theme.colors.text },
  headerSub: { fontSize: 12, color: Theme.colors.textMuted, marginTop: 1 },
  refreshBtn: {
    width: 38, height: 38, borderRadius: 19, backgroundColor: Theme.colors.card,
    alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: Theme.colors.border,
  },
  targetCard: {
    backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md,
    padding: 20, borderWidth: 1, borderColor: Theme.colors.border, marginBottom: 22,
  },
  targetHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  targetLabel: { fontSize: 12, fontWeight: '800', color: Theme.colors.accentStrong, marginLeft: 8 },
  targetValueRow: { flexDirection: 'row', alignItems: 'baseline' },
  targetValue: { fontSize: 36, fontWeight: '900', color: Theme.colors.text },
  targetUnit: { fontSize: 15, fontWeight: '600', color: Theme.colors.textMuted, marginLeft: 8 },
  targetHint: { fontSize: 11, color: Theme.colors.textMuted, marginTop: 8 },
  checkinButton: { flexDirection: 'row', alignItems: 'center', backgroundColor: Theme.colors.accentSoft, borderWidth: 1, borderColor: '#10B98145', borderRadius: Theme.radius.md, padding: 14, marginTop: -10, marginBottom: 22 },
  checkinText: { flex: 1, marginLeft: 9 },
  checkinTitle: { color: Theme.colors.accentStrong, fontSize: 13, fontWeight: '900' },
  checkinSubtitle: { color: Theme.colors.textSecondary, fontSize: 10, marginTop: 2 },
  checkinArrow: { color: Theme.colors.accentStrong, fontSize: 24, fontWeight: '700' },
  sectionTitle: { fontSize: 15, fontWeight: '800', color: Theme.colors.text, marginBottom: 12 },
  macrosGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 24 },
  macroCard: {
    width: '31%', backgroundColor: Theme.colors.card, borderRadius: Theme.radius.sm,
    padding: 12, borderWidth: 1, borderColor: Theme.colors.border, borderLeftWidth: 4,
  },
  macroValue: { fontSize: 18, fontWeight: '900', marginTop: 7 },
  macroLabel: { fontSize: 11, color: Theme.colors.textMuted, marginTop: 2 },
  dayRow: { gap: 8, paddingBottom: 14 },
  dayChip: {
    flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 13, paddingVertical: 9,
    backgroundColor: Theme.colors.card, borderWidth: 1, borderColor: Theme.colors.border,
    borderRadius: Theme.radius.full,
  },
  dayChipActive: { backgroundColor: Theme.colors.accentStrong, borderColor: Theme.colors.accentStrong },
  dayChipText: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: '700' },
  dayChipTextActive: { color: '#FFFFFF' },
  scheduleCard: {
    backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md,
    padding: 16, borderWidth: 1, borderColor: Theme.colors.border,
  },
  scheduleRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: Theme.colors.border },
  scheduleIcon: { width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center', backgroundColor: Theme.colors.accentSoft },
  scheduleContent: { flex: 1, marginLeft: 10 },
  mealType: { color: Theme.colors.accentStrong, fontSize: 11, fontWeight: '800', textTransform: 'uppercase' },
  mealName: { color: Theme.colors.text, fontSize: 13, fontWeight: '700', marginTop: 2 },
  mealKcal: { color: Theme.colors.textSecondary, fontSize: 12, fontWeight: '800', marginLeft: 8 },
  exerciseRow: { flexDirection: 'row', alignItems: 'flex-start', paddingTop: 16 },
  exerciseContent: { flex: 1, marginLeft: 10 },
  exerciseTitle: { color: '#7C3AED', fontSize: 12, fontWeight: '800' },
  exerciseText: { color: Theme.colors.textSecondary, fontSize: 13, lineHeight: 19, marginTop: 3 },
});
