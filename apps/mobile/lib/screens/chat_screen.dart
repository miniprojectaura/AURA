/// Chat Screen — Real-time WebSocket chat with the AI Fashion Designer.
///
/// Features:
/// - WebSocket streaming responses
/// - Voice input (mic button)
/// - Language selector (EN/HI/TE)
/// - Suggestion chips
/// - Message bubbles with rich formatting
import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../core/theme.dart';
import '../core/env.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

// ── Chat State ──────────────────────────────────────────────────────
class ChatMessage {
  final String content;
  final bool isUser;
  final DateTime timestamp;
  final List<String> suggestions;
  ChatMessage({required this.content, required this.isUser, DateTime? timestamp, this.suggestions = const []})
      : timestamp = timestamp ?? DateTime.now();
}

class ChatState {
  final List<ChatMessage> messages;
  final bool isConnected;
  final bool isTyping;
  final String language;
  ChatState({this.messages = const [], this.isConnected = false, this.isTyping = false, this.language = 'en'});
  ChatState copyWith({List<ChatMessage>? messages, bool? isConnected, bool? isTyping, String? language}) =>
    ChatState(
      messages: messages ?? this.messages,
      isConnected: isConnected ?? this.isConnected,
      isTyping: isTyping ?? this.isTyping,
      language: language ?? this.language,
    );
}

class ChatNotifier extends StateNotifier<ChatState> {
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  String _partialResponse = '';
  String? _accessToken;

  ChatNotifier() : super(ChatState()) {
    _initAndConnect();
  }

  /// Authenticate first, then connect WebSocket with real JWT.
  Future<void> _initAndConnect() async {
    debugPrint('[AURA] _initAndConnect starting...');
    try {
      _accessToken = await _getOrCreateToken();
      debugPrint('[AURA] Token result: ${_accessToken != null ? "got token" : "NULL"}');
      if (_accessToken != null) {
        _connect(_accessToken!);
      } else {
        debugPrint('[AURA] No token — setting offline');
        state = state.copyWith(isConnected: false);
      }
    } catch (e) {
      debugPrint('[AURA] _initAndConnect error: $e');
      state = state.copyWith(isConnected: false);
    }
  }

  /// Load saved token or auto-register a guest user.
  Future<String?> _getOrCreateToken() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString('access_token');
      if (saved != null && saved.isNotEmpty) {
        debugPrint('[AURA] Using saved token: ${saved.substring(0, 20)}...');
        return saved;
      }

      // Auto-register a guest user
      final guestId = DateTime.now().millisecondsSinceEpoch;
      final email = 'guest_$guestId@fashionai.app';
      final password = 'GuestPass${guestId}Secure';
      debugPrint('[AURA] Registering guest: $email at ${Env.apiBaseUrl}');

      final response = await http.post(
        Uri.parse('${Env.apiBaseUrl}/api/v1/auth/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': email,
          'password': password,
          'display_name': 'Fashion Lover',
        }),
      );

      debugPrint('[AURA] Register response: ${response.statusCode}');

      if (response.statusCode == 201 || response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['access_token'] as String?;
        if (token != null) {
          await prefs.setString('access_token', token);
          if (data['refresh_token'] != null) {
            await prefs.setString('refresh_token', data['refresh_token'] as String);
          }
          debugPrint('[AURA] Got token: ${token.substring(0, 20)}...');
          return token;
        } else {
          debugPrint('[AURA] No access_token in response body');
        }
      } else {
        debugPrint('[AURA] Register failed: ${response.body}');
      }
    } catch (e, st) {
      debugPrint('[AURA] Token error: $e');
      debugPrint('[AURA] Stack: $st');
    }
    return null;
  }

  void _connect(String token) {
    try {
      final wsUrl = Env.wsBaseUrl;
      final uri = Uri.parse('$wsUrl/api/v1/chat/ws/auto?token=$token');

      _channel = WebSocketChannel.connect(uri);
      state = state.copyWith(isConnected: true);

      _subscription = _channel!.stream.listen(
        (data) {
          final msg = jsonDecode(data as String);
          _handleServerMessage(msg);
        },
        onError: (e) => state = state.copyWith(isConnected: false),
        onDone: () => state = state.copyWith(isConnected: false),
      );
    } catch (_) {
      state = state.copyWith(isConnected: false);
    }
  }

  void _handleServerMessage(Map<String, dynamic> msg) {
    switch (msg['type']) {
      case 'response_start':
        state = state.copyWith(isTyping: true);
        _partialResponse = '';
        break;
      case 'response_chunk':
        _partialResponse += msg['content'] as String? ?? '';
        break;
      case 'response_end':
        final fullContent = msg['full_content'] as String? ?? _partialResponse;
        final suggestions = (msg['suggestions'] as List<dynamic>?)?.cast<String>() ?? [];
        final assistantMsg = ChatMessage(content: fullContent, isUser: false, suggestions: suggestions);
        state = state.copyWith(
          messages: [...state.messages, assistantMsg],
          isTyping: false,
        );
        _partialResponse = '';
        break;
      case 'pong':
        break;
    }
  }

  void sendMessage(String text) {
    if (text.trim().isEmpty) return;
    final userMsg = ChatMessage(content: text, isUser: true);
    state = state.copyWith(messages: [...state.messages, userMsg]);

    if (_channel != null && state.isConnected) {
      _channel!.sink.add(jsonEncode({
        'type': 'message',
        'content': text,
        'language': state.language,
      }));
    } else {
      // Offline fallback
      final offlineMsg = ChatMessage(
        content: 'I\'m currently offline. Please check your connection and try again.',
        isUser: false,
      );
      state = state.copyWith(messages: [...state.messages, offlineMsg]);
    }
  }

  void setLanguage(String lang) {
    state = state.copyWith(language: lang);
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _channel?.sink.close();
    super.dispose();
  }
}

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>((ref) => ChatNotifier());

// ── Chat Screen Widget ──────────────────────────────────────────────
class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});
  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  bool _isRecording = false;

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatProvider);

    // Auto-scroll on new messages
    ref.listen(chatProvider, (_, next) => _scrollToBottom());

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                gradient: AppColors.gradientPrimary,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.auto_awesome, color: Colors.white, size: 18),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Fashion AI', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                Text(
                  chatState.isConnected ? 'Online' : 'Offline',
                  style: TextStyle(
                    fontSize: 11,
                    color: chatState.isConnected ? AppColors.success : AppColors.error,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          // Language selector
          PopupMenuButton<String>(
            onSelected: (lang) => ref.read(chatProvider.notifier).setLanguage(lang),
            icon: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.surfaceLight,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.border),
              ),
              child: Text(
                chatState.language.toUpperCase(),
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.primary),
              ),
            ),
            itemBuilder: (_) => [
              const PopupMenuItem(value: 'en', child: Text('🇬🇧 English')),
              const PopupMenuItem(value: 'hi', child: Text('🇮🇳 हिंदी')),
              const PopupMenuItem(value: 'te', child: Text('🇮🇳 తెలుగు')),
            ],
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Column(
        children: [
          // Messages
          Expanded(
            child: chatState.messages.isEmpty
                ? _buildWelcome()
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                    itemCount: chatState.messages.length + (chatState.isTyping ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index == chatState.messages.length && chatState.isTyping) {
                        return _buildTypingIndicator();
                      }
                      return _MessageBubble(message: chatState.messages[index], onSuggestionTap: _sendSuggestion);
                    },
                  ),
          ),

          // Input bar
          Container(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
            decoration: BoxDecoration(
              color: AppColors.surface.withOpacity(0.95),
              border: const Border(top: BorderSide(color: AppColors.border, width: 0.5)),
            ),
            child: SafeArea(
              child: Row(
                children: [
                  // Mic button
                  GestureDetector(
                    onTap: () => setState(() => _isRecording = !_isRecording),
                    child: Container(
                      width: 40, height: 40,
                      decoration: BoxDecoration(
                        color: _isRecording ? AppColors.error.withOpacity(0.2) : AppColors.surfaceLight,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: _isRecording ? AppColors.error : AppColors.border),
                      ),
                      child: Icon(
                        _isRecording ? Icons.stop : Icons.mic,
                        size: 20,
                        color: _isRecording ? AppColors.error : AppColors.textMuted,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  // Text input
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      decoration: InputDecoration(
                        hintText: 'Ask about fashion...',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(20),
                          borderSide: BorderSide.none,
                        ),
                        filled: true,
                        fillColor: AppColors.surfaceLight,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        isDense: true,
                      ),
                      textInputAction: TextInputAction.send,
                      onSubmitted: _send,
                      maxLines: 3,
                      minLines: 1,
                    ),
                  ),
                  const SizedBox(width: 8),
                  // Send button
                  GestureDetector(
                    onTap: () => _send(_controller.text),
                    child: Container(
                      width: 40, height: 40,
                      decoration: BoxDecoration(
                        gradient: AppColors.gradientPrimary,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(Icons.send_rounded, color: Colors.white, size: 20),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _send(String text) {
    if (text.trim().isEmpty) return;
    ref.read(chatProvider.notifier).sendMessage(text.trim());
    _controller.clear();
  }

  void _sendSuggestion(String text) {
    ref.read(chatProvider.notifier).sendMessage(text);
  }

  Widget _buildWelcome() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80, height: 80,
              decoration: BoxDecoration(
                gradient: AppColors.gradientPrimary,
                borderRadius: BorderRadius.circular(24),
              ),
              child: const Icon(Icons.auto_awesome, color: Colors.white, size: 40),
            ),
            const SizedBox(height: 24),
            Text('Hi there! 👋', style: Theme.of(context).textTheme.displayMedium),
            const SizedBox(height: 8),
            Text(
              'I\'m your AI Fashion Designer.\nAsk me anything about fashion!',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 32),
            Wrap(
              spacing: 8, runSpacing: 8,
              alignment: WrapAlignment.center,
              children: [
                _SuggestionChip('Design a wedding outfit', onTap: _sendSuggestion),
                _SuggestionChip('What suits my body type?', onTap: _sendSuggestion),
                _SuggestionChip('Find kurtas under ₹2000', onTap: _sendSuggestion),
                _SuggestionChip('Tailoring tips for blouse', onTap: _sendSuggestion),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTypingIndicator() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: AppColors.surfaceLight,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _dot(0), const SizedBox(width: 4),
                _dot(1), const SizedBox(width: 4),
                _dot(2),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _dot(int index) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.3, end: 1.0),
      duration: Duration(milliseconds: 600 + index * 200),
      builder: (_, value, child) => Opacity(opacity: value, child: child),
      child: Container(width: 8, height: 8, decoration: BoxDecoration(color: AppColors.textMuted, shape: BoxShape.circle)),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final ChatMessage message;
  final Function(String) onSuggestionTap;
  const _MessageBubble({required this.message, required this.onSuggestionTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: message.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Container(
            constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.78),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: message.isUser ? AppColors.primary : AppColors.surfaceLight,
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(16),
                topRight: const Radius.circular(16),
                bottomLeft: Radius.circular(message.isUser ? 16 : 4),
                bottomRight: Radius.circular(message.isUser ? 4 : 16),
              ),
              border: message.isUser ? null : Border.all(color: AppColors.border),
            ),
            child: Text(
              message.content,
              style: TextStyle(
                color: message.isUser ? Colors.white : AppColors.textPrimary,
                fontSize: 14, height: 1.5,
              ),
            ),
          ),
          if (message.suggestions.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 6, runSpacing: 6,
              children: message.suggestions.map((s) =>
                _SuggestionChip(s, onTap: onSuggestionTap),
              ).toList(),
            ),
          ],
        ],
      ),
    );
  }
}

class _SuggestionChip extends StatelessWidget {
  final String text;
  final Function(String) onTap;
  const _SuggestionChip(this.text, {required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => onTap(text),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.primary.withOpacity(0.1),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.primary.withOpacity(0.3)),
        ),
        child: Text(text, style: const TextStyle(fontSize: 12, color: AppColors.primaryLight, fontWeight: FontWeight.w500)),
      ),
    );
  }
}
