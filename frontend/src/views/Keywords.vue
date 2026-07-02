<template>
  <div class="keywords-page">
    <div class="page-header">
      <h2>关键词管理</h2>
    </div>

    <div class="add-keyword card">
      <h3>添加关键词</h3>
      <form @submit.prevent="addKeyword" class="add-form">
        <input
          v-model="newKeyword"
          class="input"
          placeholder="输入关键词，如：Claude AI、大模型、GPT-5"
          :disabled="adding"
        />
        <div class="source-checkboxes">
          <label v-for="s in SOURCES" :key="s.value" class="source-check">
            <input type="checkbox" :value="s.value" v-model="selectedSources" />
            {{ s.label }}
          </label>
        </div>
        <div v-if="addError" class="alert-error">{{ addError }}</div>
        <button type="submit" class="btn btn-primary" :disabled="adding || !newKeyword.trim()">
          {{ adding ? '添加中...' : '添加' }}
        </button>
      </form>
    </div>

    <div v-if="error" class="alert-error">{{ error }}</div>

    <div v-if="loading" class="loading-list">
      <div class="card skeleton" v-for="i in 3" :key="i"></div>
    </div>

    <div v-else-if="keywords.length === 0" class="empty-state">
      <div class="empty-icon">🔍</div>
      <p>还没有添加关键词</p>
      <p class="empty-hint">添加关键词后，系统将每30分钟自动监控相关热点</p>
    </div>

    <ul v-else class="keyword-list">
      <li v-for="kw in keywords" :key="kw.id" class="card keyword-item">
        <div class="kw-info">
          <span class="kw-name">{{ kw.keyword }}</span>
          <div class="kw-sources">
            <span v-for="src in (kw.sources || defaultSources)" :key="src" class="source-tag">
              {{ src }}
            </span>
          </div>
        </div>
        <div class="kw-actions">
          <span class="kw-date">{{ formatDate(kw.created_at) }}</span>
          <button
            class="btn-toggle"
            :class="kw.is_active ? 'active' : 'inactive'"
            @click="toggleKeyword(kw)"
            :title="kw.is_active ? '点击暂停监控' : '点击启用监控'"
          >
            {{ kw.is_active ? '监控中' : '已暂停' }}
          </button>
          <button class="btn-delete" @click="deleteKeyword(kw.id)" title="删除">✕</button>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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
    const kw = await keywordsApi.create({
      keyword: newKeyword.value.trim(),
      sources: selectedSources.value.length ? selectedSources.value : defaultSources,
    })
    keywords.value.unshift(kw)
    newKeyword.value = ''
    selectedSources.value = [...defaultSources]
  } catch (e) {
    addError.value = e.message
  } finally {
    adding.value = false
  }
}

async function toggleKeyword(kw) {
  try {
    const updated = await keywordsApi.update(kw.id, { is_active: !kw.is_active })
    const idx = keywords.value.findIndex(k => k.id === kw.id)
    if (idx !== -1) keywords.value[idx] = updated
  } catch (e) {
    error.value = e.message
  }
}

async function deleteKeyword(id) {
  if (!confirm('确认删除该关键词？')) return
  try {
    await keywordsApi.delete(id)
    keywords.value = keywords.value.filter(k => k.id !== id)
  } catch (e) {
    error.value = e.message
  }
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

onMounted(fetchKeywords)
</script>

<style scoped>
.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  font-size: 2rem;
}

.add-keyword {
  margin-bottom: 1.5rem;
}

.add-keyword h3 {
  font-size: 1.1rem;
  margin-bottom: 1rem;
  color: var(--color-text-secondary);
  font-weight: 600;
}

.add-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.source-checkboxes {
  display: flex;
  gap: 1.25rem;
  flex-wrap: wrap;
}

.source-check {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.source-check input {
  accent-color: var(--color-primary);
  width: 16px;
  height: 16px;
}

.alert-error {
  background: #FEE2E2;
  color: #B91C1C;
  border-radius: 8px;
  padding: 0.6rem 0.9rem;
  font-size: 0.875rem;
}

.loading-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.skeleton {
  height: 72px;
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
  padding: 3rem 2rem;
  color: var(--color-text-secondary);
}

.empty-icon {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
}

.empty-hint {
  font-size: 0.875rem;
  margin-top: 0.4rem;
  opacity: 0.7;
}

.keyword-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.keyword-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.kw-info {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.kw-name {
  font-weight: 600;
  font-size: 1.05rem;
}

.kw-sources {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.source-tag {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  background: var(--color-bg);
  border-radius: 4px;
  color: var(--color-text-secondary);
}

.kw-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.kw-date {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.btn-toggle {
  font-size: 0.8rem;
  padding: 0.3rem 0.85rem;
  border-radius: 20px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-toggle.active {
  background: #DCFCE7;
  color: #15803D;
}

.btn-toggle.inactive {
  background: #F3F4F6;
  color: #6B7280;
}

.btn-delete {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-delete:hover {
  background: #FEE2E2;
  color: #B91C1C;
}
</style>
