from django import forms

class CustomSignupForm(forms.Form):
    """
    Extra fields appended to allauth's base signup via ACCOUNT_SIGNUP_FORM_CLASS.
    This form defines the extra fields and a `signup` method to save them.
    """
    first_name = forms.CharField(max_length=30, label='First Name',
                                 widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, label='Last Name',
                                widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'form-control'}))
    date_of_birth = forms.DateField(label='Date of Birth',
                                    widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
                                    required=False)
    address = forms.CharField(label='Address', max_length=255,
                              widget=forms.TextInput(attrs={'placeholder': 'Address', 'class': 'form-control'}),
                              required=False)
    phone_number = forms.CharField(label='Phone Number', max_length=20,
                                   widget=forms.TextInput(attrs={'placeholder': 'Phone Number', 'class': 'form-control'}),
                                   required=False)

    def signup(self, request, user):
        """
        This method is called by allauth after the user is created, to save
        the extra data.
        """
        user.first_name = self.cleaned_data.get('first_name', user.first_name)
        user.last_name = self.cleaned_data.get('last_name', user.last_name)
        user.date_of_birth = self.cleaned_data.get('date_of_birth')
        user.address = self.cleaned_data.get('address', '')
        user.phone_number = self.cleaned_data.get('phone_number', '')
        user.save()
        return user

    field_order = [
        'username', 'email', 'first_name', 'last_name',
        'date_of_birth', 'address', 'phone_number',
        'password1', 'password2',
    ]
