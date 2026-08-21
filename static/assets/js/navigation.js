/* ============================================================
   TESTIFY — Navigation (header + mobile menu + sidebar)
   ============================================================ */

/* ---------- Header scroll state ---------- */
function initHeaderScroll() {
  const header = document.querySelector('.site-header');
  if (!header) return;
  const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 8);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
}

/* ---------- Mobile menu ---------- */
function initMobileMenu() {
  const menuBtn = document.querySelector('.menu-btn');
  const nav = document.querySelector('.nav');
  if (!menuBtn || !nav) return;
  menuBtn.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    menuBtn.setAttribute('aria-expanded', open);
  });
  document.addEventListener('click', e => {
    if (!nav.contains(e.target) && !menuBtn.contains(e.target)) nav.classList.remove('open');
  });
}

/* ---------- Dashboard sidebar (mobile) ---------- */
function initSidebar() {
  const sidebar = document.querySelector('.sidebar');
  if (!sidebar) return;
  const toggle = document.querySelector('.sidebar-toggle');
  if (!toggle) return;
  let backdrop = document.querySelector('.sidebar-backdrop');
  if (!backdrop) {
    backdrop = document.createElement('div');
    backdrop.className = 'sidebar-backdrop';
    document.body.appendChild(backdrop);
  }
  const close = () => { sidebar.classList.remove('open'); backdrop.classList.remove('open'); };
  toggle.addEventListener('click', () => {
    sidebar.classList.add('open');
    backdrop.classList.add('open');
  });
  backdrop.addEventListener('click', close);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
}

/* ---------- Active link by filename ---------- */
function setActiveNav() {
  let path = window.location.pathname.split('/').pop();
  if (!path || path === '') path = 'index.html';
  document.querySelectorAll('[data-nav]').forEach(link => {
    const href = link.getAttribute('href');
    if (!href) return;
    const target = href.split('/').pop();
    if (target === path) link.classList.add('active');
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initHeaderScroll();
  initMobileMenu();
  initSidebar();
  setActiveNav();
});
