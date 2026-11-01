import os
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


def validate_profile_image(image):
    """
    Validates uploaded image size (max 3MB) and allowed extensions.
    """
    file_size = image.size
    limit_mb = 3
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Maximum image size is {limit_mb}MB.")

    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
    ext = os.path.splitext(image.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError(
            f"Unsupported file extension '{ext}'. Allowed extensions are: {', '.join(valid_extensions)}"
        )


def user_avatar_upload_path(instance, filename):
    """
    Generates a secure, user-isolated path for profile avatars.
    e.g. avatars/user_1/profile.png
    """
    ext = os.path.splitext(filename)[1].lower()
    return f"avatars/user_{instance.user.id}/avatar{ext}"


class UserProfile(models.Model):
    """
    Profile extension for Django's built-in User model.
    Maintains user avatar and supplemental profile attributes
    without duplicating first_name, last_name, or email.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        help_text="The core Django User account associated with this profile."
    )
    avatar = models.ImageField(
        upload_to=user_avatar_upload_path,
        blank=True,
        null=True,
        validators=[validate_profile_image],
        help_text="Custom profile picture."
    )
    bio = models.TextField(
        blank=True,
        max_length=500,
        help_text="Short user bio or team description."
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    @property
    def avatar_url(self):
        """
        Returns the avatar image URL if uploaded, else None.
        """
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return None
