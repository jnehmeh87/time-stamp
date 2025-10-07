from django.db import models
from django.conf import settings
from datetime import timedelta

class Contact(models.Model):
    """
    Represents a contact which can be a client for billing purposes
    or a simple category for organizing projects.
    """
    class ContactType(models.TextChoices):
        CATEGORY = 'CATEGORY', 'Category'
        CLIENT = 'CLIENT', 'Client'

    organization = models.ForeignKey('users.Organization', on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=255)
    contact_type = models.CharField(max_length=10, choices=ContactType.choices, default=ContactType.CATEGORY)

    # Client-specific fields for invoicing
    email = models.EmailField(blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    vat_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="VAT ID")
    send_reminders = models.BooleanField(default=False, help_text="Send automated payment reminders for invoices.")

    class Meta:
        ordering = ['name']
        unique_together = ('organization', 'name')

    def __str__(self):
        return f"{self.name} ({self.get_contact_type_display()})"

class Project(models.Model):
    organization = models.ForeignKey('users.Organization', on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    is_archived = models.BooleanField(default=False)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    def __str__(self):
        return self.name

class TimeEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='time_entries')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    is_paused = models.BooleanField(default=False)
    last_pause_time = models.DateTimeField(null=True, blank=True)
    paused_duration = models.DurationField(default=timedelta(0))
    is_manual = models.BooleanField(default=False)
    was_edited = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_time']

    @property
    def duration(self):
        if self.end_time:
            return self.end_time - self.start_time - self.paused_duration
        return None
    
    def __str__(self):
        return f"{self.title} ({self.user.username})"

class TimeEntryImage(models.Model):
    time_entry = models.ForeignKey(TimeEntry, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='time_entry_images/')

    class Meta:
        indexes = [models.Index(fields=['time_entry'])]

    def __str__(self):
        return f"Image for {self.time_entry.title}"