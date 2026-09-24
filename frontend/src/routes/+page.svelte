<script lang="ts">
  import { onMount } from 'svelte';
  import Header from '$lib/components/Header.svelte';
  import ChatMessage from '$lib/components/ChatMessage.svelte';
  import QuickChips from '$lib/components/QuickChips.svelte';
  import type { Message, RoomCard, BookingData } from '$lib/types/chat';

  // Svelte 5 Runes for reactive state
  let messages = $state<Message[]>([
    {
      id: 'welcome-msg',
      role: 'assistant',
      content:
        'ยินดีต้อนรับสู่ Grand Azure Resort & Residences ค่ะ ✨ ดิฉันคือ Aura ผู้ช่วยส่วนตัวระดับเอ็กเซกคิวทีฟ พร้อมดูแลการตรวจสอบห้องว่าง ข้อมูลบริการ นโยบายโรงแรม หรือช่วยยืนยันการจองห้องพักของคุณตลอด 24 ชั่วโมงค่ะ วันนี้มีสิ่งใดให้ดิฉันดูแลเป็นพิเศษไหมคะ?',
      timestamp: 'เมื่อสักครู่',
      isStreaming: false
    }
  ]);

  let inputText = $state('');
  let isLoading = $state(false);
  let threadId = $state('session-default');
  let messagesContainer = $state<HTMLDivElement | null>(null);

  // Initialize unique session threadId from localStorage on mount
  onMount(() => {
    const savedThread = localStorage.getItem('concierge_thread_id');
    if (savedThread) {
      threadId = savedThread;
    } else {
      const newThread = 'thread-' + Math.random().toString(36).substring(2, 9);
      threadId = newThread;
      localStorage.setItem('concierge_thread_id', newThread);
    }
  });

  // Auto-scroll effect when messages change
  $effect(() => {
    if (messages.length && messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  });

  function getAiApiUrl(): string {
    return typeof window !== 'undefined' && (window as any).PUBLIC_AI_API_URL
      ? (window as any).PUBLIC_AI_API_URL
      : 'http://localhost:8000';
  }

  async function handleSendMessage(customPrompt?: string) {
    const textToSend = (customPrompt || inputText).trim();
    if (!textToSend || isLoading) return;

    inputText = '';
    isLoading = true;

    const now = new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' });

    // 1. Add User message
    const userMsg: Message = {
      id: 'user-' + Date.now(),
      role: 'user',
      content: textToSend,
      timestamp: now
    };
    messages = [...messages, userMsg];

    // 2. Add Assistant placeholder message
    const assistantMsgId = 'ai-' + Date.now();
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: now,
      isStreaming: true,
      roomCards: [],
      bookingData: undefined
    };
    messages = [...messages, assistantMsg];

    try {
      const baseUrl = getAiApiUrl();
      const response = await fetch(`${baseUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream'
        },
        body: JSON.stringify({
          message: textToSend,
          thread_id: threadId
        })
      });

      if (!response.ok || !response.body) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;

          const jsonStr = trimmed.replace(/^data:\s*/, '');
          if (!jsonStr) continue;

          try {
            const eventData = JSON.parse(jsonStr);

            // Update current assistant message immutably
            messages = messages.map((msg) => {
              if (msg.id !== assistantMsgId) return msg;

              if (eventData.event === 'token' && eventData.token) {
                const combined = (msg.content + eventData.token)
                  .replaceAll('[ชื่อของคุณ]', 'Aura')
                  .replaceAll('[ชื่อคุณ]', 'Aura')
                  .replaceAll('[ชื่อผู้ช่วย]', 'Aura')
                  .replaceAll('[ชื่อเจ้าหน้าที่]', 'Aura')
                  .replaceAll('[Your Name]', 'Aura');
                return { ...msg, content: combined };
              } else if (eventData.event === 'room_cards' && Array.isArray(eventData.data)) {
                return { ...msg, roomCards: eventData.data };
              } else if (eventData.event === 'booking_confirmation' && eventData.data) {
                return { ...msg, bookingData: eventData.data };
              } else if (eventData.event === 'done') {
                const sanitized = msg.content
                  .replaceAll('[ชื่อของคุณ]', 'Aura')
                  .replaceAll('[ชื่อคุณ]', 'Aura')
                  .replaceAll('[ชื่อผู้ช่วย]', 'Aura')
                  .replaceAll('[ชื่อเจ้าหน้าที่]', 'Aura')
                  .replaceAll('[Your Name]', 'Aura');
                return { ...msg, content: sanitized, isStreaming: false };
              } else if (eventData.event === 'error') {
                return { ...msg, content: eventData.error, isStreaming: false };
              }
              return msg;
            });
          } catch (err) {
            console.error('Failed to parse SSE line JSON:', jsonStr, err);
          }
        }
      }
    } catch (err) {
      console.error('SSE Stream error:', err);
      messages = messages.map((msg) =>
        msg.id === assistantMsgId
          ? {
              ...msg,
              content:
                'ขออภัยเป็นอย่างยิ่งค่ะ ขณะนี้ระบบเชื่อมต่อฐานข้อมูลการบริการขัดข้องชั่วคราว กรุณาตรวจสอบว่าเซิร์ฟเวอร์ AI และ .NET API กำลังทำงาน หรือลองใหม่อีกครั้งในสักครู่นะคะ',
              isStreaming: false
            }
          : msg
      );
    } finally {
      isLoading = false;
      messages = messages.map((msg) =>
        msg.id === assistantMsgId ? { ...msg, isStreaming: false } : msg
      );
    }
  }

  function handleSelectRoom(room: RoomCard) {
    const today = new Date();
    const checkIn = new Date(today);
    checkIn.setDate(today.getDate() + 7);
    const checkOut = new Date(checkIn);
    checkOut.setDate(checkIn.getDate() + 2);

    const checkInStr = checkIn.toISOString().substring(0, 10);
    const checkOutStr = checkOut.toISOString().substring(0, 10);

    const prompt = `ช่วยจองห้อง ${room.name} (รหัสห้อง: ${room.id}) ในชื่อคุณ Palm สำหรับ 2 ท่าน ตั้งแต่วันที่ ${checkInStr} ถึง ${checkOutStr} ให้หน่อยครับ`;
    handleSendMessage(prompt);
  }

  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  }
</script>

<svelte:head>
  <title>Grand Azure Resort &amp; Residences — Executive Concierge</title>
</svelte:head>

<div class="app-layout">
  <Header />

  <main class="main-content">
    <div class="chat-card">
      <!-- Chat Sub-header -->
      <div class="chat-subhead">
        <div class="concierge-profile">
          <div class="concierge-avatar">✨</div>
          <div>
            <div class="concierge-name">Aura — Executive Concierge</div>
            <div class="concierge-role">Grand Azure Virtual Butler Service</div>
          </div>
        </div>
        <div class="session-badge">
          Desk: <span>VIP Service</span>
        </div>
      </div>

      <!-- Messages Stream -->
      <div class="messages-container" bind:this={messagesContainer}>
        {#each messages as message (message.id)}
          <ChatMessage {message} onSelectRoom={handleSelectRoom} />
        {/each}
      </div>

      <!-- Quick Action Chips -->
      <QuickChips onSelect={(prompt) => handleSendMessage(prompt)} />

      <!-- Input Bar -->
      <div class="input-bar-container">
        <div class="input-wrapper">
          <input
            type="text"
            class="chat-input"
            placeholder="พิมพ์ข้อความสอบถามห้องว่าง นโยบาย หรือสั่งจองห้องพัก..."
            bind:value={inputText}
            onkeydown={handleKeyDown}
            disabled={isLoading}
          />
          <button
            class="btn-send"
            onclick={() => handleSendMessage()}
            disabled={isLoading || !inputText.trim()}
            aria-label="Send message"
          >
            {#if isLoading}
              <span class="loading-spinner"></span>
            {:else}
              ➔
            {/if}
          </button>
        </div>
      </div>
    </div>
  </main>
</div>

<style>
  .app-layout {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }

  .main-content {
    max-width: 1200px;
    width: 100%;
    margin: 0 auto;
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 20px;
  }

  .chat-card {
    background: var(--bg-surface);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-luxury);
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 720px;
    overflow: hidden;
  }

  .chat-subhead {
    padding: 16px 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(255, 255, 255, 0.02);
  }

  .concierge-profile {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .concierge-avatar {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    border: 1.5px solid var(--gold-primary);
    background: radial-gradient(circle, #2a3859 0%, #151c2c 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
  }

  .concierge-name {
    font-weight: 600;
    font-size: 15px;
    color: #fff;
  }

  .concierge-role {
    font-size: 12px;
    color: var(--gold-light);
    opacity: 0.85;
  }

  .session-badge {
    font-size: 12px;
    color: var(--text-muted);
  }

  .session-badge span {
    color: var(--gold-light);
    font-weight: 600;
  }

  .messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  .input-bar-container {
    padding: 16px 24px 20px;
    background: rgba(14, 19, 31, 0.95);
    border-top: 1px solid var(--border-subtle);
  }

  .input-wrapper {
    display: flex;
    align-items: center;
    background: rgba(25, 34, 54, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: var(--radius-md);
    padding: 6px 8px 6px 18px;
    transition: all 0.2s ease;
  }

  .input-wrapper:focus-within {
    border-color: var(--gold-primary);
    box-shadow: 0 0 16px rgba(212, 175, 55, 0.25);
  }

  .chat-input {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: #fff;
    font-size: 14.5px;
    font-family: inherit;
  }

  .chat-input::placeholder {
    color: var(--text-dim);
  }

  .btn-send {
    background: var(--gold-gradient);
    color: #090d16;
    border: none;
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 16px;
    font-weight: 700;
    transition: all 0.15s ease;
  }

  .btn-send:hover:not(:disabled) {
    transform: scale(1.05);
  }

  .btn-send:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .loading-spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(9, 13, 22, 0.3);
    border-top-color: #090d16;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  @media (max-width: 640px) {
    .main-content {
      padding: 10px;
    }
    .chat-card {
      min-height: calc(100vh - 92px);
      border-radius: var(--radius-md);
    }
    .messages-container {
      padding: 16px;
    }
    .input-bar-container {
      padding: 12px 16px 16px;
    }
  }
</style>
