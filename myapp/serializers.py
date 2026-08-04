from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from rest_framework_simplejwt.tokens import RefreshToken
from myapp.models import (

    User,
    State,
    District,
    Department,
    Role,
    DepartmentOfficer,
    AssetCategory,
    GISCatalogEntry,
    GISLayerFeature,
    Facility,
    FacilityHistory,
)



class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "code", "scope_level", "description"]

class UserSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source="state.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    role_info = RoleSerializer(source="role", read_only=True)
    
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "designation",
            "state",
            "state_name",
            "district",
            "district_name",
            "department",
            "department_name",
            "role",
            "role_info",
            "is_active",
            "is_staff",
            "is_superuser",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "is_staff", "is_superuser", "created_at", "updated_at"]


class RoleField(serializers.RelatedField):
    """
    Flexible Role field accepting either Role ID (int) or Role code/name (str).
    """
    def get_queryset(self):
        return Role.objects.all()

    def to_internal_value(self, data):
        if data is None or data == "":
            raise serializers.ValidationError("Role is mandatory for user signup.")

        if isinstance(data, Role):
            return data

        if isinstance(data, int) or (isinstance(data, str) and data.isdigit()):
            try:
                return Role.objects.get(pk=int(data))
            except Role.DoesNotExist:
                raise serializers.ValidationError(f"Role with ID '{data}' does not exist.")

        if isinstance(data, str):
            try:
                return Role.objects.get(Q(code__iexact=data) | Q(name__iexact=data))
            except Role.DoesNotExist:
                raise serializers.ValidationError(f"Role with code or name '{data}' does not exist.")

        raise serializers.ValidationError("Invalid role format.")

    def to_representation(self, value):
        return value.id if value else None


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        validators=[validate_password]
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=False,
        style={"input_type": "password"}
    )
    email = serializers.EmailField(required=True)
    role = RoleField(
        required=True,
        allow_null=False,
        error_messages={
            "required": "Role is mandatory for user signup.",
            "null": "Role cannot be null.",
        }
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "phone",
            "designation",
            "state",
            "district",
            "department",
            "role",
        ]
        # extra_kwargs = {
        #     "first_name": {"required": False, "allow_blank": True},
        #     "last_name": {"required": False, "allow_blank": True},
        #     "phone": {"required": False, "allow_blank": True},
        #     "designation": {"required": False, "allow_blank": True},
        #     "state": {"required": False, "allow_null": True},
        #     "district": {"required": False, "allow_null": True},
        #     "department": {"required": False, "allow_null": True},
        # }

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return value

    def validate(self, attrs):
        confirm_pwd = attrs.pop("confirm_password", None)
        if confirm_pwd is not None and attrs.get("password") != confirm_pwd:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        # If role is Citizen, disable/forbid department
        role = attrs.get("role")
        if role and (role.code in ["CITIZEN_REGISTERED", "CITIZEN_ANONYMOUS"] or role.scope_level in ["SELF", "ANONYMOUS"]):
            if attrs.get("department") is not None:
                raise serializers.ValidationError({"department": "Department cannot be assigned to a Citizen role."})
            attrs["department"] = None
            attrs["designation"] = ""

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        required=True,
        help_text="Enter username or email address"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"}
    )

    def validate(self, attrs):
        username_or_email = attrs.get("username", "").strip()
        password = attrs.get("password", "")

        if not username_or_email or not password:
            raise serializers.ValidationError("Both username/email and password are required.")

        # Resolve user by username or email
        try:
            user_obj = User.objects.get(
                Q(username__iexact=username_or_email) | Q(email__iexact=username_or_email)
            )
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Invalid credentials."})
        except User.MultipleObjectsReturned:
            user_obj = User.objects.filter(
                Q(username__iexact=username_or_email) | Q(email__iexact=username_or_email)
            ).first()

        user = authenticate(
            request=self.context.get("request"),
            username=user_obj.username,
            password=password
        )

        if not user:
            raise serializers.ValidationError({"detail": "Invalid credentials."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "User account is disabled."})

        refresh = RefreshToken.for_user(user)

        return {
            "user": user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


# ==========================================
# GIS LAYER & FEATURE SERIALIZERS
# ==========================================

from myapp.models import GISCatalogEntry, GISLayerFeature


class GISLayerFeatureSerializer(serializers.ModelSerializer):
    """Serializer for individual GIS spatial features."""
    class Meta:
        model = GISLayerFeature
        fields = [
            "id",
            "catalog_entry",
            "feature_id",
            "name",
            "properties",
            "geom_geojson",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GISCatalogSerializer(serializers.ModelSerializer):
    """Serializer for GIS Catalog Entries (Layers)."""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = GISCatalogEntry
        fields = [
            "id",
            "layer_name",
            "display_name",
            "geometry_type",
            "category",
            "feature_count",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "feature_count", "created_at", "updated_at"]

    def get_display_name(self, obj):
        return obj.layer_name.replace("_", " ")


class GISLayerUploadSerializer(serializers.Serializer):
    """Serializer for uploading single or multi-layer shapefile (.zip) or GeoJSON file."""
    layer_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="", help_text="Custom name for the GIS layer (Optional if zip contains multiple shapefiles)")
    category = serializers.CharField(max_length=100, required=False, allow_blank=True, default="Custom Uploads", help_text="Category name (Optional)")
    file = serializers.FileField(required=True, help_text="Shapefile (.zip) or GeoJSON (.json / .geojson) file")

class DistrictSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta:
        model = District
        fields = ["id", "name", "state", "state_name"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "description"]


class DepartmentOfficerSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = DepartmentOfficer
        fields = [
            "id",
            "name",
            "designation",
            "department",
            "department_name",
            "user",
            "email",
            "contact",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AssetCategorySerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    layer_name = serializers.CharField(source="catalog_entry.layer_name", read_only=True)
    gis_category = serializers.CharField(source="catalog_entry.category", read_only=True)
    feature_count = serializers.IntegerField(source="catalog_entry.feature_count", read_only=True)

    class Meta:
        model = AssetCategory
        fields = [
            "id",
            "name",
            "department",
            "department_name",
            "catalog_entry",
            "layer_name",
            "gis_category",
            "feature_count",
            "field_schema",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class FacilityHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityHistory
        fields = [
            "id",
            "facility",
            "valid_from",
            "valid_to",
            "snapshot",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "facility", "created_at", "updated_at"]


class FacilitySerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    layer_name = serializers.CharField(source="catalog_entry.layer_name", read_only=True)
    geom_geojson = serializers.SerializerMethodField()

    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "district",
            "district_name",
            "department",
            "department_name",
            "category",
            "category_name",
            "catalog_entry",
            "layer_name",
            "gis_feature",
            "attributes",
            "geom",
            "geom_geojson",
            "hazard_safe",
            "hazard_flags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_geom_geojson(self, obj):
        if not obj.geom:
            return None
        if hasattr(obj.geom, "geojson"):
            import json
            try:
                return json.loads(obj.geom.geojson)
            except Exception:
                return str(obj.geom)
        elif isinstance(obj.geom, dict):
            return obj.geom
        return obj.geom

    def to_internal_value(self, data):
        # Allow input geom to be passed as GeoJSON dict or string
        if "geom" in data and data["geom"] is not None:
            geom_val = data["geom"]
            if isinstance(geom_val, (dict, str)):
                from myapp.models import HAS_GEODJANGO
                if HAS_GEODJANGO:
                    from django.contrib.gis.geos import GEOSGeometry
                    import json
                    try:
                        if isinstance(geom_val, dict):
                            geom_val = json.dumps(geom_val)
                        data = data.copy()
                        data["geom"] = GEOSGeometry(geom_val)
                    except Exception as e:
                        raise serializers.ValidationError({"geom": f"Invalid GeoJSON geometry: {str(e)}"})
        return super().to_internal_value(data)


