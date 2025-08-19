# user/serializers.py
from rest_framework import serializers
from users.models.customuser import CustomUser
from users.models.userprofile import UserProfile
from users.models.addresses import District, Sector, Cell  # adjust import to where you defined these


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "bio",
            "gender",
            "date_of_birth",
            "work",
            "work_description",
            "province",
            "district",
            "sector",
            "cell",
            "village",
            "website",
            "profile_picture",
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    work_assignment = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "full_names",
            "phone_number",
            "user_level",
            "national_id",
            "date_joined",
            "profile",          # where they live
            "work_assignment",  # where they work
        ]

    def get_work_assignment(self, obj):
        """Return the place this officer works (district/sector/cell)."""
        assignment = {}

        # District officer
        district = District.objects.filter(district_officer=obj).first()
        if district:
            assignment["district"] = {
                "id": district.id,
                "name": district.name,
                "province": district.province.name,
            }

        # Sector officer
        sector = Sector.objects.filter(sector_officer=obj).first()
        if sector:
            assignment["sector"] = {
                "id": sector.id,
                "name": sector.name,
                "district": sector.district.name,
                "province": sector.district.province.name,
            }

        # Cell officer
        cell = Cell.objects.filter(cell_officer=obj).first()
        if cell:
            assignment["cell"] = {
                "id": cell.id,
                "name": cell.name,
                "sector": cell.sector.name,
                "district": cell.sector.district.name,
                "province": cell.sector.district.province.name,
            }

        return assignment or None

    def update(self, instance, validated_data):
        # Handle profile update separately
        profile_data = validated_data.pop("profile", None)

        # Update main user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update or create profile
        if profile_data:
            profile, created = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance
