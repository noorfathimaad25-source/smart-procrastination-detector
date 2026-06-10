// ============================================================
// main.js — Main JavaScript
// Smart Procrastination Detector
// ============================================================

document.addEventListener('DOMContentLoaded', function () {

  // Auto-dismiss flash alerts after 4 seconds
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      if (typeof bootstrap !== 'undefined') {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
      }
    }, 4000);
  });

});

// Toggle sidebar on mobile
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.toggle('show');
}

// Toggle inline subtask edit form
function toggleEditForm(subtaskId) {
  const form = document.getElementById('edit-form-' + subtaskId);
  if (form) {
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
  }
}