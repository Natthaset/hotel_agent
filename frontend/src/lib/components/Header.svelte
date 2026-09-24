<script lang="ts">
  import { page } from '$app/state';
</script>

<header class="luxury-header">
  <div class="header-left">
    <a href="/" class="brand">
      <div class="brand-logo">GA</div>
      <div>
        <div class="brand-title">Grand Azure</div>
        <div class="brand-subtitle">Resort &amp; Luxury Residences</div>
      </div>
    </a>

    <nav class="nav-links">
      <a href="/" class="nav-link" class:active={page.url.pathname === '/'}>
        <span class="nav-icon">✨</span> Concierge Chat
      </a>
      <a href="/admin/knowledge" class="nav-link" class:active={page.url.pathname.startsWith('/admin/knowledge')}>
        <span class="nav-icon">📚</span> Knowledge &amp; Embed Manager
      </a>
    </nav>
  </div>

  <div class="header-right">
    <div class="status-badge">
      <div class="status-pulse"></div>
      AI Concierge 24/7 Live
    </div>
  </div>
</header>

<style>
  .luxury-header {
    height: 72px;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    background: rgba(9, 13, 22, 0.88);
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 32px;
    position: sticky;
    top: 0;
    z-index: 50;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 36px;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 14px;
    text-decoration: none;
  }

  .brand-logo {
    width: 42px;
    height: 42px;
    border-radius: 10px;
    background: var(--gold-gradient);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Cinzel', serif;
    font-weight: 700;
    font-size: 20px;
    color: #090D16;
    box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3);
  }

  .brand-title {
    font-family: 'Cinzel', serif;
    font-size: 19px;
    font-weight: 600;
    letter-spacing: 1.5px;
    color: var(--gold-light);
  }

  .brand-subtitle {
    font-size: 10px;
    color: var(--text-muted);
    letter-spacing: 2px;
    text-transform: uppercase;
  }

  .nav-links {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .nav-link {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-muted);
    text-decoration: none;
    transition: all 0.2s ease;
    border: 1px solid transparent;
  }

  .nav-link:hover {
    color: var(--text-main);
    background: rgba(255, 255, 255, 0.04);
  }

  .nav-link.active {
    color: var(--gold-light);
    background: rgba(212, 175, 55, 0.12);
    border-color: var(--border-subtle);
  }

  .nav-icon {
    font-size: 14px;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .status-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    padding: 6px 14px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 500;
    color: #34D399;
  }

  .status-pulse {
    width: 7px;
    height: 7px;
    background: #10B981;
    border-radius: 50%;
    box-shadow: 0 0 10px #10B981;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(1.3); }
  }

  @media (max-width: 840px) {
    .luxury-header {
      padding: 0 16px;
    }
    .brand-subtitle {
      display: none;
    }
    .header-left {
      gap: 16px;
    }
  }
</style>
