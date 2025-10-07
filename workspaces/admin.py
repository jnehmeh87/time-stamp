from django.contrib import admin
from .models import Project, TimeEntry, TimeEntryImage

class TimeEntryImageInline(admin.TabularInline):
    model = TimeEntryImage
    extra = 1 # Number of extra forms to display

@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'project', 'start_time', 'end_time', 'category', 'is_archived')
    list_filter = ('user', 'project', 'category', 'start_time')
    search_fields = ('title', 'description', 'notes')
    inlines = [TimeEntryImageInline]

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_filter = ()
    search_fields = ('name',)
