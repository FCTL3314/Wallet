<script setup lang="ts">
const year = new Date().getFullYear()
</script>

<template>
  <footer class="app-footer">
    <div class="footer-gradient" />
    <div class="footer-inner">
      <span class="footer-brand">Wallet</span>
      <span class="footer-copy">&copy; {{ year }}</span>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card-solid);
  overflow: hidden;
  margin-top: var(--gap-section);
}

.footer-gradient {
  height: 2px;
  background: linear-gradient(
    90deg,
    var(--color-accent) 0%,
    var(--color-cyan) 50%,
    var(--color-income) 100%
  );
}

.footer-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
}

.footer-brand {
  font-family: var(--font-display);
  font-size: 0.9375rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-accent);
}

.footer-copy {
  font-family: var(--font-body);
  font-size: 0.75rem;
  color: var(--text-label);
}

@media (max-width: 640px) {
  .app-footer {
    display: none;
  }
}
</style>
