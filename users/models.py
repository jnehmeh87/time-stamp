import uuid
import secrets
from django.db import models
from django.contrib.auth.models import AbstractUser
from django_countries.fields import CountryField


class CustomUser(AbstractUser):
    country = CountryField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, default='')
    phone_number = models.CharField(max_length=20, blank=True, default='')

    def __str__(self):
        return self.username


class Organization(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField('CustomUser', through='Membership', related_name='organizations')
    iban = models.CharField(max_length=34, blank=True, default='')
    bic = models.CharField(max_length=11, blank=True, default='')

    def __str__(self):
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = 'OWNER', 'Owner'
        ADMIN = 'ADMIN', 'Admin'
        MANAGER = 'MANAGER', 'Manager'
        MEMBER = 'MEMBER', 'Member'

    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        unique_together = ('user', 'organization')

    def __str__(self):
        return f'{self.user.username} in {self.organization.name} ({self.get_role_display()})'

def create_token():
    return secrets.token_urlsafe(32)

class Invitation(models.Model):
    email = models.EmailField()
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Membership.Role.choices, default=Membership.Role.MEMBER)
    token = models.CharField(max_length=64, default=create_token, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invitation for {self.email} to join {self.organization.name}"
