from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):

    def save_user(self, request, user, form, commit=True):
        """
        Saves a new `User` instance using information provided in the
        signup form.
        """
        # First, let the default adapter save the user and handle the
        # standard fields (username, email, password).
        user = super().save_user(request, user, form, commit=False)

        # Now that the user is created and the form is validated,
        # we can safely access cleaned_data to add our custom fields.
        user.first_name = form.cleaned_data.get('first_name')
        user.last_name = form.cleaned_data.get('last_name')
        user.date_of_birth = form.cleaned_data.get('date_of_birth')
        user.address = form.cleaned_data.get('address')
        user.phone_number = form.cleaned_data.get('phone_number')
        
        if commit:
            user.save()
            
        return user
