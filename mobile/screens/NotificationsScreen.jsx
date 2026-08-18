import React, { useCallback, useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Bell, BellRing, Check } from 'lucide-react-native';

import { Theme } from '../theme';
import { api } from '../services/api';
import { EmptyState, ErrorState, LoadingSkeleton } from '../components/AsyncState';
import { OfflineBanner } from '../components/OfflineBanner';

function formatDateTime(value) {
  if (!value) return '';
  const date = new Date(value);
  return date.toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit', year: 'numeric' });
}

export default function NotificationsScreen({ navigation }) {
  const [status, setStatus] = useState('loading');
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [readingId, setReadingId] = useState(null);

  const load = useCallback(async (refreshing = false) => {
    setStatus(refreshing ? 'refreshing' : 'loading');
    setError('');
    try {
      setRows(await api.notifications(50));
      setStatus('success');
    } catch (requestError) {
      setError(requestError?.userMessage || 'Không thể tải thông báo.');
      setStatus('error');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function openNotification(item) {
    if (readingId) return;
    if (!item.is_read) {
      setReadingId(item.id);
      try {
        const updated = await api.markNotificationRead(item.id);
        setRows((current) => current.map((row) => row.id === item.id ? updated : row));
      } catch (requestError) {
        setError(requestError?.userMessage || 'Không đánh dấu được thông báo.');
        setReadingId(null);
        return;
      }
      setReadingId(null);
    }
    if (String(item.type).toUpperCase().includes('CHECKIN')) navigation.navigate('Checkin');
  }

  const unreadCount = rows.filter((item) => !item.is_read).length;

  return (
    <SafeAreaView edges={['bottom']} style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.container}
        refreshControl={<RefreshControl refreshing={status === 'refreshing'} onRefresh={() => load(true)} />}
      >
        <OfflineBanner />
        <View style={styles.summary}>
          <BellRing size={22} color={Theme.colors.accentStrong} />
          <View style={styles.summaryText}>
            <Text style={styles.summaryTitle}>{unreadCount ? `${unreadCount} thông báo chưa đọc` : 'Bạn đã đọc hết thông báo'}</Text>
            <Text style={styles.summarySubtitle}>Nhắc check-in và cập nhật quan trọng từ NutriSmart.</Text>
          </View>
        </View>
        {error && status !== 'error' ? <Text style={styles.inlineError}>{error}</Text> : null}
        {status === 'loading' ? <LoadingSkeleton rows={3} /> : null}
        {status === 'error' ? <ErrorState message={error} onRetry={load} /> : null}
        {status === 'success' && !rows.length ? <EmptyState title="Chưa có thông báo" message="Các lời nhắc và cập nhật sẽ xuất hiện tại đây." /> : null}
        {rows.map((item) => (
          <TouchableOpacity
            key={item.id}
            style={[styles.card, !item.is_read && styles.unreadCard]}
            onPress={() => openNotification(item)}
            activeOpacity={0.78}
          >
            <View style={[styles.iconCircle, !item.is_read && styles.unreadIcon]}>
              {item.is_read ? <Check size={17} color={Theme.colors.textMuted} /> : <Bell size={17} color={Theme.colors.accentStrong} />}
            </View>
            <View style={styles.content}>
              <View style={styles.titleRow}>
                <Text style={styles.title}>{item.title}</Text>
                {!item.is_read ? <View style={styles.dot} /> : null}
              </View>
              {item.body ? <Text style={styles.body}>{item.body}</Text> : null}
              <Text style={styles.date}>{formatDateTime(item.created_at)}</Text>
              {String(item.type).toUpperCase().includes('CHECKIN') ? <Text style={styles.link}>Mở check-in →</Text> : null}
            </View>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Theme.colors.background },
  container: { padding: 18, paddingBottom: 42 },
  summary: { flexDirection: 'row', alignItems: 'center', backgroundColor: Theme.colors.accentSoft, borderRadius: Theme.radius.md, padding: 14, marginBottom: 14 },
  summaryText: { flex: 1, marginLeft: 10 },
  summaryTitle: { color: Theme.colors.accentStrong, fontSize: 14, fontWeight: '900' },
  summarySubtitle: { color: Theme.colors.textSecondary, fontSize: 11, lineHeight: 16, marginTop: 3 },
  inlineError: { color: Theme.colors.danger, backgroundColor: Theme.colors.dangerSoft, padding: 11, borderRadius: Theme.radius.sm, marginBottom: 12 },
  card: { flexDirection: 'row', backgroundColor: Theme.colors.card, borderWidth: 1, borderColor: Theme.colors.border, borderRadius: Theme.radius.md, padding: 14, marginBottom: 10 },
  unreadCard: { borderColor: '#10B98155', backgroundColor: '#F7FFFB' },
  iconCircle: { width: 38, height: 38, borderRadius: 19, backgroundColor: Theme.colors.cardSecondary, alignItems: 'center', justifyContent: 'center' },
  unreadIcon: { backgroundColor: Theme.colors.accentSoft },
  content: { flex: 1, marginLeft: 11 },
  titleRow: { flexDirection: 'row', alignItems: 'center' },
  title: { color: Theme.colors.text, fontSize: 14, fontWeight: '900', flex: 1 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: Theme.colors.accentStrong, marginLeft: 8 },
  body: { color: Theme.colors.textSecondary, fontSize: 12, lineHeight: 18, marginTop: 5 },
  date: { color: Theme.colors.textMuted, fontSize: 10, marginTop: 8 },
  link: { color: Theme.colors.accentStrong, fontSize: 11, fontWeight: '800', marginTop: 6 },
});
