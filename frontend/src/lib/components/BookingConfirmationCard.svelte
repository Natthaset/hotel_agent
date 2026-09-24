<script lang="ts">
  import type { BookingData } from '$lib/types/chat';

  let { booking }: { booking: BookingData } = $props();

  const formattedTotal = $derived(
    new Intl.NumberFormat('th-TH', { style: 'currency', currency: 'THB', maximumFractionDigits: 0 }).format(booking.totalPrice)
  );

  const checkInFormatted = $derived(booking.checkInDate ? booking.checkInDate.substring(0, 10) : '');
  const checkOutFormatted = $derived(booking.checkOutDate ? booking.checkOutDate.substring(0, 10) : '');
  const refCode = $derived(`GA-${String(booking.id).padStart(5, '0')}`);
</script>

<div class="booking-receipt-card">
  <div class="receipt-header">
    <div class="receipt-badge">
      <span class="seal-icon">🏆</span> RESERVATION CONFIRMED
    </div>
    <div class="receipt-code">{refCode}</div>
  </div>

  <div class="receipt-body">
    <div class="receipt-row">
      <span class="label">ชื่อผู้เข้าพัก:</span>
      <span class="value guest-name">{booking.customerName}</span>
    </div>
    <div class="receipt-row">
      <span class="label">ห้องพัก:</span>
      <span class="value room-name">{booking.roomName} ({booking.roomType})</span>
    </div>
    <div class="receipt-row">
      <span class="label">กำหนดการ:</span>
      <span class="value">{checkInFormatted} — {checkOutFormatted} ({booking.totalNights} คืน)</span>
    </div>
    <div class="receipt-row">
      <span class="label">ผู้เข้าพัก:</span>
      <span class="value">{booking.pax} ท่าน</span>
    </div>
    <div class="receipt-divider"></div>
    <div class="receipt-row total-row">
      <span class="label-total">ยอดชำระสุทธิ:</span>
      <span class="value-total">{formattedTotal}</span>
    </div>
  </div>

  <div class="receipt-footer">
    <span>✦ สถานะ: ได้รับการยืนยันในระบบเรียบร้อยแล้ว</span>
  </div>
</div>

<style>
  .booking-receipt-card {
    background: linear-gradient(135deg, rgba(20, 28, 48, 0.95) 0%, rgba(14, 19, 31, 0.98) 100%);
    border: 1px solid var(--gold-primary);
    border-radius: var(--radius-sm);
    box-shadow: 0 10px 30px rgba(212, 175, 55, 0.15);
    margin-top: 12px;
    overflow: hidden;
  }

  .receipt-header {
    background: rgba(212, 175, 55, 0.1);
    border-bottom: 1px solid rgba(212, 175, 55, 0.25);
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .receipt-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11.5px;
    font-weight: 700;
    color: var(--gold-light);
    letter-spacing: 1px;
  }

  .seal-icon {
    font-size: 14px;
  }

  .receipt-code {
    font-family: monospace;
    font-size: 12px;
    color: var(--gold-primary);
    font-weight: 700;
  }

  .receipt-body {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 13px;
  }

  .receipt-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .label {
    color: var(--text-muted);
  }

  .value {
    color: #FFF;
    font-weight: 500;
  }

  .guest-name {
    color: var(--gold-light);
    font-weight: 600;
  }

  .room-name {
    font-family: 'Cinzel', serif;
    font-size: 13.5px;
  }

  .receipt-divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.08);
    margin: 6px 0;
  }

  .total-row {
    align-items: baseline;
  }

  .label-total {
    font-size: 13.5px;
    color: var(--gold-light);
    font-weight: 600;
  }

  .value-total {
    font-size: 17px;
    font-weight: 700;
    color: #10B981;
  }

  .receipt-footer {
    padding: 8px 16px;
    background: rgba(16, 185, 129, 0.08);
    border-top: 1px solid rgba(16, 185, 129, 0.2);
    font-size: 11.5px;
    color: #34D399;
    text-align: center;
  }
</style>
