from django.core.management.base import BaseCommand
from users.models.customuser import CustomUser
from users.models.userprofile import UserProfile
from users.models.addresses import Province, District, Sector, Cell, Village
import random
from faker import Faker

fake = Faker()

class Command(BaseCommand):
    help = "Create random citizen users"

    def handle(self, *args, **kwargs):
        provinces = list(Province.objects.all())
        districts = list(District.objects.all())
        sectors = list(Sector.objects.all())
        cells = list(Cell.objects.all())
        villages = list(Village.objects.all())

        for i in range(1, 801):
            try:
                province = random.choice(provinces)
                district = random.choice([d for d in districts if d.province == province])
                sector = random.choice([s for s in sectors if s.district == district])
                cell = random.choice([c for c in cells if c.sector == sector])
                village = random.choice([v for v in villages if v.cell == cell])

                email = f"citizen{i}@example.com"
                full_names = fake.name()
                phone_number = f"+2507{random.randint(10000000, 99999999)}"
                national_id = f"{random.randint(1000000000000000, 9999999999999999)}"
                password = "Citizen123!"
                dob = fake.date_of_birth(minimum_age=18, maximum_age=80)

                user = CustomUser.objects.create_user(
                    email=email,
                    full_names=full_names,
                    phone_number=phone_number,
                    national_id=national_id,
                    password=password,
                    user_level="citizen"
                )

                UserProfile.objects.create(
                    user=user,
                    gender=random.choice(["male", "female"]),
                    date_of_birth=dob,
                    province=province,
                    district=district,
                    sector=sector,
                    cell=cell,
                    village=village,
                    bio=fake.text(max_nb_chars=100),
                    work=fake.job(),
                    work_description=fake.sentence(),
                    website=fake.url() if random.random() < 0.3 else ""
                )

                self.stdout.write(self.style.SUCCESS(f"Created citizen {i}: {full_names}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating citizen {i}: {e}"))
