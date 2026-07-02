<template>
  <div class="app">
    <header class="header">
      <h1>AI热点监控</h1>
      <nav>
        <router-link to="/">热点</router-link>
        <router-link to="/keywords">关键词</router-link>
        <router-link to="/settings">设置</router-link>
      </nav>
    </header>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>

<style scoped>
.app {
  min-height: 100vh;
}

.header {
  background: #fff;
  padding: 1.5rem 2rem;
  box-shadow: 0 2px 8px rgba(200, 133, 63, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h1 {
  margin: 0;
  font-size: 1.75rem;
  color: #C8853F;
}

.header nav {
  display: flex;
  gap: 1.5rem;
}

.header nav a {
  color: #4A4A4A;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  transition: all 0.2s;
}

.header nav a:hover {
  background: #F6F1E8;
  color: #C8853F;
}

.header nav a.router-link-active {
  background: #C8853F;
  color: #fff;
}

.main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}
</style>
