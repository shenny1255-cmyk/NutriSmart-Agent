import React, { useCallback, useState } from 'react';
import {
  Alert, ScrollView, StatusBar, StyleSheet, Text, TouchableOpacity, View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from '@react-navigation/native';
import Constants from 'expo-constants';
import { Activity, Edit3, LogOut, Scale, ShieldCheck, User } from 'lucide-react-native';

import { Theme } from '../theme';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { ErrorState, LoadingSkeleton } from '../components/AsyncState';
import { OfflineBanner } from '../components/OfflineBanner';

const ROLE_LABELS = {
  ADMIN: 'Quản trị viên',
  EXPERT: 'Chuyên gia',
  USER: 'Người dùng',
};

const GOAL_LABELS = {
  LOSE_WEIGHT: 'Giảm cân',
  MAINTAIN: 'Duy trì cân nặng',
  GAIN_MUSCLE: 'Tăng cơ',
  MEDICAL: 'Dinh dưỡng sức khỏe',
};

export default function ProfileScreen({ navigation }) {
  const { signOut } = useAuth();
  const [status, setStatus] = useState('loading');
  const [userData, setUserData] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  const loadUserData = useCallback(async () => {
    setStatus((current) => (current === 'success' ? 'refreshing' : 'loading'));
    setErrorMessage('');
    try {
      const data = await api.me();
      setUserData(data);
      setStatus('success');
    } catch (error) {
      setErrorMessage(error.userMessage || 'Không thể tải hồ sơ.');
      setStatus('error');
    }
  }, []);

  useFocusEffect(useCallback(() => {
    loadUserData();
  }, [loadUserData]));

  const handleLogout = () => {
    Alert.alert('Đăng xuất', 'Bạn có chắc chắn muốn đăng xuất không?', [
      { text: 'Huỷ', style: 'cancel' },
      { text: 'Đăng xuất', style: 'destructive', onPress: signOut },
    ]);
  };

  const profile = userData?.profile;
  const appVersion = Constants.expoConfig?.version || '1.0.0';

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor={Theme.colors.background} />
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <OfflineBanner />
        <Text style={styles.pageTitle}>Hồ sơ cá nhân</Text>

        {status === 'loading' && !userData ? <LoadingSkeleton rows={2} /> : null}
        {status === 'error' && !userData ? (
          <ErrorState message={errorMessage} onRetry={loadUserData} />
        ) : null}

        {userData ? (
          <>
            {status === 'error' ? (
              <ErrorState message={`${errorMessage} Dữ liệu bên dưới là lần tải gần nhất.`} onRetry={loadUserData} />
            ) : null}

            <View style={styles.profileCard}>
              <View style={styles.avatarCircle}>
                <User size={40} color={Theme.colors.accentStrong} />
              </View>
              <Text style={styles.fullName}>{userData.full_name || 'Người dùng NutriSmart'}</Text>
              <Text style={styles.emailText}>{userData.email}</Text>
              <View style={styles.roleBadge}>
                <ShieldCheck size={14} color={Theme.colors.accentStrong} />
                <Text style={styles.roleText}>{ROLE_LABELS[userData.role] || userData.role}</Text>
              </View>
            </View>

            <Text style={styles.sectionTitle}>Thông tin sức khỏe</Text>
            <View style={styles.infoCard}>
              <InfoRow
                icon={<Scale size={18} color={Theme.colors.textMuted} />}
                label="Cân nặng"
                value={profile?.weight_kg ? `${profile.weight_kg} kg` : 'Chưa cập nhật'}
              />
              <View style={styles.divider} />
              <InfoRow
                icon={<Activity size={18} color={Theme.colors.textMuted} />}
                label="BMI"
                value={profile?.bmi ? Number(profile.bmi).toFixed(1) : 'Chưa cập nhật'}
              />
              <View style={styles.divider} />
              <InfoRow
                icon={<ShieldCheck size={18} color={Theme.colors.textMuted} />}
                label="Mục tiêu"
                value={GOAL_LABELS[profile?.goal] || 'Chưa cập nhật'}
              />
            </View>

            <TouchableOpacity style={styles.editButton} onPress={() => navigation.getParent()?.navigate('EditProfile')} activeOpacity={0.8}>
              <Edit3 size={17} color="#FFFFFF" />
              <Text style={styles.editButtonText}>Cập nhật hồ sơ sức khỏe</Text>
            </TouchableOpacity>

            <Text style={styles.metaText}>
              NutriSmart Mobile v{appVersion} · {__DEV__ ? 'Môi trường phát triển' : 'Bản phát hành'}
            </Text>

            <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout} activeOpacity={0.8}>
              <LogOut size={18} color={Theme.colors.danger} />
              <Text style={styles.logoutText}>Đăng xuất khỏi ứng dụng</Text>
            </TouchableOpacity>
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function InfoRow({ icon, label, value }) {
  return (
    <View style={styles.infoRow}>
      {icon}
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Theme.colors.background },
  container: { padding: 20, paddingBottom: 40 },
  pageTitle: { fontSize: 24, fontWeight: '900', color: Theme.colors.text, marginBottom: 18 },
  profileCard: {
    backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md,
    padding: 24, alignItems: 'center', borderWidth: 1, borderColor: Theme.colors.border,
    marginBottom: 20,
  },
  avatarCircle: {
    width: 80, height: 80, borderRadius: 40, backgroundColor: Theme.colors.accentSoft,
    alignItems: 'center', justifyContent: 'center', marginBottom: 14,
    borderWidth: 2, borderColor: Theme.colors.accentStrong,
  },
  fullName: { fontSize: 20, fontWeight: '800', color: Theme.colors.text, marginBottom: 4 },
  emailText: { fontSize: 13, color: Theme.colors.textMuted, marginBottom: 12 },
  roleBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: Theme.colors.accentSoft,
    paddingHorizontal: 12, paddingVertical: 5, borderRadius: Theme.radius.full,
  },
  roleText: { fontSize: 12, fontWeight: '700', color: Theme.colors.accentStrong },
  sectionTitle: { fontSize: 14, fontWeight: '800', color: Theme.colors.text, marginBottom: 10 },
  infoCard: {
    backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md,
    padding: 16, borderWidth: 1, borderColor: Theme.colors.border,
  },
  infoRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10 },
  infoLabel: { color: Theme.colors.textSecondary, fontSize: 13, marginLeft: 10, flex: 1 },
  infoValue: { color: Theme.colors.text, fontSize: 13, fontWeight: '800', maxWidth: '48%', textAlign: 'right' },
  divider: { height: 1, backgroundColor: Theme.colors.border },
  editButton: { flexDirection: 'row', gap: 8, backgroundColor: Theme.colors.accentStrong, borderRadius: Theme.radius.md, paddingVertical: 14, alignItems: 'center', justifyContent: 'center', marginTop: 14 },
  editButtonText: { color: '#FFFFFF', fontWeight: '900', fontSize: 14 },
  metaText: { color: Theme.colors.textMuted, fontSize: 11, textAlign: 'center', marginVertical: 20 },
  logoutBtn: {
    flexDirection: 'row', gap: 8, backgroundColor: '#EF444412', borderRadius: Theme.radius.md,
    paddingVertical: 14, alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: '#EF444430',
  },
  logoutText: { color: Theme.colors.danger, fontWeight: '800', fontSize: 15 },
});
