# Generated by Django 4.2.5 on 2023-09-08 12:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_alter_project_options_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='project',
            name='core_project_rank_unique',
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.UniqueConstraint(fields=('unit', 'identifier'), name='core_project_id_unique', violation_error_message='Each project in a unit must have a unique ID. A project with that ID is already included in this unit.'),
        ),
    ]
