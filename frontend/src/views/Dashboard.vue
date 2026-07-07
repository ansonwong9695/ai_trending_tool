<template>
  <div class="page-shell dashboard-page">
    <section class="hero panel">
      <AceternitySpotlight top="-16%" left="26%" size="30rem" color="rgba(98, 179, 255, 0.18)" />
      <AceternitySpotlight top="6%" left="84%" size="22rem" color="rgba(44, 246, 201, 0.14)" delay="0.15s" />

      <div class="hero-copy">
        <p class="eyebrow">
          <span class="status-dot pulse"></span>
          Live signal board
        </p>
        <h2>先看到趋势，再决定要不要追。</h2>
        <p class="hero-text">
          为高频分享者设计的 AI 热点监控台。把 Hacker News、GitHub 和新闻流压缩成高密度信号，
          帮你更快判断什么值得立刻阅读、整理、转发和输出。
        </p>

        <div class="hero-actions">
          <div class="select-shell hero-filter">
            <label class="input-label" for="source-filter">来源筛选</label>
            <select id="source-filter" v-model="filterSource" class="select">
              <option value="">全部来源</option>
              <option value="hackernews">Hacker News</option>
              <option value="github">GitHub</option>
              <option value="bing">Bing News</option>
              <option value="weibo">Weibo</option>
              <option value="aggregated">聚合</option>
            </select>
          </div>

          <div class="hero-buttons">
            <AceternityGlowButton :disabled="monitoring" @click="triggerMonitor">
              {{ monitoring ? '采集中...' : '立即采集' }}
            </AceternityGlowButton>
            <button class="ghost-button" @click="fetchItems(true)" :disabled="loading">
              {{ loading ? '刷新中...' : '刷新列表' }}
            </button>
          </div>
        </div>
      </div>

      <div class="hero-metrics">
        <div class="metric-card">
          <span class="metric-label">当前信号</span>
          <strong class="metric-value mono">{{ visibleCount }}</strong>
          <span class="metric-note">已加载热点条目</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">覆盖来源</span>
          <strong class="metric-value mono">{{ sourceCount }}</strong>
          <span class="metric-note">实时活跃数据源</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">高分内容</span>
          <strong class="metric-value mono">{{ highSignalCount }}</strong>
          <span class="metric-note">评分 80+ 的热点</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">最新捕获</span>
          <strong class="metric-value">{{ latestCaptureLabel }}</strong>
          <span class="metric-note">最新一条入库时间</span>
        </div>
      </div>
    </section>

    <section class="overview-grid">
      <AceternityBentoCard
        eyebrow="Featured"
        title="当前最值得打开的内容"
        :description="primaryItem ? primaryItem.title : '触发一次采集，拉起新的候选热点。'"
        span="2"
        tone="primary"
      >
        <template #header>
          <div v-if="primaryItem" class="featured-meta">
            <span class="pill">{{ formatSource(primaryItem.source) }}</span>
            <span class="pill" :class="scoreClass(primaryItem.score)">
              {{ scoreText(primaryItem.score) }}
            </span>
          </div>
        </template>
        <template #footer>
          <div class="featured-footer">
            <p class="text-muted">
              {{ primaryItem?.summary || '抓到第一条热点后，这里会优先展示最值得你第一时间读的信号。' }}
            </p>
            <AceternityGlowButton
              v-if="resolveItemUrl(primaryItem)"
              :href="resolveItemUrl(primaryItem)"
              target="_blank"
              variant="secondary"
            >
              立即查看
            </AceternityGlowButton>
            <span v-else class="pill danger">原文缺失</span>
          </div>
        </template>
      </AceternityBentoCard>

      <AceternityBentoCard
        eyebrow="Filter"
        title="当前筛选"
        :description="filterSource ? `${formatSource(filterSource)} 正在作为焦点来源` : '未限制来源，保持全局扫描视角。'"
        tone="accent"
      >
        <template #footer>
          <div class="mini-stat mono">{{ filterSource ? formatSource(filterSource) : 'ALL SOURCES' }}</div>
        </template>
      </AceternityBentoCard>

      <AceternityBentoCard
        eyebrow="Momentum"
        title="标签热度"
        :description="topTags.length ? '最近内容里最频繁出现的标签。' : '等待更多内容来提炼热点标签。'"
        tone="warning"
      >
        <template #footer>
          <div class="tag-cloud">
            <span v-for="tag in topTags" :key="tag" class="pill">{{ tag }}</span>
            <span v-if="!topTags.length" class="pill">No tags yet</span>
          </div>
        </template>
      </AceternityBentoCard>
    </section>

    <div v-if="error" class="alert error">{{ error }}</div>

    <section class="signals-section">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Hot list</p>
          <h3 class="section-title">值得立刻读的热点</h3>
        </div>
        <p class="section-copy">
          保留足够强的信息层级，但不把你拖进复杂操作里。内容优先，动作第二，装饰最后。
        </p>
      </div>

      <div v-if="loading" class="signals-grid">
        <div v-for="i in 6" :key="i" class="signal-card loading-card"></div>
      </div>

      <div v-else-if="items.length === 0" class="panel empty-signal">
        <div class="empty-icon"></div>
        <h3>还没有热点信号</h3>
        <p class="text-muted">点击「立即采集」，把第一批可读、可转发的内容拉进来。</p>
      </div>

      <div v-else class="signals-grid">
        <article
          v-for="item in items"
          :key="item.id"
          class="signal-card"
          :class="{ clickable: !!resolveItemUrl(item) }"
          :role="resolveItemUrl(item) ? 'link' : undefined"
          :tabindex="resolveItemUrl(item) ? 0 : undefined"
          :aria-disabled="resolveItemUrl(item) ? 'false' : 'true'"
          @click="openItem(resolveItemUrl(item), $event)"
          @keydown.enter="openItem(resolveItemUrl(item), $event)"
        >
          <div class="signal-top">
            <div class="signal-badges">
              <span class="pill">{{ formatSource(item.source) }}</span>
              <span v-if="item.score" class="pill" :class="scoreClass(item.score)">
                {{ scoreText(item.score) }}
              </span>
            </div>
            <span class="signal-time mono">{{ formatDate(item.created_at) }}</span>
          </div>

          <h4 class="signal-title">
            <a
              v-if="resolveItemUrl(item)"
              :href="resolveItemUrl(item)"
              target="_blank"
              rel="noopener noreferrer"
            >
              {{ item.title }}
            </a>
            <span v-else>{{ item.title }}</span>
          </h4>

          <p v-if="item.summary" class="signal-summary">{{ item.summary }}</p>
          <p v-else class="signal-summary muted">
            这条内容暂无摘要，建议直接打开原文判断它是否适合进入你的分享流。
          </p>

          <div class="signal-footer">
            <div class="tag-cloud">
              <span v-for="tag in (item.tags || []).slice(0, 4)" :key="tag" class="pill">{{ tag }}</span>
            </div>
            <a
              v-if="resolveItemUrl(item)"
              class="signal-link"
              :href="resolveItemUrl(item)"
              target="_blank"
              rel="noopener noreferrer"
            >
              Read now
            </a>
            <span v-else class="signal-link disabled">原文缺失</span>
          </div>
        </article>
      </div>

      <div v-if="items.length > 0" class="load-more">
        <button class="ghost-button" @click="loadMore" :disabled="loadingMore">
          {{ loadingMore ? '加载中...' : '加载更多热点' }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import AceternityBentoCard from '../components/AceternityBentoCard.vue'
import AceternityGlowButton from '../components/AceternityGlowButton.vue'
import AceternitySpotlight from '../components/AceternitySpotlight.vue'
import { trendingApi } from '../services/api.js'

const items = ref([])
const loading = ref(false)
const loadingMore = ref(false)
const monitoring = ref(false)
const error = ref('')
const filterSource = ref('')
const offset = ref(0)
const LIMIT = 12

const visibleCount = computed(() => items.value.length)

const sourceCount = computed(() => new Set(items.value.map(item => item.source).filter(Boolean)).size)

const highSignalCount = computed(() => items.value.filter(item => Number(item.score) >= 80).length)

const latestCaptureLabel = computed(() => {
  if (!items.value.length) return '--'
  return formatDate(items.value[0].created_at)
})

const primaryItem = computed(() => items.value[0] || null)

const topTags = computed(() => {
  const counts = new Map()
  items.value.forEach((item) => {
    ;(item.tags || []).forEach((tag) => {
      const key = String(tag).trim()
      if (!key) return
      counts.set(key, (counts.get(key) || 0) + 1)
    })
  })
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([tag]) => tag)
})

async function fetchItems(reset = false) {
  if (reset) {
    offset.value = 0
    items.value = []
  }

  loading.value = reset
  loadingMore.value = !reset
  error.value = ''

  try {
    const params = { limit: LIMIT, offset: offset.value }
    if (filterSource.value) params.source = filterSource.value
    const data = await trendingApi.list(params)

    if (reset) {
      items.value = data
    } else {
      items.value.push(...data)
    }

    offset.value += data.length
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

async function loadMore() {
  await fetchItems(false)
}

async function triggerMonitor() {
  monitoring.value = true
  error.value = ''
  try {
    await trendingApi.triggerMonitor()
    setTimeout(() => fetchItems(true), 1800)
  } catch (e) {
    error.value = e.message
  } finally {
    monitoring.value = false
  }
}

function formatSource(source) {
  const map = {
    hackernews: 'Hacker News',
    github: 'GitHub',
    bing: 'Bing News',
    weibo: 'Weibo',
    aggregated: '聚合输出',
  }
  return map[source] || source || 'Unknown'
}

function formatDate(iso) {
  if (!iso) return '--'
  const date = new Date(iso)
  const now = new Date()
  const diff = Math.floor((now - date) / 60000)

  if (diff < 1) return '刚刚'
  if (diff < 60) return `${diff}m ago`
  if (diff < 1440) return `${Math.floor(diff / 60)}h ago`

  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function scoreClass(score) {
  if (Number(score) >= 85) return 'success'
  if (Number(score) >= 70) return 'warning'
  return ''
}

function scoreText(score) {
  if (!score) return '新信号'
  return `Score ${Number(score).toFixed(0)}`
}

function resolveItemUrl(item) {
  if (!item) return ''
  if (item.url) return item.url
  if (item.primary_url) return item.primary_url
  if (Array.isArray(item.raw_urls) && item.raw_urls.length > 0) return item.raw_urls[0]
  return ''
}

function openItem(url, event) {
  if (!url) return
  if (event?.target?.closest?.('a, button')) return
  window.open(url, '_blank', 'noopener,noreferrer')
}

watch(filterSource, () => fetchItems(true))
onMounted(() => fetchItems(true))
</script>

<style scoped>
.dashboard-page {
  gap: 1.35rem;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(280px, 0.9fr);
  gap: 1.2rem;
  padding: 1.35rem;
}

.hero-copy {
  display: grid;
  gap: 1rem;
  align-content: start;
}

.hero-copy h2 {
  max-width: 12ch;
  font-size: clamp(2.3rem, 5vw, 4.3rem);
}

.hero-text {
  max-width: 42rem;
  font-size: 1rem;
  color: var(--text-muted);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: end;
}

.hero-filter {
  min-width: 220px;
  max-width: 250px;
}

.hero-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
}

.metric-card {
  min-height: 148px;
  padding: 1rem;
  border-radius: 24px;
  border: 1px solid rgba(144, 187, 255, 0.14);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.05), transparent 24%),
    rgba(7, 16, 31, 0.82);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.metric-label,
.metric-note {
  font-size: 0.82rem;
  color: var(--text-soft);
}

.metric-value {
  font-size: clamp(1.4rem, 2vw, 2rem);
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
}

.featured-meta,
.featured-footer,
.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.featured-footer {
  justify-content: space-between;
  align-items: end;
  gap: 1rem;
}

.mini-stat {
  font-size: 1rem;
  color: var(--text);
}

.signals-section {
  display: grid;
  gap: 1rem;
}

.signals-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
  gap: 1rem;
}

.signal-card {
  position: relative;
  min-height: 260px;
  padding: 1.15rem;
  overflow: hidden;
  border-radius: 24px;
  border: 1px solid rgba(144, 187, 255, 0.14);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.045), transparent 26%),
    rgba(8, 18, 33, 0.86);
  display: flex;
  flex-direction: column;
  gap: 0.95rem;
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
  box-shadow: 0 16px 42px rgba(3, 10, 22, 0.22);
}

.signal-card::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(135deg, rgba(98, 179, 255, 0.28), rgba(44, 246, 201, 0), rgba(98, 179, 255, 0.14));
  mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  mask-composite: xor;
  -webkit-mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  opacity: 0;
  transition: opacity 180ms ease;
}

.signal-card:hover {
  transform: translateY(-4px);
  border-color: rgba(144, 187, 255, 0.26);
  box-shadow: 0 28px 60px rgba(3, 10, 22, 0.32);
}

.signal-card.clickable {
  cursor: pointer;
}

.signal-card:hover::before {
  opacity: 1;
}

.loading-card {
  min-height: 260px;
  border-radius: 24px;
}

.signal-top,
.signal-footer {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: start;
}

.signal-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.signal-time {
  color: var(--text-soft);
  font-size: 0.78rem;
}

.signal-title {
  font-size: 1.08rem;
  line-height: 1.45;
}

.signal-title a:hover {
  color: #9fd1ff;
}

.signal-summary {
  color: var(--text-muted);
  font-size: 0.92rem;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.signal-summary.muted {
  color: var(--text-soft);
}

.signal-link {
  color: #9fd1ff;
  white-space: nowrap;
  font-size: 0.84rem;
  font-weight: 700;
}

.signal-link.disabled {
  color: var(--text-soft);
}

.load-more {
  display: flex;
  justify-content: center;
}

@media (max-width: 1080px) {
  .hero,
  .overview-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .hero {
    padding: 1rem;
  }

  .hero-metrics {
    grid-template-columns: 1fr;
  }

  .hero-copy h2 {
    max-width: none;
  }

  .signal-footer {
    flex-direction: column;
    align-items: start;
  }
}
</style>
