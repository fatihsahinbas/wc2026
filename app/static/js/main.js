/* WC2026 — main.js */
'use strict';

// ── Flash message auto-dismiss ──────────────────────────────────
document.querySelectorAll('.flash').forEach(el => {
  setTimeout(() => {
    el.style.transition = 'opacity .4s, transform .4s';
    el.style.opacity = '0';
    el.style.transform = 'translateX(110%)';
    setTimeout(() => el.remove(), 400);
  }, 4000);
});

// ── Invite code copy ────────────────────────────────────────────
document.querySelectorAll('.invite-code').forEach(el => {
  el.addEventListener('click', () => {
    navigator.clipboard.writeText(el.textContent.trim()).then(() => {
      const original = el.textContent;
      el.textContent = 'Kopyalandı ✓';
      setTimeout(() => { el.textContent = original; }, 1500);
    });
  });
  el.setAttribute('title', 'Kopyalamak için tıklayın');
});

// ── Match filter ────────────────────────────────────────────────
const filterBtns = document.querySelectorAll('[data-filter]');
filterBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    filterBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const filter = btn.dataset.filter;
    document.querySelectorAll('.match-card-wrapper').forEach(card => {
      if (filter === 'all') {
        card.style.display = '';
      } else {
        card.style.display = card.dataset.status === filter ? '' : 'none';
      }
    });
  });
});

// ── Countdown timers ────────────────────────────────────────────
document.querySelectorAll('[data-countdown]').forEach(el => {
  const target = new Date(el.dataset.countdown).getTime();

  function update() {
    const now = Date.now();
    const diff = target - now;
    if (diff <= 0) {
      el.textContent = 'Başladı';
      return;
    }
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    if (h > 24) {
      el.textContent = `${Math.floor(h/24)}g ${h%24}s`;
    } else {
      el.textContent = `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;
    }
    setTimeout(update, 1000);
  }
  update();
});

// ── Tab switching ───────────────────────────────────────────────
document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
  btn.addEventListener('click', () => {
    const targetId = btn.dataset.tab;
    const parent = btn.closest('.tab-container');

    parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    parent.querySelectorAll('.tab-panel').forEach(p => p.style.display = 'none');

    btn.classList.add('active');
    const panel = parent.querySelector(`#${targetId}`);
    if (panel) panel.style.display = '';
  });
});

// Init: show first tab panel only
document.querySelectorAll('.tab-container').forEach(container => {
  const panels = container.querySelectorAll('.tab-panel');
  panels.forEach((p, i) => { p.style.display = i === 0 ? '' : 'none'; });
  const btns = container.querySelectorAll('.tab-btn');
  if (btns[0]) btns[0].classList.add('active');
});
