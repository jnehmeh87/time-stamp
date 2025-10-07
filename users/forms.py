from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import CustomUser, Invitation, Membership
from allauth.account.forms import SignupForm
from django_countries.fields import CountryField

class UserUpdateForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'country', 'address', 'phone_number')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'country': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_phone_number'}),
        }

class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=30, label='First Name', widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, label='Last Name', widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    country = CountryField(blank_label='(select country)').formfield(required=False)
    address = forms.CharField(max_length=255, label='Address', widget=forms.TextInput(attrs={'placeholder': 'Your address'}), required=False)
    phone_number = forms.CharField(max_length=20, label='Phone Number', widget=forms.TextInput(attrs={'placeholder': 'Your phone number'}), required=False)

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.country = self.cleaned_data['country']
        user.address = self.cleaned_data['address']
        user.phone_number = self.cleaned_data['phone_number']
        user.save()
        return user

class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ['email', 'role']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }
