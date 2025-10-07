from django.shortcuts import render, redirect, get_object_or_404
from allauth.account.views import LoginView as AllauthLoginView
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .forms import InvitationForm
from .models import Invitation, Membership
from django.contrib import messages
from .decorators import role_required
from django.core.mail import send_mail
from django.contrib.auth import login

# Create your views here.

class CustomLoginView(AllauthLoginView):
    """
    Custom login view to redirect staff members to the admin panel
    and regular users to the standard home page.
    """
    def get_success_url(self):
        if self.request.user.is_staff:
            return '/admin/'
        return '/'

@login_required
def session_keep_alive(request):
    """
    A simple view that is called by the frontend to keep the user's session alive.
    It just returns a success response. The real work is done by Django's
    session middleware, which will update the session's expiry on this request
    (since SESSION_SAVE_EVERY_REQUEST is True).
    """
    return JsonResponse({'success': True})

@login_required
@role_required(['ADMIN', 'MANAGER'])
def send_invitation(request):
    if request.method == 'POST':
        form = InvitationForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.organization = request.user.organizations.first()
            invitation.save()

            # Send email
            invitation_link = request.build_absolute_uri(f'/users/accept-invitation/{invitation.token}/')
            send_mail(
                'You have been invited to join an organization',
                f'Click the link to accept the invitation: {invitation_link}',
                'from@example.com',
                [invitation.email],
                fail_silently=False,
            )

            messages.success(request, 'Invitation sent successfully.')
            return redirect('users:send_invitation')
    else:
        form = InvitationForm()
    
    return render(request, 'users/send_invitation.html', {'form': form})

def accept_invitation(request, token):
    invitation = get_object_or_404(Invitation, token=token)
    if request.user.is_authenticated:
        # Add user to organization
        Membership.objects.create(
            user=request.user,
            organization=invitation.organization,
            role=invitation.role
        )
        invitation.delete()
        messages.success(request, 'You have successfully joined the organization.')
        return redirect('workspaces:home')
    else:
        # Redirect to signup page with email pre-filled
        return redirect(f'/accounts/signup/?email={invitation.email}')