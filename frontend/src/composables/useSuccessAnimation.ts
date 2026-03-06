let styleInjected = false

function injectStyles() {
  if (styleInjected) return
  styleInjected = true
  const style = document.createElement('style')
  style.textContent = `
    @keyframes particle-rise {
      0%   { transform: translate(var(--tx), 0) scale(1); opacity: 1; }
      100% { transform: translate(var(--tx), -80px) scale(0); opacity: 0; }
    }
    .success-particle {
      position: fixed;
      border-radius: 50%;
      pointer-events: none;
      z-index: 9999;
      animation: particle-rise var(--dur) ease-out var(--delay) forwards;
    }
  `
  document.head.appendChild(style)
}

const COLORS = ['#2272cc', '#1fa068', '#f5c832', '#e84565']

export function useSuccessAnimation() {
  function spawn({ x, y, count = 12 }: { x: number; y: number; count?: number }) {
    injectStyles()
    for (let i = 0; i < count; i++) {
      const el = document.createElement('div')
      el.className = 'success-particle'
      const size = 6 + Math.random() * 8
      const tx = (Math.random() - 0.5) * 80
      const dur = 0.6 + Math.random() * 0.5
      const delay = Math.random() * 0.2
      const color = COLORS[Math.floor(Math.random() * COLORS.length)]
      el.style.cssText = `
        left: ${x - size / 2}px;
        top: ${y - size / 2}px;
        width: ${size}px;
        height: ${size}px;
        background: ${color};
        --tx: ${tx}px;
        --dur: ${dur}s;
        --delay: ${delay}s;
      `
      document.body.appendChild(el)
      setTimeout(() => el.remove(), (dur + delay + 0.1) * 1000)
    }
  }

  return { spawn }
}
