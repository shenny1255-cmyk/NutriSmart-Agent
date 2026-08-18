import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { AlertCircle, Inbox } from 'lucide-react-native';

import { Theme } from '../theme';

export function LoadingSkeleton({ rows = 3 }) {
  const opacity = useRef(new Animated.Value(0.35)).current;

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 0.8, duration: 650, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.35, duration: 650, useNativeDriver: true }),
      ])
    );
    animation.start();
    return () => animation.stop();
  }, [opacity]);

  return (
    <View accessibilityLabel="Đang tải dữ liệu">
      {Array.from({ length: rows }, (_, index) => (
        <Animated.View key={index} style={[styles.skeletonCard, { opacity }]}>
          <View style={styles.skeletonTitle} />
          <View style={styles.skeletonLine} />
          <View style={[styles.skeletonLine, styles.skeletonLineShort]} />
        </Animated.View>
      ))}
    </View>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <View style={styles.stateCard} accessibilityRole="alert">
      <AlertCircle size={28} color={Theme.colors.danger} />
      <Text style={styles.stateTitle}>Chưa tải được dữ liệu</Text>
      <Text style={styles.stateMessage}>{message}</Text>
      {onRetry ? (
        <TouchableOpacity style={styles.retryButton} onPress={onRetry} activeOpacity={0.8}>
          <Text style={styles.retryText}>Thử lại</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

export function EmptyState({ title, message }) {
  return (
    <View style={styles.stateCard}>
      <Inbox size={30} color={Theme.colors.textMuted} />
      <Text style={styles.stateTitle}>{title}</Text>
      <Text style={styles.stateMessage}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  skeletonCard: {
    height: 118,
    backgroundColor: Theme.colors.cardSecondary,
    borderRadius: Theme.radius.md,
    padding: 18,
    marginBottom: 14,
  },
  skeletonTitle: { width: '45%', height: 18, borderRadius: 8, backgroundColor: '#CBD5E1', marginBottom: 18 },
  skeletonLine: { width: '90%', height: 12, borderRadius: 6, backgroundColor: '#D8E1DE', marginBottom: 10 },
  skeletonLineShort: { width: '62%' },
  stateCard: {
    alignItems: 'center', backgroundColor: Theme.colors.card, borderRadius: Theme.radius.md,
    borderWidth: 1, borderColor: Theme.colors.border, padding: 28, marginVertical: 12,
  },
  stateTitle: { color: Theme.colors.text, fontWeight: '800', fontSize: 17, marginTop: 12 },
  stateMessage: { color: Theme.colors.textMuted, fontSize: 13, lineHeight: 19, textAlign: 'center', marginTop: 6 },
  retryButton: {
    backgroundColor: Theme.colors.accentStrong, borderRadius: Theme.radius.sm,
    paddingHorizontal: 20, paddingVertical: 10, marginTop: 16,
  },
  retryText: { color: '#FFFFFF', fontSize: 14, fontWeight: '800' },
});
