import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { WifiOff } from 'lucide-react-native';
import { useNetInfo } from '@react-native-community/netinfo';

export function OfflineBanner() {
  const network = useNetInfo();
  if (network.isConnected !== false) return null;

  return (
    <View style={styles.banner} accessibilityRole="alert">
      <WifiOff size={16} color="#92400E" />
      <Text style={styles.text}>Bạn đang ngoại tuyến. Một số dữ liệu có thể chưa cập nhật.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#FEF3C7',
    borderColor: '#F59E0B55', borderWidth: 1, borderRadius: 10,
    paddingHorizontal: 12, paddingVertical: 10, marginBottom: 14,
  },
  text: { color: '#92400E', fontSize: 12, fontWeight: '600', marginLeft: 8, flex: 1 },
});
