<script lang="ts">
  import { onMount } from 'svelte';
  import Header from '$lib/components/Header.svelte';

  interface KnowledgeDoc {
    id: number;
    title: string;
    content: string;
    full_document: string;
  }

  interface SearchMatch {
    id: number;
    score: number;
    title: string;
    document: string;
  }

  let documents = $state<KnowledgeDoc[]>([]);
  let isLoadingDocs = $state(true);
  let isSubmitting = $state(false);
  let isReindexing = $state(false);
  let statusMessage = $state<{ type: 'success' | 'error'; text: string } | null>(null);

  // Popup Alert Modal State
  let popupAlert = $state<{
    visible: boolean;
    type: 'success' | 'error' | 'info';
    title: string;
    message: string;
    docTitle: string;
  }>({
    visible: false,
    type: 'success',
    title: '',
    message: '',
    docTitle: ''
  });

  function closePopup() {
    popupAlert.visible = false;
  }

  // New Document Form & File Upload State
  let docTitle = $state('');
  let docContent = $state('');
  let uploadedFile = $state<File | null>(null);
  let isExtractingFile = $state(false);
  let isDragging = $state(false);
  let fileError = $state<string | null>(null);
  let fileInputRef = $state<HTMLInputElement | null>(null);

  function getFileIcon(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'pdf': return '📄';
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'webp': return '🖼️';
      case 'docx':
      case 'doc': return '📝';
      case 'xlsx':
      case 'xls': return '📊';
      case 'csv':
      case 'tsv': return '📑';
      default: return '📃';
    }
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  async function handleFileSelected(file: File) {
    if (!file) return;
    uploadedFile = file;
    isExtractingFile = true;
    fileError = null;

    try {
      const reader = new FileReader();
      const base64Promise = new Promise<string>((resolve, reject) => {
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = () => reject(new Error('ไม่สามารถอ่านไฟล์ได้'));
      });
      reader.readAsDataURL(file);
      const base64Data = await base64Promise;

      const res = await fetch(`${getAiApiUrl()}/api/v1/knowledge/extract-file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          file_base64: base64Data
        })
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      docContent = data.content || '';
      if (!docTitle.trim() && data.suggested_title) {
        docTitle = data.suggested_title;
      }
    } catch (err: any) {
      console.error('File extraction failed:', err);
      fileError = `เกิดข้อผิดพลาดในการดึงข้อมูลจากไฟล์: ${err.message || err}`;
      if (file.type.startsWith('text/') || file.name.endsWith('.txt') || file.name.endsWith('.csv') || file.name.endsWith('.md')) {
        const textReader = new FileReader();
        textReader.onload = () => {
          docContent = (textReader.result as string) || '';
          if (!docTitle.trim()) {
            docTitle = file.name.replace(/\.[^/.]+$/, '').replace(/[-_.]+/g, ' ');
          }
          fileError = null;
        };
        textReader.readAsText(file);
      }
    } finally {
      isExtractingFile = false;
    }
  }

  function handleFileInputChange(e: Event) {
    const target = e.target as HTMLInputElement;
    if (target.files && target.files[0]) {
      handleFileSelected(target.files[0]);
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    isDragging = false;
    if (e.dataTransfer?.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    isDragging = true;
  }

  function handleDragLeave(e: DragEvent) {
    e.preventDefault();
    isDragging = false;
  }

  function handleRemoveFile() {
    uploadedFile = null;
    docContent = '';
    fileError = null;
    if (fileInputRef) {
      fileInputRef.value = '';
    }
  }

  // Vector Search Playground
  let searchQuery = $state('');
  let searchTopK = $state(3);
  let isSearching = $state(false);
  let searchResults = $state<SearchMatch[]>([]);

  function getAiApiUrl(): string {
    return typeof window !== 'undefined' && (window as any).PUBLIC_AI_API_URL
      ? (window as any).PUBLIC_AI_API_URL
      : 'http://localhost:8000';
  }

  async function fetchDocuments() {
    isLoadingDocs = true;
    try {
      const res = await fetch(`${getAiApiUrl()}/api/v1/knowledge`);
      if (res.ok) {
        const data = await res.json();
        documents = data.documents || [];
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (err) {
      console.error('Failed to load knowledge documents:', err);
    } finally {
      isLoadingDocs = false;
    }
  }

  async function handleAddDocument(e: SubmitEvent) {
    e.preventDefault();
    if (isSubmitting || isExtractingFile || !docTitle.trim() || !docContent.trim()) return;

    const targetTitle = docTitle.trim();
    const targetContent = docContent.trim();

    isSubmitting = true;
    statusMessage = null;

    try {
      const res = await fetch(`${getAiApiUrl()}/api/v1/knowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: targetTitle,
          content: targetContent
        })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const successText = `สร้าง Embedding และบันทึกลง Qdrant สำเร็จ: "${targetTitle}"`;
      statusMessage = {
        type: 'success',
        text: successText
      };

      popupAlert = {
        visible: true,
        type: 'success',
        title: 'สร้างเวกเตอร์และบันทึกสำเร็จ',
        message: successText,
        docTitle: targetTitle
      };

      docTitle = '';
      docContent = '';
      uploadedFile = null;
      fileError = null;
      if (fileInputRef) fileInputRef.value = '';
      await fetchDocuments();
    } catch (err: any) {
      statusMessage = {
        type: 'error',
        text: `เกิดข้อผิดพลาดในการทำ Embedding: ${err.message || err}`
      };
      popupAlert = {
        visible: true,
        type: 'error',
        title: 'เกิดข้อผิดพลาดในการบันทึก',
        message: `เกิดข้อผิดพลาดในการทำ Embedding: ${err.message || err}`,
        docTitle: targetTitle
      };
    } finally {
      isSubmitting = false;
    }
  }

  async function handleDeleteDocument(docId: number) {
    if (!confirm(`ยืนยันการลบ Vector Point ID ${docId} ออกจาก Qdrant หรือไม่?`)) return;

    try {
      const res = await fetch(`${getAiApiUrl()}/api/v1/knowledge/${docId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        statusMessage = { type: 'success', text: `ลบเอกสาร ID ${docId} สำเร็จ` };
        await fetchDocuments();
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (err: any) {
      statusMessage = { type: 'error', text: `ลบไม่สำเร็จ: ${err.message}` };
    }
  }

  async function handleReindexDefaults() {
    if (!confirm('ยืนยันการ Reset และทำ Embedding นโยบายเริ่มต้นทั้งหมดใหม่หรือไม่?')) return;

    isReindexing = true;
    statusMessage = null;
    try {
      const res = await fetch(`${getAiApiUrl()}/api/v1/knowledge/reindex`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        statusMessage = { type: 'success', text: data.message };
        await fetchDocuments();
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (err: any) {
      statusMessage = { type: 'error', text: `Re-index ไม่สำเร็จ: ${err.message}` };
    } finally {
      isReindexing = false;
    }
  }

  async function handleTestSearch() {
    if (!searchQuery.trim() || isSearching) return;

    isSearching = true;
    try {
      const res = await fetch(`${getAiApiUrl()}/api/v1/knowledge/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery.trim(),
          top_k: searchTopK
        })
      });

      if (res.ok) {
        const data = await res.json();
        searchResults = data.matches || [];
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (err: any) {
      console.error('Test search failed:', err);
    } finally {
      isSearching = false;
    }
  }

  onMount(() => {
    fetchDocuments();
  });
</script>

<svelte:head>
  <title>Knowledge &amp; Vector Embedding Manager — Grand Azure</title>
</svelte:head>

<div class="page-container">
  <Header />

  <main class="content-wrapper">
    <!-- Top Title & Stats Bar -->
    <div class="page-head">
      <div>
        <h1 class="page-title">Knowledge Base &amp; Vector Embedding Manager</h1>
        <p class="page-sub">
          จัดการเอกสารนโยบายโรงแรม สั่งประมวลผล Vector Embeddings (FastEmbed ONNX) และตรวจสอบข้อมูลใน Qdrant
        </p>
      </div>

      <div class="actions-group">
        <button class="btn-secondary" onclick={fetchDocuments} disabled={isLoadingDocs}>
          🔄 Refresh
        </button>
        <button class="btn-gold" onclick={handleReindexDefaults} disabled={isReindexing}>
          {isReindexing ? 'กำลัง Re-index...' : '⚡ Re-index Defaults'}
        </button>
      </div>
    </div>

    <!-- Alert Banner -->
    {#if statusMessage}
      <div class="alert-banner" class:success={statusMessage.type === 'success'} class:error={statusMessage.type === 'error'}>
        {statusMessage.text}
      </div>
    {/if}

    <!-- Stats Cards Row -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Total Embedded Documents</div>
        <div class="stat-val">{documents.length}</div>
        <div class="stat-sub">Vectors active in Qdrant collection</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Vector Database Engine</div>
        <div class="stat-val highlight">Qdrant DB</div>
        <div class="stat-sub">Port 6333 (Collection: hotel_policies)</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Embedding Model</div>
        <div class="stat-val highlight">BAAI/bge-small-en-v1.5</div>
        <div class="stat-sub">Quantized ONNX Runtime (Zero GPU Overhead)</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Hardware Optimization</div>
        <div class="stat-val">100% VRAM Free</div>
        <div class="stat-sub">All VRAM reserved for Qwen2.5 7B Chat</div>
      </div>
    </div>

    <!-- 2-Column Section: Left Form / Right Playground -->
    <div class="workbench-grid">
      <!-- Left: Create & Embed Form with File Upload -->
      <section class="panel-card">
        <h2 class="panel-title">
          <span>✦</span> เพิ่มเอกสารใหม่และสั่งทำ Vector Embedding
        </h2>
        <p class="panel-desc">
          อัปโหลดไฟล์นโยบาย (PDF, Image, Word, Text, Excel, CSV) เพื่อดึงเนื้อหา สั่งแปลงเป็น Vector Embedding และบันทึกลงใน Qdrant ทันที
        </p>

        <form class="embed-form" onsubmit={handleAddDocument}>
          <!-- File Upload Zone -->
          <div class="form-group">
            <span class="form-label">อัปโหลดไฟล์เอกสาร (Upload Document File):</span>
            
            <input
              type="file"
              id="file-input-upload"
              class="hidden-file-input"
              bind:this={fileInputRef}
              onchange={handleFileInputChange}
              accept=".pdf,.png,.jpg,.jpeg,.webp,.docx,.doc,.xlsx,.xls,.csv,.tsv,.txt,.md,.json"
            />

            {#if !uploadedFile}
              <!-- Drag and Drop Dropzone -->
              <div
                class="file-dropzone"
                class:dragging={isDragging}
                ondragover={handleDragOver}
                ondragleave={handleDragLeave}
                ondrop={handleDrop}
                onclick={() => fileInputRef?.click()}
                onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && fileInputRef?.click()}
                role="button"
                tabindex="0"
              >
                <div class="dropzone-icon">☁️ ⬆️</div>
                <div class="dropzone-title">ลากไฟล์มาวางที่นี่ หรือ <span class="highlight-link">คลิกเพื่อเลือกไฟล์</span></div>
                <div class="dropzone-sub">รองรับไฟล์หลากหลายรูปแบบสำหรับการทำ Vector Knowledge Base</div>
                
                <div class="supported-formats">
                  <span class="format-badge pdf">📄 PDF</span>
                  <span class="format-badge img">🖼️ Image</span>
                  <span class="format-badge doc">📝 Word</span>
                  <span class="format-badge xls">📊 Excel</span>
                  <span class="format-badge csv">📑 CSV</span>
                  <span class="format-badge txt">📃 Text</span>
                </div>
              </div>
            {:else}
              <!-- Selected File Card & Status -->
              <div class="file-preview-card">
                <div class="file-info-row">
                  <div class="file-type-icon">{getFileIcon(uploadedFile.name)}</div>
                  <div class="file-details">
                    <div class="file-name" title={uploadedFile.name}>{uploadedFile.name}</div>
                    <div class="file-meta">
                      <span>{formatFileSize(uploadedFile.size)}</span>
                      {#if isExtractingFile}
                        <span class="extracting-indicator">⚡ กำลังสกัดเนื้อหาจากไฟล์...</span>
                      {:else}
                        <span class="ready-indicator">✓ ดึงเนื้อหาสำเร็จ</span>
                      {/if}
                    </div>
                  </div>
                  <button
                    type="button"
                    class="btn-remove-file"
                    onclick={handleRemoveFile}
                    title="ลบไฟล์และเลือกใหม่"
                  >
                    ✕ นำออก
                  </button>
                </div>

                {#if fileError}
                  <div class="file-error-msg">⚠️ {fileError}</div>
                {/if}
              </div>
            {/if}
          </div>

          <div class="preset-pill-row">
            <span class="preset-label">ตัวอย่างด่วน:</span>
            <button
              type="button"
              class="preset-chip"
              onclick={() => {
                docTitle = 'ราคาสปา';
                docContent = 'โรงแรม Grand Azure Resort & Residences\nระเบียบการใช้บริการ Lotus Blossom Luxury Wellness Spa 2569\nศูนย์ดูแลสุขภาพและสปาเพื่อการผ่อนคลายระดับ 5 ดาว เปิดให้บริการทุกวัน ตั้งแต่เวลา 10:00 - 22:00 น. บริเวณชั้น 1 ติดสวนพฤกษศาสตร์\n\n1. รายการทรีตเมนต์และโปรแกรมฟื้นฟูสุขภาพยอดนิยม\n- ทรีตเมนต์ที่ 1: การนวดไทยราชสำนักโบราณ (90 นาที): ราคา 3,200 บาท ช่วยคลายกล้ามเนื้อและความเมื่อยล้า\n- ทรีตเมนต์ที่ 2: อโรมาเธอราพีด้วยหินภูเขาไฟร้อน (120 นาที): ราคา 4,500 บาท ใช้น้ำมันหอมระเหยออร์แกนิกเกรดพรีเมียม\n- ทรีตเมนต์ที่ 3: การแช่น้ำแข็งเพื่อฟื้นฟูสุขภาพ (Ice Plunge Bath) & ซาวน่าเกลือหิมาลายัน: บริการทรีตเมนต์ฟื้นฟูสุขภาพ (ฟรีสำหรับแขกห้อง Suite และ Villa / แขกทั่วไปสามารถสอบถามอัตราค่าบริการได้ที่เคาน์เตอร์สปา)\n\n2. เงื่อนไขและข้อแนะนำสำหรับการรับบริการ\n- กรุณาสำรองเวลาล่วงหน้าอย่างน้อย 2 ชั่วโมงผ่านแชต Concierge หรือโทรต่อเบอร์ภายใน #105\n- กรุณาเดินทางมาถึงก่อนเวลานัดหมาย 15 นาที เพื่อตรวจสุขภาพเบื้องต้นและดื่มเวลคัมดริงก์ชาเกสรบัว\n\nนโยบายการยกเลิก: สามารถยกเลิกหรือเปลี่ยนแปลงเวลาล่วงหน้าได้อย่างน้อย 2 ชั่วโมงโดยไม่มีค่าใช้จ่าย หากไม่มาตามนัด (No-show) จะมีค่าธรรมเนียม 50% ของราคาทรีตเมนต์';
              }}
            >
              🌸 เติมตัวอย่าง: ราคาสปา
            </button>
          </div>

          <div class="form-group">
            <label for="doc-title" class="form-label">หัวข้อเอกสาร (Policy Title):</label>
            <input
              id="doc-title"
              type="text"
              class="form-input"
              placeholder="เช่น ราคาสปา หรือ Early Check-in & Infinity Pool Rules"
              bind:value={docTitle}
              required
            />
          </div>

          <!-- Document Content Preview & Edit -->
          <div class="form-group">
            <div class="content-label-row">
              <label for="doc-content" class="form-label">เนื้อหารายละเอียดที่สกัดได้ (Document Content):</label>
              {#if docContent}
                <span class="char-count">สกัดได้ {docContent.length} ตัวอักษร (สามารถแก้ไขได้)</span>
              {/if}
            </div>
            <textarea
              id="doc-content"
              class="form-textarea"
              rows="5"
              placeholder={isExtractingFile ? 'กำลังดึงเนื้อหาจากไฟล์ที่อัปโหลด กรุณารอสักครู่...' : 'เนื้อหาข้อความที่ดึงมาจากไฟล์จะปรากฏที่นี่โดยอัตโนมัติ และคุณสามารถปรับแต่งข้อความเพิ่มเติมได้...'}
              bind:value={docContent}
              disabled={isExtractingFile}
              required
            ></textarea>
          </div>

          <button
            type="submit"
            class="btn-submit-embed"
            disabled={isSubmitting || isExtractingFile || !docTitle.trim() || !docContent.trim()}
          >
            {isSubmitting ? 'กำลังสร้าง Embedding & บันทึก...' : '✦ Generate Embeddings & Save to Qdrant'}
          </button>
        </form>
      </section>

      <!-- Right: Vector Similarity Search Playground -->
      <section class="panel-card">
        <h2 class="panel-title">
          <span>🔍</span> Vector Search Playground &amp; Semantic Inspector
        </h2>
        <p class="panel-desc">
          ทดสอบยิงคำถามตัวอย่างเพื่อดูว่า Vector Search ใน Qdrant จับคู่กับเอกสารใด พร้อมค่าคะแนน Similarity Score
        </p>

        <div class="playground-box">
          <div class="search-input-wrapper">
            <input
              type="text"
              class="form-input"
              placeholder="พิมพ์คำถามทดสอบ เช่น 'นำหมาเข้าพักได้ไหม', 'เวลาอาหารเช้า'..."
              bind:value={searchQuery}
              onkeydown={(e) => e.key === 'Enter' && handleTestSearch()}
            />
            <button class="btn-search" onclick={handleTestSearch} disabled={isSearching || !searchQuery.trim()}>
              {isSearching ? 'ค้นหา...' : 'Test Search'}
            </button>
          </div>

          {#if searchResults.length > 0}
            <div class="matches-list">
              <div class="matches-header">ผลลัพธ์การค้นหาด้วย Vector Similarity ({searchResults.length} รายการ):</div>
              {#each searchResults as match}
                <div class="match-item">
                  <div class="match-top">
                    <span class="match-title">{match.title}</span>
                    <span class="score-badge">Similarity: {(match.score * 100).toFixed(1)}% ({match.score})</span>
                  </div>
                  <div class="match-passage">{match.document}</div>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </section>
    </div>

    <!-- Guidance & Troubleshooting Card for Admin -->
    <section class="panel-card guide-panel">
      <div class="guide-header">
        <div class="guide-title-group">
          <span class="guide-icon">💡</span>
          <div>
            <h2 class="panel-title">หมายเหตุและแนวทางสำหรับ Admin: หาก AI ตอบข้อมูลไม่ครบถ้วน ควรแก้ไขอย่างไร?</h2>
            <p class="panel-desc">แนวทางการจัดโครงสร้างเอกสารนโยบายให้ระบบ AI และ RAG ดึงข้อมูลไปแจกแจงคำตอบได้อย่างครบถ้วน 100%</p>
          </div>
        </div>
      </div>

      <div class="guide-content-grid">
        <div class="guide-col">
          <h3 class="guide-subtitle">🔍 1. สาเหตุที่ทำให้ AI มักตอบตกหล่น</h3>
          <ul class="guide-list">
            <li><strong>ไม่มีลำดับข้อที่ชัดเจน:</strong> ข้อความเขียนเป็นย่อหน้ายาวติดกัน ทำให้โมเดลจัดกลุ่มรายการผิดพลาด</li>
            <li><strong>รูปแบบข้อมูลไม่สมมาตร:</strong> บางรายการระบุราคาตัวเลขชัดเจน แต่บางรายการระบุเป็น "ฟรี / สิทธิพิเศษ" ทำให้โมเดลจัดเป็นสิ่งอำนวยความสะดวก ไม่นับเป็นรายการบริการหลัก</li>
            <li><strong>คีย์เวิร์ดกำกวม:</strong> ไม่ระบุคำเรียกประเภท เช่น ใช้คำว่า "การแช่น้ำแข็ง" แทนที่จะระบุชัดเจนว่าเป็น "ทรีตเมนต์หรือบริการฟื้นฟูสุขภาพ"</li>
          </ul>

          <h3 class="guide-subtitle" style="margin-top: 18px;">🛠️ 2. ขั้นตอนการแก้ไขเมื่อ AI ตอบตกหล่น</h3>
          <ol class="guide-steps">
            <li><strong>ทดสอบใน Playground:</strong> พิมพ์คำถามในช่อง "Vector Search Playground" ด้านขวา เพื่อดูว่าระบบดึงเอกสารที่เกี่ยวข้องขึ้นมาด้วยคะแนน Similarity เท่าใด</li>
            <li><strong>จัดโครงสร้างใหม่:</strong> ปรับเนื้อหาในช่อง Document Content ให้มีลำดับข้อและไวยากรณ์ที่สม่ำเสมอกันทุกรายการ (ดูตัวอย่างฝั่งขวา)</li>
            <li><strong>บันทึกทับหรือลบสร้างใหม่:</strong> กดลบเอกสารเดิมในตารางด้านล่าง แล้วกดบันทึกสร้างเวกเตอร์ใหม่ลง Qdrant ทันที</li>
          </ol>
        </div>

        <div class="guide-col">
          <h3 class="guide-subtitle">📋 3. ตัวอย่างการเปรียบเทียบการจัดรูปแบบ (Before vs After)</h3>
          
          <div class="example-box bad">
            <div class="example-badge bad">❌ รูปแบบที่ไม่แนะนำ (เสี่ยงต่อการตอบตกหล่น)</div>
            <pre class="example-code">1. ทรีตเมนต์ยอดนิยม
การนวดไทยราชสำนัก (90 นาที): ราคา 3,200 บาท ช่วยคลายเมื่อย
อโรมาเธอราพีหินร้อน (120 นาที): ราคา 4,500 บาท
การแช่น้ำแข็ง Ice Plunge & ซาวน่า: ฟรีสำหรับแขกห้อง Suite
(AI อาจตอบแค่ 2 ข้อแรก เพราะเข้าใจว่าข้อ 3 เป็นเพียงเงื่อนไขสิทธิพิเศษ)</pre>
          </div>

          <div class="example-box good">
            <div class="example-badge good">✅ รูปแบบที่แนะนำ (AI ตอบครบถ้วน 100%)</div>
            <pre class="example-code">1. รายการทรีตเมนต์และโปรแกรมฟื้นฟูสุขภาพยอดนิยม
- ทรีตเมนต์ที่ 1: การนวดไทยราชสำนักโบราณ (90 นาที): ราคา 3,200 บาท
- ทรีตเมนต์ที่ 2: อโรมาเธอราพีด้วยหินภูเขาไฟร้อน (120 นาที): ราคา 4,500 บาท
- ทรีตเมนต์ที่ 3: การแช่น้ำแข็งเพื่อฟื้นฟูสุขภาพ (Ice Plunge Bath) & ซาวน่าเกลือหิมาลายัน: บริการฟื้นฟูสุขภาพ (ฟรีสำหรับแขกห้อง Suite / ทั่วไปติดต่อเคาน์เตอร์)</pre>
          </div>
        </div>
      </div>
    </section>

    <!-- Bottom: Currently Embedded Documents Browser -->
    <section class="panel-card list-panel">
      <div class="list-head">
        <div>
          <h2 class="panel-title"><span>📚</span> รายการเอกสารที่ฝังอยู่ใน Qdrant Collection ({documents.length})</h2>
          <p class="panel-desc">เอกสารความรู้ทั้งหมดที่โมเดล AI นำไปใช้อ้างอิงในการตอบคำถามลูกค้า</p>
        </div>
      </div>

      {#if isLoadingDocs}
        <div class="loading-state">กำลังเชื่อมต่อและโหลดข้อมูลจาก Qdrant Vector Engine...</div>
      {:else if documents.length === 0}
        <div class="empty-state">
          ยังไม่มีเอกสารในระบบ คลิกปุ่ม <strong>"Re-index Defaults"</strong> ด้านบนเพื่อโหลดข้อมูลนโยบายเริ่มต้น
        </div>
      {:else}
        <div class="doc-table-wrapper">
          <table class="doc-table">
            <thead>
              <tr>
                <th style="width: 80px;">ID</th>
                <th style="width: 280px;">ชื่อนโยบาย / หัวข้อ</th>
                <th>เนื้อหาเอกสาร (Vectorized Passage)</th>
                <th style="width: 100px; text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody>
              {#each documents as doc}
                <tr>
                  <td><span class="id-tag">#{doc.id}</span></td>
                  <td class="doc-title-cell">{doc.title}</td>
                  <td class="doc-content-cell">{doc.content || doc.full_document}</td>
                  <td style="text-align: right;">
                    <button class="btn-delete" onclick={() => handleDeleteDocument(doc.id)} title="ลบออกจาก Qdrant">
                      🗑️ ลบ
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>
  </main>

  <!-- Modal Popup Alert -->
  {#if popupAlert.visible}
    <div
      class="popup-alert-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="popup-title"
      onclick={(e) => { if (e.target === e.currentTarget) closePopup(); }}
      onkeydown={(e) => e.key === 'Escape' && closePopup()}
      tabindex="-1"
    >
      <div class="popup-alert-card" class:success={popupAlert.type === 'success'} class:error={popupAlert.type === 'error'}>
        <!-- Close Button (✕) -->
        <button
          type="button"
          class="popup-close-btn"
          onclick={closePopup}
          aria-label="ปิดหน้าต่างแจ้งเตือน"
        >
          ✕
        </button>

        <!-- Icon Aura -->
        <div class="popup-icon-container">
          {#if popupAlert.type === 'success'}
            <div class="popup-icon-pulse"></div>
            <div class="popup-icon-badge success">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
          {:else}
            <div class="popup-icon-badge error">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
            </div>
          {/if}
        </div>

        <!-- Meta Subtitle -->
        <div class="popup-kicker">
          <span>QDRANT VECTOR DATABASE</span>
          <span class="dot-separator">•</span>
          <span>RAG KNOWLEDGE BASE</span>
        </div>

        <!-- Header Title -->
        <h3 id="popup-title" class="popup-title">
          {popupAlert.type === 'success' ? 'บันทึกข้อมูลและสร้างเวกเตอร์สำเร็จ' : 'เกิดข้อผิดพลาดในการบันทึก'}
        </h3>

        <!-- Core Message Highlight Box -->
        <div class="popup-message-box">
          <p class="popup-message-text">
            {#if popupAlert.type === 'success'}
              สร้าง Embedding และบันทึกลง Qdrant สำเร็จ:
              <strong class="highlight-title">"{popupAlert.docTitle}"</strong>
            {:else}
              {popupAlert.message}
            {/if}
          </p>
        </div>

        <!-- Metadata Badges Grid (for success) -->
        {#if popupAlert.type === 'success'}
          <div class="popup-meta-grid">
            <div class="popup-meta-item">
              <span class="meta-label">Collection</span>
              <span class="meta-value">hotel_policies</span>
            </div>
            <div class="popup-meta-item">
              <span class="meta-label">Embedding Model</span>
              <span class="meta-value">BAAI/bge-small</span>
            </div>
            <div class="popup-meta-item">
              <span class="meta-label">Vector Dim</span>
              <span class="meta-value">384 Dimensions</span>
            </div>
            <div class="popup-meta-item">
              <span class="meta-label">Status</span>
              <span class="meta-value active-status">● Live in Qdrant</span>
            </div>
          </div>
        {/if}

        <!-- Actions -->
        <div class="popup-actions">
          <button
            type="button"
            class="btn-popup-ok"
            onclick={closePopup}
          >
            ตกลง (รับทราบ)
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .page-container {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background: var(--bg-base);
  }

  .content-wrapper {
    max-width: 1300px;
    width: 100%;
    margin: 0 auto;
    padding: 32px 24px 60px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .page-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 20px;
    flex-wrap: wrap;
  }

  .page-title {
    font-family: 'Cinzel', serif;
    font-size: 26px;
    font-weight: 700;
    color: var(--gold-light);
    letter-spacing: 0.5px;
  }

  .page-sub {
    font-size: 13.5px;
    color: var(--text-muted);
    margin-top: 6px;
  }

  .actions-group {
    display: flex;
    gap: 12px;
  }

  .btn-gold {
    background: var(--gold-gradient);
    color: #090D16;
    border: none;
    padding: 10px 20px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: opacity 0.2s;
  }

  .btn-gold:hover {
    opacity: 0.9;
  }

  .btn-secondary {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #FFF;
    padding: 10px 18px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }

  .btn-secondary:hover {
    background: rgba(255, 255, 255, 0.12);
  }

  .alert-banner {
    padding: 14px 20px;
    border-radius: var(--radius-sm);
    font-size: 13.5px;
    font-weight: 500;
  }

  .alert-banner.success {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.4);
    color: #34D399;
  }

  .alert-banner.error {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.4);
    color: #F87171;
  }

  /* Stats Grid */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
  }

  .stat-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 18px 22px;
    backdrop-filter: blur(16px);
  }

  .stat-label {
    font-size: 11.5px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
  }

  .stat-val {
    font-size: 22px;
    font-weight: 700;
    color: #FFF;
    margin: 8px 0 4px;
  }

  .stat-val.highlight {
    color: var(--gold-light);
  }

  .stat-sub {
    font-size: 11.5px;
    color: var(--text-dim);
  }

  /* 2-Col Workbench Grid */
  .workbench-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }

  .panel-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 26px;
    backdrop-filter: blur(20px);
    box-shadow: var(--shadow-luxury);
  }

  .panel-title {
    font-size: 17px;
    font-weight: 700;
    color: var(--gold-light);
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .panel-desc {
    font-size: 12.5px;
    color: var(--text-muted);
    margin: 6px 0 20px;
    line-height: 1.5;
  }

  .embed-form {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .form-label {
    font-size: 12.5px;
    font-weight: 600;
    color: #E2E8F0;
  }

  .form-input, .form-textarea {
    background: rgba(14, 19, 31, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: var(--radius-sm);
    padding: 12px 14px;
    color: #FFF;
    font-size: 13.5px;
    font-family: inherit;
    outline: none;
    transition: all 0.2s;
  }

  .form-input:focus, .form-textarea:focus {
    border-color: var(--gold-primary);
    box-shadow: 0 0 12px rgba(212, 175, 55, 0.2);
  }

  .btn-submit-embed {
    background: var(--gold-gradient);
    color: #090D16;
    border: none;
    padding: 13px 0;
    border-radius: var(--radius-sm);
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    transition: opacity 0.2s, transform 0.1s;
    margin-top: 4px;
  }

  .btn-submit-embed:hover:not(:disabled) {
    opacity: 0.92;
    transform: translateY(-1px);
  }

  .btn-submit-embed:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  /* File Upload & Dropzone Styles */
  .hidden-file-input {
    display: none;
  }

  .file-dropzone {
    border: 2px dashed rgba(212, 175, 55, 0.35);
    background: rgba(14, 19, 31, 0.6);
    border-radius: var(--radius-md);
    padding: 22px 16px;
    text-align: center;
    cursor: pointer;
    transition: all 0.25s ease;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .file-dropzone:hover, .file-dropzone.dragging {
    border-color: var(--gold-light);
    background: rgba(212, 175, 55, 0.08);
    box-shadow: 0 0 20px rgba(212, 175, 55, 0.15);
    transform: translateY(-1px);
  }

  .dropzone-icon {
    font-size: 28px;
    filter: drop-shadow(0 2px 6px rgba(0,0,0,0.5));
  }

  .dropzone-title {
    font-size: 13.5px;
    font-weight: 600;
    color: #E2E8F0;
  }

  .highlight-link {
    color: var(--gold-light);
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  .dropzone-sub {
    font-size: 11.5px;
    color: var(--text-muted);
  }

  .supported-formats {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 6px;
    margin-top: 6px;
  }

  .format-badge {
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #CBD5E1;
  }

  .file-preview-card {
    background: rgba(14, 19, 31, 0.85);
    border: 1px solid rgba(212, 175, 55, 0.3);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .file-info-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .file-type-icon {
    font-size: 26px;
    flex-shrink: 0;
  }

  .file-details {
    flex: 1;
    min-width: 0;
  }

  .file-name {
    font-size: 13.5px;
    font-weight: 600;
    color: #FFF;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .file-meta {
    font-size: 11.5px;
    color: var(--text-muted);
    display: flex;
    gap: 10px;
    margin-top: 2px;
  }

  .extracting-indicator {
    color: #F59E0B;
    animation: pulse 1.5s infinite;
  }

  .ready-indicator {
    color: #34D399;
  }

  .btn-remove-file {
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #F87171;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-remove-file:hover {
    background: rgba(239, 68, 68, 0.25);
    color: #FFF;
  }

  .file-error-msg {
    font-size: 12px;
    color: #F87171;
    background: rgba(239, 68, 68, 0.1);
    padding: 8px 12px;
    border-radius: 4px;
    border: 1px solid rgba(239, 68, 68, 0.25);
  }

  .content-label-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }

  .char-count {
    font-size: 11px;
    color: var(--gold-light);
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  /* Playground */
  .search-input-wrapper {
    display: flex;
    gap: 10px;
  }

  .btn-search {
    background: rgba(212, 175, 55, 0.15);
    border: 1px solid var(--border-glow);
    color: var(--gold-light);
    padding: 0 20px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.2s;
  }

  .btn-search:hover {
    background: rgba(212, 175, 55, 0.25);
  }

  .matches-list {
    margin-top: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .matches-header {
    font-size: 12px;
    color: var(--gold-light);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .match-item {
    background: rgba(14, 19, 31, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
  }

  .match-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .match-title {
    font-weight: 700;
    font-size: 13.5px;
    color: #FFF;
  }

  .score-badge {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #34D399;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 999px;
    font-weight: 600;
  }

  .match-passage {
    font-size: 12.5px;
    color: var(--text-muted);
    line-height: 1.5;
  }

  /* List Table */
  .list-panel {
    margin-top: 8px;
  }

  .doc-table-wrapper {
    overflow-x: auto;
    margin-top: 16px;
  }

  .doc-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  .doc-table th {
    text-align: left;
    padding: 12px 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-muted);
    font-size: 11.5px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .doc-table td {
    padding: 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    color: #E2E8F0;
    vertical-align: top;
  }

  .id-tag {
    font-family: monospace;
    color: var(--gold-light);
    font-weight: 600;
  }

  .doc-title-cell {
    font-weight: 600;
    color: #FFF;
  }

  .doc-content-cell {
    color: var(--text-muted);
    line-height: 1.5;
  }

  .btn-delete {
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #F87171;
    padding: 5px 12px;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-delete:hover {
    background: rgba(239, 68, 68, 0.25);
  }

  .loading-state, .empty-state {
    padding: 40px;
    text-align: center;
    color: var(--text-muted);
    font-size: 14px;
  }

  /* Preset Helper Chip */
  .preset-pill-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
  }

  .preset-label {
    font-size: 12px;
    color: var(--text-dim);
  }

  .preset-chip {
    background: rgba(212, 175, 55, 0.1);
    border: 1px solid rgba(212, 175, 55, 0.3);
    color: var(--gold-light);
    font-size: 12px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 999px;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .preset-chip:hover {
    background: rgba(212, 175, 55, 0.22);
    border-color: rgba(212, 175, 55, 0.55);
    transform: translateY(-1px);
  }

  /* ========================================================================= */
  /* Popup Alert Modal Styles                                                 */
  /* ========================================================================= */
  .popup-alert-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(4, 7, 14, 0.78);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    animation: popupFadeIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .popup-alert-card {
    background: linear-gradient(160deg, rgba(22, 30, 48, 0.98) 0%, rgba(12, 17, 28, 0.98) 100%);
    border: 1px solid rgba(212, 175, 55, 0.45);
    box-shadow: 
      0 25px 60px -15px rgba(0, 0, 0, 0.85),
      0 0 35px rgba(212, 175, 55, 0.14),
      0 0 25px rgba(16, 185, 129, 0.18);
    border-radius: 20px;
    width: 100%;
    max-width: 480px;
    padding: 32px 28px 28px;
    text-align: center;
    position: relative;
    animation: popupSlideUp 0.28s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .popup-alert-card.error {
    border-color: rgba(239, 68, 68, 0.4);
    box-shadow: 
      0 25px 60px -15px rgba(0, 0, 0, 0.85),
      0 0 30px rgba(239, 68, 68, 0.18);
  }

  .popup-close-btn {
    position: absolute;
    top: 16px;
    right: 16px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-muted);
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .popup-close-btn:hover {
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
    transform: scale(1.08);
  }

  .popup-icon-container {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
  }

  .popup-icon-pulse {
    position: absolute;
    inset: -6px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(16, 185, 129, 0.35) 0%, transparent 70%);
    animation: pulseGlow 2.5s infinite ease-in-out;
  }

  .popup-icon-badge {
    position: relative;
    width: 64px;
    height: 64px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1;
  }

  .popup-icon-badge.success {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.25) 0%, rgba(5, 150, 105, 0.4) 100%);
    border: 2px solid rgba(16, 185, 129, 0.6);
    color: #34D399;
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
  }

  .popup-icon-badge.error {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.25) 0%, rgba(220, 38, 38, 0.4) 100%);
    border: 2px solid rgba(239, 68, 68, 0.6);
    color: #F87171;
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
  }

  .popup-kicker {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 1.2px;
    color: var(--gold-primary);
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  .dot-separator {
    opacity: 0.5;
  }

  .popup-title {
    font-family: 'Cinzel', serif;
    font-size: 20px;
    font-weight: 700;
    color: var(--gold-light);
    letter-spacing: 0.5px;
    margin-bottom: 16px;
  }

  .popup-message-box {
    background: rgba(10, 15, 25, 0.7);
    border: 1px solid rgba(212, 175, 55, 0.25);
    border-radius: var(--radius-sm);
    padding: 14px 18px;
    margin-bottom: 20px;
  }

  .popup-message-text {
    font-size: 14.5px;
    color: #E2E8F0;
    line-height: 1.6;
    margin: 0;
  }

  .highlight-title {
    color: #FDE047;
    font-weight: 700;
  }

  .popup-meta-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    margin-bottom: 24px;
    text-align: left;
  }

  .popup-meta-item {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .meta-label {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .meta-value {
    font-size: 12.5px;
    font-weight: 600;
    color: #E2E8F0;
  }

  .meta-value.active-status {
    color: #34D399;
  }

  .popup-actions {
    display: flex;
    justify-content: center;
  }

  .btn-popup-ok {
    background: var(--gold-gradient);
    color: #090D16;
    border: none;
    padding: 12px 36px;
    border-radius: var(--radius-sm);
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3);
    transition: all 0.2s ease;
  }

  .btn-popup-ok:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(212, 175, 55, 0.45);
    filter: brightness(1.06);
  }

  @keyframes popupFadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes popupSlideUp {
    from {
      opacity: 0;
      transform: translateY(18px) scale(0.96);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  @keyframes pulseGlow {
    0%, 100% {
      transform: scale(1);
      opacity: 0.6;
    }
    50% {
      transform: scale(1.15);
      opacity: 0.9;
    }
  }

  /* ========================================================================= */
  /* Guidance & Troubleshooting Panel Styles                                  */
  /* ========================================================================= */
  .guide-panel {
    border-color: rgba(212, 175, 55, 0.35);
    background: linear-gradient(180deg, rgba(20, 27, 43, 0.95) 0%, rgba(13, 18, 29, 0.95) 100%);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35), 0 0 20px rgba(212, 175, 55, 0.08);
  }

  .guide-header {
    margin-bottom: 20px;
    padding-bottom: 14px;
    border-bottom: 1px solid rgba(212, 175, 55, 0.2);
  }

  .guide-title-group {
    display: flex;
    align-items: flex-start;
    gap: 14px;
  }

  .guide-icon {
    font-size: 26px;
    background: rgba(212, 175, 55, 0.15);
    border: 1px solid rgba(212, 175, 55, 0.3);
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .guide-content-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }

  .guide-subtitle {
    font-size: 14px;
    font-weight: 700;
    color: var(--gold-light);
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .guide-list, .guide-steps {
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.6;
    padding-left: 18px;
    margin: 0;
  }

  .guide-list li, .guide-steps li {
    margin-bottom: 8px;
  }

  .guide-list li strong, .guide-steps li strong {
    color: #E2E8F0;
  }

  .example-box {
    border-radius: var(--radius-sm);
    padding: 12px 14px;
    margin-bottom: 12px;
    font-size: 12px;
  }

  .example-box.bad {
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.3);
  }

  .example-box.good {
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.35);
  }

  .example-badge {
    font-size: 11px;
    font-weight: 700;
    margin-bottom: 6px;
  }

  .example-badge.bad {
    color: #F87171;
  }

  .example-badge.good {
    color: #34D399;
  }

  .example-code {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 11.5px;
    color: #CBD5E1;
    margin: 0;
    white-space: pre-wrap;
    line-height: 1.5;
  }

  @media (max-width: 960px) {
    .workbench-grid, .guide-content-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
