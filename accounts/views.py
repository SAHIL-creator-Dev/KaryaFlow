from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    UserProfileUpdateForm,
    UserProfileAvatarForm,
    StyledPasswordChangeForm,
)
from .models import UserProfile


def register_view(request):
    """
    Handles user registration.
    Redirects already-authenticated users to dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f"Welcome to KaryaFlow, {user.first_name or user.username}! Your account has been created. Please sign in."
            )
            return redirect('login')
        else:
            # Display form errors via messages banner if appropriate
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """
    Handles user authentication and login session creation.
    Redirects already-authenticated users to dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            remember_me = form.cleaned_data.get('remember_me')
            login(request, user)

            if remember_me:
                # Session cookie lasts for 2 weeks
                request.session.set_expiry(1209600)
            else:
                # Browser session cookie expires when browser is closed
                request.session.set_expiry(0)

            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next') or request.POST.get('next') or 'dashboard'
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username/email or password. Please try again.")
    else:
        form = UserLoginForm(request)

    return render(request, 'accounts/login.html', {'form': form})


@require_http_methods(["POST"])
def logout_view(request):
    """
    Handles user logout via POST request with CSRF verification.
    Prevents insecure GET-based logout attacks.
    """
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "You have been successfully signed out.")
    return redirect('home')


@login_required
def profile_view(request):
    """
    Allows authenticated users to view and update their profile details
    (first name, last name, email, profile avatar) or change password.
    """
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            profile_form = UserProfileUpdateForm(request.POST, instance=user)
            avatar_form = UserProfileAvatarForm(request.POST, request.FILES, instance=profile)

            if profile_form.is_valid() and avatar_form.is_valid():
                profile_form.save()
                avatar_form.save()
                messages.success(request, "Your profile has been successfully updated.")
                return redirect('profile')
            else:
                # Display errors
                for form in (profile_form, avatar_form):
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, error)

        elif action == 'change_password':
            password_form = StyledPasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                user_updated = password_form.save()
                # Maintain active session so the user is not unexpectedly logged out
                update_session_auth_hash(request, user_updated)
                messages.success(request, "Your password has been changed successfully.")
                return redirect('profile')
            else:
                for field, errors in password_form.errors.items():
                    for error in errors:
                        messages.error(request, error)

    # Initial form states for GET or post-error rendering
    profile_form = UserProfileUpdateForm(instance=user)
    avatar_form = UserProfileAvatarForm(instance=profile)
    password_form = StyledPasswordChangeForm(user=user)

    context = {
        'user': user,
        'profile': profile,
        'profile_form': profile_form,
        'avatar_form': avatar_form,
        'password_form': password_form,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
@require_http_methods(["POST"])
def change_password_view(request):
    """
    Dedicated endpoint for password change form submissions.
    """
    form = StyledPasswordChangeForm(user=request.user, data=request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been updated successfully.")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
    return redirect('profile')
