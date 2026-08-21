/* ============================================================
   TESTIFY — Animations (scroll reveal, stagger, counters)
   ============================================================ */

/* ---------- Scroll reveal ---------- */
function initScrollReveal() {
  const els = document.querySelectorAll('[data-reveal]');
  if (!els.length) return;
  if (!('IntersectionObserver' in window)) {
    els.forEach(el => el.classList.add('in'));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  els.forEach(el => io.observe(el));
}

/* ---------- Stagger children ---------- */
function initStagger() {
  document.querySelectorAll('[data-stagger]').forEach(group => {
    const children = group.querySelectorAll(':scope > *');
    const step = parseInt(group.dataset.stagger || '90', 10);
    children.forEach((child, i) => {
      child.style.setProperty('--reveal-delay', (i * step) + 'ms');
      if (!child.hasAttribute('data-reveal')) child.setAttribute('data-reveal', '');
    });
  });
}

/* ---------- Progress bar fill on reveal ---------- */
function initProgressFill() {
  const bars = document.querySelectorAll('[data-progress]');
  if (!bars.length) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const val = el.dataset.progress;
        el.style.width = val + '%';
        io.unobserve(el);
      }
    });
  }, { threshold: 0.3 });
  bars.forEach(b => { b.style.width = '0'; io.observe(b); });
}

/* ---------- Bar chart fill ---------- */
function initBarChart() {
  const charts = document.querySelectorAll('[data-bar-chart]');
  if (!charts.length) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.querySelectorAll('[data-bar]').forEach((bar, i) => {
          const h = bar.dataset.bar;
          setTimeout(() => { bar.style.height = h; }, i * 80);
        });
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });
  charts.forEach(c => {
    c.querySelectorAll('[data-bar]').forEach(b => { b.style.height = '0'; });
    io.observe(c);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initStagger();
  initScrollReveal();
  initProgressFill();
  initBarChart();
});
