<script lang="ts">
  let { onSelect }: { onSelect: (text: string) => void } = $props();

  const chips = [
    { label: '🕒 เวลาเช็คอิน & เช็คเอาต์', query: 'เวลาเช็คอินและเช็คเอาต์ของโรงแรมกี่โมง มีบริการ Early check-in ไหมครับ?' },
    { label: '🛏️ ตรวจสอบห้องว่างสัปดาห์นี้', query: 'ช่วยตรวจสอบห้องพักว่างสำหรับ 2 ท่าน ในสุดสัปดาห์นี้ให้หน่อยครับ' },
    { label: '🍽️ อาหารเช้า & บุฟเฟต์', query: 'อาหารเช้าให้บริการกี่โมง มีเมนูอะไรบ้าง รวมอยู่ในค่าห้องไหมครับ?' },
    { label: '🐾 นโยบายสัตว์เลี้ยง', query: 'โรงแรมอนุญาตให้นำสัตว์เลี้ยงเข้าพักได้ไหม และมีเงื่อนไขอย่างไรบ้างครับ?' },
    { label: '🚗 รถรับ-ส่งสนามบิน', query: 'มีบริการรถรับส่งสนามบินไหม ค่าบริการเท่าไหร่ครับ?' },
    { label: '❌ นโยบายการยกเลิกการจอง', query: 'นโยบายการยกเลิกห้องพักเป็นอย่างไร ต้องแจ้งล่วงหน้ากี่ชั่วโมงครับ?' },
  ];
</script>

<div class="chips-container">
  <div class="chips-scroll">
    {#each chips as chip}
      <button class="chip-btn" onclick={() => onSelect(chip.query)}>
        {chip.label}
      </button>
    {/each}
  </div>
</div>

<style>
  .chips-container {
    padding: 8px 24px 14px;
    background: transparent;
  }

  .chips-scroll {
    display: flex;
    gap: 10px;
    overflow-x: auto;
    scrollbar-width: none;
    -ms-overflow-style: none;
    padding-bottom: 2px;
  }

  .chips-scroll::-webkit-scrollbar {
    display: none;
  }

  .chip-btn {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-muted);
    padding: 7px 15px;
    border-radius: 999px;
    font-size: 12.5px;
    white-space: nowrap;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s ease;
    font-family: inherit;
  }

  .chip-btn:hover {
    background: rgba(212, 175, 55, 0.12);
    border-color: var(--border-glow);
    color: var(--gold-light);
    transform: translateY(-1px);
  }

  @media (max-width: 640px) {
    .chips-container {
      padding: 6px 16px 10px;
    }
  }
</style>
