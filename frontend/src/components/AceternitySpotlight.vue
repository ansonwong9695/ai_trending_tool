<template>
  <div class="spotlight" :style="spotlightStyle" aria-hidden="true"></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  top: { type: String, default: '-12%' },
  left: { type: String, default: '50%' },
  size: { type: String, default: '34rem' },
  color: { type: String, default: 'rgba(98, 179, 255, 0.22)' },
  delay: { type: String, default: '0s' },
})

const spotlightStyle = computed(() => ({
  '--spotlight-top': props.top,
  '--spotlight-left': props.left,
  '--spotlight-size': props.size,
  '--spotlight-color': props.color,
  '--spotlight-delay': props.delay,
}))
</script>

<style scoped>
.spotlight {
  position: absolute;
  top: var(--spotlight-top);
  left: var(--spotlight-left);
  width: var(--spotlight-size);
  height: var(--spotlight-size);
  transform: translate3d(-50%, -42%, 0) scale(0.72);
  border-radius: 50%;
  pointer-events: none;
  opacity: 0;
  mix-blend-mode: screen;
  filter: blur(18px);
  background:
    radial-gradient(circle, var(--spotlight-color) 0%, rgba(32, 83, 155, 0.15) 34%, rgba(4, 8, 15, 0) 72%);
  animation: spotlight-enter 1.8s var(--spotlight-delay) cubic-bezier(0.19, 1, 0.22, 1) forwards;
}

@keyframes spotlight-enter {
  0% {
    opacity: 0;
    transform: translate3d(-50%, -42%, 0) scale(0.72);
  }
  100% {
    opacity: 1;
    transform: translate3d(-50%, -50%, 0) scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .spotlight {
    animation: none;
    opacity: 0.9;
    transform: translate3d(-50%, -50%, 0) scale(1);
  }
}
</style>
