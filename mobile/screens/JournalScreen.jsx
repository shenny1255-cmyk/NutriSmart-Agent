import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator, Alert, RefreshControl, ScrollView, StyleSheet, Text,
  TextInput, TouchableOpacity, View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Dumbbell, Scale, Trash2, UtensilsCrossed } from 'lucide-react-native';

import { Theme } from '../theme';
import { api } from '../services/api';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/AsyncState';
import { OfflineBanner } from '../components/OfflineBanner';

const TABS = [
  { key: 'meals', label: 'Bữa ăn', icon: UtensilsCrossed },
  { key: 'activities', label: 'Vận động', icon: Dumbbell },
  { key: 'weight', label: 'Cân nặng', icon: Scale },
];

const MEAL_TYPES = [
  ['BREAKFAST', 'Sáng'], ['LUNCH', 'Trưa'], ['DINNER', 'Tối'], ['SNACK', 'Ăn nhẹ'],
];

function localDate(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function shiftDate(value, amount) {
  const date = new Date(`${value}T12:00:00`);
  date.setDate(date.getDate() + amount);
  return localDate(date);
}

function displayDate(value) {
  const [year, month, day] = value.split('-');
  return `${day}/${month}/${year}`;
}

function errorText(error, fallback) {
  return error?.userMessage || fallback;
}

export default function JournalScreen() {
  const [tab, setTab] = useState('meals');
  const [date, setDate] = useState(localDate());
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [meals, setMeals] = useState([]);
  const [activities, setActivities] = useState([]);
  const [weights, setWeights] = useState([]);
  const [exercises, setExercises] = useState([]);

  const load = useCallback(async (refreshing = false) => {
    setStatus(refreshing ? 'refreshing' : 'loading');
    setError('');
    try {
      const [mealRows, activityRows, weightRows, exerciseRows] = await Promise.all([
        api.meals(date), api.activities(date), api.weightHistory(90), api.exercises(),
      ]);
      setMeals(mealRows || []);
      setActivities(activityRows || []);
      setWeights(weightRows || []);
      setExercises(exerciseRows || []);
      setStatus('success');
    } catch (requestError) {
      setError(errorText(requestError, 'Không thể tải nhật ký.'));
      setStatus('error');
    }
  }, [date]);

  useEffect(() => {
    load();
  }, [load]);

  const saved = async (message) => {
    setNotice(message);
    await load(true);
  };

  return (
    <SafeAreaView edges={['bottom']} style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
        refreshControl={<RefreshControl refreshing={status === 'refreshing'} onRefresh={() => load(true)} />}
      >
        <OfflineBanner />
        <Text style={styles.intro}>Ghi lại dữ liệu hằng ngày để lộ trình phản ánh đúng tiến độ của bạn.</Text>

        <View style={styles.tabs}>
          {TABS.map(({ key, label, icon: Icon }) => (
            <TouchableOpacity
              key={key}
              onPress={() => setTab(key)}
              style={[styles.tab, tab === key && styles.tabActive]}
            >
              <Icon size={16} color={tab === key ? '#FFFFFF' : Theme.colors.textMuted} />
              <Text style={[styles.tabText, tab === key && styles.tabTextActive]}>{label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.dateRow}>
          <TouchableOpacity style={styles.dateButton} onPress={() => setDate(shiftDate(date, -1))}>
            <Text style={styles.dateButtonText}>‹ Ngày trước</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setDate(localDate())}>
            <Text style={styles.dateText}>{date === localDate() ? 'Hôm nay' : displayDate(date)}</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.dateButton}
            onPress={() => setDate(shiftDate(date, 1))}
            disabled={date >= localDate()}
          >
            <Text style={[styles.dateButtonText, date >= localDate() && styles.disabledText]}>Ngày sau ›</Text>
          </TouchableOpacity>
        </View>

        {notice ? <Notice text={notice} onClose={() => setNotice('')} /> : null}
        {status === 'loading' ? <LoadingSkeleton rows={2} /> : null}
        {status === 'error' ? <ErrorState message={error} onRetry={load} /> : null}

        {status !== 'loading' && status !== 'error' && tab === 'meals' ? (
          <MealPanel date={date} rows={meals} onSaved={saved} onError={setError} />
        ) : null}
        {status !== 'loading' && status !== 'error' && tab === 'activities' ? (
          <ActivityPanel date={date} rows={activities} exercises={exercises} onSaved={saved} onError={setError} />
        ) : null}
        {status !== 'loading' && status !== 'error' && tab === 'weight' ? (
          <WeightPanel date={date} rows={weights} onSaved={saved} onError={setError} />
        ) : null}
        {error && status !== 'error' ? <Text style={styles.inlineError}>{error}</Text> : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function MealPanel({ date, rows, onSaved, onError }) {
  const [name, setName] = useState('');
  const [calories, setCalories] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [mealType, setMealType] = useState('LUNCH');
  const [saving, setSaving] = useState(false);

  const kcal = Number(calories);
  const portions = Number(quantity);
  const valid = name.trim().length >= 2 && kcal >= 1 && kcal <= 5000
    && portions >= 0.5 && portions <= 20;

  async function submit() {
    if (!valid || saving) return;
    setSaving(true);
    onError('');
    try {
      const result = await api.addMeal({
        food_name: name.trim(), calories_kcal: kcal, quantity: portions,
        meal_type: mealType, log_date: date,
      });
      setName('');
      setCalories('');
      setQuantity('1');
      await onSaved(`Đã ghi ${result.food_name} vào nhật ký.`);
    } catch (requestError) {
      onError(errorText(requestError, 'Không ghi được bữa ăn. Vui lòng thử lại.'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Section title="Thêm bữa ăn">
        <Field label="Tên món" value={name} onChangeText={setName} placeholder="Ví dụ: Cơm gà" maxLength={100} />
        <View style={styles.twoColumns}>
          <Field label="Kcal mỗi phần" value={calories} onChangeText={setCalories} keyboardType="decimal-pad" />
          <Field label="Số phần" value={quantity} onChangeText={setQuantity} keyboardType="decimal-pad" />
        </View>
        <Text style={styles.label}>Loại bữa</Text>
        <ChoiceRow options={MEAL_TYPES} value={mealType} onChange={setMealType} />
        <PrimaryButton title="Thêm vào nhật ký" onPress={submit} disabled={!valid || saving} loading={saving} />
      </Section>
      <Section title={`Bữa ăn · ${displayDate(date)}`}>
        {rows.length ? rows.map((row) => (
          <LogRow
            key={row.id}
            title={row.food_name}
            subtitle={`${MEAL_TYPES.find(([key]) => key === row.meal_type)?.[1] || row.meal_type} · ${row.quantity} phần`}
            value={`${Math.round(row.calories_kcal)} kcal`}
            onDelete={() => confirmDelete('bữa ăn', async () => {
              await api.deleteMeal(row.id);
              await onSaved('Đã xóa bữa ăn khỏi nhật ký.');
            }, onError)}
          />
        )) : <EmptyState title="Chưa có bữa ăn" message="Thêm món đã ăn trong ngày để theo dõi năng lượng." />}
      </Section>
    </>
  );
}

function ActivityPanel({ date, rows, exercises, onSaved, onError }) {
  const [exerciseId, setExerciseId] = useState('');
  const [duration, setDuration] = useState('30');
  const [calories, setCalories] = useState('');
  const [saving, setSaving] = useState(false);
  const minutes = Number(duration);
  const kcal = Number(calories);
  const valid = Boolean(exerciseId) && minutes >= 1 && minutes <= 600
    && (calories === '' || (kcal >= 1 && kcal <= 5000));

  async function submit() {
    if (!valid || saving) return;
    setSaving(true);
    onError('');
    try {
      const result = await api.addActivity({
        exercise_id: Number(exerciseId), duration_min: minutes,
        started_at: `${date}T12:00:00`,
        ...(calories ? { calories_burned: kcal } : {}),
      });
      setCalories('');
      await onSaved(`Đã ghi ${result.exercise_name} vào nhật ký.`);
    } catch (requestError) {
      onError(errorText(requestError, 'Không ghi được buổi tập. Vui lòng thử lại.'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Section title="Thêm vận động">
        <Text style={styles.label}>Bài tập</Text>
        {exercises.length ? (
          <View style={styles.choiceWrap}>
            {exercises.map((item) => (
              <Choice key={item.id} label={item.name} selected={String(item.id) === String(exerciseId)} onPress={() => setExerciseId(item.id)} />
            ))}
          </View>
        ) : <Text style={styles.help}>Chưa tải được danh mục bài tập.</Text>}
        <View style={styles.twoColumns}>
          <Field label="Số phút" value={duration} onChangeText={setDuration} keyboardType="number-pad" />
          <Field label="Kcal thiết bị (tuỳ chọn)" value={calories} onChangeText={setCalories} keyboardType="decimal-pad" />
        </View>
        <Text style={styles.help}>Để trống kcal để hệ thống tự tính theo bài tập và cân nặng.</Text>
        <PrimaryButton title="Thêm buổi tập" onPress={submit} disabled={!valid || saving} loading={saving} />
      </Section>
      <Section title={`Vận động · ${displayDate(date)}`}>
        {rows.length ? rows.map((row) => (
          <LogRow
            key={row.id}
            title={row.exercise_name}
            subtitle={`${row.duration_min} phút${row.steps ? ` · ${row.steps} bước` : ''}`}
            value={`${Math.round(row.calories_burned)} kcal`}
            onDelete={() => confirmDelete('buổi tập', async () => {
              await api.deleteActivity(row.id);
              await onSaved('Đã xóa buổi tập khỏi nhật ký.');
            }, onError)}
          />
        )) : <EmptyState title="Chưa có vận động" message="Thêm buổi tập để theo dõi năng lượng tiêu hao." />}
      </Section>
    </>
  );
}

function WeightPanel({ date, rows, onSaved, onError }) {
  const [weight, setWeight] = useState('');
  const [saving, setSaving] = useState(false);
  const kg = Number(weight);
  const valid = kg >= 20 && kg <= 300;
  const latestRows = [...rows].reverse().slice(0, 10);

  async function submit() {
    if (!valid || saving) return;
    setSaving(true);
    onError('');
    try {
      const result = await api.updateWeight({ weight_kg: kg, recorded_at: date });
      setWeight('');
      await onSaved(`Đã cập nhật ${result.weight_kg} kg${result.bmi ? ` · BMI ${result.bmi}` : ''}.`);
    } catch (requestError) {
      onError(errorText(requestError, 'Không cập nhật được cân nặng.'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Section title="Cập nhật cân nặng">
        <Field label={`Cân nặng ngày ${displayDate(date)} (kg)`} value={weight} onChangeText={setWeight} keyboardType="decimal-pad" placeholder="Ví dụ: 68.5" />
        <Text style={styles.help}>Giá trị hợp lệ từ 20 đến 300 kg.</Text>
        <PrimaryButton title="Lưu cân nặng" onPress={submit} disabled={!valid || saving} loading={saving} />
      </Section>
      <Section title="Lịch sử gần đây">
        {latestRows.length ? latestRows.map((row) => (
          <View key={row.recorded_at} style={styles.logRow}>
            <View style={styles.logContent}>
              <Text style={styles.logTitle}>{displayDate(row.recorded_at)}</Text>
              <Text style={styles.logSubtitle}>{row.bmi ? `BMI ${Number(row.bmi).toFixed(1)}` : 'Chưa có BMI'}</Text>
            </View>
            <Text style={styles.logValue}>{row.weight_kg} kg</Text>
          </View>
        )) : <EmptyState title="Chưa có dữ liệu" message="Cập nhật cân nặng để bắt đầu theo dõi xu hướng." />}
      </Section>
    </>
  );
}

function confirmDelete(label, action, onError) {
  Alert.alert('Xác nhận xóa', `Bạn có muốn xóa ${label} này khỏi nhật ký không?`, [
    { text: 'Huỷ', style: 'cancel' },
    {
      text: 'Xóa', style: 'destructive', onPress: async () => {
        try {
          await action();
        } catch (requestError) {
          onError(errorText(requestError, `Không xóa được ${label}.`));
        }
      },
    },
  ]);
}

function Section({ title, children }) {
  return <View style={styles.section}><Text style={styles.sectionTitle}>{title}</Text>{children}</View>;
}

function Field({ label, ...props }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput style={styles.input} placeholderTextColor={Theme.colors.textMuted} {...props} />
    </View>
  );
}

function ChoiceRow({ options, value, onChange }) {
  return <View style={styles.choiceWrap}>{options.map(([key, label]) => <Choice key={key} label={label} selected={value === key} onPress={() => onChange(key)} />)}</View>;
}

function Choice({ label, selected, onPress }) {
  return (
    <TouchableOpacity onPress={onPress} style={[styles.choice, selected && styles.choiceActive]}>
      <Text style={[styles.choiceText, selected && styles.choiceTextActive]}>{label}</Text>
    </TouchableOpacity>
  );
}

function PrimaryButton({ title, onPress, disabled, loading }) {
  return (
    <TouchableOpacity style={[styles.primaryButton, disabled && styles.buttonDisabled]} onPress={onPress} disabled={disabled}>
      {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.primaryButtonText}>{title}</Text>}
    </TouchableOpacity>
  );
}

function LogRow({ title, subtitle, value, onDelete }) {
  return (
    <View style={styles.logRow}>
      <View style={styles.logContent}><Text style={styles.logTitle}>{title}</Text><Text style={styles.logSubtitle}>{subtitle}</Text></View>
      <Text style={styles.logValue}>{value}</Text>
      <TouchableOpacity onPress={onDelete} style={styles.deleteButton} accessibilityLabel="Xóa khỏi nhật ký">
        <Trash2 size={17} color={Theme.colors.danger} />
      </TouchableOpacity>
    </View>
  );
}

function Notice({ text, onClose }) {
  return <TouchableOpacity onPress={onClose} style={styles.notice}><Text style={styles.noticeText}>{text}</Text></TouchableOpacity>;
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Theme.colors.background },
  container: { padding: 18, paddingBottom: 40 },
  intro: { color: Theme.colors.textMuted, fontSize: 13, lineHeight: 19, marginBottom: 14 },
  tabs: { flexDirection: 'row', backgroundColor: Theme.colors.cardSecondary, borderRadius: Theme.radius.md, padding: 4, marginBottom: 14 },
  tab: { flex: 1, minHeight: 42, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 5, borderRadius: 9 },
  tabActive: { backgroundColor: Theme.colors.accentStrong },
  tabText: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: '800' },
  tabTextActive: { color: '#FFFFFF' },
  dateRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 },
  dateButton: { paddingVertical: 8, minWidth: 88 },
  dateButtonText: { color: Theme.colors.accentStrong, fontSize: 12, fontWeight: '800' },
  disabledText: { color: Theme.colors.borderStrong },
  dateText: { color: Theme.colors.text, fontSize: 14, fontWeight: '900' },
  notice: { backgroundColor: Theme.colors.accentSoft, borderRadius: Theme.radius.sm, padding: 12, marginBottom: 12 },
  noticeText: { color: Theme.colors.accentStrong, fontSize: 13, fontWeight: '700' },
  inlineError: { color: Theme.colors.danger, backgroundColor: Theme.colors.dangerSoft, borderRadius: Theme.radius.sm, padding: 12, marginTop: 12, fontSize: 13 },
  section: { backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md, borderWidth: 1, borderColor: Theme.colors.border, padding: 16, marginBottom: 14 },
  sectionTitle: { color: Theme.colors.text, fontSize: 16, fontWeight: '900', marginBottom: 13 },
  field: { flex: 1, marginBottom: 12 },
  label: { color: Theme.colors.textSecondary, fontSize: 12, fontWeight: '700', marginBottom: 6 },
  input: { minHeight: 46, backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: Theme.colors.borderStrong, borderRadius: Theme.radius.sm, paddingHorizontal: 12, color: Theme.colors.text, fontSize: 14 },
  twoColumns: { flexDirection: 'row', gap: 10 },
  choiceWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12 },
  choice: { borderWidth: 1, borderColor: Theme.colors.borderStrong, backgroundColor: '#FFFFFF', borderRadius: Theme.radius.full, paddingHorizontal: 12, paddingVertical: 9 },
  choiceActive: { borderColor: Theme.colors.accentStrong, backgroundColor: Theme.colors.accentSoft },
  choiceText: { color: Theme.colors.textSecondary, fontSize: 12, fontWeight: '700' },
  choiceTextActive: { color: Theme.colors.accentStrong },
  help: { color: Theme.colors.textMuted, fontSize: 11, lineHeight: 17, marginTop: -3, marginBottom: 12 },
  primaryButton: { minHeight: 46, alignItems: 'center', justifyContent: 'center', backgroundColor: Theme.colors.accentStrong, borderRadius: Theme.radius.sm, marginTop: 3 },
  buttonDisabled: { opacity: 0.45 },
  primaryButtonText: { color: '#FFFFFF', fontSize: 14, fontWeight: '900' },
  logRow: { flexDirection: 'row', alignItems: 'center', minHeight: 62, borderBottomWidth: 1, borderBottomColor: Theme.colors.border },
  logContent: { flex: 1, paddingVertical: 9 },
  logTitle: { color: Theme.colors.text, fontSize: 13, fontWeight: '800' },
  logSubtitle: { color: Theme.colors.textMuted, fontSize: 11, marginTop: 3 },
  logValue: { color: Theme.colors.textSecondary, fontSize: 12, fontWeight: '800', marginLeft: 8 },
  deleteButton: { width: 38, height: 38, alignItems: 'center', justifyContent: 'center', marginLeft: 3 },
});
