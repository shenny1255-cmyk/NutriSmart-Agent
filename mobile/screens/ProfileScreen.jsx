import React, { useEffect, useState } from 'react';
import {
  StyleSheet, Text, View, ScrollView, StatusBar, TouchableOpacity, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { User, LogOut, ShieldCheck, Cpu, ChevronRight, Activity, Flame, Scale, Globe } from 'lucide-react-native';
import { Theme } from '../theme';
import { LogoMark } from '../components/Logo';

export default function ProfileScreen({ navigation, route }) {
  let rawIp = route?.params?.backendIp ?? '10.251.3.81';
  if (rawIp === '172.16.162' || rawIp === '172.16.1.162') rawIp = '10.251.3.81';
  const backendIp = rawIp.trim();

  const [userData, setUserData] = useState(null);

  useEffect(() => {
    async function loadUserData() {
      try {
        const token = await AsyncStorage.getItem('access_token');
        if (token) {
          const res = await axios.get(`http://${backendIp}:8000/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
            timeout: 5000,
          });
          setUserData(res.data);
        }
      } catch (e) {
        console.log('Error loading me:', e.message);
      }
    }
    loadUserData();
  }, [backendIp]);

  const handleLogout = () => {
    Alert.alert('Đăng xuất', 'Bạn có chắc chắn muốn đăng xuất không?', [
      { text: 'Huỷ', style: 'cancel' },
      {
        text: 'Đăng xuất',
        style: 'destructive',
        onPress: async () => {
          await AsyncStorage.removeItem('access_token');
          navigation.replace('Login', { backendIp });
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor={Theme.colors.background} />
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>

        {/* Header Avatar & Email */}
        <View style={styles.profileCard}>
          <View style={styles.avatarCircle}>
            <User size={40} color={Theme.colors.accentStrong} />
          </View>
          <Text style={styles.fullName}>{userData?.full_name ?? 'Người dùng NutriSmart'}</Text>
          <Text style={styles.emailText}>{userData?.email ?? 'user@nutrismart.vn'}</Text>

          <View style={styles.roleBadge}>
            <ShieldCheck size={14} color={Theme.colors.accentStrong} style={{ marginRight: 4 }} />
            <Text style={styles.roleText}>Tài khoản Đã xác thực (ROLE_{userData?.role ?? 'USER'})</Text>
          </View>
        </View>

        {/* Thông số hệ thống */}
        <Text style={styles.sectionTitle}>Thông tin kết nối & Thiết bị</Text>
        <View style={styles.infoCard}>
          <View style={styles.infoRow}>
            <Globe size={18} color={Theme.colors.textMuted} />
            <Text style={styles.infoLabel}>Địa chỉ Máy chủ API</Text>
            <Text style={styles.infoVal}>{backendIp}:8000</Text>
          </View>

          <View style={styles.divider} />

          <View style={styles.infoRow}>
            <Cpu size={18} color={Theme.colors.textMuted} />
            <Text style={styles.infoLabel}>Phiên bản Ứng dụng</Text>
            <Text style={styles.infoVal}>NutriSmart Mobile v1.2.0</Text>
          </View>
        </View>

        {/* Nút Đăng xuất */}
        <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout} activeOpacity={0.8}>
          <LogOut size={18} color={Theme.colors.danger} style={{ marginRight: 8 }} />
          <Text style={styles.logoutText}>Đăng xuất khỏi ứng dụng</Text>
        </TouchableOpacity>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Theme.colors.background },
  container: { padding: 20, paddingBottom: 40 },

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
    flexDirection: 'row', alignItems: 'center', backgroundColor: Theme.colors.accentSoft,
    paddingHorizontal: 12, paddingVertical: 4, borderRadius: Theme.radius.full,
  },
  roleText: { fontSize: 11, fontWeight: '700', color: Theme.colors.accentStrong },

  sectionTitle: { fontSize: 14, fontWeight: '700', color: Theme.colors.textMuted, marginBottom: 10 },
  infoCard: {
    backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md,
    padding: 16, borderWidth: 1, borderColor: Theme.colors.border, marginBottom: 24,
  },
  infoRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8 },
  infoLabel: { fontSize: 13, color: Theme.colors.text, marginLeft: 10, flex: 1, fontWeight: '600' },
  infoVal: { fontSize: 13, fontWeight: '700', color: Theme.colors.accentStrong },
  divider: { height: 1, backgroundColor: Theme.colors.border, marginVertical: 4 },

  logoutBtn: {
    flexDirection: 'row', backgroundColor: '#EF444412', borderRadius: Theme.radius.md,
    paddingVertical: 14, alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: '#EF444430',
  },
  logoutText: { color: Theme.colors.danger, fontWeight: '800', fontSize: 15 },
});
