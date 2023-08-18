# Generated by Django 4.2.4 on 2023-08-18 05:23

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EnrolledStudent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student_id', models.CharField(max_length=15)),
            ],
            options={
                'ordering': ['student_id'],
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(max_length=15)),
                ('name', models.CharField(max_length=150)),
                ('description', models.TextField(blank=True, null=True)),
                ('min_students', models.IntegerField()),
                ('max_students', models.IntegerField()),
            ],
            options={
                'ordering': ['number', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Unit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=15)),
                ('name', models.CharField(max_length=255)),
                ('year', models.CharField(max_length=4)),
                ('semester', models.CharField(max_length=50)),
                ('preference_submission_start', models.DateTimeField(blank=True, null=True)),
                ('preference_submission_end', models.DateTimeField(blank=True, null=True)),
                ('minimum_preference_limit', models.IntegerField(blank=True, null=True)),
                ('manager', models.ForeignKey(limit_choices_to={'is_manager': True}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='managed_units', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['code', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ProjectPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rank', models.PositiveIntegerField()),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_preferences', to='core.project')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_preferences', to='core.enrolledstudent')),
            ],
            options={
                'ordering': ['student__student_id', 'rank', 'project_id'],
            },
        ),
        migrations.AddField(
            model_name='project',
            name='unit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='projects', to='core.unit'),
        ),
        migrations.AddField(
            model_name='enrolledstudent',
            name='assigned_project',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_students', to='core.project'),
        ),
        migrations.AddField(
            model_name='enrolledstudent',
            name='unit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrolled_students', to='core.unit'),
        ),
        migrations.AddField(
            model_name='enrolledstudent',
            name='user',
            field=models.ForeignKey(blank=True, limit_choices_to={'is_student': True}, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='enrollments', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(
            model_name='unit',
            constraint=models.UniqueConstraint(fields=('code', 'year', 'semester'), name='core_unit_unique'),
        ),
        migrations.AddConstraint(
            model_name='projectpreference',
            constraint=models.UniqueConstraint(fields=('student', 'rank'), name='core_projectpreference_rank_unique'),
        ),
        migrations.AddConstraint(
            model_name='projectpreference',
            constraint=models.UniqueConstraint(fields=('student', 'project'), name='core_projectpreference_project_unique'),
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.UniqueConstraint(fields=('unit', 'number'), name='core_project_rank_unique'),
        ),
        migrations.AddConstraint(
            model_name='enrolledstudent',
            constraint=models.UniqueConstraint(fields=('student_id', 'unit'), name='core_enrolledstudent_unique'),
        ),
    ]
