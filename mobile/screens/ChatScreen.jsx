import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator, Alert, KeyboardAvoidingView, Linking, Platform, ScrollView,
  StyleSheet, Text, TextInput, TouchableOpacity, View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Bot, ExternalLink, Send, Sparkles, Trash2, User } from 'lucide-react-native';

import { Theme } from '../theme';
import { api } from '../services/api';
import { ErrorState, LoadingSkeleton } from '../components/AsyncState';
import { OfflineBanner } from '../components/OfflineBanner';

const QUICK_PROMPTS = [
  'Gợi ý bữa tối phù hợp mục tiêu của tôi',
  'Hôm nay tôi nên ăn bao nhiêu protein?',
  'Làm sao giảm cảm giác đói khi giảm cân?',
];

export default function ChatScreen() {
  const listRef = useRef(null);
  const [status, setStatus] = useState('loading');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [clearing, setClearing] = useState(false);

  const load = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setMessages(await api.chatHistory());
      setStatus('success');
      setTimeout(() => listRef.current?.scrollToEnd({ animated: false }), 0);
    } catch (requestError) {
      setError(requestError?.userMessage || 'Không thể tải lịch sử trò chuyện.');
      setStatus('error');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function send(prompt = input) {
    const content = prompt.trim();
    if (!content || sending || content.length > 4000) return;
    const userMessage = { id: `local-user-${Date.now()}`, role: 'user', content };
    setMessages((current) => [...current, userMessage]);
    setInput('');
    setError('');
    setSending(true);
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 0);
    try {
      const response = await api.sendChat(content);
      setMessages((current) => [...current, {
        id: `local-assistant-${Date.now()}`, role: 'assistant',
        content: response.reply, citations: response.citations || [],
      }]);
    } catch (requestError) {
      setError(requestError?.userMessage || 'Trợ lý chưa thể trả lời. Vui lòng thử lại.');
    } finally {
      setSending(false);
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 0);
    }
  }

  function confirmClear() {
    if (!messages.length || clearing) return;
    Alert.alert('Xóa lịch sử trò chuyện', 'Hành động này không thể hoàn tác.', [
      { text: 'Huỷ', style: 'cancel' },
      {
        text: 'Xóa tất cả', style: 'destructive', onPress: async () => {
          setClearing(true);
          setError('');
          try {
            await api.clearChatHistory();
            setMessages([]);
          } catch (requestError) {
            setError(requestError?.userMessage || 'Không thể xóa lịch sử trò chuyện.');
          } finally {
            setClearing(false);
          }
        },
      },
    ]);
  }

  return (
    <SafeAreaView edges={['bottom']} style={styles.safeArea}>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
        <View style={styles.container}>
          <OfflineBanner />
          <View style={styles.chatHeader}>
            <View style={styles.headerIdentity}><View style={styles.botCircle}><Bot size={22} color={Theme.colors.accentStrong} /></View><View style={styles.headerText}><Text style={styles.title}>Trợ lý dinh dưỡng</Text><Text style={styles.subtitle}>Tư vấn dựa trên hồ sơ và lộ trình của bạn</Text></View></View>
            {messages.length ? <TouchableOpacity onPress={confirmClear} style={styles.clearButton} disabled={clearing}><Trash2 size={18} color={Theme.colors.danger} /></TouchableOpacity> : null}
          </View>

          {status === 'loading' ? <LoadingSkeleton rows={2} /> : null}
          {status === 'error' ? <ErrorState message={error} onRetry={load} /> : null}
          {status === 'success' ? (
            <ScrollView
              ref={listRef}
              style={styles.messages}
              contentContainerStyle={styles.messagesContent}
              keyboardShouldPersistTaps="handled"
              onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
            >
              {!messages.length ? (
                <View style={styles.welcome}>
                  <View style={styles.welcomeIcon}><Sparkles size={28} color={Theme.colors.accentStrong} /></View>
                  <Text style={styles.welcomeTitle}>Bạn muốn hỏi gì về dinh dưỡng?</Text>
                  <Text style={styles.welcomeText}>Chọn một gợi ý hoặc nhập câu hỏi riêng của bạn.</Text>
                  {QUICK_PROMPTS.map((prompt) => <TouchableOpacity key={prompt} onPress={() => send(prompt)} style={styles.prompt}><Text style={styles.promptText}>{prompt}</Text></TouchableOpacity>)}
                </View>
              ) : null}
              {messages.map((message) => <MessageBubble key={message.id} item={message} />)}
              {sending ? <View style={styles.typing}><ActivityIndicator size="small" color={Theme.colors.accentStrong} /><Text style={styles.typingText}>Trợ lý đang suy nghĩ…</Text></View> : null}
            </ScrollView>
          ) : null}

          {error && status === 'success' ? <Text style={styles.error}>{error}</Text> : null}
          <View style={styles.composer}>
            <TextInput
              style={styles.input}
              value={input}
              onChangeText={setInput}
              placeholder="Nhập câu hỏi của bạn…"
              placeholderTextColor={Theme.colors.textMuted}
              multiline
              maxLength={4000}
              editable={!sending && status === 'success'}
            />
            <TouchableOpacity style={[styles.sendButton, (!input.trim() || sending) && styles.disabled]} onPress={() => send()} disabled={!input.trim() || sending}>
              {sending ? <ActivityIndicator size="small" color="#FFFFFF" /> : <Send size={19} color="#FFFFFF" />}
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function MessageBubble({ item }) {
  const isUser = item.role === 'user';
  return (
    <View style={[styles.messageRow, isUser && styles.messageRowUser]}>
      <View style={[styles.avatar, isUser && styles.avatarUser]}>{isUser ? <User size={15} color="#FFFFFF" /> : <Bot size={15} color={Theme.colors.accentStrong} />}</View>
      <View style={[styles.bubble, isUser && styles.userBubble]}>
        <Text style={[styles.messageText, isUser && styles.userMessageText]}>{item.content}</Text>
        {!isUser && item.citations?.length ? (
          <View style={styles.citations}>
            <Text style={styles.citationHeading}>Nguồn tham khảo</Text>
            {item.citations.map((citation, index) => {
              const title = citation.title || `Tài liệu ${index + 1}`;
              return (
                <TouchableOpacity key={`${title}-${index}`} onPress={() => citation.url && Linking.openURL(citation.url)} disabled={!citation.url} style={styles.citation}>
                  <Text style={styles.citationText} numberOfLines={2}>{index + 1}. {title}</Text>
                  {citation.url ? <ExternalLink size={13} color={Theme.colors.accentStrong} /> : null}
                </TouchableOpacity>
              );
            })}
          </View>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Theme.colors.background },
  flex: { flex: 1 },
  container: { flex: 1, paddingHorizontal: 14, paddingBottom: 10 },
  chatHeader: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10 },
  headerIdentity: { flex: 1, flexDirection: 'row', alignItems: 'center' },
  botCircle: { width: 42, height: 42, borderRadius: 21, backgroundColor: Theme.colors.accentSoft, alignItems: 'center', justifyContent: 'center' },
  headerText: { marginLeft: 10, flex: 1 },
  title: { color: Theme.colors.text, fontSize: 15, fontWeight: '900' },
  subtitle: { color: Theme.colors.textMuted, fontSize: 10, marginTop: 2 },
  clearButton: { width: 42, height: 42, alignItems: 'center', justifyContent: 'center', borderRadius: 21, backgroundColor: Theme.colors.dangerSoft },
  messages: { flex: 1, backgroundColor: Theme.colors.card, borderWidth: 1, borderColor: Theme.colors.border, borderRadius: Theme.radius.lg },
  messagesContent: { flexGrow: 1, padding: 14 },
  welcome: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingVertical: 26 },
  welcomeIcon: { width: 58, height: 58, borderRadius: 29, backgroundColor: Theme.colors.accentSoft, alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  welcomeTitle: { color: Theme.colors.text, fontSize: 17, fontWeight: '900', textAlign: 'center' },
  welcomeText: { color: Theme.colors.textMuted, fontSize: 12, marginTop: 5, marginBottom: 16 },
  prompt: { alignSelf: 'stretch', borderWidth: 1, borderColor: '#10B98145', borderRadius: Theme.radius.md, padding: 12, marginBottom: 8, backgroundColor: Theme.colors.accentSoft },
  promptText: { color: Theme.colors.accentStrong, fontSize: 12, fontWeight: '700', textAlign: 'center' },
  messageRow: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 13 },
  messageRowUser: { flexDirection: 'row-reverse' },
  avatar: { width: 30, height: 30, borderRadius: 15, backgroundColor: Theme.colors.accentSoft, alignItems: 'center', justifyContent: 'center', marginRight: 7 },
  avatarUser: { backgroundColor: Theme.colors.accentStrong, marginRight: 0, marginLeft: 7 },
  bubble: { maxWidth: '82%', backgroundColor: Theme.colors.cardSecondary, borderRadius: 15, borderTopLeftRadius: 4, paddingHorizontal: 12, paddingVertical: 10 },
  userBubble: { backgroundColor: Theme.colors.accentStrong, borderTopLeftRadius: 15, borderTopRightRadius: 4 },
  messageText: { color: Theme.colors.text, fontSize: 13, lineHeight: 19 },
  userMessageText: { color: '#FFFFFF' },
  citations: { borderTopWidth: 1, borderTopColor: Theme.colors.border, marginTop: 9, paddingTop: 7 },
  citationHeading: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '800', marginBottom: 4 },
  citation: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingVertical: 4 },
  citationText: { color: Theme.colors.accentStrong, fontSize: 10, flex: 1 },
  typing: { flexDirection: 'row', alignItems: 'center', gap: 8, marginLeft: 38, marginBottom: 10 },
  typingText: { color: Theme.colors.textMuted, fontSize: 11 },
  error: { color: Theme.colors.danger, backgroundColor: Theme.colors.dangerSoft, borderRadius: Theme.radius.sm, padding: 9, marginTop: 7, fontSize: 11 },
  composer: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, paddingTop: 9 },
  input: { flex: 1, maxHeight: 110, minHeight: 46, backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: Theme.colors.borderStrong, borderRadius: 23, paddingHorizontal: 16, paddingVertical: 12, color: Theme.colors.text, textAlignVertical: 'top' },
  sendButton: { width: 46, height: 46, borderRadius: 23, backgroundColor: Theme.colors.accentStrong, alignItems: 'center', justifyContent: 'center' },
  disabled: { opacity: 0.45 },
});
