from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('datasets', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AIAnalysisRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aoi_geometry', models.JSONField(help_text='GeoJSON Polygon geometry of the Area of Interest')),
                ('aoi_bounds', models.JSONField(blank=True, help_text='[west, south, east, north]', null=True)),
                ('area_m2', models.FloatField(default=0.0, help_text='Analyzed area in square meters')),
                ('source_imagery_type', models.CharField(default='SATELLITE_TILES', max_length=50)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed')], default='PENDING', max_length=20)),
                ('method_category', models.CharField(default='COMPUTER_VISION_HEURISTIC', max_length=50)),
                ('model_name', models.CharField(default='GeoHarmonize CV & Spectral Classifier', max_length=100)),
                ('model_version', models.CharField(default='1.0-prototype', max_length=20)),
                ('is_ml_model', models.BooleanField(default=False, help_text='False for classical CV/spectral heuristic')),
                ('confidence_score', models.FloatField(default=0.0)),
                ('summary_statistics', models.JSONField(blank=True, default=dict)),
                ('features_geojson', models.JSONField(blank=True, default=dict)),
                ('recommendations_geojson', models.JSONField(blank=True, default=dict)),
                ('error_message', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('source_dataset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_analyses', to='datasets.dataset')),
            ],
            options={
                'db_table': 'gh_ai_analysis_runs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AIAnalysisFeature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature_type', models.CharField(choices=[('BUILT_UP', 'Built-up / Occupied'), ('BARE_LAND', 'Bare / Vacant Land'), ('AGRICULTURE', 'Agriculture / Cropland'), ('VEGETATION', 'Vegetation / Green Area'), ('WATER', 'Water Body'), ('ROAD', 'Road / Infrastructure'), ('UNKNOWN', 'Unknown')], max_length=30)),
                ('geometry_wkt', models.TextField(help_text='WKT polygon geometry')),
                ('area_m2', models.FloatField(default=0.0)),
                ('confidence', models.FloatField(default=0.0)),
                ('attributes', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('analysis_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='features', to='ai.aianalysisrun')),
            ],
            options={
                'db_table': 'gh_ai_analysis_features',
            },
        ),
        migrations.CreateModel(
            name='AIPlanningRecommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recommendation_type', models.CharField(choices=[('AGRICULTURE', 'Agriculture Candidate'), ('CONSTRUCTION', 'Construction Candidate'), ('NOT_RECOMMENDED', 'Not Recommended / Low Confidence')], max_length=30)),
                ('geometry_wkt', models.TextField(help_text='WKT candidate polygon geometry')),
                ('suitability_score', models.FloatField(default=0.0, help_text='0-100')),
                ('confidence', models.FloatField(default=0.0, help_text='0-100')),
                ('area_m2', models.FloatField(default=0.0)),
                ('reasons', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('analysis_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommendations', to='ai.aianalysisrun')),
            ],
            options={
                'db_table': 'gh_ai_planning_recommendations',
            },
        ),
    ]
