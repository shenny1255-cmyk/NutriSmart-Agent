import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { View, Text, ActivityIndicator, StyleSheet, StatusBar } from 'react-native';

import LoginScreen from './screens/LoginScreen';
import MainTabNavigator from './navigation/MainTabNavigator';
import JournalScreen from './screens/JournalScreen';
import CheckinScreen from './screens/CheckinScreen';
import EditProfileScreen from './screens/EditProfileScreen';
import NotificationsScreen from './screens/NotificationsScreen';
import ChatScreen from './screens/ChatScreen';
import { Theme } from './theme';
import { LogoMark } from './components/Logo';
import { AuthProvider, useAuth } from './context/AuthContext';

const Stack = createNativeStackNavigator();

function RootNavigator() {
  const { status } = useAuth();

  if (status === 'loading') {
    return (
      <View style={styles.splash}>
        <StatusBar barStyle="dark-content" backgroundColor={Theme.colors.background} />
        <LogoMark size={80} />
        <ActivityIndicator size="large" color={Theme.colors.accentStrong} style={{ marginTop: 24 }} />
        <Text style={styles.splashText}>NutriSmart</Text>
      </View>
    );
  }

  return (
    <NavigationContainer>
      <StatusBar barStyle="dark-content" backgroundColor={Theme.colors.background} />
      <Stack.Navigator
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: Theme.colors.background },
          headerStyle: { backgroundColor: Theme.colors.card },
          headerTintColor: Theme.colors.text,
          headerTitleStyle: { fontWeight: '800' },
          headerShadowVisible: false,
        }}
      >
        {status === 'authenticated' ? (
          <>
            <Stack.Screen name="Main" component={MainTabNavigator} />
            <Stack.Screen name="Journal" component={JournalScreen} options={{ headerShown: true, title: 'Nhật ký' }} />
            <Stack.Screen name="Checkin" component={CheckinScreen} options={{ headerShown: true, title: 'Check-in 14 ngày' }} />
            <Stack.Screen name="EditProfile" component={EditProfileScreen} options={{ headerShown: true, title: 'Cập nhật hồ sơ' }} />
            <Stack.Screen name="Notifications" component={NotificationsScreen} options={{ headerShown: true, title: 'Thông báo' }} />
            <Stack.Screen name="Chat" component={ChatScreen} options={{ headerShown: true, title: 'Trợ lý AI' }} />
          </>
        ) : (
          <Stack.Screen name="Login" component={LoginScreen} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <RootNavigator />
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  splash: {
    flex: 1,
    backgroundColor: Theme.colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  splashText: {
    color: Theme.colors.textSecondary,
    fontSize: 18,
    marginTop: 12,
    fontWeight: 'bold',
  },
});
