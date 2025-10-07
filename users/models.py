from django.contrib.auth.models import AbstractUser
from django.db import models
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
