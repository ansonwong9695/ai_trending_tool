<template>
  <div class="dashboard">
    <div class="page-header">
      <h2>热点动态</h2>
      <div class="header-actions">
        <select v-model="filterSource" class="input filter-select">
          <option value="">全部来源</option>
          <option value="hackernews">Hacker News</option>
          <option value="github">GitHub</option>
          <option value="bing">Bing News</option>
          <option value="aggregated">聚合</option>
        </select>
        <button class="btn btn-primary" @click="triggerMonitor" :disabled="monitoring">
          {{ monitoring ? '采集中...' : '立即采集' }}
        </button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>

    <div v-if="loading" class="loading-grid">
      <div class="card skeleton" v-for="i in 6" :key="i"></div>
    </div>

    <div v-else-if="items.length === 0" class="empty-state">
      <div class="empty-icon">📰</div>
      <p>暂无热点内容</p>
      <p class="empty-hint">点击「立即采集」开始抓取热点，或添加关键词进行监控</p>
    </div>

    <div v-else class="trending-grid">
      <article
        v-for="item in items"
        :key="item.id"
        class="card trending-card"
      >
        <div class="card-meta">
          <span class="source-badge" :class="`source-${item.source}`">{{ item.source }}</span>
          <span class="card-date">{{ formatDate(item.created_at) }}</span>
        </div>
        <h3 class="card-title">
          <a v-if="item.url" :href="item.url" target="_blank" rel="noopener">{{ item.title }}</a>
          <span v-else>{{ item.title }}</span>
        </h3>
        <p v-if="item.summary" class="card-summary">{{ item.summary }}</p>
        <div class="card-footer">
          <div class="card-tags">
            <span v-for="tag in (item.tags || []).slice(0, 3)" :key="tag" class="tag">{{ tag }}</span>
          </div>
          <div class="card-score" v-if="item.score">
            <span class="score-value">{{ item.score.toFixed(0) }}</span>
          </div>
        </div>
      </article>
    </div>

    <div v-if="items.length > 0" class="load-more">
      <button class="btn btn-outline" @click="loadMore" :disabled="loadingMore">
        {{ loadingMore ? '加载中...' : '加载更多' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { trendingApi } from '../services/api.js'

const items = ref([])
const loading = ref(false)
const loadingMore = ref(false)
const monitoring = ref(false)
const error = ref('')
const filterSource = ref('')
const offset = ref(0)
const LIMIT = 12

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
    setTimeout(() => fetchItems(true), 2000)
  } catch (e) {
    error.value = e.message
  } finally {
    monitoring.value = false
  }
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = Math.floor((now - d) / 60000)
  if (diff < 1) return '刚刚'
  if (diff < 60) return `${diff}分钟前`
  if (diff < 1440) return `${Math.floor(diff / 60)}小时前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

watch(filterSource, () => fetchItems(true))
onMounted(() => fetchItems(true))
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.page-header h2 {
  font-size: 2rem;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.filter-select {
  width: auto;
  padding: 0.5rem 0.75rem;
}

.alert-error {
  background: #FEE2E2;
  color: #B91C1C;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.loading-grid,
.trending-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.25rem;
}

.skeleton {
  height: 180px;
  background: linear-gradient(90deg, #ede8df 25%, #f6f1e8 50%, #ede8df 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: var(--color-text-secondary);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-hint {
  font-size: 0.9rem;
  margin-top: 0.5rem;
  opacity: 0.7;
}

.trending-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.source-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 20px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: var(--color-bg);
  color: var(--color-text-secondary);
}

.source-hackernews { background: #FFF3E0; color: #E65100; }
.source-github { background: #E8F5E9; color: #2E7D32; }
.source-bing { background: #E8F1FF; color: #1D4ED8; }
.source-aggregated { background: #F3E5F5; color: #6A1B9A; }

.card-date {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.card-title {
  font-size: 1rem;
  line-height: 1.4;
  flex: 1;
}

.card-title a {
  color: var(--color-text);
  text-decoration: none;
}

.card-title a:hover {
  color: var(--color-primary);
  text-decoration: none;
}

.card-summary {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
}

.card-tags {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.tag {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  background: var(--color-bg);
  border-radius: 4px;
  color: var(--color-text-secondary);
}

.card-score {
  font-size: 0.8rem;
  color: var(--color-primary);
  font-weight: 600;
}

.load-more {
  text-align: center;
  margin-top: 2rem;
}

.btn-outline {
  border: 2px solid var(--color-primary);
  color: var(--color-primary);
  padding: 0.6rem 2rem;
  border-radius: 8px;
  background: transparent;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline:hover:not(:disabled) {
  background: var(--color-primary);
  color: white;
}

.btn-outline:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
