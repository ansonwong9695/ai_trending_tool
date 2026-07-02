<template>
  <div class="settings-page">
    <div class="page-header">
      <h2>设置</h2>
    </div>

    <div v-if="loading" class="loading-placeholder card"></div>

    <div v-else class="settings-form">
      <section class="card settings-section">
        <h3>通知设置</h3>
        <div class="form-row">
          <label class="toggle-label">
            <span>启用邮件通知</span>
            <div class="toggle" :class="{ on: form.enable_email }" @click="form.enable_email = !form.enable_email"></div>
          </label>
        </div>
        <div class="form-row" v-if="form.enable_email">
          <label class="field-label">通知邮箱</label>
          <input v-model="form.notification_email" class="input" placeholder="your@email.com" type="email" />
        </div>
        <div class="form-row">
          <label class="toggle-label">
            <span>每日热点摘要（每天9:00）</span>
            <div class="toggle" :class="{ on: form.daily_summary }" @click="form.daily_summary = !form.daily_summary"></div>
          </label>
        </div>
      </section>

<div v-if="saveError" class="alert-error">{{ saveError }}</div>
      <div v-if="saveSuccess" class="alert-success">设置已保存</div>

      <div class="form-actions">
        <button class="btn btn-primary" @click="saveSettings" :disabled="saving">
          {{ saving ? '保存中...' : '保存设置' }}
        </button>
      </div>
    </div>

    <section class="card settings-section notifications-section">
      <h3>通知测试</h3>
      <div class="test-actions">
        <div class="test-item">
          <div>
            <p class="test-name">发送测试邮件</p>
            <p class="test-desc">验证邮件配置是否正常</p>
          </div>
          <button class="btn btn-outline-sm" @click="testEmail" :disabled="testingEmail">
            {{ testingEmail ? '发送中...' : '发送测试' }}
          </button>
        </div>
        <div class="test-item">
          <div>
            <p class="test-name">触发每日摘要</p>
            <p class="test-desc">立即生成并发送今日热点摘要</p>
          </div>
          <button class="btn btn-outline-sm" @click="triggerSummary" :disabled="triggeringSummary">
            {{ triggeringSummary ? '发送中...' : '立即发送' }}
          </button>
        </div>
      </div>
      <div v-if="testMessage" class="alert-success">{{ testMessage }}</div>
      <div v-if="testError" class="alert-error">{{ testError }}</div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { settingsApi, notificationsApi } from '../services/api.js'

const loading = ref(false)
const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref(false)
const testingEmail = ref(false)
const triggeringSummary = ref(false)
const testMessage = ref('')
const testError = ref('')

const form = ref({
  enable_email: false,
  daily_summary: true,
  notification_email: '',
})

async function fetchSettings() {
  loading.value = true
  try {
    const data = await settingsApi.get()
    form.value = {
      enable_email: data.enable_email ?? false,
      daily_summary: data.daily_summary ?? true,
      notification_email: data.notification_email || '',
    }
  } catch {
    // use defaults if no settings yet
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  saveError.value = ''
  saveSuccess.value = false
  try {
    await settingsApi.update(form.value)
    saveSuccess.value = true
    setTimeout(() => { saveSuccess.value = false }, 3000)
  } catch (e) {
    saveError.value = e.message
  } finally {
    saving.value = false
  }
}

async function testEmail() {
  testingEmail.value = true
  testMessage.value = ''
  testError.value = ''
  try {
    await notificationsApi.testEmail()
    testMessage.value = '测试邮件已发送，请检查收件箱'
    setTimeout(() => { testMessage.value = '' }, 4000)
  } catch (e) {
    testError.value = e.message
    setTimeout(() => { testError.value = '' }, 4000)
  } finally {
    testingEmail.value = false
  }
}

async function triggerSummary() {
  triggeringSummary.value = true
  testMessage.value = ''
  testError.value = ''
  try {
    await notificationsApi.dailySummary()
    testMessage.value = '每日摘要已发送'
    setTimeout(() => { testMessage.value = '' }, 4000)
  } catch (e) {
    testError.value = e.message
    setTimeout(() => { testError.value = '' }, 4000)
  } finally {
    triggeringSummary.value = false
  }
}

onMounted(fetchSettings)
</script>

<style scoped>
.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  font-size: 2rem;
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.settings-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.settings-section h3 {
  font-size: 1.1rem;
  color: var(--color-text-secondary);
  font-weight: 600;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-border);
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.field-label {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-text);
}

.field-hint {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.input-sm {
  max-width: 160px;
}

.toggle-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.toggle-label span {
  font-size: 0.95rem;
  font-weight: 500;
}

.toggle {
  width: 44px;
  height: 24px;
  border-radius: 12px;
  background: #D1D5DB;
  position: relative;
  transition: background 0.2s;
  cursor: pointer;
  flex-shrink: 0;
}

.toggle::after {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: white;
  top: 3px;
  left: 3px;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}

.toggle.on {
  background: var(--color-primary);
}

.toggle.on::after {
  transform: translateX(20px);
}

.form-actions {
  display: flex;
  justify-content: flex-start;
}

.alert-error {
  background: #FEE2E2;
  color: #B91C1C;
  border-radius: 8px;
  padding: 0.6rem 0.9rem;
  font-size: 0.875rem;
}

.alert-success {
  background: #DCFCE7;
  color: #15803D;
  border-radius: 8px;
  padding: 0.6rem 0.9rem;
  font-size: 0.875rem;
}

.loading-placeholder {
  height: 200px;
  background: linear-gradient(90deg, #ede8df 25%, #f6f1e8 50%, #ede8df 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  margin-bottom: 1.25rem;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.notifications-section {
  margin-top: 0.25rem;
}

.test-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.test-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.test-name {
  font-weight: 500;
  font-size: 0.95rem;
}

.test-desc {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  margin-top: 0.15rem;
}

.btn-outline-sm {
  border: 1.5px solid var(--color-primary);
  color: var(--color-primary);
  padding: 0.35rem 0.9rem;
  border-radius: 6px;
  background: transparent;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.btn-outline-sm:hover:not(:disabled) {
  background: var(--color-primary);
  color: white;
}

.btn-outline-sm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
