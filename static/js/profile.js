/**
 * KaryaFlow — Profile & Account Settings Interactions (profile.js)
 * Handles:
 * - Password visibility toggles
 * - Avatar file picker preview
 * - Client-side form feedback validation
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Password Visibility Toggle Buttons
  const passwordToggles = document.querySelectorAll('.password-toggle-btn');
  passwordToggles.forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.closest('.form-control-wrap')?.querySelector('input');
      if (!input) return;

      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';

      const icon = btn.querySelector('i');
      if (icon) {
        icon.setAttribute('data-lucide', isPassword ? 'eye-off' : 'eye');
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
      }
    });
  });

  // 2. Avatar Upload Preview (Micro-interaction)
  const avatarInput = document.getElementById('avatarFileInput');
  const avatarTrigger = document.querySelector('.avatar-edit-trigger');
  const avatarPreview = document.getElementById('profileAvatarDisplay');

  if (avatarTrigger && avatarInput) {
    avatarTrigger.addEventListener('click', () => {
      avatarInput.click();
    });

    avatarInput.addEventListener('change', (e) => {
      const file = e.target.files?.[0];
      if (file && avatarPreview) {
        const reader = new FileReader();
        reader.onload = function(evt) {
          avatarPreview.innerHTML = `<img src="${evt.target.result}" alt="Profile avatar preview" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // 3. New Password Confirmation Match Check
  const newPassInput = document.getElementById('newPasswordInput');
  const confirmPassInput = document.getElementById('confirmPasswordInput');
  const matchNotice = document.getElementById('passMatchNotice');

  function checkPasswordMatch() {
    if (!newPassInput || !confirmPassInput || !matchNotice) return;
    if (confirmPassInput.value.length === 0) {
      matchNotice.style.display = 'none';
      return;
    }

    if (newPassInput.value === confirmPassInput.value) {
      matchNotice.textContent = 'Passwords match';
      matchNotice.style.color = 'var(--status-success)';
      matchNotice.style.display = 'block';
    } else {
      matchNotice.textContent = 'Passwords do not match';
      matchNotice.style.color = '#C81E1E';
      matchNotice.style.display = 'block';
    }
  }

  newPassInput?.addEventListener('input', checkPasswordMatch);
  confirmPassInput?.addEventListener('input', checkPasswordMatch);

  // Initialize Lucide icons
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});
