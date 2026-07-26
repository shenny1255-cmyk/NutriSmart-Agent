import React, { useState } from 'react';
import {
  StyleSheet, Text, View, TouchableOpacity, Image,
  ScrollView, SafeAreaView, StatusBar, ActivityIndicator, Alert,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { Camera, Image as ImageIcon, Sparkles, CheckCircle2, ChevronLeft, Flame, Utensils } from 'lucide-react-native';
import { Theme } from '../theme';

export default function FoodScanScreen({ navigation, route }) {
  const backendIp = route?.params?.backendIp ?? '10.120.56.85';

  const [imageUri, setImageUri] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [portion, setPortion] = useState(1.0);
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  // 1. Chụp ảnh từ Camera
  const takePhoto = async () => {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) {
      Alert.alert('Cần cấp quyền', 'Ứng dụng cần quyền Camera để chụp ảnh đĩa thức ăn.');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      quality: 0.8,
    });

    if (!result.canceled && result.assets[0]) {
      const uri = result.assets[0].uri;
      setImageUri(uri);
      analyzeImage(uri);
    }
  };

  // 2. Chọn ảnh từ Thư viện (Gallery)
  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      quality: 0.8,
    });

    if (!result.canceled && result.assets[0]) {
      const uri = result.assets[0].uri;
      setImageUri(uri);
      analyzeImage(uri);
    }
  };

  // 3. Gửi ảnh lên Backend Python (Gemini 2.0 Flash AI)
  const analyzeImage = async (uri) => {
    setAnalyzing(true);
    setAnalysisResult(null);
    setSuccessMessage('');

    try {
      const token = await AsyncStorage.getItem('access_token');
      const formData = new FormData();
      formData.append('file', {
        uri,
        name: 'food_photo.jpg',
        type: 'image/jpeg',
      });

      const res = await axios.post(
        `http://${backendIp}:8000/api/v1/vision/analyze-meal`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            Authorization: `Bearer ${token}`,
          },
          timeout: 25000,
        }
      );

      if (res.data) {
        setAnalysisResult(res.data);
        setPortion(1.0);
      }
    } catch (err) {
      Alert.alert(
        'Phân tích thất bại',
        err.response?.data?.detail || 'Không thể kết nối đến AI Gemini. Vui lòng thử lại.'
      );
    } finally {
      setAnalyzing(false);
    }
  };

  // 4. Lưu bữa ăn vào CSDL
  const handleSaveMeal = async () => {
    if (!analysisResult) return;

    setSaving(true);
    try {
      const token = await AsyncStorage.getItem('access_token');
      const payload = {
        food_name: analysisResult.food_name,
        calories_kcal: analysisResult.calories_kcal,
        protein_g: analysisResult.protein_g,
        carb_g: analysisResult.carb_g,
        fat_g: analysisResult.fat_g,
        quantity: portion,
        meal_type: 'LUNCH',
      };

      const res = await axios.post(
        `http://${backendIp}:8000/api/v1/vision/log-meal`,
        payload,
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          timeout: 10000,
        }
      );

      if (res.data && res.data.status === 'success') {
        const addedKcal = (analysisResult.calories_kcal * portion).toFixed(0);
        setSuccessMessage(`✅ Đã lưu ${analysisResult.food_name} (+${addedKcal} kcal) vào Nhật ký!`);
      }
    } catch (err) {
      Alert.alert('Lỗi lưu bữa ăn', err.response?.data?.detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  // Tính toán dinh dưỡng dựa trên Khẩu phần (Portion multiplier)
  const calcKcal = analysisResult ? (analysisResult.calories_kcal * portion).toFixed(0) : 0;
  const calcProtein = analysisResult ? (analysisResult.protein_g * portion).toFixed(1) : 0;
  const calcCarbs = analysisResult ? (analysisResult.carb_g * portion).toFixed(1) : 0;
  const calcFat = analysisResult ? (analysisResult.fat_g * portion).toFixed(1) : 0;

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor={Theme.colors.background} />
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>

        {/* Header Navigation */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn} activeOpacity={0.7}>
            <ChevronLeft size={22} color={Theme.colors.text} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Phân tích Món ăn AI</Text>
          <View style={{ width: 40 }} />
        </View>

        {/* Nút bấm Chọn / Chụp Ảnh */}
        <View style={styles.actionRow}>
          <TouchableOpacity style={styles.actionCard} onPress={takePhoto} activeOpacity={0.8}>
            <View style={[styles.iconCircle, { backgroundColor: '#10B98115' }]}>
              <Camera size={26} color={Theme.colors.accentStrong} />
            </View>
            <Text style={styles.actionCardTitle}>Chụp ảnh mới</Text>
            <Text style={styles.actionCardSub}>Mở Camera điện thoại</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.actionCard} onPress={pickImage} activeOpacity={0.8}>
            <View style={[styles.iconCircle, { backgroundColor: '#38BDF815' }]}>
              <ImageIcon size={26} color="#38BDF8" />
            </View>
            <Text style={styles.actionCardTitle}>Chọn từ Thư viện</Text>
            <Text style={styles.actionCardSub}>Tải ảnh sẵn có lên</Text>
          </TouchableOpacity>
        </View>

        {/* Xem Ảnh đã chọn */}
        {imageUri && (
          <View style={styles.imagePreviewBox}>
            <Image source={{ uri: imageUri }} style={styles.foodImage} />
            {analyzing && (
              <View style={styles.analyzingOverlay}>
                <ActivityIndicator size="large" color={Theme.colors.accentStrong} />
                <Text style={styles.analyzingText}>Gemini AI đang phân tích đĩa thức ăn...</Text>
              </View>
            )}
          </View>
        )}

        {/* Kết quả Phân tích Gemini Flash AI */}
        {analysisResult && (
          <View style={styles.resultCard}>
            <View style={styles.resultHeader}>
              <Sparkles size={20} color={Theme.colors.accentStrong} />
              <Text style={styles.resultHeaderTitle}>Kết quả nhận diện AI</Text>
              <Text style={styles.confidenceText}>{(analysisResult.confidence * 100).toFixed(0)}% tin cậy</Text>
            </View>

            <Text style={styles.foodName}>{analysisResult.food_name}</Text>
            <Text style={styles.foodDesc}>{analysisResult.description}</Text>

            {/* Thẻ Calo lớn */}
            <View style={styles.kcalBanner}>
              <Flame size={28} color="#F97316" />
              <View style={{ marginLeft: 12 }}>
                <Text style={styles.kcalValue}>{calcKcal} <Text style={styles.kcalUnit}>kcal</Text></Text>
                <Text style={styles.kcalSubtitle}>Năng lượng ước tính</Text>
              </View>
            </View>

            {/* Chọn Khẩu phần (Portion Selector) */}
            <Text style={styles.portionTitle}>Khẩu phần ăn (Portion):</Text>
            <View style={styles.portionRow}>
              {[0.5, 1.0, 1.5, 2.0].map((p) => (
                <TouchableOpacity
                  key={p}
                  style={[styles.portionChip, portion === p && styles.portionChipActive]}
                  onPress={() => setPortion(p)}
                >
                  <Text style={[styles.portionChipText, portion === p && styles.portionChipTextActive]}>
                    {p}x
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Chi tiết Macros (Protein, Carbs, Fat) */}
            <View style={styles.macrosRow}>
              <View style={styles.macroBox}>
                <Text style={[styles.macroVal, { color: '#38BDF8' }]}>{calcProtein}g</Text>
                <Text style={styles.macroLabel}>Protein (Đạm)</Text>
              </View>
              <View style={styles.macroDivider} />
              <View style={styles.macroBox}>
                <Text style={[styles.macroVal, { color: '#EAB308' }]}>{calcCarbs}g</Text>
                <Text style={styles.macroLabel}>Carbs (Đường)</Text>
              </View>
              <View style={styles.macroDivider} />
              <View style={styles.macroBox}>
                <Text style={[styles.macroVal, { color: '#EF4444' }]}>{calcFat}g</Text>

                <Text style={styles.macroLabel}>Fat (Béo)</Text>
              </View>
            </View>

            {/* Thông báo thành công */}
            {successMessage !== '' && (
              <View style={styles.successBox}>
                <CheckCircle2 size={18} color="#10B981" style={{ marginRight: 8 }} />
                <Text style={styles.successText}>{successMessage}</Text>
              </View>
            )}

            {/* Nút Xác Nhận Nạp Bữa Ăn */}
            <TouchableOpacity
              style={[styles.saveBtn, saving && styles.saveBtnDisabled]}
              onPress={handleSaveMeal}
              disabled={saving}
              activeOpacity={0.8}
            >
              {saving ? (
                <ActivityIndicator color="#0F172A" />
              ) : (
                <>
                  <Utensils size={18} color="#0F172A" style={{ marginRight: 8 }} />
                  <Text style={styles.saveBtnText}>Lưu vào Nhật ký (+{calcKcal} kcal)</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
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
  backBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: Theme.colors.card, alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: Theme.colors.border,
  },
  headerTitle: { fontSize: 18, fontWeight: '700', color: Theme.colors.text },

  actionRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20 },
  actionCard: {
    width: '48%', backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md,
    padding: 16, alignItems: 'center', borderWidth: 1, borderColor: Theme.colors.border,
  },
  iconCircle: {
    width: 52, height: 52, borderRadius: 26, alignItems: 'center',
    justifyContent: 'center', marginBottom: 10,
  },
  actionCardTitle: { fontSize: 14, fontWeight: '700', color: Theme.colors.text, marginBottom: 2 },
  actionCardSub: { fontSize: 11, color: Theme.colors.textMuted },

  imagePreviewBox: {
    borderRadius: Theme.radius.md, overflow: 'hidden', marginBottom: 20,
    borderWidth: 1, borderColor: Theme.colors.border, position: 'relative',
  },
  foodImage: { width: '100%', height: 220, resizeMode: 'cover' },
  analyzingOverlay: {
    ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(15, 23, 42, 0.75)',
    alignItems: 'center', justifyContent: 'center', padding: 20,
  },
  analyzingText: { color: '#F8FAFC', fontSize: 14, fontWeight: '600', marginTop: 12, textAlign: 'center' },

  resultCard: {
    backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md,
    padding: 20, borderWidth: 1, borderColor: Theme.colors.border, marginBottom: 20,
  },
  resultHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  resultHeaderTitle: { fontSize: 14, fontWeight: '700', color: Theme.colors.accentStrong, marginLeft: 6, flex: 1 },
  confidenceText: { fontSize: 11, color: Theme.colors.textMuted, backgroundColor: Theme.colors.cardSecondary, paddingHorizontal: 8, paddingVertical: 2, borderRadius: 10 },

  foodName: { fontSize: 22, fontWeight: '800', color: Theme.colors.text, marginBottom: 6 },
  foodDesc: { fontSize: 13, color: Theme.colors.textMuted, lineHeight: 19, marginBottom: 16 },

  kcalBanner: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#F9731610',
    borderRadius: Theme.radius.sm, padding: 14, borderWidth: 1, borderColor: '#F9731630',
    marginBottom: 16,
  },
  kcalValue: { fontSize: 28, fontWeight: '900', color: '#F97316' },
  kcalUnit: { fontSize: 16, fontWeight: '600', color: Theme.colors.textMuted },
  kcalSubtitle: { fontSize: 12, color: Theme.colors.textMuted, marginTop: 2 },

  portionTitle: { fontSize: 12, fontWeight: '700', color: Theme.colors.textMuted, marginBottom: 8 },
  portionRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 },
  portionChip: {
    flex: 1, marginHorizontal: 3, backgroundColor: Theme.colors.cardSecondary,
    paddingVertical: 8, borderRadius: Theme.radius.sm, alignItems: 'center',
    borderWidth: 1, borderColor: Theme.colors.border,
  },
  portionChipActive: { backgroundColor: Theme.colors.accentStrong, borderColor: Theme.colors.accentStrong },
  portionChipText: { fontSize: 13, fontWeight: '700', color: Theme.colors.text },
  portionChipTextActive: { color: '#0F172A' },

  macrosRow: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: Theme.colors.cardSecondary,
    borderRadius: Theme.radius.sm, padding: 12, marginBottom: 16,
  },
  macroBox: { flex: 1, alignItems: 'center' },
  macroDivider: { width: 1, height: 24, backgroundColor: Theme.colors.border },
  macroVal: { fontSize: 15, fontWeight: '800' },
  macroLabel: { fontSize: 10, color: Theme.colors.textMuted, marginTop: 2 },

  successBox: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#10B98115',
    padding: 12, borderRadius: Theme.radius.sm, borderWidth: 1, borderColor: '#10B98140',
    marginBottom: 16,
  },
  successText: { color: '#10B981', fontSize: 13, fontWeight: '600', flex: 1 },

  saveBtn: {
    flexDirection: 'row', backgroundColor: Theme.colors.accentStrong,
    paddingVertical: 14, borderRadius: Theme.radius.sm, alignItems: 'center', justifyContent: 'center',
  },
  saveBtnDisabled: { backgroundColor: Theme.colors.cardSecondary },
  saveBtnText: { color: '#0F172A', fontWeight: 'bold', fontSize: 15 },
});
