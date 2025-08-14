<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div id="app-layout">
    <nav class="sidebar">
      <div class="sidebar-header">
        <h3>Print Vault</h3>
      </div>
      <RouterLink to="/">Inventory</RouterLink>
      <RouterLink to="/printers">Printers</RouterLink>
      <RouterLink to="/projects">Projects</RouterLink>
      <div class="sidebar-footer">
        <RouterLink to="/settings">Settings</RouterLink>
      </div>
    </nav>

    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
#app-layout {
  display: flex;
  height: 100vh;
  background-color: var(--color-background);
}

.sidebar {
  width: 250px;
  flex-shrink: 0;
  background-color: var(--color-background-soft);
  border-right: 1px solid var(--color-border);
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  margin-bottom: 20px;
}

.sidebar h3 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--color-heading);
  white-space: nowrap;
}

.sidebar a {
  text-decoration: none;
  color: var(--color-text);
  font-weight: 500;
  padding: 10px;
  border-radius: 5px;
  transition: background-color 0.3s;
  margin-bottom: 5px;
  user-select: none; /* Prevents text selection cursor */
}

.sidebar a.router-link-exact-active,
.sidebar a:hover {
  background-color: var(--color-background-mute);
  color: var(--color-heading);
}

.sidebar-footer {
  margin-top: auto;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.main-content {
  flex-grow: 1;
  overflow-y: auto;
  padding: 20px;
  min-width: 0;
}
@media (max-width: 768px) {
  #app-layout {
    flex-direction: column;
    height: auto;
  }
  .sidebar {
    width: 100%;
    height: 60px;
    flex-direction: row;
    align-items: center;
    justify-content: space-around;
    padding: 0 10px;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }
  .sidebar-header,
  .sidebar-footer {
    display: none;
  }
}
</style>
