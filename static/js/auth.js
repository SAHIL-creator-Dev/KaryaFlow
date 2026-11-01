/**
 * KaryaFlow — Authentication Interactions (auth.js)
 * Features:
 * - Password visibility toggle with accessible state updates
 * - Client-side confirmation matching validation
 * - Password requirement indicator updates
 * - Double-submission prevention with loading state
 * - Lucide icons initialization
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Password Visibility Toggles
  const toggleButtons = document.querySelectorAll('.password-toggle-btn');
  toggleButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (!input) return;

      const isPassword = input.getAttribute('type') === 'password';
      input.setAttribute('type', isPassword ? 'text' : 'password');

      // Update button aria-label
      btn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');

      // Swap Lucide icon
      btn.innerHTML = isPassword 
        ? '<i data-lucide="eye-off" class="toggle-icon"></i>' 
        : '<i data-lucide="eye" class="toggle-icon"></i>';

      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    });
  });

  // 2. Registration Password Real-time Checks & Confirmation Validation
  const regPassword = document.getElementById('id_password');
  const regConfirm = document.getElementById('id_confirm_password');
  const confirmError = document.getElementById('confirmPasswordError');

  // Password requirements items
  const reqLength = document.getElementById('reqLength');
  const reqNumber = document.getElementById('reqNumber');

  if (regPassword) {
    regPassword.addEventListener('input', () => {
      const val = regPassword.value;
      
      // Check min length (8 chars)
      if (reqLength) {
        if (val.length >= 8) {
          reqLength.classList.add('met');
        } else {
          reqLength.classList.remove('met');
        }
      }

      // Check number
      if (reqNumber) {
        if (/\d/.test(val)) {
          reqNumber.classList.add('met');
        } else {
          reqNumber.classList.remove('met');
        }
      }

      // Re-validate match if confirm has value
      if (regConfirm && regConfirm.value) {
        validatePasswordMatch();
      }
    });
  }

  function validatePasswordMatch() {
    if (!regPassword || !regConfirm) return true;
    if (regConfirm.value && regPassword.value !== regConfirm.value) {
      if (confirmError) {
        confirmError.style.display = 'flex';
      }
      regConfirm.classList.add('is-invalid');
      regConfirm.classList.remove('is-valid');
      return false;
    } else if (regConfirm.value && regPassword.value === regConfirm.value) {
      if (confirmError) {
        confirmError.style.display = 'none';
      }
      regConfirm.classList.remove('is-invalid');
      regConfirm.classList.add('is-valid');
      return true;
    } else {
      if (confirmError) {
        confirmError.style.display = 'none';
      }
      regConfirm.classList.remove('is-invalid');
      regConfirm.classList.remove('is-valid');
      return true;
    }
  }

  if (regConfirm) {
    regConfirm.addEventListener('input', validatePasswordMatch);
  }

  // 3. Double-Submission Prevention & Loading Feedback
  const authForms = document.querySelectorAll('form.auth-form');
  authForms.forEach(form => {
    form.addEventListener('submit', (e) => {
      // Validate match if registration
      if (regPassword && regConfirm && !validatePasswordMatch()) {
        e.preventDefault();
        regConfirm.focus();
        return;
      }

      const submitBtn = form.querySelector('.btn-auth-submit');
      if (submitBtn) {
        if (submitBtn.classList.contains('is-submitting')) {
          e.preventDefault();
          return;
        }

        submitBtn.classList.add('is-submitting');
        submitBtn.setAttribute('disabled', 'true');

        const submitText = submitBtn.querySelector('.submit-text');
        if (submitText) {
          const loadingLabel = submitBtn.getAttribute('data-loading-text') || 'Processing...';
          submitText.textContent = loadingLabel;
        }
      }
    });
  });

  // 4. Initialize Lucide Icons
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});
