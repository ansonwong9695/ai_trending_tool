<template>
  <div class="beam-field" aria-hidden="true">
    <span
      v-for="beam in beams"
      :key="beam.id"
      class="beam"
      :style="{
        '--beam-top': beam.top,
        '--beam-left': beam.left,
        '--beam-angle': beam.angle,
        '--beam-duration': beam.duration,
        '--beam-delay': beam.delay,
      }"
    ></span>
    <div class="beam-grid"></div>
  </div>
</template>

<script setup>
const beams = [
  { id: 1, top: '12%', left: '-6%', angle: '-18deg', duration: '18s', delay: '-5s' },
  { id: 2, top: '28%', left: '18%', angle: '-12deg', duration: '22s', delay: '-9s' },
  { id: 3, top: '56%', left: '8%', angle: '-8deg', duration: '20s', delay: '-3s' },
  { id: 4, top: '72%', left: '34%', angle: '-6deg', duration: '24s', delay: '-14s' },
]
</script>

<style scoped>
.beam-field {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.9), transparent 94%);
}

.beam-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(114, 165, 255, 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(114, 165, 255, 0.12) 1px, transparent 1px);
  background-size: 88px 88px;
  opacity: 0.12;
}

.beam {
  position: absolute;
  top: var(--beam-top);
  left: var(--beam-left);
  width: 42rem;
  height: 1px;
  opacity: 0.58;
  transform: rotate(var(--beam-angle));
  background: linear-gradient(90deg, transparent, rgba(98, 179, 255, 0.22), rgba(44, 246, 201, 0.66), rgba(98, 179, 255, 0.18), transparent);
  box-shadow: 0 0 20px rgba(98, 179, 255, 0.3);
  animation: beam-drift var(--beam-duration) linear infinite;
  animation-delay: var(--beam-delay);
}

.beam::after {
  content: '';
  position: absolute;
  right: 18%;
  top: 50%;
  width: 8rem;
  height: 8rem;
  transform: translateY(-50%);
  border-radius: 999px;
  background: radial-gradient(circle, rgba(44, 246, 201, 0.18) 0%, rgba(44, 246, 201, 0) 70%);
}

@keyframes beam-drift {
  0% {
    transform: rotate(var(--beam-angle)) translateX(-10%);
    opacity: 0.2;
  }
  20% {
    opacity: 0.6;
  }
  100% {
    transform: rotate(var(--beam-angle)) translateX(32%);
    opacity: 0.15;
  }
}

@media (prefers-reduced-motion: reduce) {
  .beam {
    animation: none;
    opacity: 0.35;
  }
}
</style>
