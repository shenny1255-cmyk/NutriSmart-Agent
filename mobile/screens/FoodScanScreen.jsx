import React, { useRef, useState } from 'react';
import {
  ActivityIndicator, Alert, Image, ScrollView, StatusBar, StyleSheet,
  Text, TouchableOpacity, View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as ImagePicker from 'expo-image-picker';
import {
  AlertCircle, AlertTriangle, Camera, CheckCircle2, Flame, Image as ImageIcon,
  RefreshCw, Sparkles, Utensils,
} from 'lucide-react-native';

import { Theme } from '../theme';
import { ApiError, api } from '../services/api';
import { OfflineBanner } from '../components/OfflineBanner';

const PORTIONS = [0.5, 1, 1.5, 2];
const MEAL_TYPES = [
  { value: 'BREAKFAST', label: 'Bữa sáng' },
  { value: 'LUNCH', label: 'Bữa trưa' },
  { value: 'DINNER', label: 'Bữa tối' },
  { value: 'SNACK', label: 'Ăn nhẹ' },
];

function validNutritionResult(result) {
  if (result?.is_food_image !== true || !result.food_name) return false;
  return ['calories_kcal', 'protein_g', 'carb_g', 'fat_g']
    .every((field) => Number.isFinite(Number(result[field])) && Number(result[field]) >= 0);
}

export default function FoodScanScreen() {
  const [imageAsset, setImageAsset] = useState(null);
  const [status, setStatus] = useState('idle');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [portion, setPortion] = useState(1);
  const [mealType, setMealType] = useState('LUNCH');
  const [saving, setSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState('');
  const [saveError, setSaveError] = useState('');
  const savingRef = useRef(false);

  const analyzeImage = async (asset) => {
    setImageAsset(asset);
    setStatus('analyzing');
    setAnalysisResult(null);
    setErrorMessage('');
    setSaveError('');
    setSavedMessage('');
    setPortion(1);
    setMealType('LUNCH');

    try {
      const result = await api.analyzeMeal(asset);
      setAnalysisResult(result);
      if (result?.is_food_image === false) {
        setStatus('rejected');
      } else if (validNutritionResult(result)) {
        setStatus('success');
      } else {
        throw new ApiError({
          code: 'INVALID_AI_RESULT',
          message: 'Kết quả phân tích chưa đầy đủ. Vui lòng thử ảnh khác.',
        });
      }
    } catch (error) {
      const message = error.code === 'SERVICE_UNAVAILABLE'
        ? 'Dịch vụ phân tích ảnh đang tạm thời gián đoạn. Vui lòng thử lại sau.'
        : error.code === 'TIMEOUT'
          ? 'Phân tích ảnh mất nhiều thời gian hơn dự kiến. Vui lòng thử lại.'
          : error.userMessage || 'Không thể phân tích ảnh. Vui lòng thử lại.';
      setErrorMessage(message);
      setStatus('error');
    }
  };

  const takePhoto = async () => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Cần cấp quyền', 'Hãy cấp quyền Camera để chụp ảnh món ăn.');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({ allowsEditing: true, quality: 0.8 });
    if (!result.canceled && result.assets?.[0]) await analyzeImage(result.assets[0]);
  };

  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({ allowsEditing: true, quality: 0.8 });
    if (!result.canceled && result.assets?.[0]) await analyzeImage(result.assets[0]);
  };

  const chooseAnotherImage = () => {
    Alert.alert('Chọn ảnh khác', 'Bạn muốn lấy ảnh từ đâu?', [
      { text: 'Huỷ', style: 'cancel' },
      { text: 'Thư viện', onPress: pickImage },
      { text: 'Camera', onPress: takePhoto },
    ]);
  };

  const handleSaveMeal = async () => {
    if (!validNutritionResult(analysisResult) || savingRef.current || savedMessage) return;

    savingRef.current = true;
    setSaving(true);
    setSaveError('');
    try {
      const response = await api.logMeal({
        food_name: analysisResult.food_name,
        calories_kcal: Number(analysisResult.calories_kcal),
        protein_g: Number(analysisResult.protein_g),
        carb_g: Number(analysisResult.carb_g),
        fat_g: Number(analysisResult.fat_g),
        quantity: portion,
        meal_type: mealType,
      });
      const added = Math.round(Number(response?.added_calories || analysisResult.calories_kcal * portion));
      setSavedMessage(`Đã lưu ${analysisResult.food_name} (+${added} kcal) vào nhật ký.`);
    } catch (error) {
      setSaveError(error.userMessage || 'Không thể lưu bữa ăn. Vui lòng thử lại.');
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  const hasFoodResult = status === 'success' && validNutritionResult(analysisResult);
  const calculated = hasFoodResult ? {
    kcal: (Number(analysisResult.calories_kcal) * portion).toFixed(0),
    protein: (Number(analysisResult.protein_g) * portion).toFixed(1),
    carbs: (Number(analysisResult.carb_g) * portion).toFixed(1),
    fat: (Number(analysisResult.fat_g) * portion).toFixed(1),
  } : null;

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor={Theme.colors.background} />
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <OfflineBanner />
        <View style={styles.header}>
          <View style={styles.headerIcon}><Sparkles size={22} color={Theme.colors.accentStrong} /></View>
          <View>
            <Text style={styles.headerTitle}>Phân tích món ăn AI</Text>
            <Text style={styles.headerSubtitle}>Chụp rõ món ăn trong điều kiện đủ sáng</Text>
          </View>
        </View>

        {status === 'idle' ? (
          <View style={styles.actionRow}>
            <ActionCard icon={<Camera size={27} color={Theme.colors.accentStrong} />} title="Chụp ảnh" subtitle="Mở Camera" onPress={takePhoto} />
            <ActionCard icon={<ImageIcon size={27} color="#0284C7" />} title="Thư viện" subtitle="Chọn ảnh có sẵn" onPress={pickImage} />
          </View>
        ) : null}

        {imageAsset ? (
          <>
            <View style={styles.previewBox}>
              <Image source={{ uri: imageAsset.uri }} style={styles.foodImage} />
              {status === 'analyzing' ? (
                <View style={styles.analyzingOverlay}>
                  <ActivityIndicator size="large" color={Theme.colors.accentStrong} />
                  <Text style={styles.analyzingText}>Đang phân tích ảnh món ăn...</Text>
                </View>
              ) : null}
            </View>
            {status !== 'analyzing' ? (
              <TouchableOpacity style={styles.changeButton} onPress={chooseAnotherImage}>
                <RefreshCw size={16} color={Theme.colors.accentStrong} />
                <Text style={styles.changeButtonText}>Chọn ảnh khác</Text>
              </TouchableOpacity>
            ) : null}
          </>
        ) : null}

        {status === 'error' ? (
          <View style={styles.errorCard} accessibilityRole="alert">
            <AlertCircle size={25} color={Theme.colors.danger} />
            <Text style={styles.errorTitle}>Phân tích chưa thành công</Text>
            <Text style={styles.errorText}>{errorMessage}</Text>
            <TouchableOpacity style={styles.retryButton} onPress={() => analyzeImage(imageAsset)}>
              <Text style={styles.retryButtonText}>Thử phân tích lại</Text>
            </TouchableOpacity>
          </View>
        ) : null}

        {status === 'rejected' ? (
          <View style={styles.rejectionCard} accessibilityRole="alert">
            <AlertTriangle size={25} color="#D97706" />
            <View style={styles.rejectionContent}>
              <Text style={styles.rejectionTitle}>Không nhận diện được món ăn</Text>
              <Text style={styles.rejectionText}>
                {analysisResult?.rejection_reason || 'Ảnh không chứa món ăn hoặc món ăn chưa đủ rõ.'}
              </Text>
              <Text style={styles.rejectionHint}>Không có dữ liệu kcal nào được tạo từ ảnh này.</Text>
            </View>
          </View>
        ) : null}

        {hasFoodResult ? (
          <View style={styles.resultCard}>
            <View style={styles.resultHeader}>
              <Sparkles size={19} color={Theme.colors.accentStrong} />
              <Text style={styles.resultHeaderTitle}>Kết quả nhận diện</Text>
              <Text style={styles.confidence}>{Math.round(Number(analysisResult.confidence || 0) * 100)}% tin cậy</Text>
            </View>
            <Text style={styles.foodName}>{analysisResult.food_name}</Text>
            {analysisResult.description ? <Text style={styles.foodDescription}>{analysisResult.description}</Text> : null}

            <View style={styles.kcalBanner}>
              <Flame size={28} color="#F97316" />
              <View style={styles.kcalContent}>
                <Text style={styles.kcalValue}>{calculated.kcal} <Text style={styles.kcalUnit}>kcal</Text></Text>
                <Text style={styles.kcalSubtitle}>Năng lượng ước tính theo khẩu phần</Text>
              </View>
            </View>

            <Text style={styles.selectorTitle}>Khẩu phần</Text>
            <View style={styles.chipRow}>
              {PORTIONS.map((value) => (
                <ChoiceChip
                  key={value}
                  active={portion === value}
                  label={`${value}x`}
                  onPress={() => setPortion(value)}
                  disabled={Boolean(savedMessage)}
                />
              ))}
            </View>

            <Text style={styles.selectorTitle}>Loại bữa</Text>
            <View style={styles.mealTypeRow}>
              {MEAL_TYPES.map((item) => (
                <ChoiceChip
                  key={item.value}
                  active={mealType === item.value}
                  label={item.label}
                  onPress={() => setMealType(item.value)}
                  disabled={Boolean(savedMessage)}
                />
              ))}
            </View>

            <View style={styles.macrosRow}>
              <Macro value={`${calculated.protein}g`} label="Protein" color="#0284C7" />
              <View style={styles.macroDivider} />
              <Macro value={`${calculated.carbs}g`} label="Carb" color="#CA8A04" />
              <View style={styles.macroDivider} />
              <Macro value={`${calculated.fat}g`} label="Chất béo" color="#DC2626" />
            </View>

            {saveError ? <Text style={styles.saveError}>{saveError}</Text> : null}
            {savedMessage ? (
              <View style={styles.successBox}>
                <CheckCircle2 size={18} color={Theme.colors.success} />
                <Text style={styles.successText}>{savedMessage}</Text>
              </View>
            ) : null}

            <TouchableOpacity
              style={[styles.saveButton, (saving || savedMessage) && styles.saveButtonDisabled]}
              onPress={handleSaveMeal}
              disabled={saving || Boolean(savedMessage)}
            >
              {saving ? <ActivityIndicator color="#0F172A" /> : savedMessage ? (
                <><CheckCircle2 size={18} color="#0F172A" /><Text style={styles.saveButtonText}>Đã lưu bữa ăn</Text></>
              ) : (
                <><Utensils size={18} color="#0F172A" /><Text style={styles.saveButtonText}>Lưu vào nhật ký (+{calculated.kcal} kcal)</Text></>
              )}
            </TouchableOpacity>
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function ActionCard({ icon, title, subtitle, onPress }) {
  return (
    <TouchableOpacity style={styles.actionCard} onPress={onPress} activeOpacity={0.8}>
      <View style={styles.actionIcon}>{icon}</View>
      <Text style={styles.actionTitle}>{title}</Text>
      <Text style={styles.actionSubtitle}>{subtitle}</Text>
    </TouchableOpacity>
  );
}

function ChoiceChip({ active, label, onPress, disabled }) {
  return (
    <TouchableOpacity
      style={[styles.choiceChip, active && styles.choiceChipActive, disabled && styles.choiceChipDisabled]}
      onPress={onPress}
      disabled={disabled}
    >
      <Text style={[styles.choiceChipText, active && styles.choiceChipTextActive]}>{label}</Text>
    </TouchableOpacity>
  );
}

function Macro({ value, label, color }) {
  return (
    <View style={styles.macroBox}>
      <Text style={[styles.macroValue, { color }]}>{value}</Text>
      <Text style={styles.macroLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Theme.colors.background },
  container: { padding: 20, paddingBottom: 40 },
  header: { flexDirection: 'row', alignItems: 'center', marginBottom: 20 },
  headerIcon: { width: 44, height: 44, borderRadius: 22, backgroundColor: Theme.colors.accentSoft, alignItems: 'center', justifyContent: 'center', marginRight: 11 },
  headerTitle: { fontSize: 20, fontWeight: '900', color: Theme.colors.text },
  headerSubtitle: { color: Theme.colors.textMuted, fontSize: 11, marginTop: 2 },
  actionRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20 },
  actionCard: { width: '48%', backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md, padding: 17, alignItems: 'center', borderWidth: 1, borderColor: Theme.colors.border },
  actionIcon: { width: 54, height: 54, borderRadius: 27, backgroundColor: Theme.colors.accentSoft, alignItems: 'center', justifyContent: 'center', marginBottom: 10 },
  actionTitle: { color: Theme.colors.text, fontSize: 14, fontWeight: '800' },
  actionSubtitle: { color: Theme.colors.textMuted, fontSize: 11, marginTop: 3 },
  previewBox: { borderRadius: Theme.radius.md, overflow: 'hidden', borderWidth: 1, borderColor: Theme.colors.border, position: 'relative' },
  foodImage: { width: '100%', height: 230, resizeMode: 'cover' },
  analyzingOverlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(15, 23, 42, 0.78)', alignItems: 'center', justifyContent: 'center', padding: 20 },
  analyzingText: { color: '#FFFFFF', fontSize: 14, fontWeight: '700', marginTop: 12 },
  changeButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 7, paddingVertical: 12, marginBottom: 16 },
  changeButtonText: { color: Theme.colors.accentStrong, fontSize: 13, fontWeight: '800' },
  errorCard: { alignItems: 'center', backgroundColor: Theme.colors.dangerSoft, borderRadius: Theme.radius.md, padding: 20, borderWidth: 1, borderColor: '#EF444430', marginBottom: 16 },
  errorTitle: { color: Theme.colors.danger, fontSize: 16, fontWeight: '900', marginTop: 9 },
  errorText: { color: Theme.colors.textSecondary, textAlign: 'center', fontSize: 13, lineHeight: 19, marginTop: 5 },
  retryButton: { backgroundColor: Theme.colors.danger, borderRadius: Theme.radius.sm, paddingHorizontal: 18, paddingVertical: 9, marginTop: 13 },
  retryButtonText: { color: '#FFFFFF', fontWeight: '800', fontSize: 13 },
  rejectionCard: { flexDirection: 'row', gap: 12, backgroundColor: '#FEF3C7', borderRadius: Theme.radius.md, padding: 18, borderWidth: 1, borderColor: '#F59E0B55', marginBottom: 16 },
  rejectionContent: { flex: 1 },
  rejectionTitle: { color: Theme.colors.text, fontSize: 17, fontWeight: '900' },
  rejectionText: { color: Theme.colors.textSecondary, fontSize: 14, lineHeight: 20, marginTop: 6 },
  rejectionHint: { color: '#92400E', fontSize: 12, fontWeight: '700', marginTop: 7 },
  resultCard: { backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md, padding: 20, borderWidth: 1, borderColor: Theme.colors.border },
  resultHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  resultHeaderTitle: { color: Theme.colors.accentStrong, fontSize: 14, fontWeight: '800', marginLeft: 6, flex: 1 },
  confidence: { color: Theme.colors.textMuted, fontSize: 11, backgroundColor: Theme.colors.cardSecondary, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 10 },
  foodName: { color: Theme.colors.text, fontSize: 22, fontWeight: '900' },
  foodDescription: { color: Theme.colors.textMuted, fontSize: 13, lineHeight: 19, marginTop: 5, marginBottom: 15 },
  kcalBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#F9731610', borderRadius: Theme.radius.sm, padding: 14, borderWidth: 1, borderColor: '#F9731630', marginVertical: 16 },
  kcalContent: { marginLeft: 12 },
  kcalValue: { color: '#F97316', fontSize: 28, fontWeight: '900' },
  kcalUnit: { color: Theme.colors.textMuted, fontSize: 15, fontWeight: '600' },
  kcalSubtitle: { color: Theme.colors.textMuted, fontSize: 11, marginTop: 2 },
  selectorTitle: { color: Theme.colors.textSecondary, fontSize: 12, fontWeight: '800', marginBottom: 8 },
  chipRow: { flexDirection: 'row', gap: 7, marginBottom: 16 },
  mealTypeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 7, marginBottom: 16 },
  choiceChip: { minWidth: 58, flexGrow: 1, backgroundColor: Theme.colors.cardSecondary, paddingHorizontal: 10, paddingVertical: 9, borderRadius: Theme.radius.sm, alignItems: 'center', borderWidth: 1, borderColor: Theme.colors.border },
  choiceChipActive: { backgroundColor: Theme.colors.accentStrong, borderColor: Theme.colors.accentStrong },
  choiceChipDisabled: { opacity: 0.65 },
  choiceChipText: { color: Theme.colors.text, fontSize: 12, fontWeight: '800' },
  choiceChipTextActive: { color: '#FFFFFF' },
  macrosRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: Theme.colors.cardSecondary, borderRadius: Theme.radius.sm, padding: 12, marginBottom: 16 },
  macroBox: { flex: 1, alignItems: 'center' },
  macroDivider: { width: 1, height: 28, backgroundColor: Theme.colors.border },
  macroValue: { fontSize: 16, fontWeight: '900' },
  macroLabel: { color: Theme.colors.textMuted, fontSize: 10, marginTop: 2 },
  saveError: { color: Theme.colors.danger, fontSize: 13, lineHeight: 18, textAlign: 'center', marginBottom: 12 },
  successBox: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: Theme.colors.accentSoft, padding: 12, borderRadius: Theme.radius.sm, borderWidth: 1, borderColor: '#10B98140', marginBottom: 14 },
  successText: { color: Theme.colors.accentStrong, fontSize: 12, fontWeight: '700', flex: 1 },
  saveButton: { flexDirection: 'row', gap: 8, backgroundColor: Theme.colors.accentStrong, paddingVertical: 14, borderRadius: Theme.radius.sm, alignItems: 'center', justifyContent: 'center' },
  saveButtonDisabled: { opacity: 0.55 },
  saveButtonText: { color: '#0F172A', fontWeight: '900', fontSize: 14 },
});
