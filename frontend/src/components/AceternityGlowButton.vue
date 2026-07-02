<template>
  <component
    :is="resolvedTag"
    class="glow-button"
    :class="variant"
    v-bind="componentProps"
  >
    <span class="glow-border"></span>
    <span class="glow-label">
      <slot />
    </span>
  </component>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  href: { type: String, default: '' },
  to: { type: [String, Object], default: '' },
  type: { type: String, default: 'button' },
  variant: { type: String, default: 'primary' },
  disabled: { type: Boolean, default: false },
  target: { type: String, default: '_self' },
})

const resolvedTag = computed(() => {
  if (props.to) return 'router-link'
  if (props.href) return 'a'
  return 'button'
})

const componentProps = computed(() => {
  if (props.to) return { to: props.to }
  if (props.href) {
    return {
      href: props.href,
      target: props.target,
      rel: props.target === '_blank' ? 'noopener noreferrer' : undefined,
    }
  }
  return {
    type: props.type,
    disabled: props.disabled,
  }
})
</script>

<style scoped>
.glow-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  padding: 0.1rem;
  border-radius: 999px;
  overflow: hidden;
  color: var(--text);
  transition: transform 180ms ease, opacity 180ms ease;
}

.glow-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.glow-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.glow-border {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background:
    linear-gradient(135deg, rgba(98, 179, 255, 0.95), rgba(44, 246, 201, 0.82), rgba(98, 179, 255, 0.95));
  background-size: 200% 200%;
  animation: gradient-shift 4s linear infinite;
}

.glow-label {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  width: 100%;
  min-height: 46px;
  padding: 0 1.2rem;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(10, 24, 44, 0.98), rgba(8, 19, 35, 0.98));
  font-weight: 700;
}

.secondary .glow-border {
  background: linear-gradient(135deg, rgba(255, 198, 109, 0.92), rgba(98, 179, 255, 0.6), rgba(255, 198, 109, 0.92));
}

@keyframes gradient-shift {
  0% {
    background-position: 0% 50%;
  }
  100% {
    background-position: 200% 50%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .glow-border {
    animation: none;
  }
}
</style>
