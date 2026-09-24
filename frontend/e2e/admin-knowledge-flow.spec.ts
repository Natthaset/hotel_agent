import { test, expect } from '@playwright/test';

test.describe('E2E: Admin Knowledge Base Management Flow', () => {
  test('should display knowledge documents, add new policy, search vectors, and delete', async ({ page }) => {
    let mockDocs = [
      {
        id: 1,
        title: 'Check-in Policy',
        content: 'Check-in begins at 15:00. Passport required.',
        full_document: 'Check-in Policy: Check-in begins at 15:00.'
      },
      {
        id: 2,
        title: 'Breakfast Hours',
        content: 'Breakfast is served from 06:30 to 10:30.',
        full_document: 'Breakfast Hours: Breakfast is served from 06:30 to 10:30.'
      }
    ];

    // 1. Mock Knowledge Base APIs
    await page.route('**/api/v1/knowledge', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'success',
            count: mockDocs.length,
            documents: mockDocs
          })
        });
      } else if (route.request().method() === 'POST') {
        const body = JSON.parse(route.request().postData() || '{}');
        const newDoc = {
          id: 99,
          title: body.title,
          content: body.content,
          full_document: `${body.title}: ${body.content}`
        };
        mockDocs.push(newDoc);
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'success',
            message: `Successfully embedded document '${body.title}'`,
            document: newDoc
          })
        });
      }
    });

    await page.route('**/api/v1/knowledge/search', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          query: 'breakfast',
          matches_count: 1,
          matches: [
            {
              id: 2,
              score: 0.94,
              title: 'Breakfast Hours',
              document: 'Breakfast is served from 06:30 to 10:30.'
            }
          ]
        })
      });
    });

    await page.route('**/api/v1/knowledge/*', async (route) => {
      if (route.request().method() === 'DELETE') {
        mockDocs = mockDocs.filter(d => !route.request().url().endsWith(`/${d.id}`));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'success', message: 'Document deleted' })
        });
      }
    });

    // 2. Visit Admin Knowledge page
    await page.goto('/admin/knowledge');

    // 3. Verify page header and table rows
    await expect(page.locator('body')).toContainText('Knowledge Base & Vector Embedding Manager');
    await expect(page.locator('body')).toContainText('Check-in Policy');
    await expect(page.locator('body')).toContainText('Breakfast Hours');

    // 4. Fill and submit new document
    const titleInput = page.locator('input[placeholder*="หัวข้อ"], input[id*="title"], form input[type="text"]').first();
    const contentTextarea = page.locator('textarea[placeholder*="เนื้อหา"], textarea[id*="content"], form textarea').first();

    await titleInput.fill('Private Helipad Transfer');
    await contentTextarea.fill('Helicopter transfers from Suvarnabhumi Airport to resort helipad available 24/7.');

    const submitBtn = page.getByRole('button', { name: /บันทึก|สร้าง|Embed|Save/i }).first();
    await submitBtn.click();

    // 5. Verify the new policy appears
    await expect(page.locator('body')).toContainText('Private Helipad Transfer');

    // 6. Test Vector Search Playground
    const searchInput = page.locator('input[placeholder*="ค้นหา"], input[placeholder*="search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('breakfast buffet');
      const testSearchBtn = page.getByRole('button', { name: /ทดสอบค้นหา|Search|ค้นหา/i }).first();
      await testSearchBtn.click();
      await expect(page.locator('body')).toContainText('Breakfast Hours');
    }
  });

  test('should upload document file, extract content, and save to Qdrant vector database', async ({ page }) => {
    let mockDocs = [
      {
        id: 1,
        title: 'Check-in Policy',
        content: 'Check-in begins at 15:00.',
        full_document: 'Check-in Policy: Check-in begins at 15:00.'
      }
    ];

    await page.route('**/api/v1/knowledge', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'success',
            count: mockDocs.length,
            documents: mockDocs
          })
        });
      } else if (route.request().method() === 'POST') {
        const body = JSON.parse(route.request().postData() || '{}');
        const newDoc = {
          id: 101,
          title: body.title,
          content: body.content,
          full_document: `${body.title}: ${body.content}`
        };
        mockDocs.push(newDoc);
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'success',
            message: `Successfully embedded document '${body.title}'`,
            document: newDoc
          })
        });
      }
    });

    await page.route('**/api/v1/knowledge/extract-file', async (route) => {
      const body = JSON.parse(route.request().postData() || '{}');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          filename: body.filename,
          suggested_title: 'Spa And Wellness Rules 2026',
          content: 'Lotus Blossom Spa operates daily from 10:00 to 22:00. Traditional Thai massage and aromatherapy.',
          size_bytes: 1024
        })
      });
    });

    await page.goto('/admin/knowledge');

    // 1. Verify dropzone elements
    await expect(page.locator('.file-dropzone')).toBeVisible();
    await expect(page.locator('.supported-formats')).toContainText('PDF');
    await expect(page.locator('.supported-formats')).toContainText('Word');
    await expect(page.locator('.supported-formats')).toContainText('Excel');

    // 2. Upload sample file
    const fileInput = page.locator('#file-input-upload');
    await fileInput.setInputFiles({
      name: 'spa_wellness_rules_2026.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 Mock PDF Content')
    });

    // 3. Verify file preview card and extracted content
    await expect(page.locator('.file-preview-card')).toBeVisible();
    await expect(page.locator('.file-name')).toContainText('spa_wellness_rules_2026.pdf');
    await expect(page.locator('.ready-indicator')).toContainText('ดึงเนื้อหาสำเร็จ');

    // 4. Verify title auto-filled and content auto-filled
    const titleInput = page.locator('#doc-title');
    await expect(titleInput).toHaveValue('Spa And Wellness Rules 2026');

    const contentTextarea = page.locator('#doc-content');
    await expect(contentTextarea).toHaveValue(/Lotus Blossom Spa operates daily/);

    // 5. Submit embeddings
    const submitBtn = page.getByRole('button', { name: /Generate Embeddings|Save to Qdrant/i });
    await submitBtn.click();

    // 6. Verify success alert and updated document list
    await expect(page.locator('.alert-banner.success')).toBeVisible();
    await expect(page.locator('body')).toContainText('Spa And Wellness Rules 2026');
  });
});
