from rest_framework import serializers
from users.models.customuser import CustomUser
from users.models.userprofile import UserProfile
from users.models.addresses import District, Sector, Cell


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
    managed_district = serializers.PrimaryKeyRelatedField(read_only=True)
    managed_sector = serializers.PrimaryKeyRelatedField(read_only=True)
    managed_cell = serializers.PrimaryKeyRelatedField(read_only=True)

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
            "managed_district",
            "managed_sector",
            "managed_cell",
            "profile",
            "work_assignment",
        ]

    def get_work_assignment(self, obj):
        assignment = {}

        district = District.objects.filter(district_officer=obj).first()
        if district:
            assignment["district"] = {
                "id": district.id,
                "name": district.name,
                "province": district.province.name,
            }

        sector = Sector.objects.filter(sector_officer=obj).first()
        if sector:
            assignment["sector"] = {
                "id": sector.id,
                "name": sector.name,
                "district": sector.district.name,
                "province": sector.district.province.name,
            }

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

    def validate(self, attrs):
        errors = {}

        # Field-level required checks
        if not attrs.get("email"):
            errors["email"] = "Email is required."
        if not attrs.get("full_names"):
            errors["full_names"] = "Full names are required."
        if not attrs.get("phone_number"):
            errors["phone_number"] = "Phone number is required."
        if not attrs.get("national_id"):
            errors["national_id"] = "National ID is required."

        # Password validation on creation
        if self.instance is None:
            password = attrs.get("password")
            confirm_password = attrs.pop("confirm_password", None)
            if not password:
                errors["password"] = "Password is required."
            elif password != confirm_password:
                errors["confirm_password"] = "Passwords do not match."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        profile_data = validated_data.pop("profile", None)

        try:
            user = CustomUser.objects.create(**validated_data)
            if profile_data:
                UserProfile.objects.create(user=user, **profile_data)
            return user
        except Exception as e:
            # All DB/constraint errors are captured
            raise serializers.ValidationError({"non_field_error": str(e)})

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)

        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if profile_data:
                profile, created = UserProfile.objects.get_or_create(user=instance)
                for attr, value in profile_data.items():
                    setattr(profile, attr, value)
                profile.save()
        except Exception as e:
            raise serializers.ValidationError({"non_field_error": str(e)})

        return instance
