from django.db import migrations
from django.conf import settings

def setup_initial_data(apps, schema_editor):
    """
    Update the default Site object for production and create a default Category.
    """
    # Part 1: Fix django-allauth by setting the correct site domain
    Site = apps.get_model('sites', 'Site')
    production_domain = 'timestamp-trackr-68fdb365e285.herokuapp.com'
    
    # Get the default site (pk=1) and update its domain and name
    default_site = Site.objects.get(pk=settings.SITE_ID)
    default_site.domain = production_domain
    default_site.name = 'Timestamp Trackr'
    default_site.save()

    # Part 2: Create a default 'Work' category for the daily-earnings page
    # This assumes you have a model named 'Category' in your 'tracker' app.
    try:
        Category = apps.get_model('tracker', 'Category')
        Category.objects.get_or_create(name='Work')
    except LookupError:
        # If the Category model doesn't exist, just skip this part.
        pass

class Migration(migrations.Migration):

    dependencies = [
        # This should be the name of your last migration file in the 'tracker' app
        ('tracker', '0002_auto_20250830_1400'), 
        # This ensures the sites app migration has run first
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(setup_initial_data),
    ]
