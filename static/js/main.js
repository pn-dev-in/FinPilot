/* FinPilot — Main JS */

// Sidebar toggle (mobile)
const sidebar = document.getElementById('sidebar');
const menuToggle = document.getElementById('menuToggle');
const sidebarClose = document.getElementById('sidebarClose');
const sidebarOverlay = document.getElementById('sidebarOverlay');

function openSidebar() {
  sidebar && sidebar.classList.add('open');
  sidebarOverlay && sidebarOverlay.classList.add('open');
}
function closeSidebar() {
  sidebar && sidebar.classList.remove('open');
  sidebarOverlay && sidebarOverlay.classList.remove('open');
}

menuToggle && menuToggle.addEventListener('click', openSidebar);
sidebarClose && sidebarClose.addEventListener('click', closeSidebar);
sidebarOverlay && sidebarOverlay.addEventListener('click', closeSidebar);

// Modals
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('open');
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('open');
}

// Close modal on overlay click
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

// Close modal on Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(el => el.classList.remove('open'));
  }
});

// Tab switching inside modals
function switchTab(btn, tabId) {
  const modal = btn.closest('.modal');
  if (!modal) return;

  // Deactivate all tabs & panels
  modal.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
  modal.querySelectorAll('.modal-body').forEach(b => b.style.display = 'none');

  // Activate selected
  btn.classList.add('active');
  const panel = document.getElementById(tabId);
  if (panel) panel.style.display = '';
}

// Auto-dismiss toasts after 4 seconds
setTimeout(() => {
  document.querySelectorAll('.toast').forEach(t => {
    t.style.transition = 'opacity .3s';
    t.style.opacity = '0';
    setTimeout(() => t.remove(), 300);
  });
}, 4000);

// Format numbers in Indian style (for any data-format elements)
document.querySelectorAll('[data-format="currency"]').forEach(el => {
  const val = parseFloat(el.textContent);
  if (!isNaN(val)) {
    el.textContent = val.toLocaleString('en-IN');
  }
});
