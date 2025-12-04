from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm, PasswordChangeForm
from .models import User
from django.utils.translation import activate
from django.conf import settings
from django.utils import translation

def change_language(request):
    """Til o'zgartirish view"""
    if request.method == 'POST':
        language = request.POST.get('language')
        
        # Til to'g'ri formatda ekanini tekshirish
        if language and language in dict(settings.LANGUAGES):
            # Sessionda saqlash
            request.session['django_language'] = language
            request.session.modified = True
            
            # Cookie'da ham saqlash
            response = redirect(request.POST.get('next', '/'))
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                language,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
            )
            
            # Hozirgi sessionni aktivlashtirish
            translation.activate(language)
            
            return response
    
    return redirect('/')


def register_view(request):
    """Ro'yxatdan o'tish"""
    if request.user.is_authenticated:
        return redirect('tickets:dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'user'  # Default role
            user.save()
            
            # Avtomatik login qilish
            from django.contrib.auth import login as auth_login
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            messages.success(request, _('Xush kelibsiz! Ro\'yxatdan muvaffaqiyatli o\'tdingiz.'))
            return redirect('tickets:dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Tizimga kirish"""
    if request.user.is_authenticated:
        return redirect('tickets:dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, _('Xush kelibsiz, {}!').format(user.get_full_name()))
                    
                    # Rolga qarab yo'naltirish
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    elif user.is_admin():
                        return redirect('tickets:admin_dashboard')
                    else:
                        return redirect('tickets:dashboard')
                else:
                    messages.error(request, _('Sizning hisobingiz bloklangan.'))
            else:
                messages.error(request, _('Login yoki parol noto\'g\'ri.'))
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    """Tizimdan chiqish"""
    logout(request)
    messages.success(request, _('Tizimdan chiqdingiz.'))
    return redirect('accounts:login')


@login_required
def profile_view(request):
    """Profil ko'rish va tahrirlash"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Profil ma\'lumotlari saqlandi.'))
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def change_password_view(request):
    """Parolni o'zgartirish"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            old_password = form.cleaned_data['old_password']
            new_password = form.cleaned_data['new_password1']
            new_password2 = form.cleaned_data['new_password2']
            
            if not request.user.check_password(old_password):
                messages.error(request, _('Joriy parol noto\'g\'ri.'))
            elif new_password != new_password2:
                messages.error(request, _('Yangi parollar bir xil emas.'))
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, _('Parol muvaffaqiyatli o\'zgartirildi.'))
                return redirect('accounts:profile')
    else:
        form = PasswordChangeForm()
    
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def change_language(request):
    """Tilni o'zgartirish"""
    if request.method == 'POST':
        language = request.POST.get('language')
        if language in ['uz', 'uz-cy', 'ru']:
            # User modelda tilni saqlash
            user = request.user
            user.language = language
            user.save()
            
            # Session tilini o'zgartirish
            from django.utils import translation
            translation.activate(language)
            # Django 5.0 da to'g'ri konstanta nomi
            request.session['_language'] = language
            
            messages.success(request, _('Til muvaffaqiyatli o\'zgartirildi.'))
            
            # Redirect to previous page
            next_url = request.META.get('HTTP_REFERER', '/')
            return redirect(next_url)
    
    return redirect('tickets:dashboard')