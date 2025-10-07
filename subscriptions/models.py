from django.db import models

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    stripe_plan_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

class Subscription(models.Model):
    organization = models.OneToOneField('users.Organization', on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='subscriptions')
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.organization.name} - {self.plan.name}"