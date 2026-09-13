from django.core.management.base import BaseCommand
from pathlib import Path
from demo.realistic_cadastral_fixture import RealisticCadastralFixture, load_realistic_fixtures_to_db


class Command(BaseCommand):
    help = "Generate realistic cadastral test GeoJSON files and optionally ingest into database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-db", action="store_true", help="Only write GeoJSON files to disk without inserting into DB."
        )
        parser.add_argument(
            "--harmonize", action="store_true", help="Immediately run harmonization pipeline on the loaded datasets."
        )
        parser.add_argument(
            "--output-dir", type=str, default="/app/media/fixtures", help="Output directory for generated GeoJSON."
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"])
        self.stdout.write(f"Generating realistic cadastral GeoJSON files in {output_dir}...")
        file_a, file_b = RealisticCadastralFixture.write_geojson_files(output_dir)
        self.stdout.write(self.style.SUCCESS(f"Saved: {file_a}"))
        self.stdout.write(self.style.SUCCESS(f"Saved: {file_b}"))

        if not options["no_db"]:
            self.stdout.write("Ingesting datasets into PostgreSQL / PostGIS...")
            ds_a, ds_b = load_realistic_fixtures_to_db()
            self.stdout.write(self.style.SUCCESS(f"Ingested Dataset A: ID {ds_a.id} ({ds_a.name}) with {ds_a.feature_count} features."))
            self.stdout.write(self.style.SUCCESS(f"Ingested Dataset B: ID {ds_b.id} ({ds_b.name}) with {ds_b.feature_count} features."))

            if options["harmonize"]:
                from apps.harmonization.models import HarmonizationRun, RunStatus
                from apps.harmonization.services.pipeline_service import HarmonizationPipeline

                self.stdout.write("Executing Harmonization Pipeline on real data...")
                run = HarmonizationRun.objects.create(
                    status=RunStatus.PENDING,
                    dataset_ids=[ds_a.id, ds_b.id],
                )
                stats = HarmonizationPipeline(run).run_pipeline([ds_a.id, ds_b.id])
                self.stdout.write(self.style.SUCCESS(f"Harmonization Run ID {run.id} Complete! Status: {run.status}"))
                self.stdout.write(self.style.SUCCESS(f"Stats: {stats}"))
