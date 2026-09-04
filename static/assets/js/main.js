/* ============================================================
   TESTIFY — Main JS (shared helpers, components, toast, modal)
   ============================================================ */

/* ---------- Toast ---------- */
function ensureToastWrap() {
  let wrap = document.querySelector('.toast-wrap');
  if (!wrap) {
    wrap = document.createElement('div');
    wrap.className = 'toast-wrap';
    document.body.appendChild(wrap);
  }
  return wrap;
}
function toast(msg, opts = {}) {
  const { title = 'Notification', type = 'info', duration = 3200 } = opts;
  const icons = {
    success: '<svg class="t-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
    error: '<svg class="t-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>',
    info: '<svg class="t-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
  };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `${icons[type] || icons.info}<div class="t-body"><div class="t-title">${title}</div><div class="t-msg">${msg}</div></div>`;
  ensureToastWrap().appendChild(el);
  requestAnimationFrame(() => el.classList.add('show'));
  setTimeout(() => {
    el.classList.remove('show');
    setTimeout(() => el.remove(), 500);
  }, duration);
}

/* ---------- Modal ---------- */
function openModal(id) {
  const m = document.getElementById(id);
  if (m) { m.classList.add('open'); document.body.style.overflow = 'hidden'; }
}
function closeModal(id) {
  const m = document.getElementById(id);
  if (m) { m.classList.remove('open'); document.body.style.overflow = ''; }
}
function initModals() {
  document.querySelectorAll('.modal-backdrop').forEach(bd => {
    bd.addEventListener('click', e => { if (e.target === bd) closeModal(bd.id); });
    bd.querySelectorAll('[data-close], .modal-close').forEach(btn => {
      btn.addEventListener('click', () => closeModal(bd.id));
    });
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') document.querySelectorAll('.modal-backdrop.open').forEach(m => closeModal(m.id));
  });
}

/* ---------- Confirm dialog ---------- */
function confirmAction(message, onConfirm, opts = {}) {
  const { title = 'Are you sure?', confirmText = 'Confirm', danger = true } = opts;
  let modal = document.getElementById('confirm-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'confirm-modal';
    modal.className = 'modal-backdrop';
    modal.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="cm-title">
        <div class="modal-head"><h3 id="cm-title">${title}</h3><button class="modal-close" aria-label="Close"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button></div>
        <div class="modal-body"><p class="text-muted">${message}</p></div>
        <div class="modal-foot"><button class="btn btn-secondary" data-close>Cancel</button><button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" id="cm-confirm">${confirmText}</button></div>
      </div>`;
    document.body.appendChild(modal);
    initModals();
  } else {
    modal.querySelector('#cm-title').textContent = title;
    modal.querySelector('.modal-body p').textContent = message;
    modal.querySelector('#cm-confirm').textContent = confirmText;
    modal.querySelector('#cm-confirm').className = `btn ${danger ? 'btn-danger' : 'btn-primary'}`;
  }
  const confirmBtn = modal.querySelector('#cm-confirm');
  const handler = () => { closeModal('confirm-modal'); onConfirm(); confirmBtn.removeEventListener('click', handler); };
  confirmBtn.addEventListener('click', handler);
  openModal('confirm-modal');
}

/* ---------- Counter animation ---------- */
function animateCounters() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseFloat(el.dataset.count);
    const suffix = el.dataset.suffix || '';
    const decimals = parseInt(el.dataset.decimals || '0', 10);
    const duration = 1200;
    const start = performance.now();
    function frame(now) {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      const val = target * eased;
      el.textContent = (decimals ? val.toFixed(decimals) : Math.round(val).toLocaleString()) + suffix;
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  });
}

/* ---------- Tabs ---------- */
function initTabs() {
  document.querySelectorAll('[data-tabs]').forEach(group => {
    const tabs = group.querySelectorAll('.tab');
    const panes = group.querySelectorAll('.tab-pane');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const target = tab.dataset.tab;
        tabs.forEach(t => t.classList.toggle('active', t === tab));
        panes.forEach(p => p.classList.toggle('active', p.dataset.tabPane === target));
      });
    });
  });
}

/* ---------- Accordion ---------- */
function initAccordion() {
  document.querySelectorAll('.acc-item').forEach(item => {
    const trigger = item.querySelector('.acc-trigger');
    const body = item.querySelector('.acc-body');
    if (!trigger || !body) return;
    trigger.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      if (isOpen) {
        body.style.maxHeight = '0';
        item.classList.remove('open');
      } else {
        item.classList.add('open');
        body.style.maxHeight = body.scrollHeight + 'px';
      }
    });
  });
}

/* ---------- Dropdowns ---------- */
function initDropdowns() {
  document.querySelectorAll('.dropdown').forEach(dd => {
    const trigger = dd.querySelector('.dropdown-trigger');
    if (!trigger) return;
    trigger.addEventListener('click', e => {
      e.stopPropagation();
      const wasOpen = dd.classList.contains('open');
      document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
      if (!wasOpen) dd.classList.add('open');
    });
  });
  document.addEventListener('click', () => {
    document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
  });
}

/* ---------- Password visibility ---------- */
function initPasswordToggles() {
  document.querySelectorAll('.input-toggle[data-toggle-password]').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.closest('.input-group').querySelector('input');
      if (!input) return;
      const isPw = input.type === 'password';
      input.type = isPw ? 'text' : 'password';
      btn.innerHTML = isPw
        ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>'
        : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>';
    });
  });
}

/* ---------- Form validation demo ---------- */
function initFormValidation() {
  document.querySelectorAll('form[data-validate]').forEach(form => {
    form.addEventListener('submit', e => {
      e.preventDefault();
      let valid = true;
      form.querySelectorAll('[required]').forEach(field => {
        const group = field.closest('.form-group') || field.parentElement;
        const errEl = group.querySelector('.form-error');
        field.classList.remove('is-invalid');
        if (errEl) errEl.style.display = 'none';
        if (!field.value.trim()) {
          field.classList.add('is-invalid');
          if (errEl) errEl.style.display = 'block';
          valid = false;
        } else if (field.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(field.value)) {
          field.classList.add('is-invalid');
          if (errEl) { errEl.textContent = 'Please enter a valid email address.'; errEl.style.display = 'block'; }
          valid = false;
        }
      });
      const pw = form.querySelector('[data-match]');
      if (pw) {
        const target = form.querySelector(pw.dataset.match);
        if (target && pw.value !== target.value) {
          pw.classList.add('is-invalid');
          const errEl = pw.closest('.form-group').querySelector('.form-error');
          if (errEl) { errEl.textContent = 'Passwords do not match.'; errEl.style.display = 'block'; }
          valid = false;
        }
      }
      if (valid) {
        // Forms with a real backend action (e.g. login: action="{% url 'login' %}")
        // should actually submit to the server instead of faking success client-side.
        const action = form.getAttribute('action');
        const isLiveForm = action && action.trim() !== '' && action.trim() !== '#';

        if (isLiveForm) {
          const submitBtn = form.querySelector('[type="submit"]');
          if (submitBtn) submitBtn.classList.add('is-loading');
          form.submit();
          return;
        }

        const submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) {
          submitBtn.classList.add('is-loading');
          setTimeout(() => {
            submitBtn.classList.remove('is-loading');
            toast('Your action was processed successfully.', { title: 'Success', type: 'success' });
            form.reset();
          }, 900);
        }
      } else {
        toast('Please fix the highlighted fields.', { title: 'Check your input', type: 'error' });
      }
    });
  });
}

/* ---------- Static search/filter ---------- */
function initStaticSearch() {
  document.querySelectorAll('[data-search-input]').forEach(input => {
    const targetSel = input.dataset.searchInput;
    const target = document.querySelector(targetSel);
    if (!target) return;
    const rows = Array.from(target.querySelectorAll('[data-search-row]'));
    input.addEventListener('input', () => {
      const q = input.value.toLowerCase().trim();
      rows.forEach(row => {
        const text = (row.dataset.searchText || row.textContent).toLowerCase();
        row.style.display = text.includes(q) ? '' : 'none';
      });
    });
  });
  document.querySelectorAll('[data-filter-select]').forEach(sel => {
    const target = document.querySelector(sel.dataset.filterSelect);
    if (!target) return;
    const rows = Array.from(target.querySelectorAll('[data-filter-row]'));
    sel.addEventListener('change', () => {
      const val = sel.value;
      rows.forEach(row => {
        const match = !val || row.dataset.filterValue === val;
        row.style.display = match ? '' : 'none';
      });
    });
  });
}

/* ---------- Loading state demo ---------- */
function initLoadingDemo() {
  document.querySelectorAll('[data-loader]').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.classList.add('is-loading');
      setTimeout(() => btn.classList.remove('is-loading'), 1200);
    });
  });
}

/* ---------- Page loader ---------- */
function hidePageLoader() {
  const loader = document.querySelector('.page-loader');
  if (loader) {
    loader.classList.add('hide');
    setTimeout(() => loader.remove(), 500);
  }
}

/* ---------- Boot ---------- */
document.addEventListener('DOMContentLoaded', () => {
  initModals();
  initTabs();
  initAccordion();
  initDropdowns();
  initPasswordToggles();
  initFormValidation();
  initStaticSearch();
  initLoadingDemo();
  animateCounters();
  hidePageLoader();
});