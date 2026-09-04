from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.decorators import login_required


 
 
@login_required
def logout_view(request):
    """
    Logs the current user out and sends them back to the login page.
    GET is enough here since this is only ever reached via a link/button
    click, not a form — no sensitive data is being submitted.
    """
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("login")

def login_view(request):
    """
    Handles login for admin / teacher / user in one form.
    USERNAME_FIELD on the custom User model is 'email', so
    authenticate() is called with username=email.

    Redirect rules:
      - admin   -> 'admin_dashboard'
      - teacher -> no teacher UI yet, so send to the same place as 'user'
      - user    -> 'userpanel:dashboard'
    """
    if request.user.is_authenticated:
        if request.user.role == "admin":
            return redirect("admin_dashboard")
        return redirect("index")
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.status != "active":
                messages.error(request, "Your account is not active. Please contact support.")
                return redirect("login")

            login(request, user)

            if user.role == "admin":
                return redirect("admin_dashboard")

            # teacher has no dedicated dashboard template yet,
            # so fall through to the regular user dashboard
            return redirect("index")

        messages.error(request, "Invalid email or password.")
        return redirect("login")

    return render(request, "login.html")

 
def index(request):
    """
    Renders the public homepage only. Fully static — no context, no db.
    """
    return render(request, "index.html")
 