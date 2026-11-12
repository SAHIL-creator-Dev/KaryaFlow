/**
 * KaryaFlow — Profile & Account Workspace Interactions (profile.js)
 * Handles:
 * - Password visibility toggles
 * - Quick avatar upload & Edit Profile form live avatar preview
 * - Bio live character counter
 * - Cancel/reset state restoration for Edit Profile & Change Password forms
 * - Smooth section focus & highlight shortcuts
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

  // 2. Avatar Upload Triggers & Live Preview
  const quickAvatarInput = document.getElementById('avatarFileInput');
  const avatarCameraTrigger = document.querySelector('.avatar-edit-trigger');
  const heroChangePhotoBtn = document.getElementById('btnTriggerAvatarUpload');
  const editFormAvatarInput = document.getElementById('editProfileAvatarInput');
  const heroAvatarPreview = document.getElementById('profileAvatarDisplay');
  const editFormAvatarPreview = document.getElementById('editFormAvatarPreview');
  const avatarFileMeta = document.getElementById('avatarFileMeta');

  const initialHeroAvatarHTML = heroAvatarPreview ? heroAvatarPreview.innerHTML : '';
  const initialEditAvatarHTML = editFormAvatarPreview ? editFormAvatarPreview.innerHTML : '';
  const initialAvatarMetaText = avatarFileMeta ? avatarFileMeta.textContent : '';

  if (avatarCameraTrigger && quickAvatarInput) {
    avatarCameraTrigger.addEventListener('click', () => {
      quickAvatarInput.click();
    });
  }

  if (heroChangePhotoBtn && editFormAvatarInput) {
    heroChangePhotoBtn.addEventListener('click', () => {
      const editSection = document.getElementById('edit-profile-section');
      editSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      editFormAvatarInput.click();
    });
  }

  function renderAvatarPreviewFile(file) {
    if (!file) return;
    const maxBytes = 3 * 1024 * 1024;
    if (file.size > maxBytes) {
      if (avatarFileMeta) {
        avatarFileMeta.textContent = 'Selected file exceeds 3MB limit. Please choose a smaller image.';
        avatarFileMeta.style.color = 'var(--status-danger)';
      }
      if (editFormAvatarInput) editFormAvatarInput.value = '';
      return;
    }

    const sizeKB = Math.max(1, Math.round(file.size / 1024));
    if (avatarFileMeta) {
      avatarFileMeta.textContent = `Selected: ${file.name} (${sizeKB} KB) — Click Save Changes to apply`;
      avatarFileMeta.style.color = 'var(--accent-deep)';
    }

    const reader = new FileReader();
    reader.onload = function(evt) {
      const imgHtml = `<img src="${evt.target.result}" alt="Profile avatar preview" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
      if (editFormAvatarPreview) editFormAvatarPreview.innerHTML = imgHtml;
      if (heroAvatarPreview) heroAvatarPreview.innerHTML = imgHtml;
    };
    reader.readAsDataURL(file);
  }

  editFormAvatarInput?.addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (file) {
      renderAvatarPreviewFile(file);
    }
  });

  // 3. Bio Live Character Counter
  const bioInput = document.getElementById('profileBio');
  const bioCounter = document.getElementById('bioCharCounter');

  function updateBioCounter() {
    if (!bioInput || !bioCounter) return;
    const len = bioInput.value.length;
    bioCounter.textContent = `${len} / 500`;
  }

  bioInput?.addEventListener('input', updateBioCounter);
  updateBioCounter();

  // 4. Edit Profile Cancel / Reset Handler
  const editProfileForm = document.getElementById('editProfileForm');
  editProfileForm?.addEventListener('reset', () => {
    setTimeout(() => {
      if (heroAvatarPreview) heroAvatarPreview.innerHTML = initialHeroAvatarHTML;
      if (editFormAvatarPreview) editFormAvatarPreview.innerHTML = initialEditAvatarHTML;
      if (avatarFileMeta) {
        avatarFileMeta.textContent = initialAvatarMetaText;
        avatarFileMeta.style.color = '';
      }
      updateBioCounter();
    }, 0);
  });

  // 5. New Password Confirmation Match Check
  const newPassInput = document.getElementById('newPasswordInput');
  const confirmPassInput = document.getElementById('confirmPasswordInput');
  const matchNotice = document.getElementById('passMatchNotice');
  const changePasswordForm = document.getElementById('changePasswordForm');

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
      matchNotice.style.color = 'var(--status-danger)';
      matchNotice.style.display = 'block';
    }
  }

  newPassInput?.addEventListener('input', checkPasswordMatch);
  confirmPassInput?.addEventListener('input', checkPasswordMatch);

  changePasswordForm?.addEventListener('reset', () => {
    if (matchNotice) {
      matchNotice.style.display = 'none';
      matchNotice.textContent = '';
    }
  });

  // 6. Smooth Focus & Section Highlight Shortcuts
  function bindSmoothSectionFocus(triggerId, sectionId, inputId) {
    const trigger = document.getElementById(triggerId);
    const section = document.getElementById(sectionId);
    const input = document.getElementById(inputId);
    if (!trigger || !section) return;

    trigger.addEventListener('click', (e) => {
      e.preventDefault();
      section.scrollIntoView({ behavior: 'smooth', block: 'start' });
      section.classList.add('is-highlighted');
      setTimeout(() => {
        input?.focus();
      }, 280);
      setTimeout(() => {
        section.classList.remove('is-highlighted');
      }, 1600);
    });
  }

  bindSmoothSectionFocus('btnHeroEditProfile', 'edit-profile-section', 'profileFirstName');
  bindSmoothSectionFocus('topbarEditProfileBtn', 'edit-profile-section', 'profileFirstName');
  bindSmoothSectionFocus('btnShortcutChangePassword', 'account-security-section', 'currentPasswordInput');

  // 7. Form Submission Loading State
  [editProfileForm, changePasswordForm].forEach(form => {
    if (!form) return;
    form.addEventListener('submit', () => {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.classList.contains('is-submitting')) {
        submitBtn.classList.add('is-submitting');
        const submittingText = submitBtn.getAttribute('data-submitting-text');
        const span = submitBtn.querySelector('span');
        if (submittingText && span) {
          span.textContent = submittingText;
        }
      }
    });
  });

  // Initialize Lucide icons
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});
