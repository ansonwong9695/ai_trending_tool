<template>
  <div class="app-shell">
    <div class="shell-backdrop">
      <AceternitySpotlight top="-10%" left="18%" size="28rem" color="rgba(98, 179, 255, 0.18)" />
      <AceternitySpotlight top="6%" left="82%" size="24rem" color="rgba(44, 246, 201, 0.16)" delay="0.15s" />
      <AceternityBeams />
    </div>

    <header class="topbar panel">
      <div class="brand-block">
        <div class="brand-mark">AI</div>
        <div>
          <p class="eyebrow">Trend Radar</p>
          <h1>AI 热点雷达</h1>
        </div>
      </div>

      <nav class="topnav" aria-label="主导航">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
        >
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="topbar-status">
        <span class="status-dot pulse"></span>
        <div>
          <p class="status-label">采集节奏</p>
          <p class="status-value mono">Every 30 min</p>
        </div>
      </div>
    </header>

    <main class="shell-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import AceternityBeams from './components/AceternityBeams.vue'
import AceternitySpotlight from './components/AceternitySpotlight.vue'

const navItems = [
  { to: '/', label: '热点追踪' },
  { to: '/keywords', label: '关键词' },
  { to: '/settings', label: '系统设置' },
]
</script>

<style scoped>
.app-shell {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  padding: 1.25rem;
}

.shell-backdrop {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.topbar,
.shell-main {
  position: relative;
  z-index: 1;
}

.topbar {
  width: min(100%, var(--container));
  margin: 0 auto 1rem;
  padding: 1rem 1.15rem;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 1rem;
  align-items: center;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 0.9rem;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background:
    linear-gradient(135deg, rgba(98, 179, 255, 0.2), rgba(44, 246, 201, 0.14)),
    rgba(9, 18, 34, 0.92);
  border: 1px solid rgba(144, 187, 255, 0.22);
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  letter-spacing: -0.04em;
}

.brand-block h1 {
  font-size: 1.1rem;
}

.topnav {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.nav-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 1rem;
  border-radius: 999px;
  color: var(--text-muted);
  transition: color 180ms ease, transform 180ms ease;
}

.nav-link::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  border: 1px solid transparent;
  background: linear-gradient(180deg, rgba(11, 22, 40, 0.92), rgba(8, 18, 35, 0.84));
  transition: border-color 180ms ease, background 180ms ease;
  z-index: 0;
}

.nav-link span {
  position: relative;
  z-index: 1;
}

.nav-link:hover {
  color: var(--text);
  transform: translateY(-1px);
}

.nav-link:hover::before {
  border-color: rgba(144, 187, 255, 0.18);
}

.nav-link.router-link-active {
  color: var(--text);
}

.nav-link.router-link-active::before {
  border-color: rgba(144, 187, 255, 0.3);
  background:
    linear-gradient(135deg, rgba(98, 179, 255, 0.16), rgba(44, 246, 201, 0.06)),
    rgba(8, 18, 34, 0.92);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.topbar-status {
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.65rem 0.85rem;
  border-radius: 18px;
  border: 1px solid rgba(144, 187, 255, 0.14);
  background: rgba(7, 15, 29, 0.72);
}

.status-label {
  font-size: 0.74rem;
  color: var(--text-soft);
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.status-value {
  font-size: 0.86rem;
}

.shell-main {
  width: min(100%, var(--container));
  margin: 0 auto;
  padding-bottom: 2.5rem;
}

@media (max-width: 960px) {
  .topbar {
    grid-template-columns: 1fr;
  }

  .topnav {
    justify-content: start;
  }

  .topbar-status {
    width: fit-content;
  }
}

@media (max-width: 640px) {
  .app-shell {
    padding: 0.85rem;
  }

  .topbar {
    padding: 1rem;
  }

  .nav-link {
    flex: 1 1 calc(50% - 0.5rem);
  }
}
</style>
