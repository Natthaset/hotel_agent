<script lang="ts">
  import type { RoomCard } from '$lib/types/chat';

  let { room, onSelect }: { room: RoomCard; onSelect: (r: RoomCard) => void } = $props();

  const formattedPrice = $derived(
    new Intl.NumberFormat('th-TH', { style: 'currency', currency: 'THB', maximumFractionDigits: 0 }).format(room.pricePerNight)
  );

  const amenitiesList = $derived(
    room.amenities ? room.amenities.split(',').map((a) => a.trim()).slice(0, 3) : []
  );
</script>

<div class="room-card">
  <div class="room-card-header">
    <div class="room-info-top">
      <h4 class="room-name">{room.name}</h4>
      <div class="room-availability-tag">
        <span class="status-dot"></span> มีห้องว่างพร้อมจอง
      </div>
    </div>
    <div class="room-price-box">
      <div class="price-value">{formattedPrice}</div>
      <div class="price-unit">/ คืน (สำหรับ {room.capacity} ท่าน)</div>
    </div>
  </div>

  <p class="room-desc">{room.description}</p>

  {#if amenitiesList.length > 0}
    <div class="room-amenities">
      {#each amenitiesList as amenity}
        <span class="amenity-pill">✦ {amenity}</span>
      {/each}
    </div>
  {/if}

  <div class="room-card-footer">
    <button class="btn-book" onclick={() => onSelect(room)}>
      จองห้องนี้ทันที
    </button>
  </div>
</div>

<style>
  .room-card {
    background: rgba(15, 21, 35, 0.92);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    overflow: hidden;
    transition: all 0.25s ease;
    display: flex;
    flex-direction: column;
    margin-top: 6px;
  }

  .room-card:hover {
    border-color: var(--gold-primary);
    transform: translateY(-2px);
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.6), 0 0 15px rgba(212, 175, 55, 0.15);
  }

  .room-card-header {
    padding: 14px 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
  }

  .room-name {
    font-family: 'Cinzel', serif;
    font-size: 15px;
    font-weight: 700;
    color: var(--gold-light);
    line-height: 1.3;
  }

  .room-availability-tag {
    font-size: 11px;
    color: #10B981;
    margin-top: 4px;
    display: flex;
    align-items: center;
    gap: 5px;
    font-weight: 500;
  }

  .status-dot {
    width: 6px;
    height: 6px;
    background: #10B981;
    border-radius: 50%;
  }

  .room-price-box {
    text-align: right;
    flex-shrink: 0;
  }

  .price-value {
    font-size: 16px;
    font-weight: 700;
    color: #FFF;
  }

  .price-unit {
    font-size: 11px;
    color: var(--text-muted);
  }

  .room-desc {
    padding: 10px 16px 6px;
    font-size: 12.5px;
    color: var(--text-muted);
    line-height: 1.5;
  }

  .room-amenities {
    padding: 6px 16px 12px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .amenity-pill {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #CBD5E1;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
  }

  .room-card-footer {
    padding: 10px 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    background: rgba(255, 255, 255, 0.02);
    margin-top: auto;
  }

  .btn-book {
    width: 100%;
    background: var(--gold-gradient);
    color: #090D16;
    border: none;
    padding: 9px 0;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: opacity 0.2s ease, transform 0.1s ease;
    letter-spacing: 0.5px;
  }

  .btn-book:hover {
    opacity: 0.92;
    transform: translateY(-1px);
  }
</style>
