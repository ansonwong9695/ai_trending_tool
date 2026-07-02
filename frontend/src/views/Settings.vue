<template>
  <div class="page-shell settings-page">
    <section class="intro panel">
      <div>
        <p class="eyebrow">Delivery controls</p>
        <h2>让重要热点更快到你面前，也更稳地发出去。</h2>
      </div>
      <div class="intro-pills">
        <span class="pill" :class="form.enable_email ? 'success' : 'danger'">
          {{ form.enable_email ? '邮件通知已开启' : '邮件通知未开启' }}
        </span>
        <span class="pill" :class="form.daily_summary ? 'warning' : ''">
          {{ form.daily_summary ? '每日摘要 09:00' : '每日摘要已关闭' }}
        </span>
      </div>
    </section>

    <section class="settings-grid">
      <div class="panel settings-card">
        <div class="card-heading">
          <div>
            <p class="eyebrow">Notify</p>
            <h3 class="section-title">通知设置</h3>
          </div>
          <span class="pill">{{ form.notification_email || 'No inbox yet' }}</span>
        </div>

        <div v-if="loading" class="settings-loading loading-card"></div>

        <div v-else class="settings-form">
          <div class="toggle-row">
            <div>
              <p class="toggle-title">启用邮件通知</p>
              <p class="text-muted">当监控到热点时，通过邮件把信号推到你的收件箱。</p>
            </div>
            <button
              class="toggle-switch"
              :class="{ on: form.enable_email }"
              @click="form.enable_email = !form.enable_email"
              :aria-pressed="String(form.enable_email)"
            >
              <span></span>
            </button>
          </div>

          <div v-if="form.enable_email" class="input-shell">
            <label class="input-label" for="notification-email">通知邮箱</label>
            <input
              id="notification-email"
              v-model="form.notification_email"
              class="input"
              type="email"
              placeholder="you@domain.com"
            />
          </div>

          <div class="toggle-row">
            <div>
              <p class="toggle-title">每日热点摘要</p>
              <p class="text-muted">每天 09:00 自动发送当日精选热点，适合回顾和二次整理。</p>
            </div>
            <button
              class="toggle-switch"
              :class="{ on: form.daily_summary }"
              @click="form.daily_summary = !form.daily_summary"
              :aria-pressed="String(form.daily_summary)"
            >
              <span></span>
            </button>
          </div>

          <div v-if="saveError" class="alert error">{{ saveError }}</div>
          <div v-if="saveSuccess" class="alert success">设置已保存</div>

          <div class="actions">
            <AceternityGlowButton :disabled="saving" @click="saveSettings">
              {{ saving ? '保存中...' : '保存设置' }}
            </AceternityGlowButton>
          </div>
        </div>
      </div>

      <div class="side-stack">
        <div class="panel ops-card">
          <div class="card-heading">
            <div>
              <p class="eyebrow">Operations</p>
              <h3 class="section-title">通知测试</h3>
            </div>
          </div>

          <div class="ops-list">
            <div class="ops-item">
              <div>
                <p class="toggle-title">发送测试邮件</p>
                <p class="text-muted">验证 SMTP 配置、收件箱和模板是否正常。</p>
              </div>
              <button class="ghost-button" @click="testEmail" :disabled="testingEmail">
                {{ testingEmail ? '发送中...' : '发送测试' }}
              </button>
            </div>

            <div class="ops-item">
              <div>
                <p class="toggle-title">触发每日摘要</p>
                <p class="text-muted">立即发送一封模拟当日摘要，检查最终交付体验。</p>
              </div>
              <button class="ghost-button" @click="triggerSummary" :disabled="triggeringSummary">
                {{ triggeringSummary ? '发送中...' : '立即发送' }}
              </button>
            </div>
          </div>

          <div v-if="testMessage" class="alert success">{{ testMessage }}</div>
          <div v-if="testError" class="alert error">{{ testError }}</div>
        </div>

        <div class="panel insight-card">
          <p class="eyebrow">System note</p>
          <h3 class="section-title">这套通知流的目标</h3>
          <p class="section-copy">
            平时用关键词和热点流筛掉噪声，真正有价值的内容再用邮件和摘要送出来。即时性和可回顾性都要有，但谁也不能压过主界面的判断效率。
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import AceternityGlowButton from '../components/AceternityGlowButton.vue'
import { notificationsApi, settingsApi } from '../services/api.js'

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
    // Keep defaults when settings are not initialized yet.
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
    setTimeout(() => {
      saveSuccess.value = false
    }, 3000)
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
    setTimeout(() => {
      testMessage.value = ''
    }, 4000)
  } catch (e) {
    testError.value = e.message
    setTimeout(() => {
      testError.value = ''
    }, 4000)
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
    setTimeout(() => {
      testMessage.value = ''
    }, 4000)
  } catch (e) {
    testError.value = e.message
    setTimeout(() => {
      testError.value = ''
    }, 4000)
  } finally {
    triggeringSummary.value = false
  }
}

onMounted(fetchSettings)
</script>

<style scoped>
.settings-page {
  gap: 1.35rem;
}

.intro {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 1.2rem;
}

.intro h2 {
  font-size: clamp(1.8rem, 3vw, 2.8rem);
  max-width: 14ch;
}

.intro-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  gap: 1rem;
}

.settings-card,
.ops-card,
.insight-card {
  padding: 1.2rem;
}

.card-heading {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: start;
  margin-bottom: 1rem;
}

.settings-form,
.side-stack {
  display: grid;
  gap: 1rem;
}

.settings-loading {
  min-height: 320px;
  border-radius: 22px;
}

.toggle-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 1rem;
  border-radius: 20px;
  border: 1px solid rgba(144, 187, 255, 0.12);
  background: rgba(8, 18, 33, 0.68);
}

.toggle-title {
  font-weight: 700;
  margin-bottom: 0.15rem;
}

.toggle-switch {
  position: relative;
  flex-shrink: 0;
  width: 58px;
  height: 32px;
  padding: 3px;
  border-radius: 999px;
  background: rgba(52, 68, 96, 0.8);
  border: 1px solid rgba(144, 187, 255, 0.12);
  transition: background 180ms ease;
}

.toggle-switch span {
  display: block;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #f3f7ff;
  transform: translateX(0);
  transition: transform 180ms ease;
}

.toggle-switch.on {
  background: linear-gradient(135deg, rgba(98, 179, 255, 0.88), rgba(44, 246, 201, 0.76));
}

.toggle-switch.on span {
  transform: translateX(26px);
}

.actions {
  display: flex;
}

.ops-list {
  display: grid;
  gap: 0.85rem;
}

.ops-item {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 1rem;
  border-radius: 20px;
  border: 1px solid rgba(144, 187, 255, 0.12);
  background: rgba(8, 18, 33, 0.66);
}

.insight-card {
  display: grid;
  gap: 0.75rem;
}

@media (max-width: 1080px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .toggle-row,
  .ops-item {
    flex-direction: column;
    align-items: start;
  }
}
</style>
