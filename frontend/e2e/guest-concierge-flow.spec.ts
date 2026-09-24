import { test, expect } from '@playwright/test';

test.describe('E2E: Guest VIP Concierge Chat & Booking Flow', () => {
  test('should display luxury chat desk, send message, stream room cards, and display booking receipt', async ({ page }) => {
    // 1. Intercept /chat SSE streaming endpoint
    let chatCallCount = 0;
    await page.route('**/chat', async (route) => {
      chatCallCount++;

      if (chatCallCount === 1) {
        // First call: Room discovery
        const sseData = [
          `data: ${JSON.stringify({ event: 'token', token: 'ยินดีอย่างยิ่งค่ะ ' })}\n\n`,
          `data: ${JSON.stringify({ event: 'token', token: 'พบห้องพักว่างพร้อมให้บริการดังนี้ค่ะ:' })}\n\n`,
          `data: ${JSON.stringify({
            event: 'room_cards',
            data: [
              {
                id: 1,
                name: 'Deluxe Ocean King',
                type: 'Deluxe King',
                pricePerNight: 6500,
                capacity: 2,
                description: 'Spacious ocean-view room with king bed and private balcony.',
                amenities: 'King Bed, Ocean View, Free Breakfast, High-Speed WiFi',
                isAvailable: true
              }
            ]
          })}\n\n`,
          `data: ${JSON.stringify({ event: 'done', thread_id: 'test-thread', intent: 'room_availability' })}\n\n`
        ].join('');

        await route.fulfill({
          status: 200,
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            Connection: 'keep-alive'
          },
          body: sseData
        });
      } else {
        // Second call: Booking confirmation triggered by clicking "จองห้องนี้ทันที"
        const sseData = [
          `data: ${JSON.stringify({ event: 'token', token: 'ทำการสำรองห้องพักเรียบร้อยแล้วค่ะ ' })}\n\n`,
          `data: ${JSON.stringify({
            event: 'booking_confirmation',
            data: {
              id: 101,
              customerName: 'Khun Palm',
              checkInDate: '2026-10-01T00:00:00Z',
              checkOutDate: '2026-10-03T00:00:00Z',
              roomId: 1,
              roomName: 'Deluxe Ocean King',
              roomType: 'Deluxe King',
              pax: 2,
              totalPrice: 13000,
              totalNights: 2,
              status: 'Confirmed',
              createdAt: '2026-09-24T12:00:00Z'
            }
          })}\n\n`,
          `data: ${JSON.stringify({ event: 'done', thread_id: 'test-thread', intent: 'create_booking' })}\n\n`
        ].join('');

        await route.fulfill({
          status: 200,
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            Connection: 'keep-alive'
          },
          body: sseData
        });
      }
    });

    // 2. Visit Chat Desk
    await page.goto('/');

    // 3. Verify Header and Welcome Assistant message
    await expect(page.locator('body')).toContainText('Grand Azure Resort & Residences');
    await expect(page.locator('body')).toContainText('ยินดีต้อนรับสู่ Grand Azure Resort & Residences');

    // 4. Send a room discovery message
    const chatInput = page.locator('input.chat-input');
    await chatInput.fill('ช่วยตรวจสอบห้องว่าง Deluxe วันที่ 1-4 เดือนหน้าให้หน่อยครับ');
    
    // Click send button
    const sendBtn = page.locator('button.btn-send');
    await expect(sendBtn).toBeEnabled();
    await sendBtn.click();

    // 5. Verify streamed text and Room Card appears
    await expect(page.locator('body')).toContainText('Deluxe Ocean King');
    await expect(page.locator('body')).toContainText('฿6,500');
    await expect(page.locator('body')).toContainText('มีห้องว่างพร้อมจอง');

    // 6. Click "จองห้องนี้ทันที" on the Room Card (this directly invokes handleSelectRoom)
    const bookBtn = page.getByRole('button', { name: 'จองห้องนี้ทันที' }).first();
    await bookBtn.click();

    // 7. Verify Golden Booking Confirmation Card
    await expect(page.locator('body')).toContainText('RESERVATION CONFIRMED');
    await expect(page.locator('body')).toContainText('GA-00101');
    await expect(page.locator('body')).toContainText('Khun Palm');
    await expect(page.locator('body')).toContainText('฿13,000');
  });
});
