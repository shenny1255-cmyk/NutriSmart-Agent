import React, { useState } from 'react';
import {
  StyleSheet, Text, View, TextInput, TouchableOpacity,
  SafeAreaView, StatusBar, KeyboardAvoidingView, Platform,
  ActivityIndicator, ScrollView,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { Mail, Lock, Server, AlertCircle } from 'lucide-react-native';
import { Theme } from '../theme';
import { LogoMark } from '../components/Logo';

export default function LoginScreen({ navigation, route }) {
  let rawIp = route?.params?.backendIp ?? '10.120.56.85';
  if (rawIp === '172.16.162' || rawIp === '172.16.1.162') rawIp = '10.120.56.85';
  const backendIp = rawIp.trim();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [emailFocused, setEmailFocused] = useState(false);
  const [passwordFocused, setPasswordFocused] = useState(false);

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      setError('Vui lòng nhập email và mật khẩu');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const url = `http://${backendIp.trim()}:8000/api/v1/auth/login`;
      const res = await axios.post(
        url,
        { email: email.trim().toLowerCase(), password },
        { headers: { 'Content-Type': 'application/json' }, timeout: 8000 }
      );

      const token = res.data?.access_token;
      if (token) {
        await AsyncStorage.setItem('access_token', token);
        await AsyncStorage.setItem('backend_ip', backendIp.trim());
        navigation.replace('Home', { backendIp: backendIp.trim() });
      } else {
        setError('Không nhận được token từ server');
      }
    } catch (err) {
      if (err.response?.status === 401 || err.response?.status === 400) {
        setError('Email hoặc mật khẩu không đúng');
      } else if (err.code === 'ECONNABORTED') {
        setError('Kết nối timeout — kiểm tra IP và Backend đang chạy');
      } else {
        setError(`Lỗi kết nối: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor={Theme.colors.background} />
      <ScrollView
        contentContainerStyle={styles.scrollContainer}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
        automaticallyAdjustKeyboardInsets={true}
        style={styles.flex}
      >
        <View style={styles.container}>

          {/* Logo & Title */}
          <View style={styles.logoArea}>
            <View style={styles.logoCircle}>
              <LogoMark size={52} />
            </View>
            <Text style={styles.appName}>
              Nutri<Text style={styles.appNameHighlight}>Smart</Text>
            </Text>
            <Text style={styles.appSubtitle}>Trợ lý dinh dưỡng thông minh</Text>
          </View>

          {/* Form Card */}
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Đăng nhập</Text>

            <Text style={styles.label}>Email</Text>
            <View style={[styles.inputContainer, emailFocused && styles.inputContainerFocused]}>
              <Mail size={18} color={emailFocused ? Theme.colors.accentStrong : Theme.colors.textMuted} style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                value={email}
                onChangeText={setEmail}
                placeholder="example@email.com"
                placeholderTextColor={Theme.colors.textMuted}
                autoCapitalize="none"
                keyboardType="email-address"
                autoCorrect={false}
                onFocus={() => setEmailFocused(true)}
                onBlur={() => setEmailFocused(false)}
              />
            </View>

            <Text style={styles.label}>Mật khẩu</Text>
            <View style={[styles.inputContainer, passwordFocused && styles.inputContainerFocused]}>
              <Lock size={18} color={passwordFocused ? Theme.colors.accentStrong : Theme.colors.textMuted} style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                value={password}
                onChangeText={setPassword}
                placeholder="Nhập mật khẩu"
                placeholderTextColor={Theme.colors.textMuted}
                secureTextEntry
                autoCapitalize="none"
                onFocus={() => setPasswordFocused(true)}
                onBlur={() => setPasswordFocused(false)}
              />
            </View>

            <Text style={styles.label}>IP Máy chủ Backend</Text>
            <View style={[styles.inputContainer, styles.inputContainerDisabled]}>
              <Server size={18} color={Theme.colors.textMuted} style={styles.inputIcon} />
              <TextInput
                style={[styles.input, styles.inputDisabled]}
                value={backendIp}
                editable={false}
                selectTextOnFocus={false}
                placeholderTextColor={Theme.colors.textMuted}
              />
            </View>

            {error !== '' && (
              <View style={styles.errorBox}>
                <AlertCircle size={18} color={Theme.colors.danger} style={styles.errorIcon} />
                <Text style={styles.errorText}>{error}</Text>
              </View>
            )}

            <TouchableOpacity
              style={[styles.loginBtn, loading && styles.loginBtnDisabled]}
              onPress={handleLogin}
              disabled={loading}
              activeOpacity={0.8}
            >
              {loading ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <Text style={styles.loginBtnText}>Đăng nhập</Text>
              )}
            </TouchableOpacity>
          </View>

          <Text style={styles.footerNote}>
            Tài khoản được tạo trên Web NutriSmart
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Theme.colors.background },
  flex: { flex: 1 },
  scrollContainer: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  container: {
    paddingHorizontal: 24,
    paddingVertical: 32,
  },
  logoArea: { alignItems: 'center', marginBottom: 36 },
  logoCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: Theme.colors.accentSoft,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 14,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.2)',
    shadowColor: Theme.colors.accent,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 2,
  },
  logoEmoji: { fontSize: 38 },
  appName: {
    fontSize: 32,
    fontWeight: '800',
    color: Theme.colors.text,
    letterSpacing: -0.5,
  },
  appNameHighlight: {
    color: Theme.colors.accentStrong,
  },
  appSubtitle: {
    fontSize: 14,
    color: Theme.colors.textMuted,
    marginTop: 6,
    fontWeight: '500',
  },

  card: {
    backgroundColor: Theme.colors.card,
    borderRadius: Theme.radius.md,
    padding: 24,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    shadowColor: '#10b981',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.06,
    shadowRadius: 16,
    elevation: 3,
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: Theme.colors.text,
    marginBottom: 18,
    textAlign: 'center',
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: Theme.colors.textSecondary,
    marginBottom: 6,
    marginTop: 12,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: Theme.radius.sm,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    paddingHorizontal: 12,
    height: 48,
  },
  inputContainerFocused: {
    borderColor: Theme.colors.accentStrong,
  },
  inputContainerDisabled: {
    backgroundColor: Theme.colors.cardSecondary,
  },
  inputIcon: {
    marginRight: 10,
  },
  input: {
    flex: 1,
    color: Theme.colors.text,
    fontSize: 15,
    height: '100%',
  },
  inputDisabled: {
    color: Theme.colors.textMuted,
  },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Theme.colors.dangerSoft,
    borderRadius: Theme.radius.sm,
    padding: 12,
    marginTop: 14,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.15)',
  },
  errorIcon: {
    marginRight: 8,
  },
  errorText: {
    color: Theme.colors.danger,
    fontSize: 13,
    fontWeight: '500',
    flex: 1,
    lineHeight: 18,
  },
  loginBtn: {
    backgroundColor: Theme.colors.accentStrong,
    paddingVertical: 14,
    borderRadius: Theme.radius.sm,
    alignItems: 'center',
    marginTop: 22,
    shadowColor: Theme.colors.accentStrong,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 6,
    elevation: 2,
  },
  loginBtnDisabled: { backgroundColor: '#A7F3D0' },
  loginBtnText: { color: '#FFFFFF', fontWeight: 'bold', fontSize: 16 },
  footerNote: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    textAlign: 'center',
    marginTop: 24,
    fontWeight: '500',
  },
});

