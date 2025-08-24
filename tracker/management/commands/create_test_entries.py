import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from tracker.models import TimeEntry, Project

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates several test time entries for the latest work project of the first user.'

    def handle(self, *args, **options):
        try:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR('No users found in the database. Please create a user first.'))
                return
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('No users found in the database. Please create a user first.'))
            return

        self.stdout.write(f"Using user: {user.username}")

        latest_project = Project.objects.filter(user=user, category='personal').order_by('-id').first()

        if not latest_project:
            self.stdout.write(self.style.ERROR('No projects found in the "Personal" category for this user.'))
            return
        
        if not latest_project.hourly_rate:
            self.stdout.write(self.style.WARNING(f"Project '{latest_project.name}' has no hourly rate. Setting a temporary rate of 100 for testing."))
            latest_project.hourly_rate = 100
            latest_project.save()

        self.stdout.write(self.style.SUCCESS(f"Found latest work project: '{latest_project.name}'"))

        today = timezone.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Optional: Clear existing entries for this project in the current month to avoid duplicates on re-run
        # TimeEntry.objects.filter(project=latest_project, start_time__gte=start_of_month).delete()
        # self.stdout.write("Cleared existing test entries for this project in the current month.")

        # Create 10 new entries on different days of the current month
        num_entries_created = 0
        for i in range(1, 31):
            try:
                # Create entries only up to the current day of the month
                day = random.randint(1, today.day)
                start_hour = random.randint(8, 12)
                
                start_time = today.replace(day=day, hour=start_hour, minute=random.randint(0, 59))
                
                # Ensure we don't create duplicate start times
                if TimeEntry.objects.filter(start_time=start_time).exists():
                    continue

                duration_hours = random.uniform(2.5, 8.0)
                end_time = start_time + timedelta(hours=duration_hours)
                
                pause_minutes = random.randint(0, 60)
                pause_duration = timedelta(minutes=pause_minutes)

                TimeEntry.objects.create(
                    user=user,
                    project=latest_project,
                    category='personal',
                    title=f'Test Task {i}',
                    start_time=start_time,
                    end_time=end_time,
                    paused_duration=pause_duration
                )
                num_entries_created += 1
            except ValueError:
                # Handles cases where a random day might not be valid (e.g. day 31 in a 30 day month)
                continue

        self.stdout.write(self.style.SUCCESS(f'Successfully created {num_entries_created} new test time entries.'))

