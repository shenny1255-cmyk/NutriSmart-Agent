import React, { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { View, Text, ActivityIndicator, StyleSheet, StatusBar } from 'react-native';

import LoginScreen from './screens/LoginScreen';
import MainTabNavigator from './navigation/MainTabNavigator';
import { Theme } from './theme';
import { LogoMark } from './components/Logo';

const Stack = createNativeStackNavigator();

const BACKEND_IP = '10.120.56.85';

export default function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [initialRoute, setInitialRoute] = useState('Login');

  useEffect(() => {
    AsyncStorage.getItem('access_token')
      .then((token) => {
        setInitialRoute(token ? 'Main' : 'Login');
      })
      .catch(() => {
        setInitialRoute('Login');
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  if (isLoading) {
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
        initialRouteName={initialRoute}
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: Theme.colors.background },
        }}
      >
        <Stack.Screen
          name="Login"
          component={LoginScreen}
          initialParams={{ backendIp: BACKEND_IP }}
        />
        <Stack.Screen
          name="Main"
          component={MainTabNavigator}
          initialParams={{ backendIp: BACKEND_IP }}
        />
      </Stack.Navigator>
    </NavigationContainer>
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
