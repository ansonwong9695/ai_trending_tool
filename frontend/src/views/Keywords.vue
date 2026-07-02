<template>
  <div class="page-shell keywords-page">
    <section class="section-intro panel">
      <div>
        <p class="eyebrow">Keyword watchlist</p>
        <h2>把你的注意力，绑定到会爆发的话题上。</h2>
      </div>
      <p class="section-copy">
        关键词不是“存档”，而是你的长期雷达。把你最想抢先输出的概念放进去，系统会稳定追踪并在热点发生时给你信号。
      </p>
    </section>

    <section class="keywords-layout">
      <div class="panel form-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Create rule</p>
            <h3 class="section-title">添加监控关键词</h3>
          </div>
          <span class="pill success">{{ activeCount }} active</span>
        </div>

        <form class="keyword-form" @submit.prevent="addKeyword">
          <div class="input-shell">
            <label class="input-label" for="keyword-input">关键词</label>
            <input
              id="keyword-input"
              v-model="newKeyword"
              class="input"
              placeholder="例如：Claude Code、MCP、Agents、GPT-5"
              :disabled="adding"
            />
          </div>

          <div class="source-block">
            <p class="input-label">追踪来源</p>
            <div class="source-options">
              <label v-for="s in SOURCES" :key="s.value" class="source-option">
                <input type="checkbox" :value="s.value" v-model="selectedSources" />
                <span>{{ s.label }}</span>
              </label>
            </div>
          </div>

          <div v-if="addError" class="alert error">{{ addError }}</div>

          <div class="form-actions">
            <AceternityGlowButton type="submit" :disabled="adding || !newKeyword.trim()">
              {{ adding ? '添加中...' : '加入监控队列' }}
            </AceternityGlowButton>
            <p class="text-soft">默认每 30 分钟自动扫描一次。</p>
          </div>
        </form>
      </div>

      <div class="summary-column">
        <div class="summary-grid">
          <div class="summary-card panel">
            <span class="summary-label">关键词总数</span>
            <strong class="summary-value mono">{{ keywords.length }}</strong>
            <p class="text-muted">当前 watchlist 中的关键词条目</p>
          </div>
          <div class="summary-card panel">
            <span class="summary-label">活跃规则</span>
            <strong class="summary-value mono">{{ activeCount }}</strong>
            <p class="text-muted">正在持续推送热点的监控规则</p>
          </div>
          <div class="summary-card panel">
            <span class="summary-label">覆盖来源</span>
            <strong class="summary-value mono">{{ coverageCount }}</strong>
            <p class="text-muted">当前关键词涉及的数据源数量</p>
          </div>
        </div>

        <div class="panel tips-panel">
          <p class="eyebrow">Operator notes</p>
          <h3 class="section-title">更有效的关键词策略</h3>
          <ul class="tips-list">
            <li>优先填“会引发讨论”的概念，而不是泛泛的行业词。</li>
            <li>新模型、新工具、新协议，用英文名和缩写一起监控。</li>
            <li>保持数量克制，关键词过多会稀释真正值得看的信号。</li>
          </ul>
        </div>
      </div>
    </section>

    <div v-if="error" class="alert error">{{ error }}</div>

    <section class="list-section">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Watchlist</p>
          <h3 class="section-title">已建立的热点雷达</h3>
        </div>
        <p class="section-copy">启用状态、来源覆盖和创建时间保持在同一层视线里，不需要点进去才知道规则是否正常工作。</p>
      </div>

      <div v-if="loading" class="keyword-list">
        <div v-for="i in 4" :key="i" class="keyword-card loading-card"></div>
      </div>

      <div v-else-if="keywords.length === 0" class="panel empty-signal">
        <div class="empty-icon"></div>
        <h3>还没有建立关键词规则</h3>
        <p class="text-muted">先加 3 到 5 个最值得你长期盯住的主题，监控价值会立刻显现出来。</p>
      </div>

      <div v-else class="keyword-list">
        <article v-for="kw in keywords" :key="kw.id" class="keyword-card">
          <div class="keyword-main">
            <div class="keyword-title-row">
              <h4>{{ kw.keyword }}</h4>
              <span class="pill" :class="kw.is_active ? 'success' : 'danger'">
                {{ kw.is_active ? '监控中' : '已暂停' }}
              </span>
            </div>

            <div class="tag-row">
              <span
                v-for="src in (kw.sources || defaultSources)"
                :key="src"
                class="pill"
              >
                {{ formatSource(src) }}
              </span>
            </div>
          </div>

          <div class="keyword-side">
            <span class="keyword-date mono">{{ formatDate(kw.created_at) }}</span>
            <button
              class="toggle-button"
              :class="kw.is_active ? 'active' : 'inactive'"
              @click="toggleKeyword(kw)"
              :title="kw.is_active ? '点击暂停监控' : '点击启用监控'"
            >
              {{ kw.is_active ? '暂停' : '启用' }}
            </button>
            <button class="delete-button" @click="deleteKeyword(kw.id)" title="删除关键词">
              删除
            </button>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import AceternityGlowButton from '../components/AceternityGlowButton.vue'
import { keywordsApi } from '../services/api.js'

const SOURCES = [
  { value: 'hackernews', label: 'Hacker News' },
  { value: 'bing', label: 'Bing News' },
]
const defaultSources = ['hackernews', 'bing']

const keywords = ref([])
const loading = ref(false)
const error = ref('')
const newKeyword = ref('')
const selectedSources = ref([...defaultSources])
const adding = ref(false)
const addError = ref('')

const activeCount = computed(() => keywords.value.filter(item => item.is_active).length)

const coverageCount = computed(() => {
  const sources = new Set()
  keywords.value.forEach((item) => {
    ;(item.sources || defaultSources).forEach(source => sources.add(source))
  })
  return sources.size
})

async function fetchKeywords() {
  loading.value = true
  error.value = ''
  try {
    keywords.value = await keywordsApi.list()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function addKeyword() {
  if (!newKeyword.value.trim()) return
  adding.value = true
  addError.value = ''
  try {
    const keyword = await keywordsApi.create({
      keyword: newKeyword.value.trim(),
      sources: selectedSources.value.length ? selectedSources.value : defaultSources,
    })
    keywords.value.unshift(keyword)
    newKeyword.value = ''
    selectedSources.value = [...defaultSources]
  } catch (e) {
    addError.value = e.message
  } finally {
    adding.value = false
  }
}

async function toggleKeyword(keyword) {
  try {
    const updated = await keywordsApi.update(keyword.id, { is_active: !keyword.is_active })
    const index = keywords.value.findIndex(item => item.id === keyword.id)
    if (index !== -1) {
      keywords.value[index] = updated
    }
  } catch (e) {
    error.value = e.message
  }
}

async function deleteKeyword(id) {
  if (!confirm('确认删除该关键词？')) return
  try {
    await keywordsApi.delete(id)
    keywords.value = keywords.value.filter(item => item.id !== id)
  } catch (e) {
    error.value = e.message
  }
}

function formatDate(iso) {
  if (!iso) return '--'
  return new Date(iso).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function formatSource(source) {
  return source === 'hackernews' ? 'Hacker News' : source === 'bing' ? 'Bing News' : source
}

onMounted(fetchKeywords)
</script>

<style scoped>
.keywords-page {
  gap: 1.35rem;
}

.section-intro {
  display: grid;
  gap: 0.7rem;
  padding: 1.25rem;
}

.section-intro h2 {
  font-size: clamp(1.8rem, 3vw, 2.75rem);
  max-width: 14ch;
}

.keywords-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 1rem;
}

.form-panel,
.tips-panel {
  padding: 1.2rem;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: start;
  margin-bottom: 1rem;
}

.keyword-form {
  display: grid;
  gap: 1rem;
}

.source-block {
  display: grid;
  gap: 0.65rem;
}

.source-options {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
}

.source-option {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  min-height: 44px;
  padding: 0.7rem 0.9rem;
  border-radius: 16px;
  border: 1px solid rgba(144, 187, 255, 0.14);
  background: rgba(8, 18, 33, 0.72);
  color: var(--text-muted);
  cursor: pointer;
}

.source-option input {
  accent-color: var(--primary);
}

.form-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.9rem;
}

.summary-column,
.list-section {
  display: grid;
  gap: 1rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
}

.summary-card {
  padding: 1rem;
  display: grid;
  gap: 0.55rem;
}

.summary-label {
  font-size: 0.82rem;
  color: var(--text-soft);
}

.summary-value {
  font-size: 1.9rem;
}

.tips-list {
  margin: 0;
  padding-left: 1.1rem;
  color: var(--text-muted);
}

.tips-list li + li {
  margin-top: 0.55rem;
}

.keyword-list {
  display: grid;
  gap: 0.9rem;
}

.keyword-card {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 1rem 1.1rem;
  border-radius: 24px;
  border: 1px solid rgba(144, 187, 255, 0.14);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.045), transparent 22%),
    rgba(8, 18, 33, 0.84);
  box-shadow: 0 16px 42px rgba(3, 10, 22, 0.22);
}

.keyword-main,
.keyword-side {
  display: flex;
  gap: 0.75rem;
}

.keyword-main {
  flex-direction: column;
  flex: 1;
}

.keyword-side {
  align-items: center;
  flex-wrap: wrap;
  justify-content: end;
}

.keyword-title-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  align-items: center;
}

.keyword-title-row h4 {
  font-size: 1.05rem;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.keyword-date {
  color: var(--text-soft);
  font-size: 0.82rem;
}

.toggle-button,
.delete-button {
  min-height: 42px;
  padding: 0 0.95rem;
  border-radius: 999px;
  border: 1px solid transparent;
  font-weight: 700;
  transition: transform 180ms ease, opacity 180ms ease;
}

.toggle-button:hover,
.delete-button:hover {
  transform: translateY(-1px);
}

.toggle-button.active {
  background: rgba(12, 66, 38, 0.78);
  color: #9bf4c0;
  border-color: rgba(155, 244, 192, 0.18);
}

.toggle-button.inactive {
  background: rgba(35, 46, 67, 0.72);
  color: var(--text-muted);
  border-color: rgba(144, 187, 255, 0.14);
}

.delete-button {
  background: rgba(73, 17, 33, 0.76);
  color: #ffb4c1;
  border-color: rgba(255, 125, 148, 0.2);
}

.loading-card {
  min-height: 108px;
  border-radius: 24px;
}

@media (max-width: 1080px) {
  .keywords-layout,
  .summary-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .keyword-card {
    flex-direction: column;
    align-items: start;
  }

  .keyword-side {
    justify-content: start;
  }
}
</style>
