import React from 'react';
import { StyleSheet, View, Text, Platform } from 'react-native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Footprints, Camera, Calendar, User } from 'lucide-react-native';

import HomeScreen from '../screens/HomeScreen';
import FoodScanScreen from '../screens/FoodScanScreen';
import PlanScreen from '../screens/PlanScreen';
import ProfileScreen from '../screens/ProfileScreen';
import { Theme } from '../theme';

const Tab = createBottomTabNavigator();

export default function MainTabNavigator({ route }) {
  const backendIp = route?.params?.backendIp ?? '10.120.56.85';

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarShowLabel: true,
        tabBarActiveTintColor: Theme.colors.accentStrong,
        tabBarInactiveTintColor: Theme.colors.textMuted,
        tabBarStyle: styles.tabBar,
        tabBarLabelStyle: styles.tabBarLabel,
        tabBarIcon: ({ focused, color, size }) => {
          const iconSize = focused ? 24 : 22;

          if (route.name === 'TabHome') {
            return <Footprints size={iconSize} color={color} />;
          } else if (route.name === 'TabFoodScan') {
            return <Camera size={iconSize} color={color} />;
          } else if (route.name === 'TabPlan') {
            return <Calendar size={iconSize} color={color} />;
          } else if (route.name === 'TabProfile') {
            return <User size={iconSize} color={color} />;
          }
        },
      })}
    >
      <Tab.Screen
        name="TabHome"
        component={HomeScreen}
        options={{ tabBarLabel: 'Tổng quan' }}
        initialParams={{ backendIp }}
      />
      <Tab.Screen
        name="TabFoodScan"
        component={FoodScanScreen}
        options={{ tabBarLabel: 'Quét AI' }}
        initialParams={{ backendIp }}
      />
      <Tab.Screen
        name="TabPlan"
        component={PlanScreen}
        options={{ tabBarLabel: 'Lộ trình' }}
        initialParams={{ backendIp }}
      />
      <Tab.Screen
        name="TabProfile"
        component={ProfileScreen}
        options={{ tabBarLabel: 'Cá nhân' }}
        initialParams={{ backendIp }}
      />
    </Tab.Navigator>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: Theme.colors.card,
    borderTopWidth: 1,
    borderTopColor: Theme.colors.border,
    height: Platform.OS === 'ios' ? 88 : 64,
    paddingBottom: Platform.OS === 'ios' ? 28 : 10,
    paddingTop: 8,
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.05,
    shadowRadius: 6,
  },
  tabBarLabel: {
    fontSize: 11,
    fontWeight: '700',
    marginTop: 2,
  },
});
