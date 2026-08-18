import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { CheckCircle2 } from 'lucide-react-native';

import { Theme } from '../theme';
import { api } from '../services/api';
import { ErrorState, LoadingSkeleton } from '../components/AsyncState';
import { OfflineBanner } from '../components/OfflineBanner';

const GENDERS = [['MALE', 'Nam'], ['FEMALE', 'Nữ'], ['OTHER', 'Khác']];
const GOALS = [
  ['LOSE_WEIGHT', 'Giảm cân'], ['MAINTAIN', 'Duy trì'],
  ['GAIN_MUSCLE', 'Tăng cơ'], ['MEDICAL', 'Sức khỏe'],
];
const ACTIVITY_LEVELS = [
  [1, 'Rất ít'], [2, 'Ít'], [3, 'Vừa'], [4, 'Nhiều'], [5, 'Rất nhiều'],
];

function validDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T12:00:00`);
  return !Number.isNaN(date.getTime()) && date <= new Date();
}

function errorText(error, fallback) {
  return error?.userMessage || fallback;
}

export default function EditProfileScreen() {
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [conditions, setConditions] = useState([]);
  const [allergens, setAllergens] = useState([]);
  const [form, setForm] = useState(null);

  const load = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      const [user, conditionRows, allergenRows] = await Promise.all([
        api.me(), api.conditions(), api.allergens(),
      ]);
      const profile = user.profile || {};
      setConditions(conditionRows || []);
      setAllergens(allergenRows || []);
      setForm({
        fullName: user.full_name || '', gender: profile.gender || 'OTHER',
        birthDate: profile.birth_date || '', height: String(profile.height_cm || ''),
        weight: String(profile.weight_kg || ''), activity: profile.activity_level || 3,
        goal: profile.goal || 'MAINTAIN',
        conditionIds: (profile.conditions || []).map((item) => item.id),
        allergenIds: (profile.allergens || []).map((item) => item.id),
      });
      setStatus('success');
    } catch (requestError) {
      setError(errorText(requestError, 'Không thể tải hồ sơ sức khỏe.'));
      setStatus('error');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (status === 'loading' && !form) {
    return <SafeAreaView edges={['bottom']} style={styles.safeArea}><View style={styles.container}><OfflineBanner /><LoadingSkeleton rows={3} /></View></SafeAreaView>;
  }
  if (status === 'error' && !form) {
    return <SafeAreaView edges={['bottom']} style={styles.safeArea}><View style={styles.container}><OfflineBanner /><ErrorState message={error} onRetry={load} /></View></SafeAreaView>;
  }
  if (!form) return null;

  const height = Number(form.height);
  const weight = Number(form.weight);
  const valid = form.fullName.trim().length >= 2 && validDate(form.birthDate)
    && height > 50 && height < 250 && weight >= 20 && weight <= 300;

  const set = (key, value) => {
    setSaved(false);
    setForm((current) => ({ ...current, [key]: value }));
  };

  const toggleId = (key, id) => {
    const current = form[key];
    set(key, current.includes(id) ? current.filter((value) => value !== id) : [...current, id]);
  };

  async function save() {
    if (!valid || saving) return;
    setSaving(true);
    setError('');
    setSaved(false);
    try {
      await api.updateProfile({
        full_name: form.fullName.trim(), gender: form.gender, birth_date: form.birthDate,
        height_cm: height, weight_kg: weight, activity_level: Number(form.activity),
        goal: form.goal, condition_ids: form.conditionIds, allergen_ids: form.allergenIds,
      });
      setSaved(true);
    } catch (requestError) {
      setError(errorText(requestError, 'Không lưu được hồ sơ. Vui lòng kiểm tra lại thông tin.'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <SafeAreaView edges={['bottom']} style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <OfflineBanner />
        <Text style={styles.intro}>Thông tin chính xác giúp tính nhu cầu năng lượng và cá nhân hóa lộ trình.</Text>
        {saved ? <View style={styles.success}><CheckCircle2 size={18} color={Theme.colors.accentStrong} /><Text style={styles.successText}>Đã lưu hồ sơ thành công.</Text></View> : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Section title="Thông tin cá nhân">
          <Field label="Họ và tên" value={form.fullName} onChangeText={(value) => set('fullName', value)} maxLength={100} />
          <Field label="Ngày sinh (YYYY-MM-DD)" value={form.birthDate} onChangeText={(value) => set('birthDate', value)} keyboardType="numbers-and-punctuation" placeholder="1995-08-20" maxLength={10} />
          <Text style={styles.label}>Giới tính</Text>
          <ChoiceRow options={GENDERS} value={form.gender} onChange={(value) => set('gender', value)} />
        </Section>

        <Section title="Chỉ số cơ thể">
          <View style={styles.twoColumns}>
            <Field label="Chiều cao (cm)" value={form.height} onChangeText={(value) => set('height', value)} keyboardType="decimal-pad" />
            <Field label="Cân nặng (kg)" value={form.weight} onChangeText={(value) => set('weight', value)} keyboardType="decimal-pad" />
          </View>
          <Text style={styles.label}>Mức vận động</Text>
          <ChoiceRow options={ACTIVITY_LEVELS} value={form.activity} onChange={(value) => set('activity', value)} />
          <Text style={styles.label}>Mục tiêu</Text>
          <ChoiceRow options={GOALS} value={form.goal} onChange={(value) => set('goal', value)} />
        </Section>

        <Section title="Tình trạng sức khỏe">
          <Text style={styles.help}>Chọn tất cả tình trạng phù hợp.</Text>
          <CatalogChoices rows={conditions} selected={form.conditionIds} onToggle={(id) => toggleId('conditionIds', id)} empty="Chưa có danh mục tình trạng sức khỏe." />
        </Section>

        <Section title="Dị ứng thực phẩm">
          <Text style={styles.help}>Lộ trình sẽ tránh các thực phẩm bạn chọn.</Text>
          <CatalogChoices rows={allergens} selected={form.allergenIds} onToggle={(id) => toggleId('allergenIds', id)} empty="Chưa có danh mục dị ứng." />
        </Section>

        {!valid ? <Text style={styles.validation}>Vui lòng nhập đủ họ tên, ngày sinh hợp lệ, chiều cao 50–250 cm và cân nặng 20–300 kg.</Text> : null}
        <TouchableOpacity style={[styles.saveButton, (!valid || saving) && styles.disabled]} onPress={save} disabled={!valid || saving}>
          {saving ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.saveText}>Lưu hồ sơ sức khỏe</Text>}
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

function Section({ title, children }) {
  return <View style={styles.section}><Text style={styles.sectionTitle}>{title}</Text>{children}</View>;
}

function Field({ label, ...props }) {
  return <View style={styles.field}><Text style={styles.label}>{label}</Text><TextInput style={styles.input} placeholderTextColor={Theme.colors.textMuted} {...props} /></View>;
}

function ChoiceRow({ options, value, onChange }) {
  return (
    <View style={styles.choices}>
      {options.map(([key, label]) => (
        <TouchableOpacity key={key} onPress={() => onChange(key)} style={[styles.choice, value === key && styles.choiceActive]}>
          <Text style={[styles.choiceText, value === key && styles.choiceTextActive]}>{label}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

function CatalogChoices({ rows, selected, onToggle, empty }) {
  if (!rows.length) return <Text style={styles.help}>{empty}</Text>;
  return (
    <View style={styles.choices}>
      {rows.map((item) => (
        <TouchableOpacity key={item.id} onPress={() => onToggle(item.id)} style={[styles.choice, selected.includes(item.id) && styles.choiceActive]}>
          <Text style={[styles.choiceText, selected.includes(item.id) && styles.choiceTextActive]}>{item.name}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Theme.colors.background },
  container: { padding: 18, paddingBottom: 42 },
  intro: { color: Theme.colors.textMuted, fontSize: 13, lineHeight: 19, marginBottom: 14 },
  success: { flexDirection: 'row', alignItems: 'center', gap: 7, backgroundColor: Theme.colors.accentSoft, borderRadius: Theme.radius.sm, padding: 12, marginBottom: 12 },
  successText: { color: Theme.colors.accentStrong, fontSize: 13, fontWeight: '800' },
  error: { color: Theme.colors.danger, backgroundColor: Theme.colors.dangerSoft, borderRadius: Theme.radius.sm, padding: 12, marginBottom: 12, fontSize: 13 },
  section: { backgroundColor: Theme.colors.card, borderWidth: 1, borderColor: Theme.colors.border, borderRadius: Theme.radius.md, padding: 16, marginBottom: 14 },
  sectionTitle: { color: Theme.colors.text, fontSize: 16, fontWeight: '900', marginBottom: 13 },
  field: { flex: 1, marginBottom: 13 },
  label: { color: Theme.colors.textSecondary, fontSize: 12, fontWeight: '800', marginBottom: 7 },
  input: { minHeight: 46, borderWidth: 1, borderColor: Theme.colors.borderStrong, borderRadius: Theme.radius.sm, backgroundColor: '#FFFFFF', paddingHorizontal: 12, color: Theme.colors.text, fontSize: 14 },
  twoColumns: { flexDirection: 'row', gap: 10 },
  choices: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 8 },
  choice: { borderWidth: 1, borderColor: Theme.colors.borderStrong, backgroundColor: '#FFFFFF', borderRadius: Theme.radius.full, paddingHorizontal: 12, paddingVertical: 9 },
  choiceActive: { borderColor: Theme.colors.accentStrong, backgroundColor: Theme.colors.accentSoft },
  choiceText: { color: Theme.colors.textSecondary, fontSize: 12, fontWeight: '700' },
  choiceTextActive: { color: Theme.colors.accentStrong },
  help: { color: Theme.colors.textMuted, fontSize: 11, lineHeight: 17, marginBottom: 10 },
  validation: { color: Theme.colors.danger, fontSize: 12, lineHeight: 18, marginBottom: 10 },
  saveButton: { minHeight: 49, alignItems: 'center', justifyContent: 'center', backgroundColor: Theme.colors.accentStrong, borderRadius: Theme.radius.sm },
  saveText: { color: '#FFFFFF', fontSize: 15, fontWeight: '900' },
  disabled: { opacity: 0.45 },
});
