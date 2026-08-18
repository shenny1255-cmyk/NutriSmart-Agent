import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator, RefreshControl, ScrollView, StyleSheet, Text, TextInput,
  TouchableOpacity, View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { CalendarClock, RotateCcw, ShieldAlert, Sparkles } from 'lucide-react-native';

import { Theme } from '../theme';
import { api } from '../services/api';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/AsyncState';
import { OfflineBanner } from '../components/OfflineBanner';

const STATUS_LABELS = {
  UPCOMING: 'Chưa đến hạn', DUE: 'Đến hạn', OVERDUE: 'Quá hạn', COMPLETED: 'Đã hoàn tất',
};

const RECOMMENDATION_LABELS = {
  NEEDS_REVIEW: 'Cần kiểm tra lại số liệu',
  CONTINUE_AND_TRACK: 'Tiếp tục theo dõi',
  IMPROVE_ADHERENCE: 'Cải thiện mức tuân thủ',
  CONTINUE: 'Tiếp tục lộ trình',
  CONTINUE_AND_MONITOR: 'Tiếp tục và theo dõi thêm',
  ADJUST_PLAN: 'Đề xuất điều chỉnh lộ trình',
};

function errorText(error, fallback) {
  return error?.userMessage || fallback;
}

function formatDate(value) {
  if (!value) return '—';
  const [year, month, day] = String(value).slice(0, 10).split('-');
  return `${day}/${month}/${year}`;
}

export default function CheckinScreen() {
  const [status, setStatus] = useState('loading');
  const [checkin, setCheckin] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async (refreshing = false) => {
    setStatus(refreshing ? 'refreshing' : 'loading');
    setError('');
    try {
      const [current, previous] = await Promise.all([api.activeCheckin(), api.checkinHistory(10)]);
      setCheckin(current);
      setHistory((previous || []).filter((item) => item.id !== current?.id));
      setStatus('success');
    } catch (requestError) {
      if (requestError?.status === 404) {
        setCheckin(null);
        setHistory([]);
        setStatus('empty');
      } else {
        setError(errorText(requestError, 'Không thể tải kỳ check-in.'));
        setStatus('error');
      }
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const changed = async (message) => {
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
        <Text style={styles.intro}>Mỗi 14 ngày, NutriSmart dùng số liệu thực tế để đánh giá và đề xuất bước tiếp theo.</Text>
        {notice ? <TouchableOpacity onPress={() => setNotice('')} style={styles.notice}><Text style={styles.noticeText}>{notice}</Text></TouchableOpacity> : null}
        {status === 'loading' ? <LoadingSkeleton rows={2} /> : null}
        {status === 'error' ? <ErrorState message={error} onRetry={load} /> : null}
        {status === 'empty' ? <EmptyState title="Chưa có kỳ check-in" message="Hãy tạo lộ trình dinh dưỡng trước khi bắt đầu check-in." /> : null}
        {checkin ? <CurrentCheckin item={checkin} onChanged={changed} onError={setError} /> : null}
        {error && status !== 'error' ? <Text style={styles.inlineError}>{error}</Text> : null}

        {history.length ? (
          <View style={styles.historySection}>
            <Text style={styles.sectionTitle}>Các kỳ trước</Text>
            {history.map((item) => <HistoryCard key={item.id} item={item} />)}
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function CurrentCheckin({ item, onChanged, onError }) {
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    weight: String(item.actual_weight_kg ?? item.baseline_weight_kg ?? ''),
    waist: String(item.actual_waist_cm ?? ''),
    activity: item.actual_activity_level ?? 3,
    adherence: item.adherence_pct ?? 70,
    energy: item.energy_level ?? 3,
    hunger: item.hunger_level ?? 3,
    sleep: item.sleep_quality ?? 3,
    notes: item.notes ?? '',
  });

  useEffect(() => {
    setForm({
      weight: String(item.actual_weight_kg ?? item.baseline_weight_kg ?? ''),
      waist: String(item.actual_waist_cm ?? ''), activity: item.actual_activity_level ?? 3,
      adherence: item.adherence_pct ?? 70, energy: item.energy_level ?? 3,
      hunger: item.hunger_level ?? 3, sleep: item.sleep_quality ?? 3, notes: item.notes ?? '',
    });
  }, [item.id, item.status]);

  const weight = Number(form.weight);
  const waist = Number(form.waist);
  const weightValid = weight >= 20 && weight <= 300
    && Math.abs(weight - Number(item.baseline_weight_kg)) / Number(item.baseline_weight_kg) <= 0.2;
  const waistValid = form.waist === '' || (waist >= 30 && waist <= 250);
  const canSubmit = item.status === 'OPEN' && item.display_status === 'DUE'
    && weightValid && waistValid && form.notes.length <= 1000;

  async function submit() {
    if (!canSubmit || busy) return;
    setBusy(true);
    onError('');
    try {
      await api.submitCheckin(item.id, {
        actual_weight_kg: weight,
        ...(form.waist ? { actual_waist_cm: waist } : {}),
        actual_activity_level: Number(form.activity), adherence_pct: Number(form.adherence),
        energy_level: Number(form.energy), hunger_level: Number(form.hunger),
        sleep_quality: Number(form.sleep), notes: form.notes.trim() || null,
      });
      await onChanged('Đã gửi báo cáo tiến độ. Hãy xem kết quả bên dưới.');
    } catch (requestError) {
      onError(errorText(requestError, 'Không gửi được báo cáo tiến độ.'));
    } finally {
      setBusy(false);
    }
  }

  async function reopen() {
    if (busy) return;
    setBusy(true);
    onError('');
    try {
      await api.reopenCheckin(item.id);
      await onChanged('Đã mở lại báo cáo để chỉnh sửa.');
    } catch (requestError) {
      onError(errorText(requestError, 'Không thể mở lại báo cáo.'));
    } finally {
      setBusy(false);
    }
  }

  async function decide(action) {
    if (busy) return;
    setBusy(true);
    onError('');
    try {
      await api.decideCheckin(item.id, action);
      await onChanged(action === 'APPLY_ADJUSTMENT' ? 'Đã áp dụng lộ trình điều chỉnh.' : 'Đã bắt đầu kỳ theo dõi tiếp theo.');
    } catch (requestError) {
      onError(errorText(requestError, 'Không áp dụng được quyết định.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.iconCircle}><CalendarClock size={22} color={Theme.colors.accentStrong} /></View>
        <View style={styles.headerContent}>
          <Text style={styles.cardTitle}>Kỳ {item.period_number}</Text>
          <Text style={styles.cardSubtitle}>{formatDate(item.start_date)} → {formatDate(item.period_end)}</Text>
        </View>
        <View style={[styles.badge, item.display_status === 'DUE' && styles.badgeDue, item.display_status === 'OVERDUE' && styles.badgeOverdue]}>
          <Text style={styles.badgeText}>{STATUS_LABELS[item.display_status] || item.display_status}</Text>
        </View>
      </View>

      {item.status === 'OPEN' ? (
        <>
          <View style={styles.targetBox}>
            <Text style={styles.targetLabel}>Mốc đầu kỳ</Text>
            <Text style={styles.targetValue}>{item.baseline_weight_kg} kg</Text>
            <Text style={styles.targetLabel}>Khoảng kỳ vọng</Text>
            <Text style={styles.targetValue}>{item.expected_weight_min_kg}–{item.expected_weight_max_kg} kg</Text>
          </View>
          {item.display_status === 'UPCOMING' ? (
            <Text style={styles.infoText}>Bạn có thể gửi báo cáo từ ngày {formatDate(item.due_date)} đến {formatDate(item.grace_until)}.</Text>
          ) : null}
          {item.display_status === 'OVERDUE' ? (
            <View style={styles.warningBox}><ShieldAlert size={18} color={Theme.colors.danger} /><Text style={styles.warningText}>Kỳ này đã quá hạn nhận dữ liệu. Kéo xuống để xem lịch sử hoặc liên hệ chuyên gia.</Text></View>
          ) : null}
          <TextField label="Cân nặng hiện tại (kg)" value={form.weight} onChangeText={(value) => setForm({ ...form, weight: value })} keyboardType="decimal-pad" />
          {!weightValid && form.weight ? <Text style={styles.validation}>Cân nặng phải từ 20–300 kg và không lệch quá 20% so với đầu kỳ.</Text> : null}
          <TextField label="Vòng eo (cm, tuỳ chọn)" value={form.waist} onChangeText={(value) => setForm({ ...form, waist: value })} keyboardType="decimal-pad" />
          <Rating label="Mức vận động thực tế" value={form.activity} onChange={(activity) => setForm({ ...form, activity })} />
          <Rating label="Mức tuân thủ (%)" value={form.adherence} onChange={(adherence) => setForm({ ...form, adherence })} options={[10, 30, 50, 70, 90]} suffix="%" />
          <Rating label="Mức năng lượng" value={form.energy} onChange={(energy) => setForm({ ...form, energy })} />
          <Rating label="Mức đói" value={form.hunger} onChange={(hunger) => setForm({ ...form, hunger })} />
          <Rating label="Chất lượng giấc ngủ" value={form.sleep} onChange={(sleep) => setForm({ ...form, sleep })} />
          <TextField label="Ghi chú (tuỳ chọn)" value={form.notes} onChangeText={(notes) => setForm({ ...form, notes })} multiline maxLength={1000} />
          <PrimaryButton title={item.display_status === 'DUE' ? 'Gửi báo cáo tiến độ' : 'Chưa thể gửi báo cáo'} onPress={submit} disabled={!canSubmit || busy} loading={busy} />
        </>
      ) : (
        <ResultPanel item={item} busy={busy} onReopen={reopen} onDecide={decide} />
      )}
    </View>
  );
}

function ResultPanel({ item, busy, onReopen, onDecide }) {
  const canAdjust = item.recommendation === 'ADJUST_PLAN' && item.proposed_kcal_target;
  return (
    <>
      <View style={styles.resultBox}>
        <View style={styles.resultTitleRow}><Sparkles size={18} color={Theme.colors.accentStrong} /><Text style={styles.resultTitle}>{RECOMMENDATION_LABELS[item.recommendation] || 'Kết quả check-in'}</Text></View>
        <Text style={styles.resultReason}>{item.recommendation_reason || 'Hệ thống đã ghi nhận báo cáo của bạn.'}</Text>
        <Text style={styles.resultMeta}>Cân nặng: {item.actual_weight_kg} kg · Thay đổi {Number(item.weight_change_kg || 0) >= 0 ? '+' : ''}{item.weight_change_kg || 0} kg</Text>
        <Text style={styles.resultMeta}>Tuân thủ: {item.adherence_pct}% · Nhật ký: {item.meal_log_days ?? 0} ngày</Text>
        {item.proposed_kcal_target ? <Text style={styles.proposed}>Mục tiêu đề xuất: {item.proposed_kcal_target} kcal/ngày</Text> : null}
        {item.ai_feedback ? <Text style={styles.aiFeedback}>{item.ai_feedback}</Text> : null}
        {item.safety_flags?.length ? <Text style={styles.validation}>Lưu ý an toàn: {item.safety_flags.join(', ')}</Text> : null}
      </View>
      {!item.decision ? (
        <>
          <TouchableOpacity style={styles.secondaryButton} onPress={onReopen} disabled={busy}>
            <RotateCcw size={16} color={Theme.colors.textSecondary} />
            <Text style={styles.secondaryButtonText}>Sửa số liệu vừa gửi</Text>
          </TouchableOpacity>
          {canAdjust ? <PrimaryButton title="Áp dụng lộ trình điều chỉnh" onPress={() => onDecide('APPLY_ADJUSTMENT')} disabled={busy} loading={busy} /> : null}
          <TouchableOpacity style={styles.continueButton} onPress={() => onDecide('CONTINUE')} disabled={busy}>
            <Text style={styles.continueText}>Tiếp tục lộ trình hiện tại</Text>
          </TouchableOpacity>
        </>
      ) : <Text style={styles.decisionText}>Quyết định: {item.decision === 'APPLY_ADJUSTMENT' ? 'Đã áp dụng điều chỉnh' : 'Tiếp tục lộ trình'}</Text>}
    </>
  );
}

function HistoryCard({ item }) {
  return (
    <View style={styles.historyCard}>
      <View style={styles.historyHeader}><Text style={styles.historyTitle}>Kỳ {item.period_number}</Text><Text style={styles.historyDate}>{formatDate(item.period_end)}</Text></View>
      <Text style={styles.historyResult}>{RECOMMENDATION_LABELS[item.recommendation] || STATUS_LABELS[item.display_status] || item.display_status}</Text>
      {item.actual_weight_kg ? <Text style={styles.historyMeta}>{item.actual_weight_kg} kg · Tuân thủ {item.adherence_pct ?? 0}%</Text> : null}
    </View>
  );
}

function TextField({ label, multiline, ...props }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput style={[styles.input, multiline && styles.multiline]} placeholderTextColor={Theme.colors.textMuted} multiline={multiline} {...props} />
    </View>
  );
}

function Rating({ label, value, onChange, options = [1, 2, 3, 4, 5], suffix = '' }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.ratingRow}>
        {options.map((option) => (
          <TouchableOpacity key={option} onPress={() => onChange(option)} style={[styles.rating, value === option && styles.ratingActive]}>
            <Text style={[styles.ratingText, value === option && styles.ratingTextActive]}>{option}{suffix}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

function PrimaryButton({ title, onPress, disabled, loading }) {
  return (
    <TouchableOpacity style={[styles.primaryButton, disabled && styles.disabled]} onPress={onPress} disabled={disabled}>
      {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.primaryButtonText}>{title}</Text>}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Theme.colors.background },
  container: { padding: 18, paddingBottom: 42 },
  intro: { color: Theme.colors.textMuted, fontSize: 13, lineHeight: 19, marginBottom: 14 },
  notice: { backgroundColor: Theme.colors.accentSoft, borderRadius: Theme.radius.sm, padding: 12, marginBottom: 12 },
  noticeText: { color: Theme.colors.accentStrong, fontSize: 13, fontWeight: '700' },
  inlineError: { color: Theme.colors.danger, backgroundColor: Theme.colors.dangerSoft, padding: 12, borderRadius: Theme.radius.sm, marginBottom: 12 },
  card: { backgroundColor: Theme.colors.card, borderWidth: 1, borderColor: Theme.colors.border, borderRadius: Theme.radius.lg, padding: 17, marginBottom: 18 },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 15 },
  iconCircle: { width: 44, height: 44, borderRadius: 22, backgroundColor: Theme.colors.accentSoft, alignItems: 'center', justifyContent: 'center' },
  headerContent: { flex: 1, marginLeft: 10 },
  cardTitle: { color: Theme.colors.text, fontSize: 18, fontWeight: '900' },
  cardSubtitle: { color: Theme.colors.textMuted, fontSize: 11, marginTop: 3 },
  badge: { backgroundColor: Theme.colors.cardSecondary, borderRadius: Theme.radius.full, paddingHorizontal: 10, paddingVertical: 6 },
  badgeDue: { backgroundColor: Theme.colors.warningSoft },
  badgeOverdue: { backgroundColor: Theme.colors.dangerSoft },
  badgeText: { color: Theme.colors.textSecondary, fontSize: 10, fontWeight: '900' },
  targetBox: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', backgroundColor: Theme.colors.cardSecondary, borderRadius: Theme.radius.sm, padding: 12, marginBottom: 14 },
  targetLabel: { width: '50%', color: Theme.colors.textMuted, fontSize: 11, marginBottom: 4 },
  targetValue: { width: '50%', color: Theme.colors.text, fontSize: 12, fontWeight: '900', textAlign: 'right', marginBottom: 4 },
  infoText: { color: Theme.colors.textSecondary, fontSize: 12, lineHeight: 18, backgroundColor: '#DBEAFE', borderRadius: Theme.radius.sm, padding: 11, marginBottom: 12 },
  warningBox: { flexDirection: 'row', gap: 8, backgroundColor: Theme.colors.dangerSoft, borderRadius: Theme.radius.sm, padding: 11, marginBottom: 12 },
  warningText: { flex: 1, color: Theme.colors.danger, fontSize: 12, lineHeight: 17 },
  field: { marginBottom: 13 },
  label: { color: Theme.colors.textSecondary, fontSize: 12, fontWeight: '800', marginBottom: 7 },
  input: { minHeight: 46, borderWidth: 1, borderColor: Theme.colors.borderStrong, borderRadius: Theme.radius.sm, backgroundColor: '#FFFFFF', paddingHorizontal: 12, color: Theme.colors.text },
  multiline: { minHeight: 90, paddingTop: 12, textAlignVertical: 'top' },
  validation: { color: Theme.colors.danger, fontSize: 11, lineHeight: 16, marginTop: -8, marginBottom: 12 },
  ratingRow: { flexDirection: 'row', gap: 7 },
  rating: { flex: 1, minHeight: 39, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: Theme.colors.borderStrong, borderRadius: Theme.radius.sm, backgroundColor: '#FFFFFF' },
  ratingActive: { backgroundColor: Theme.colors.accentSoft, borderColor: Theme.colors.accentStrong },
  ratingText: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: '800' },
  ratingTextActive: { color: Theme.colors.accentStrong },
  primaryButton: { minHeight: 47, alignItems: 'center', justifyContent: 'center', backgroundColor: Theme.colors.accentStrong, borderRadius: Theme.radius.sm, marginTop: 4 },
  primaryButtonText: { color: '#FFFFFF', fontSize: 14, fontWeight: '900' },
  disabled: { opacity: 0.45 },
  resultBox: { backgroundColor: Theme.colors.accentSoft, borderRadius: Theme.radius.md, padding: 14 },
  resultTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  resultTitle: { color: Theme.colors.accentStrong, fontSize: 15, fontWeight: '900', flex: 1 },
  resultReason: { color: Theme.colors.textSecondary, fontSize: 13, lineHeight: 19, marginTop: 9 },
  resultMeta: { color: Theme.colors.textMuted, fontSize: 11, marginTop: 7 },
  proposed: { color: Theme.colors.text, fontSize: 13, fontWeight: '900', marginTop: 10 },
  aiFeedback: { color: Theme.colors.textSecondary, fontSize: 12, fontStyle: 'italic', lineHeight: 18, marginTop: 10 },
  secondaryButton: { minHeight: 44, flexDirection: 'row', gap: 7, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: Theme.colors.borderStrong, borderRadius: Theme.radius.sm, marginTop: 12 },
  secondaryButtonText: { color: Theme.colors.textSecondary, fontSize: 13, fontWeight: '800' },
  continueButton: { alignItems: 'center', padding: 13, marginTop: 5 },
  continueText: { color: Theme.colors.accentStrong, fontSize: 13, fontWeight: '800' },
  decisionText: { color: Theme.colors.accentStrong, fontSize: 12, fontWeight: '800', textAlign: 'center', marginTop: 12 },
  historySection: { marginTop: 2 },
  sectionTitle: { color: Theme.colors.text, fontSize: 16, fontWeight: '900', marginBottom: 10 },
  historyCard: { backgroundColor: Theme.colors.card, borderWidth: 1, borderColor: Theme.colors.border, borderRadius: Theme.radius.md, padding: 14, marginBottom: 10 },
  historyHeader: { flexDirection: 'row', justifyContent: 'space-between' },
  historyTitle: { color: Theme.colors.text, fontSize: 14, fontWeight: '900' },
  historyDate: { color: Theme.colors.textMuted, fontSize: 11 },
  historyResult: { color: Theme.colors.accentStrong, fontSize: 12, fontWeight: '800', marginTop: 7 },
  historyMeta: { color: Theme.colors.textMuted, fontSize: 11, marginTop: 5 },
});
