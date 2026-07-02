<template>
  <article class="bento-card" :class="[spanClass, toneClass]">
    <div class="bento-header">
      <p v-if="eyebrow" class="eyebrow">{{ eyebrow }}</p>
      <slot name="meta"></slot>
    </div>
    <div class="bento-main">
      <slot name="header"></slot>
      <h3 class="bento-title">{{ title }}</h3>
      <p v-if="description" class="bento-description">{{ description }}</p>
    </div>
    <slot name="footer"></slot>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  eyebrow: { type: String, default: '' },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  span: { type: String, default: '1' },
  tone: { type: String, default: 'default' },
})

const spanClass = computed(() => `span-${props.span}`)
const toneClass = computed(() => `tone-${props.tone}`)
</script>

<style scoped>
.bento-card {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 1rem;
  min-height: 220px;
  padding: 1.35rem;
  overflow: hidden;
  border-radius: 26px;
  border: 1px solid rgba(144, 187, 255, 0.16);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.05), transparent 28%),
    rgba(8, 18, 34, 0.86);
  box-shadow: 0 18px 48px rgba(4, 9, 19, 0.28);
  transition: transform 200ms ease, border-color 200ms ease, box-shadow 200ms ease;
}

.bento-card::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(circle at top right, rgba(98, 179, 255, 0.18), transparent 34%);
}

.bento-card:hover {
  transform: translateY(-4px);
  border-color: rgba(144, 187, 255, 0.3);
  box-shadow: 0 28px 64px rgba(4, 9, 19, 0.42);
}

.bento-header,
.bento-main {
  position: relative;
  z-index: 1;
}

.bento-header {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: start;
}

.bento-main {
  display: grid;
  gap: 0.6rem;
}

.bento-title {
  font-size: 1.2rem;
  color: var(--text);
}

.bento-description {
  font-size: 0.92rem;
  color: var(--text-muted);
  max-width: 28rem;
}

.tone-accent::before {
  background: radial-gradient(circle at top right, rgba(44, 246, 201, 0.14), transparent 34%);
}

.tone-primary::before {
  background: radial-gradient(circle at top right, rgba(98, 179, 255, 0.2), transparent 34%);
}

.tone-warning::before {
  background: radial-gradient(circle at top right, rgba(255, 198, 109, 0.16), transparent 34%);
}

.span-2 {
  grid-column: span 2;
}

.span-3 {
  grid-column: span 3;
}

@media (max-width: 960px) {
  .span-2,
  .span-3 {
    grid-column: span 1;
  }
}
</style>
