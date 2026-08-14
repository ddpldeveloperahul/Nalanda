from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from rest_framework_simplejwt.tokens import RefreshToken
from myapp.models import (
    User,
    State,
    District,
    Block,
    Department,
    Role,
    DepartmentOfficer,
    AssetCategory,
    GISCatalogEntry,
    GISLayerFeature,
    Facility,
    FacilityHistory,
    ComplaintCategory,
    Complaint,
    ComplaintEvidence,
    ComplaintTimeline,
    NotificationTemplate,
    NotificationDispatchLog,
    GapScore,
    Proposal,
    BudgetApproval,
    ProjectExecution,
    SiteDiary,
    MeasurementBook,
    ProjectBill,
    ExecutionRisk,
    Report,
    Employee,
    EmployeeInvitation,
    StateBudget,
    DepartmentBudget,
    DistrictAllocation,
    SchemeMaster,
    FinancialLedgerEntry,
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
        email = str(value).strip().lower()
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            raise serializers.ValidationError("Please enter a valid email address (e.g., user@gmail.com).")
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return email

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
    """
    Comprehensive Serializer for individual GIS spatial features with support for:
    - GeoJSON & Spatial point coordinates (lat, lng)
    - Automatic catalog entry binding & layer name resolution
    - Dynamic attribute properties JSONB
    """
    layer_name = serializers.CharField(source="catalog_entry.layer_name", read_only=True)
    category = serializers.CharField(source="catalog_entry.category", read_only=True)
    latitude = serializers.FloatField(write_only=True, required=False, allow_null=True)
    longitude = serializers.FloatField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = GISLayerFeature
        fields = [
            "id",
            "catalog_entry",
            "layer_name",
            "category",
            "feature_id",
            "name",
            "properties",
            "geom_geojson",
            "latitude",
            "longitude",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "layer_name", "category", "created_at", "updated_at"]

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            data_dict = data.dict()
        elif hasattr(data, 'copy'):
            data_dict = data.copy()
        else:
            data_dict = dict(data)

        # Parse stringified properties or geom_geojson if sent as JSON string
        import json
        if "properties" in data_dict and isinstance(data_dict["properties"], str):
            try:
                data_dict["properties"] = json.loads(data_dict["properties"])
            except Exception:
                pass

        if "geom_geojson" in data_dict and isinstance(data_dict["geom_geojson"], str):
            try:
                data_dict["geom_geojson"] = json.loads(data_dict["geom_geojson"])
            except Exception:
                pass

        # Handle latitude & longitude inputs
        lat_val = None
        for k in ["latitude", "lat"]:
            if k in data_dict and data_dict[k] not in [None, "", "null"]:
                try:
                    lat_val = float(data_dict[k])
                    break
                except (ValueError, TypeError):
                    pass

        lng_val = None
        for k in ["longitude", "lng", "long", "lon"]:
            if k in data_dict and data_dict[k] not in [None, "", "null"]:
                try:
                    lng_val = float(data_dict[k])
                    break
                except (ValueError, TypeError):
                    pass

        if lat_val is not None and lng_val is not None:
            data_dict["latitude"] = lat_val
            data_dict["longitude"] = lng_val
            data_dict["geom_geojson"] = {
                "type": "Point",
                "coordinates": [lng_val, lat_val]
            }

        return super().to_internal_value(data_dict)

    def _sync_geos_geometry(self, instance, validated_data):
        geom_dict = instance.geom_geojson or validated_data.get("geom_geojson")
        from myapp.models import HAS_GEODJANGO
        if HAS_GEODJANGO and geom_dict:
            import json
            from django.contrib.gis.geos import GEOSGeometry
            try:
                instance.geom = GEOSGeometry(json.dumps(geom_dict))
            except Exception:
                pass

    def create(self, validated_data):
        lat = validated_data.pop("latitude", None)
        lng = validated_data.pop("longitude", None)
        if lat is not None and lng is not None and "geom_geojson" not in validated_data:
            validated_data["geom_geojson"] = {
                "type": "Point",
                "coordinates": [float(lng), float(lat)]
            }

        catalog = validated_data.get("catalog_entry")
        if catalog and not validated_data.get("feature_id"):
            next_num = catalog.features.count() + 1
            validated_data["feature_id"] = str(next_num)

        feature = super().create(validated_data)
        self._sync_geos_geometry(feature, validated_data)
        feature.save(update_fields=["geom"] if getattr(feature, "geom", None) else [])
        
        # Update feature_count on catalog entry
        if catalog:
            catalog.feature_count = catalog.features.count()
            catalog.save(update_fields=["feature_count", "updated_at"])

        return feature

    def update(self, instance, validated_data):
        lat = validated_data.pop("latitude", None)
        lng = validated_data.pop("longitude", None)
        if lat is not None and lng is not None:
            validated_data["geom_geojson"] = {
                "type": "Point",
                "coordinates": [float(lng), float(lat)]
            }

        feature = super().update(instance, validated_data)
        self._sync_geos_geometry(feature, validated_data)
        feature.save()

        # Update feature_count on catalog entry
        catalog = feature.catalog_entry
        if catalog:
            catalog.feature_count = catalog.features.count()
            catalog.save(update_fields=["feature_count", "updated_at"])

        return feature


class GISCatalogSerializer(serializers.ModelSerializer):
    """Serializer for GIS Catalog Entries (Layers)."""
    display_name = serializers.SerializerMethodField()
    feature_count = serializers.SerializerMethodField()

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

    def get_feature_count(self, obj):
        # Return real-time feature count from database
        cnt = obj.features.count()
        if obj.feature_count != cnt:
            obj.feature_count = cnt
            obj.save(update_fields=["feature_count"])
        return cnt



class GISLayerUploadSerializer(serializers.Serializer):
    """Serializer for uploading single or multi-layer shapefile (.zip) or GeoJSON file."""
    layer_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="", help_text="Custom name for the GIS layer (Optional if zip contains multiple shapefiles)")
    category = serializers.CharField(max_length=100, required=False, allow_blank=True, default="Custom Uploads", help_text="Category name (Optional)")
    file = serializers.FileField(required=True, help_text="Shapefile (.zip) or GeoJSON (.json / .geojson) file")

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name"]


class DistrictSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta:
        model = District
        fields = ["id", "name", "state", "state_name"]


class BlockSerializer(serializers.ModelSerializer):
    district_id = serializers.IntegerField(source="subdivision.district.id", read_only=True)
    district_name = serializers.CharField(source="subdivision.district.name", read_only=True)

    class Meta:
        model = Block
        fields = ["id", "name", "district_id", "district_name"]


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
    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)

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
            "latitude",     
            "longitude",  
            "geom_geojson",
            "hazard_safe",
            "hazard_flags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
    def create(self, validated_data):
        from django.contrib.gis.geos import Point

        lat = validated_data.pop("latitude", None)
        lng = validated_data.pop("longitude", None)

        if lat is not None and lng is not None:
            validated_data["geom"] = Point(float(lng), float(lat))

        return super().create(validated_data)

    def update(self, instance, validated_data):
        from django.contrib.gis.geos import Point

        lat = validated_data.pop("latitude", None)
        lng = validated_data.pop("longitude", None)

        if lat is not None and lng is not None:
            instance.geom = Point(float(lng), float(lat))

        return super().update(instance, validated_data)
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


class ComplaintCategorySerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = ComplaintCategory
        fields = [
            "id",
            "name",
            "department",
            "department_name",
            "default_priority",
            "default_sla_hours",
            "icon",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ComplaintEvidenceSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True)

    class Meta:
        model = ComplaintEvidence
        fields = [
            "id",
            "complaint",
            "file",
            "file_name",
            "file_type",
            "stage",
            "uploaded_by",
            "uploaded_by_name",
            "latitude",
            "longitude",
            "is_geotag_verified",
            "distance_from_pin_m",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ComplaintTimelineSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ComplaintTimeline
        fields = [
            "id",
            "complaint",
            "action",
            "from_status",
            "to_status",
            "performed_by",
            "performed_by_name",
            "performer_role",
            "remarks",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_performed_by_name(self, obj):
        if obj.performed_by:
            full = obj.performed_by.get_full_name()
            return full if full else obj.performed_by.username
        return "System"


class ComplaintSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    block_name = serializers.CharField(source="block.name", read_only=True)
    village_ward_name = serializers.CharField(source="village_ward.name", read_only=True)
    assigned_officer_name = serializers.SerializerMethodField()
    assigned_inspector_name = serializers.SerializerMethodField()
    evidences = ComplaintEvidenceSerializer(many=True, read_only=True)
    timeline = ComplaintTimelineSerializer(many=True, read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "tracking_no",
            "title",
            "description",
            "category",
            "category_name",
            "department",
            "department_name",
            "citizen_user",
            "citizen_name",
            "citizen_phone",
            "citizen_email",
            "is_identity_masked",
            "assigned_officer",
            "assigned_officer_name",
            "assigned_inspector",
            "assigned_inspector_name",
            "status",
            "priority",
            "sla_target_hours",
            "sla_deadline",
            "is_sla_breached",
            "latitude",
            "longitude",
            "district",
            "district_name",
            "subdivision",
            "block",
            "block_name",
            "village_ward",
            "village_ward_name",
            "nearest_facility",
            "nearest_facility_name",
            "nearest_facility_distance_m",
            "nearest_gis_feature",
            "resolution_summary",
            "rejection_reason",
            "transfer_reason",
            "escalation_reason",
            "rating",
            "feedback_comment",
            "evidences",
            "timeline",
            "resolved_at",
            "closed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "tracking_no",
            "sla_deadline",
            "is_sla_breached",
            "resolved_at",
            "closed_at",
            "created_at",
            "updated_at",
        ]

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            data_dict = data.dict()
        elif hasattr(data, 'copy'):
            data_dict = data.copy()
        else:
            data_dict = dict(data)

        # Flexible Latitude parsing (handles latitude, latitute, lat, Lat, etc.)
        lat_val = None
        for key in ["latitude", "latitute", "lat", "Lat", "Latitude", "Latitute"]:
            if key in data_dict and data_dict[key] not in [None, "", "null", "undefined"]:
                lat_val = data_dict[key]
                break

        if lat_val is not None:
            try:
                if isinstance(lat_val, (list, tuple)):
                    lat_val = lat_val[0]
                data_dict["latitude"] = float(lat_val)
            except (ValueError, TypeError):
                pass

        # Flexible Longitude parsing (handles longitude, longitute, lng, long, lon, Lng, etc.)
        lng_val = None
        for key in ["longitude", "longitute", "lng", "long", "lon", "Lng", "Long", "Longitude", "Longitute"]:
            if key in data_dict and data_dict[key] not in [None, "", "null", "undefined"]:
                lng_val = data_dict[key]
                break

        if lng_val is not None:
            try:
                if isinstance(lng_val, (list, tuple)):
                    lng_val = lng_val[0]
                data_dict["longitude"] = float(lng_val)
            except (ValueError, TypeError):
                pass

        return super().to_internal_value(data_dict)

    def get_assigned_officer_name(self, obj):
        if obj.assigned_officer:
            full = obj.assigned_officer.get_full_name()
            return full if full else obj.assigned_officer.username
        return None

    def get_assigned_inspector_name(self, obj):
        if obj.assigned_inspector:
            full = obj.assigned_inspector.get_full_name()
            return full if full else obj.assigned_inspector.username
        return None


class ComplaintActionSerializer(serializers.Serializer):
    target_user_id = serializers.IntegerField(required=False, allow_null=True)
    target_department_id = serializers.IntegerField(required=False, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    resolution_summary = serializers.CharField(required=False, allow_blank=True, default="")
    rating = serializers.IntegerField(required=False, allow_null=True)
    feedback_comment = serializers.CharField(required=False, allow_blank=True, default="")


class ProposalSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source="state.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    reviewed_by_name = serializers.SerializerMethodField(read_only=True)
    approved_by_name = serializers.SerializerMethodField(read_only=True)
    cost_formatted = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    linked_complaint_number = serializers.CharField(source="linked_complaint.complaint_number", read_only=True)
    funding_source = serializers.CharField(required=False, allow_blank=True, default="District")

    def validate_funding_source(self, value):
        if not value:
            return "District"
        v_lower = str(value).strip().lower()
        mapping = {
            "district": "District",
            "distict": "District",
            "state": "State",
            "central": "Central",
            "csr": "CSR",
            "world bank": "World Bank",
            "worldbank": "World Bank",
            "adb": "ADB",
            "other": "Other",
        }
        if v_lower in mapping:
            return mapping[v_lower]
        for key, val in mapping.items():
            if key in v_lower:
                return val
        return "District"

    class Meta:
        model = Proposal
        fields = [
            "id",
            "proposal_id",
            "title",
            "category",
            "state",
            "state_name",
            "district",
            "district_name",
            "department",
            "department_name",
            "created_by",
            "created_by_name",
            "status",
            "status_display",
            "stage",
            "stage_display",
            "priority",
            
            # Step 1: Need ID
            "village",
            "block",
            "ward",
            "population_impact",
            "gap_score",
            "linked_complaint",
            "linked_complaint_number",
            "linked_complaint_ids",
            "problem_statement",
            
            # Step 2: Survey & Inspection
            "inspection_date",
            "survey_team",
            "inspection_notes",
            "gis_reference",
            "latitude",
            "longitude",
            
            # Step 3: Technical DPR
            "technical_scope",
            "engineering_notes",
            "estimated_timeline",
            
            # Step 4: Financial Estimation
            "civil_works",
            "equipment_cost",
            "electrical_cost",
            "contingency_cost",
            "maintenance_cost",
            "estimated_cost",
            "cost_formatted",
            "delegated_power_note",
            
            # Step 5: Clearances
            "funding_source",
            "clearances_notes",
            "clearances",
            
            # Step 6: Attachments
            "attachments",
            
            # Step 7: Review & Submission
            "review_notes",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "approved_by",
            "approved_by_name",
            "approved_at",
            
            "is_deleted",
            "created_at",
            "updated_at",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return "System"

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name() or obj.reviewed_by.username
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return None

    def get_cost_formatted(self, obj):
        cost = float(obj.estimated_cost or 0)
        if cost >= 10000000:
            return f"₹{round(cost / 10000000.0, 2)} Cr"
        elif cost >= 100000:
            return f"₹{round(cost / 100000.0, 2)} Lakh"
        return f"₹{cost:,.2f}"


# ==========================================
# PROJECT EXECUTION ERP SERIALIZERS
# ==========================================

class ProjectExecutionSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    proposal_id_str = serializers.CharField(source="proposal.proposal_id", read_only=True)
    proposal_details = ProposalSerializer(source="proposal", read_only=True)
    proposed_amount_formatted = serializers.SerializerMethodField(read_only=True)
    budget_formatted = serializers.SerializerMethodField(read_only=True)
    expenditure_formatted = serializers.SerializerMethodField(read_only=True)
    bill_amount = serializers.SerializerMethodField(read_only=True)
    bill_amount_formatted = serializers.SerializerMethodField(read_only=True)
    net_payable_amount = serializers.SerializerMethodField(read_only=True)
    net_payable_amount_formatted = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    risk_display = serializers.CharField(source="get_risk_level_display", read_only=True)

    class Meta:
        model = ProjectExecution
        fields = "__all__"

    def get_proposed_amount_formatted(self, obj):
        amt = float(obj.proposed_amount or 0)
        if amt >= 10000000:
            return f"₹{round(amt / 10000000.0, 2)} Cr"
        elif amt >= 100000:
            return f"₹{round(amt / 100000.0, 2)} Lakh"
        return f"₹{amt:,.2f}"

    def get_budget_formatted(self, obj):
        amt = float(obj.sanction_amount or 0)
        if amt >= 10000000:
            return f"₹{round(amt / 10000000.0, 2)} Cr"
        elif amt >= 100000:
            return f"₹{round(amt / 100000.0, 2)} Lakh"
        return f"₹{amt:,.2f}"

    def get_expenditure_formatted(self, obj):
        amt = float(obj.expenditure_amount or 0)
        if amt >= 10000000:
            return f"₹{round(amt / 10000000.0, 2)} Cr"
        elif amt >= 100000:
            return f"₹{round(amt / 100000.0, 2)} Lakh"
        return f"₹{amt:,.2f}"

    def get_bill_amount(self, obj):
        bills = getattr(obj, "bills", None)
        if bills is not None:
            return sum(float(b.claimed_amount or 0) for b in bills.all())
        return 0.0

    def get_bill_amount_formatted(self, obj):
        amt = self.get_bill_amount(obj)
        if amt >= 10000000:
            return f"₹{round(amt / 10000000.0, 2)} Cr"
        elif amt >= 100000:
            return f"₹{round(amt / 100000.0, 2)} Lakh"
        return f"₹{amt:,.2f}"

    def get_net_payable_amount(self, obj):
        bills = getattr(obj, "bills", None)
        if bills is not None:
            return sum(float(b.net_payable_amount or 0) for b in bills.all())
        return 0.0

    def get_net_payable_amount_formatted(self, obj):
        amt = self.get_net_payable_amount(obj)
        if amt >= 10000000:
            return f"₹{round(amt / 10000000.0, 2)} Cr"
        elif amt >= 100000:
            return f"₹{round(amt / 100000.0, 2)} Lakh"
        return f"₹{amt:,.2f}"


class SiteDiarySerializer(serializers.ModelSerializer):
    project_id_str = serializers.CharField(source="project.project_id", read_only=True)
    project_title = serializers.CharField(source="project.title", read_only=True)
    logged_by_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SiteDiary
        fields = "__all__"

    def get_logged_by_name(self, obj):
        if obj.logged_by:
            return obj.logged_by.get_full_name() or obj.logged_by.username
        return "Field Engineer"

    def to_internal_value(self, data):
        data_copy = data.copy() if hasattr(data, 'copy') else dict(data)
        
        # Map modal fields from screenshot
        if "physical_progress" in data_copy and "progress_logged" not in data_copy:
            data_copy["progress_logged"] = data_copy["physical_progress"]
        elif "physical_progress_%" in data_copy and "progress_logged" not in data_copy:
            data_copy["progress_logged"] = data_copy["physical_progress_%"]
        elif "progress_percentage" in data_copy and "progress_logged" not in data_copy:
            data_copy["progress_logged"] = data_copy["progress_percentage"]
            
        if "labour_deployed" in data_copy and "labour_count" not in data_copy:
            data_copy["labour_count"] = data_copy["labour_deployed"]
            
        if "materials_consumed" in data_copy and "materials_used" not in data_copy:
            data_copy["materials_used"] = data_copy["materials_consumed"]
            
        if "remarks" in data_copy and "work_description" not in data_copy:
            data_copy["work_description"] = data_copy["remarks"]
        elif "observations" in data_copy and "work_description" not in data_copy:
            data_copy["work_description"] = data_copy["observations"]

        return super().to_internal_value(data_copy)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["physical_progress"] = float(instance.progress_logged or 0)
        rep["labour_deployed"] = instance.labour_count
        rep["materials_consumed"] = instance.materials_used
        rep["remarks"] = instance.work_description
        rep["observations"] = instance.work_description
        return rep


class MeasurementBookSerializer(serializers.ModelSerializer):
    project_id_str = serializers.CharField(source="project.project_id", read_only=True)
    project_title = serializers.CharField(source="project.title", read_only=True)

    class Meta:
        model = MeasurementBook
        fields = "__all__"

    def to_internal_value(self, data):
        data_copy = data.copy() if hasattr(data, 'copy') else dict(data)
        
        # Modal field mappings for Measurement Book Entry screenshot
        if "work_item" in data_copy and "item_description" not in data_copy:
            data_copy["item_description"] = data_copy["work_item"]
        elif "remarks" in data_copy and "item_description" not in data_copy:
            data_copy["item_description"] = data_copy["remarks"]
        elif "observations" in data_copy and "item_description" not in data_copy:
            data_copy["item_description"] = data_copy["observations"]

        if "executed_quantity" in data_copy and "quantity_measured" not in data_copy:
            data_copy["quantity_measured"] = data_copy["executed_quantity"]

        return super().to_internal_value(data_copy)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["work_item"] = instance.item_description
        rep["executed_quantity"] = float(instance.quantity_measured or 0)
        rep["estimated_quantity"] = float(instance.estimated_quantity or 0)
        rep["remarks"] = instance.item_description
        rep["observations"] = instance.item_description
        return rep


class ProjectBillSerializer(serializers.ModelSerializer):
    project_id_str = serializers.CharField(source="project.project_id", read_only=True)
    project_title = serializers.CharField(source="project.title", read_only=True)

    class Meta:
        model = ProjectBill
        fields = "__all__"

    def to_internal_value(self, data):
        data_copy = data.copy() if hasattr(data, 'copy') else dict(data)
        
        # Modal field mappings for Submit Running Bill screenshot
        if "bill_amount" in data_copy and "claimed_amount" not in data_copy:
            data_copy["claimed_amount"] = data_copy["bill_amount"]
            if "verified_amount" not in data_copy:
                data_copy["verified_amount"] = data_copy["bill_amount"]
            if "net_payable_amount" not in data_copy:
                data_copy["net_payable_amount"] = data_copy["bill_amount"]

        if "observations" in data_copy and "remarks" not in data_copy:
            data_copy["remarks"] = data_copy["observations"]

        return super().to_internal_value(data_copy)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["bill_amount"] = float(instance.claimed_amount or 0)
        rep["remarks"] = instance.remarks or f"Bill {instance.bill_number}"
        rep["observations"] = instance.remarks or f"Bill {instance.bill_number}"
        return rep


class ExecutionRiskSerializer(serializers.ModelSerializer):
    project_id_str = serializers.CharField(source="project.project_id", read_only=True)
    project_title = serializers.CharField(source="project.title", read_only=True)
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)

    class Meta:
        model = ExecutionRisk
        fields = "__all__"


class ReportSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    generated_by_name = serializers.SerializerMethodField(read_only=True)
    generated_date_str = serializers.DateTimeField(source="generated_at", format="%Y-%m-%d", read_only=True)
    size = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Report
        fields = "__all__"

    def get_generated_by_name(self, obj):
        if obj.generated_by:
            return obj.generated_by.get_full_name() or obj.generated_by.username
        return "System Admin"

    def get_size(self, obj):
        if obj.file and hasattr(obj.file, 'size') and obj.file.size:
            return f"{round(obj.file.size / (1024 * 1024), 1)} MB"
class EmployeeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    reports_to_name = serializers.CharField(source="reports_to.full_name", read_only=True)
    role_display = serializers.CharField(source="role_name", read_only=True)
    role_id = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Employee
        fields = "__all__"
        extra_kwargs = {
            'employee_code': {'required': False, 'allow_blank': True}
        }

    def get_role_id(self, obj):
        return obj.role.id if obj.role else None


class EmployeeInvitationSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    invited_by_name = serializers.SerializerMethodField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = EmployeeInvitation
        fields = "__all__"

    def get_invited_by_name(self, obj):
        if obj.invited_by:
            return obj.invited_by.get_full_name() or obj.invited_by.username
        return "System Admin"


class StateBudgetSerializer(serializers.ModelSerializer):
    financial_year = serializers.CharField(max_length=20, required=True)
    total_state_budget_cr = serializers.DecimalField(max_digits=14, decimal_places=2, required=True)
    department_allocation_cr = serializers.DecimalField(max_digits=14, decimal_places=2, required=True)
    available_balance_cr = serializers.SerializerMethodField()
    class Meta:
        model = StateBudget
        fields = "__all__"
        extra_kwargs = {
            "financial_year": {
                "required": True,
                "error_messages": {
                    "required": "Financial year (e.g. '2026-27' or '2027-28') is required.",
                    "unique": "State Master Budget for this Financial Year already exists."
                }
            },
            "total_state_budget_cr": {
                "required": True,
                "error_messages": {"required": "Total State Budget amount in Cr is required."}
            },
            "department_allocation_cr": {
                "required": True,
                "error_messages": {"required": "Department Allocation amount in Cr is required."}
            }
        }
    
    def get_available_balance_cr(self, obj):
        tot = obj.total_state_budget_cr or 0
        dept = obj.department_allocation_cr or 0
        return float(tot - dept)


class DepartmentBudgetSerializer(serializers.ModelSerializer):
    financial_year = serializers.CharField(max_length=20, required=True)
    authorized_budget_cr = serializers.DecimalField(max_digits=14, decimal_places=2, required=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    utilization_percentage = serializers.ReadOnlyField()

    class Meta:
        model = DepartmentBudget
        fields = "__all__"
        extra_kwargs = {
            "financial_year": {
                "required": True,
                "error_messages": {"required": "Financial year (e.g. '2026-27') is required."}
            },
            "department": {
                "required": True,
                "error_messages": {"required": "Department ID is required."}
            },
            "authorized_budget_cr": {
                "required": True,
                "error_messages": {"required": "Authorized budget amount in Cr is required."}
            }
        }


class DistrictAllocationSerializer(serializers.ModelSerializer):
    financial_year = serializers.CharField(max_length=20, required=True)
    allocation_amount_cr = serializers.DecimalField(max_digits=14, decimal_places=2, required=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default="")

    class Meta:
        model = DistrictAllocation
        fields = "__all__"
        extra_kwargs = {
            "financial_year": {
                "required": True,
                "error_messages": {"required": "Financial year (e.g. '2026-27') is required."}
            },
            "district": {
                "required": True,
                "error_messages": {"required": "District ID is required."}
            },
            "allocation_amount_cr": {
                "required": True,
                "error_messages": {"required": "Allocation amount in Cr is required."}
            }
        }


class SchemeMasterSerializer(serializers.ModelSerializer):
    code = serializers.CharField(max_length=50, required=True)
    name = serializers.CharField(max_length=255, required=True)
    total_allocation_cr = serializers.DecimalField(max_digits=14, decimal_places=2, required=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = SchemeMaster
        fields = "__all__"
        extra_kwargs = {
            "code": {
                "required": True,
                "error_messages": {
                    "required": "Scheme Code (e.g. 'SCH-HEALTH-001') is required.",
                    "unique": "Scheme Code must be unique."
                }
            },
            "name": {
                "required": True,
                "error_messages": {"required": "Scheme Name is required."}
            },
            "department": {
                "required": True,
                "error_messages": {"required": "Department ID is required."}
            },
            "total_allocation_cr": {
                "required": True,
                "error_messages": {"required": "Total Scheme Allocation amount in Cr is required."}
            }
        }


class FinancialLedgerEntrySerializer(serializers.ModelSerializer):
    transaction_id = serializers.CharField(max_length=100, required=True)
    financial_year = serializers.CharField(max_length=20, required=True)
    amount_cr = serializers.DecimalField(max_digits=14, decimal_places=2, required=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    district_name = serializers.CharField(source="district.name", read_only=True, default="")
    scheme_name = serializers.CharField(source="scheme.name", read_only=True, default="")

    class Meta:
        model = FinancialLedgerEntry
        fields = "__all__"
        extra_kwargs = {
            "transaction_id": {
                "required": True,
                "error_messages": {
                    "required": "Transaction ID (e.g. 'TXN-FIN-2026-001') is required.",
                    "unique": "Transaction ID must be unique."
                }
            },
            "financial_year": {
                "required": True,
                "error_messages": {"required": "Financial year (e.g. '2026-27') is required."}
            },
            "entry_type": {
                "required": True,
                "error_messages": {"required": "Entry Type (PROVISION, ALLOCATION, SANCTION, RELEASE, COMMITMENT, UTILIZATION) is required."}
            },
            "amount_cr": {
                "required": True,
                "error_messages": {"required": "Amount in Cr is required."}
            }
        }


# ==========================================
# AUTH PASSWORD MANAGEMENT SERIALIZERS
# ==========================================

class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="Registered email address")

    def validate_email(self, value):
        email_str = str(value).strip().lower()
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email_str):
            raise serializers.ValidationError("Please enter a valid email address (e.g., user@gmail.com).")
        if not User.objects.filter(Q(email__iexact=email_str) | Q(username__iexact=email_str)).exists():
            raise serializers.ValidationError(f"No user account found registered with email '{email_str}'.")
        return email_str


class ResetPasswordWithOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="Registered email address")
    otp = serializers.CharField(max_length=10, required=True, help_text="6-digit verification code")
    new_password = serializers.CharField(min_length=6, write_only=True, required=True)
    confirm_password = serializers.CharField(min_length=6, write_only=True, required=True)

    def validate_email(self, value):
        email_str = str(value).strip().lower()
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email_str):
            raise serializers.ValidationError("Please enter a valid email address (e.g., user@gmail.com).")
        return email_str

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "New password and Confirm password do not match."})
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(min_length=6, required=True, write_only=True)
    confirm_password = serializers.CharField(min_length=6, required=True, write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "New password and Confirm password do not match."})
        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError({"new_password": "New password cannot be the same as your old password."})
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True, help_text="JWT Refresh token to blacklist")




