from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile


class UserRegistrationForm(forms.ModelForm):
    """
    Form for new user registration.
    Includes first_name, optional last_name, unique username, validated email,
    and matching passwords hashed using Django's password validators.
    """
    full_name = forms.CharField(
        max_length=150,
        required=False,
        label="Full Name",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Sahil Verma',
            'id': 'id_full_name',
            'autocomplete': 'name',
            'autofocus': True,
        })
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        label="First Name",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'First Name',
            'id': 'id_first_name',
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label="Last Name",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Last Name',
            'id': 'id_last_name',
        })
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        label="Username",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'sahil_creator',
            'id': 'id_username',
            'autocomplete': 'username',
        })
    )
    email = forms.EmailField(
        required=True,
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'name@company.com',
            'id': 'id_email',
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        required=True,
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'At least 8 characters',
            'id': 'id_password',
            'autocomplete': 'new-password',
        })
    )
    confirm_password = forms.CharField(
        required=True,
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Repeat your password',
            'id': 'id_confirm_password',
            'autocomplete': 'new-password',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                self.add_error('confirm_password', "Passwords do not match.")
            else:
                # Validate against Django's configured password validators
                try:
                    validate_password(password)
                except ValidationError as err:
                    self.add_error('password', err)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])

        # Process name
        full_name = self.cleaned_data.get('full_name', '').strip()
        first_name = self.cleaned_data.get('first_name', '').strip()
        last_name = self.cleaned_data.get('last_name', '').strip()

        if full_name and not first_name:
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            if len(parts) > 1:
                user.last_name = parts[1]
        else:
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name

        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    """
    Standard login form accepting username or email, styled with KaryaFlow classes.
    """
    username = forms.CharField(
        label="Email or Username",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'name@company.com or username',
            'id': 'id_username',
            'autocomplete': 'username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••',
            'id': 'id_password',
            'autocomplete': 'current-password',
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'custom-checkbox',
            'id': 'id_remember_me',
        })
    )

    def clean(self):
        """
        Allow login with either username or email address.
        """
        username_or_email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username_or_email and password:
            # Check if input is an email address
            if '@' in username_or_email:
                user_match = User.objects.filter(email__iexact=username_or_email).first()
                if user_match:
                    self.cleaned_data['username'] = user_match.username

        return super().clean()


class UserProfileUpdateForm(forms.ModelForm):
    """
    Form for updating basic User account fields (first_name, last_name, email).
    """
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="First Name",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'id': 'profileFirstName',
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label="Last Name",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'id': 'profileLastName',
        })
    )
    email = forms.EmailField(
        required=True,
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'id': 'profileEmail',
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = kwargs.get('instance')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This email is already in use by another account.")
        return email


class UserProfileAvatarForm(forms.ModelForm):
    """
    Form for uploading profile avatar image.
    """
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'id': 'avatarFileInput',
            'accept': 'image/*',
            'style': 'display: none;',
        })
    )

    class Meta:
        model = UserProfile
        fields = ['avatar']


class StyledPasswordChangeForm(PasswordChangeForm):
    """
    Custom-styled extension of Django's PasswordChangeForm matching KaryaFlow UI.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-input',
            'id': 'currentPasswordInput',
            'placeholder': 'Enter current password',
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-input',
            'id': 'newPasswordInput',
            'placeholder': 'At least 8 characters',
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-input',
            'id': 'confirmPasswordInput',
            'placeholder': 'Re-enter new password',
        })
