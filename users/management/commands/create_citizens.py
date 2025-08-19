from django.core.management.base import BaseCommand
from django.conf import settings
import dj_database_url
from users.models.customuser import CustomUser
from users.models.userprofile import UserProfile
from users.models.addresses import Province, District, Sector, Cell, Village
from django.db import transaction
import os
import threading
import time
import traceback

class Command(BaseCommand):
    help = "Create deterministic citizen users without Faker (scalable to thousands)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--database-url',
            type=str,
            help='Optional: override default database URL'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=5000,
            help='Number of citizens to create (default: 5000)'
        )

    def handle(self, *args, **options):
        # Set database
        db_url = options.get('database_url') or os.getenv('DATABASE_URL')
        if not db_url:
            self.stdout.write(self.style.ERROR(
                "No database URL provided. Set --database-url or DATABASE_URL env variable."
            ))
            return

        settings.DATABASES['default'] = dj_database_url.parse(db_url)
        self.stdout.write(self.style.SUCCESS(f"Using database: {db_url}"))

        count = options.get('count')

        # Fetch address data
        self.stdout.write("Fetching address data...")
        provinces = list(Province.objects.all())
        districts = list(District.objects.all())
        sectors = list(Sector.objects.all())
        cells = list(Cell.objects.all())
        villages = list(Village.objects.all())

        self.stdout.write(f"Fetched: {len(provinces)} provinces, {len(districts)} districts, "
                          f"{len(sectors)} sectors, {len(cells)} cells, {len(villages)} villages.")

        if not (provinces and districts and sectors and cells and villages):
            self.stdout.write(self.style.ERROR(
                "Address data is incomplete. Please ensure all provinces, districts, sectors, cells, and villages exist."
            ))
            return

        # Timer to warn if nothing created
        created_count = [0]
        def progress_check():
            time.sleep(6)
            if created_count[0] == 0:
                self.stdout.write(self.style.WARNING(
                    "No citizens created in the first 6 seconds. Check DB connection or address data."
                ))
        threading.Thread(target=progress_check, daemon=True).start()

        self.stdout.write(f"Starting creation of {count} citizens...")

        for i in range(1, count + 1):
            try:
                # Deterministic selection of addresses
                province = provinces[(i-1) % len(provinces)]
                district = [d for d in districts if d.province == province][0]
                sector = [s for s in sectors if s.district == district][0]
                cell = [c for c in cells if c.sector == sector][0]
                village = [v for v in villages if v.cell == cell][0]

                # Hardcoded values
                email = f"citizen{i}@example.com"
                full_names = f"Citizen {i}"
                phone_number = f"+2507000{i:04d}"
                national_id = f"{1000000000000000 + i}"
                password = "Citizen123!"
                dob = "1990-01-01"

                # Transaction to catch FK/constraint errors
                with transaction.atomic():
                    user = CustomUser.objects.create_user(
                        email=email,
                        full_names=full_names,
                        phone_number=phone_number,
                        national_id=national_id,
                        password=password,
                        user_level="citizen"
                    )
                    self.stdout.write(f"CustomUser created: {email}")

                    profile = UserProfile.objects.create(
                        user=user,
                        gender="male" if i % 2 == 0 else "female",
                        date_of_birth=dob,
                        province=province,
                        district=district,
                        sector=sector,
                        cell=cell,
                        village=village,
                        bio=f"Citizen {i} profile",
                        work="Farmer",
                        work_description="Working in agriculture",
                        website=""
                    )
                    self.stdout.write(f"UserProfile created: {full_names}")

                created_count[0] += 1

                if i % 100 == 0:
                    self.stdout.write(self.style.SUCCESS(f"{created_count[0]} citizens created so far..."))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating citizen {i}: {e}"))
                traceback.print_exc()

        self.stdout.write(self.style.SUCCESS(f"Finished creating {created_count[0]} citizens."))
