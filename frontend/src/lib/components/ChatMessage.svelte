<script lang="ts">
  import type { Message, RoomCard } from '$lib/types/chat';
  import RoomCardItem from './RoomCardItem.svelte';
  import BookingConfirmationCard from './BookingConfirmationCard.svelte';

  let { message, onSelectRoom }: { message: Message; onSelectRoom: (room: RoomCard) => void } = $props();

  const isAssistant = $derived(message.role === 'assistant');
</script>

<div class="msg-row" class:ai={isAssistant} class:user={!isAssistant}>
  <div class="msg-avatar" class:ai={isAssistant} class:user={!isAssistant}>
    {isAssistant ? 'A' : 'P'}
  </div>

  <div class="msg-bubble-wrapper">
    <div class="msg-bubble">
      <div class="msg-text">
        {message.content}
        {#if message.isStreaming}
          <span class="typing-cursor"></span>
        {/if}
      </div>

      {#if message.roomCards && message.roomCards.length > 0}
        <div class="room-cards-grid">
          {#each message.roomCards as room (room.id)}
            <RoomCardItem {room} onSelect={onSelectRoom} />
          {/each}
        </div>
      {/if}

      {#if message.bookingData}
        <BookingConfirmationCard booking={message.bookingData} />
      {/if}
    </div>
    <div class="msg-timestamp">{message.timestamp}</div>
  </div>
</div>

<style>
  .msg-row {
    display: flex;
    gap: 14px;
    max-width: 85%;
    animation: fadeIn 0.25s ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .msg-row.user {
    align-self: flex-end;
    flex-direction: row-reverse;
  }

  .msg-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 700;
  }

  .msg-avatar.ai {
    background: var(--gold-gradient);
    color: #090D16;
    box-shadow: 0 2px 10px rgba(212, 175, 55, 0.3);
    font-family: 'Cinzel', serif;
  }

  .msg-avatar.user {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
    color: #FFF;
  }

  .msg-bubble-wrapper {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .msg-row.user .msg-bubble-wrapper {
    align-items: flex-end;
  }

  .msg-bubble {
    padding: 16px 20px;
    border-radius: var(--radius-md);
    font-size: 14.5px;
    line-height: 1.6;
    position: relative;
    max-width: 100%;
    word-break: break-word;
  }

  .msg-row.ai .msg-bubble {
    background: var(--bubble-ai);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-top-left-radius: 4px;
    color: #E2E8F0;
  }

  .msg-row.user .msg-bubble {
    background: var(--bubble-user);
    border: 1px solid rgba(212, 175, 55, 0.2);
    border-top-right-radius: 4px;
    color: #FFFFFF;
  }

  .msg-text {
    white-space: pre-wrap;
  }

  .typing-cursor {
    display: inline-block;
    width: 6px;
    height: 15px;
    background: var(--gold-primary);
    margin-left: 4px;
    vertical-align: middle;
    animation: blink 0.9s infinite;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }

  .room-cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 14px;
    margin-top: 14px;
  }

  .msg-timestamp {
    font-size: 11px;
    color: var(--text-dim);
    padding: 0 4px;
  }

  @media (max-width: 640px) {
    .msg-row {
      max-width: 95%;
    }
    .room-cards-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
