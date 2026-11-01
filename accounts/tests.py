from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import UserProfile


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.profile_url = reverse('profile')
        self.dashboard_url = reverse('dashboard')

        # Create a pre-existing test user
        self.user = User.objects.create_user(
            username='existinguser',
            email='existing@karyaflow.io',
            password='ComplexPassword123!',
            first_name='Existing',
            last_name='User'
        )

    # -------------------------------------------------------------------------
    # 1. Registration Tests
    # -------------------------------------------------------------------------
    def test_successful_registration(self):
        response = self.client.post(self.register_url, {
            'first_name': 'Aanya',
            'last_name': 'Roy',
            'username': 'aanyaroy',
            'email': 'aanya@karyaflow.io',
            'password': 'StrongPassword456!',
            'confirm_password': 'StrongPassword456!',
        })
        self.assertRedirects(response, self.login_url)
        self.assertTrue(User.objects.filter(username='aanyaroy').exists())
        user = User.objects.get(username='aanyaroy')
        self.assertEqual(user.first_name, 'Aanya')
        self.assertEqual(user.last_name, 'Roy')
        self.assertEqual(user.email, 'aanya@karyaflow.io')
        # Check automatic UserProfile creation via signal
        self.assertTrue(hasattr(user, 'profile'))

    def test_duplicate_username_registration(self):
        response = self.client.post(self.register_url, {
            'first_name': 'Duplicate',
            'username': 'existinguser',
            'email': 'different@karyaflow.io',
            'password': 'StrongPassword456!',
            'confirm_password': 'StrongPassword456!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A user with that username already exists.")

    def test_duplicate_email_registration(self):
        response = self.client.post(self.register_url, {
            'first_name': 'Different',
            'username': 'differentuser',
            'email': 'existing@karyaflow.io',
            'password': 'StrongPassword456!',
            'confirm_password': 'StrongPassword456!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email address already exists.")

    def test_password_mismatch_registration(self):
        response = self.client.post(self.register_url, {
            'first_name': 'Mismatch',
            'username': 'mismatchuser',
            'email': 'mismatch@karyaflow.io',
            'password': 'StrongPassword456!',
            'confirm_password': 'DifferentPassword456!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passwords do not match.")

    def test_invalid_weak_password_registration(self):
        response = self.client.post(self.register_url, {
            'first_name': 'Weak',
            'username': 'weakuser',
            'email': 'weak@karyaflow.io',
            'password': '123',
            'confirm_password': '123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='weakuser').exists())

    # -------------------------------------------------------------------------
    # 2. Login Tests
    # -------------------------------------------------------------------------
    def test_valid_login_with_username(self):
        response = self.client.post(self.login_url, {
            'username': 'existinguser',
            'password': 'ComplexPassword123!',
        })
        self.assertRedirects(response, self.dashboard_url)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_valid_login_with_email(self):
        response = self.client.post(self.login_url, {
            'username': 'existing@karyaflow.io',
            'password': 'ComplexPassword123!',
        })
        self.assertRedirects(response, self.dashboard_url)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_invalid_credentials_login(self):
        response = self.client.post(self.login_url, {
            'username': 'existinguser',
            'password': 'WrongPassword!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username/email or password")
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_authenticated_user_redirected_from_login_and_register(self):
        self.client.force_login(self.user)
        resp_login = self.client.get(self.login_url)
        self.assertRedirects(resp_login, self.dashboard_url)
        resp_reg = self.client.get(self.register_url)
        self.assertRedirects(resp_reg, self.dashboard_url)

    # -------------------------------------------------------------------------
    # 3. Logout Tests
    # -------------------------------------------------------------------------
    def test_successful_post_logout(self):
        self.client.force_login(self.user)
        response = self.client.post(self.logout_url)
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_get_logout_rejected(self):
        self.client.force_login(self.user)
        response = self.client.get(self.logout_url)
        # Should return 405 Method Not Allowed because GET is disallowed
        self.assertEqual(response.status_code, 405)
        # User must still remain logged in
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    # -------------------------------------------------------------------------
    # 4. Access Control Tests
    # -------------------------------------------------------------------------
    def test_anonymous_user_cannot_access_protected_routes(self):
        protected_routes = [
            self.dashboard_url,
            reverse('my_projects'),
            reverse('my_tasks'),
            self.profile_url,
        ]
        for url in protected_routes:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302)
            self.assertTrue(resp.url.startswith(self.login_url))

    def test_authenticated_user_can_access_protected_routes(self):
        self.client.force_login(self.user)
        protected_routes = [
            self.dashboard_url,
            reverse('my_projects'),
            reverse('my_tasks'),
            self.profile_url,
        ]
        for url in protected_routes:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)

    # -------------------------------------------------------------------------
    # 5. Profile Management Tests
    # -------------------------------------------------------------------------
    def test_user_can_update_their_own_profile(self):
        self.client.force_login(self.user)
        response = self.client.post(self.profile_url, {
            'action': 'update_profile',
            'first_name': 'SahilUpdated',
            'last_name': 'VermaUpdated',
            'email': 'sahil.updated@karyaflow.io',
        })
        self.assertRedirects(response, self.profile_url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'SahilUpdated')
        self.assertEqual(self.user.last_name, 'VermaUpdated')
        self.assertEqual(self.user.email, 'sahil.updated@karyaflow.io')

    def test_user_cannot_update_another_user_profile(self):
        # Create second user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@karyaflow.io',
            password='OtherPassword123!',
            first_name='Other',
            last_name='User'
        )
        self.client.force_login(self.user)
        # Post form: views strictly use request.user and ignore client-supplied IDs
        response = self.client.post(self.profile_url, {
            'action': 'update_profile',
            'user_id': other_user.id,
            'first_name': 'HackedName',
            'last_name': 'HackedLastName',
            'email': 'hacked@karyaflow.io',
        })
        self.assertRedirects(response, self.profile_url)
        other_user.refresh_from_db()
        self.assertEqual(other_user.first_name, 'Other')
        self.assertEqual(other_user.email, 'other@karyaflow.io')

    # -------------------------------------------------------------------------
    # 6. Change Password Tests
    # -------------------------------------------------------------------------
    def test_successful_password_change(self):
        self.client.force_login(self.user)
        response = self.client.post(self.profile_url, {
            'action': 'change_password',
            'old_password': 'ComplexPassword123!',
            'new_password1': 'BrandNewSecurePass999!',
            'new_password2': 'BrandNewSecurePass999!',
        })
        self.assertRedirects(response, self.profile_url)
        # Verify user can log in with new password
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNewSecurePass999!'))
        # Verify session is retained
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_password_change_incorrect_current_password(self):
        self.client.force_login(self.user)
        response = self.client.post(self.profile_url, {
            'action': 'change_password',
            'old_password': 'WrongCurrentPassword!',
            'new_password1': 'BrandNewSecurePass999!',
            'new_password2': 'BrandNewSecurePass999!',
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('ComplexPassword123!'))

    def test_password_change_mismatch(self):
        self.client.force_login(self.user)
        response = self.client.post(self.profile_url, {
            'action': 'change_password',
            'old_password': 'ComplexPassword123!',
            'new_password1': 'BrandNewSecurePass999!',
            'new_password2': 'DifferentPass888!',
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('ComplexPassword123!'))
