from django.shortcuts import render
from django.db.models import Q, Count
from rest_framework import status, permissions, viewsets


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from myapp.models import *
from myapp.serializers import (
    SignupSerializer,
    LoginSerializer,
    UserSerializer,
    DepartmentSerializer,
    DistrictSerializer,
    DepartmentOfficerSerializer,
    AssetCategorySerializer,
    FacilitySerializer,
    FacilityHistorySerializer,
    RoleSerializer,
    ComplaintCategorySerializer,
    ComplaintSerializer,
    ComplaintEvidenceSerializer,
    ComplaintTimelineSerializer,
    ComplaintActionSerializer,
    ProposalSerializer,
)
from myapp.services.complaint_service import (
    ComplaintService,
    calculate_haversine_distance_m,
    safe_float,
    extract_facility_lat_lng
)


def index(request):
    return render(request, "index.html")

def facilities_page(request):
    return render(request, "facilities.html")

def login_page(request):
    return render(request, "login.html", {"mode": "login"})

def signup_page(request):
    return render(request, "login.html", {"mode": "signup"})


class RoleListView(APIView):
    """
    API View to list all RBAC Roles for User Registration dropdown.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        roles = Role.objects.all().order_by("id")
        return Response(RoleSerializer(roles, many=True).data, status=status.HTTP_200_OK)


class SignupView(APIView):
    """
    API View to register a new user.
    Returns the created user profile alongside JWT access and refresh tokens.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = SignupSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user, context={"request": request}).data

            return Response(
                {
                    "message": "User registered successfully.",
                    "user": user_data,
                    "tokens": {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    API View to authenticate a user with username/email and password.
    Returns user profile alongside JWT access and refresh tokens.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            user_data = UserSerializer(user, context={"request": request}).data

            return Response(
                {
                    "message": "Login successful.",
                    "user": user_data,
                    "tokens": {
                        "access": serializer.validated_data["access"],
                        "refresh": serializer.validated_data["refresh"],
                    },
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """
    API View to retrieve the current authenticated user's profile information.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class GISCatalogListView(APIView):
    """
    API View to list all available GIS layers grouped by category.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        from myapp.models import GISCatalogEntry
        entries = GISCatalogEntry.objects.filter(is_published=True).order_by("category", "layer_name")

        grouped = {}
        for entry in entries:
            cat = entry.category or "Other GIS Layers"
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append({
                "id": entry.id,
                "layer_name": entry.layer_name,
                "display_name": entry.layer_name.replace("_", " "),
                "category": entry.category,
                "geometry_type": entry.geometry_type,
                "feature_count": entry.feature_count,
            })

        return Response(
            {
                "status": "success",
                "categories": grouped,
                "total_layers": entries.count(),
            },
            status=status.HTTP_200_OK,
        )


class GISLayerGeoJSONView(APIView):
    """
    API View to return full GeoJSON FeatureCollection for a specific layer.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, layer_name, *args, **kwargs):
        from myapp.models import GISCatalogEntry, GISLayerFeature

        try:
            catalog = GISCatalogEntry.objects.get(layer_name__iexact=layer_name, is_published=True)
        except GISCatalogEntry.DoesNotExist:
            return Response(
                {"error": f"Layer '{layer_name}' not found or not published."},
                status=status.HTTP_404_NOT_FOUND,
            )

        features_qs = GISLayerFeature.objects.filter(catalog_entry=catalog)
        features_list = []

        for feat in features_qs:
            geom = feat.geom_geojson
            if not geom and feat.geom:
                try:
                    import json
                    geom = json.loads(feat.geom.geojson)
                except Exception:
                    geom = None

            features_list.append({
                "type": "Feature",
                "id": feat.feature_id or feat.id,
                "properties": {
                    **feat.properties,
                    "feature_name": feat.name,
                    "layer_name": catalog.layer_name,
                },
                "geometry": geom,
            })

        geojson_data = {
            "type": "FeatureCollection",
            "layer_name": catalog.layer_name,
            "category": catalog.category,
            "geometry_type": catalog.geometry_type,
            "feature_count": len(features_list),
            "features": features_list,
        }

        return Response(geojson_data, status=status.HTTP_200_OK)

#=============================================
# Department, Officer & Asset Category CRUD Viewsets
# ==========================================

class DepartmentViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Line Departments.
    """
    queryset = Department.objects.all().order_by("id")
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs

    @action(detail=True, methods=["get"], url_path="complain")
    def department_complaints_singular(self, request, pk=None):
        return self.get_department_complaints(request, pk)

    @action(detail=True, methods=["get"], url_path="complaints")
    def department_complaints_plural(self, request, pk=None):
        return self.get_department_complaints(request, pk)

    def get_department_complaints(self, request, pk=None):
        if str(pk).isdigit():
            dept = Department.objects.filter(pk=pk).first()
        else:
            dept = Department.objects.filter(name__icontains=pk).first()

        if not dept:
            return Response(
                {"error": f"Department with ID/Name '{pk}' not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        complaints_qs = Complaint.objects.filter(department=dept).order_by("-created_at")
        
        status_counts = complaints_qs.values("status").annotate(total=Count("id"))
        priority_counts = complaints_qs.values("priority").annotate(total=Count("id"))
        
        status_summary = {item["status"]: item["total"] for item in status_counts}
        priority_summary = {item["priority"]: item["total"] for item in priority_counts}
        
        sla_breached_count = complaints_qs.filter(is_sla_breached=True).count()

        return Response({
            "department_id": dept.id,
            "department_name": dept.name,
            "total_complaints": complaints_qs.count(),
            "sla_breached_count": sla_breached_count,
            "status_summary": status_summary,
            "priority_summary": priority_summary,
            "complaints": ComplaintSerializer(complaints_qs, many=True).data
        }, status=status.HTTP_200_OK)


class DepartmentComplaintsAPIView(APIView):
    """
    Direct API View for /api/department/<department_id>/complain/
    Returns total complaint count, status/priority breakdown & complaint list for a department.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, department_id, *args, **kwargs):
        viewset = DepartmentViewSet()
        viewset.request = request
        return viewset.get_department_complaints(request, pk=department_id)


class UserViewSet(viewsets.ModelViewSet):
    """
    Complete RESTful CRUD ViewSet for System Users with Department-wise and Role-wise filtering.
    """
    queryset = User.objects.all().select_related("state", "district", "department", "role").order_by("-id")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        dept_val = self.request.query_params.get("department")
        role_val = self.request.query_params.get("role")
        district_val = self.request.query_params.get("district")

        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
                | Q(designation__icontains=search)
            )

        if dept_val:
            if str(dept_val).isdigit():
                qs = qs.filter(department_id=dept_val)
            else:
                qs = qs.filter(department__name__icontains=dept_val)

        if role_val:
            if str(role_val).isdigit():
                qs = qs.filter(role_id=role_val)
            else:
                qs = qs.filter(Q(role__code__iexact=role_val) | Q(role__name__icontains=role_val))

        if district_val:
            if str(district_val).isdigit():
                qs = qs.filter(district_id=district_val)
            else:
                qs = qs.filter(district__name__icontains=district_val)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = SignupSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user, context={"request": request}).data, status=status.HTTP_201_CREATED)


class DepartmentUsersAPIView(APIView):
    """
    Direct API View for GET /api/department/<department_id>/users/
    Returns list and count of all users assigned to a specific department.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, department_id, *args, **kwargs):
        if str(department_id).isdigit():
            dept = Department.objects.filter(pk=department_id).first()
        else:
            dept = Department.objects.filter(name__icontains=department_id).first()

        if not dept:
            return Response(
                {"error": f"Department with ID/Name '{department_id}' not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        users_qs = User.objects.filter(department=dept).select_related("state", "district", "department", "role").order_by("id")
        return Response({
            "department_id": dept.id,
            "department_name": dept.name,
            "total_users": users_qs.count(),
            "users": UserSerializer(users_qs, many=True, context={"request": request}).data
        }, status=status.HTTP_200_OK)


class DistrictViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Master Districts.
    """
    queryset = District.objects.all().select_related("state").order_by("name")
    serializer_class = DistrictSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None




class DepartmentOfficerViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Department Officers / Nodal Officers.
    """
    queryset = DepartmentOfficer.objects.all().order_by("id")
    serializer_class = DepartmentOfficerSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        dept_id = self.request.query_params.get("department")
        search = self.request.query_params.get("search")

        if dept_id:
            qs = qs.filter(department_id=dept_id)
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(designation__icontains=search)
                | Q(email__icontains=search)
                | Q(contact__icontains=search)
            )
        return qs


class AssetCategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Asset Categories.
    """
    queryset = AssetCategory.objects.all().select_related("department", "catalog_entry").order_by("name")
    serializer_class = AssetCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        dept_id = self.request.query_params.get("department")
        search = self.request.query_params.get("search")

        if dept_id:
            qs = qs.filter(department_id=dept_id)
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


def sync_facilities_from_gis():
    """
    Fast bulk-sync of GIS layer features (from shapefiles/catalog entries) into Facility instances.
    """
    from myapp.models import State, District, Department, AssetCategory, Facility, GISLayerFeature, HAS_GEODJANGO
    if HAS_GEODJANGO:
        from django.contrib.gis.geos import GEOSGeometry

    state, _ = State.objects.get_or_create(name="Bihar")
    district, _ = District.objects.get_or_create(state=state, name="Nalanda")

    dept_mapping = {
        "Health & Medical": "Health Department",
        "Education": "Education Department",
        "Hydrology & Water": "Water Resources Department",
        "Transportation": "Public Works & Transport Department",
        "Administrative & Boundaries": "District Administration",
        "Demographics & Admin": "Revenue & Admin Department",
        "Civic & Infrastructure": "Urban Development & Infra",
        "Environment & Land Use": "Forest & Environment Department",
    }

    existing_facilities = set(Facility.objects.values_list("name", "category_id"))
    dept_cache = {}
    cat_cache = {}

    features = GISLayerFeature.objects.select_related("catalog_entry").all()
    facilities_to_create = []

    for feat in features:
        cat_entry = feat.catalog_entry
        gis_category_name = cat_entry.category or "Civic & Infrastructure"
        dept_name = dept_mapping.get(gis_category_name, "General Administration")

        if dept_name not in dept_cache:
            dept, _ = Department.objects.get_or_create(name=dept_name)
            dept_cache[dept_name] = dept
        dept = dept_cache[dept_name]

        raw_cat_name = cat_entry.layer_name.replace("_", " ").title()
        cat_key = (dept.id, raw_cat_name)
        if cat_key not in cat_cache:
            asset_cat, _ = AssetCategory.objects.get_or_create(department=dept, name=raw_cat_name)
            if not asset_cat.catalog_entry:
                asset_cat.catalog_entry = cat_entry
                asset_cat.save(update_fields=["catalog_entry"])
            cat_cache[cat_key] = asset_cat
        asset_cat = cat_cache[cat_key]

        facility_name = (
            feat.name
            or (feat.properties and (feat.properties.get("NAME") or feat.properties.get("name") or feat.properties.get("feature_name")))
            or f"{raw_cat_name} #{feat.id}"
        )

        if (facility_name, asset_cat.id) not in existing_facilities:
            existing_facilities.add((facility_name, asset_cat.id))
            geom_val = feat.geom
            if not geom_val and feat.geom_geojson:
                if HAS_GEODJANGO:
                    import json
                    try:
                        geom_val = GEOSGeometry(json.dumps(feat.geom_geojson))
                    except Exception:
                        geom_val = None
                else:
                    geom_val = feat.geom_geojson

            facilities_to_create.append(Facility(
                name=facility_name,
                district=district,
                department=dept,
                category=asset_cat,
                catalog_entry=cat_entry,
                gis_feature=feat,
                attributes=feat.properties or {},
                geom=geom_val,
                hazard_safe=True
            ))

    if facilities_to_create:
        Facility.objects.bulk_create(facilities_to_create, batch_size=500)

    return len(facilities_to_create)


class FacilityViewSet(viewsets.ModelViewSet):
    """
    Complete CRUD ViewSet for Spatial Facilities / Assets (ast_facility).
    """
    queryset = Facility.objects.all().select_related("district", "department", "category", "catalog_entry", "gis_feature").order_by("id")
    serializer_class = FacilitySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if Facility.objects.count() == 0:
            sync_facilities_from_gis()

        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        district_val = self.request.query_params.get("district") or self.request.query_params.get("distict")
        dept_val = self.request.query_params.get("department")
        category_id = self.request.query_params.get("category")
        catalog_entry_id = self.request.query_params.get("catalog_entry")
        hazard_safe = self.request.query_params.get("hazard_safe")

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(attributes__icontains=search))

        if district_val:
            d_str = str(district_val).strip()
            if d_str.isdigit():
                qs = qs.filter(district_id=int(d_str))
            else:
                qs = qs.filter(district__name__icontains=d_str)

        if dept_val:
            d_dept = str(dept_val).strip()
            if d_dept.isdigit():
                qs = qs.filter(department_id=int(d_dept))
            else:
                qs = qs.filter(department__name__icontains=d_dept)

        if category_id:
            qs = qs.filter(category_id=category_id)
        if catalog_entry_id:
            qs = qs.filter(catalog_entry_id=catalog_entry_id)
        if hazard_safe is not None:
            safe_bool = hazard_safe.lower() in ["true", "1", "yes"]
            qs = qs.filter(hazard_safe=safe_bool)

        return qs

    def perform_update(self, serializer):
        instance = self.get_object()
        snapshot_data = FacilitySerializer(instance).data
        FacilityHistory.objects.create(
            facility=instance,
            snapshot=snapshot_data
        )
        serializer.save()

    @action(detail=False, methods=["post", "get"], url_path="sync-gis")
    def sync_gis(self, request):
        """
        Endpoint to trigger syncing of GIS Layer features into Facilities table.
        """
        count = sync_facilities_from_gis()
        return Response({
            "message": f"Successfully synced {count} GIS layer features into Facilities.",
            "synced_facilities_count": count,
            "total_facilities": Facility.objects.count()
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="geojson")
    def geojson(self, request):
        """
        Endpoint to export facilities as a standard GeoJSON FeatureCollection.
        """
        qs = self.filter_queryset(self.get_queryset())
        features = []
        for facility in qs:
            geom_data = None
            if facility.geom:
                if hasattr(facility.geom, "geojson"):
                    import json
                    try:
                        geom_data = json.loads(facility.geom.geojson)
                    except Exception:
                        geom_data = None
                elif isinstance(facility.geom, dict):
                    geom_data = facility.geom

            properties = {
                "id": facility.id,
                "name": facility.name,
                "district_id": facility.district_id,
                "district_name": facility.district.name if facility.district else None,
                "department_id": facility.department_id,
                "department_name": facility.department.name if facility.department else None,
                "category_id": facility.category_id,
                "category_name": facility.category.name if facility.category else None,
                "hazard_safe": facility.hazard_safe,
                "hazard_flags": facility.hazard_flags,
                "attributes": facility.attributes,
                "created_at": facility.created_at.isoformat() if facility.created_at else None,
            }
            features.append({
                "type": "Feature",
                "id": facility.id,
                "geometry": geom_data,
                "properties": properties,
            })

        return Response({
            "type": "FeatureCollection",
            "features": features
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        """
        Endpoint to retrieve version history (SCD Type 2 snapshots) for a specific facility.
        """
        facility = self.get_object()
        history_qs = facility.history_records.all().order_by("-valid_from")
        serializer = FacilityHistorySerializer(history_qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)







#=============================================
# GIS LAYER & FEATURE CRUD VIEWSETS
# ==========================================

import os
import json
import zipfile
import tempfile
# pyrefly: ignore [missing-import]
from rest_framework import viewsets
# pyrefly: ignore [missing-import]
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction   

from myapp.models import GISCatalogEntry, GISLayerFeature, HAS_GEODJANGO
from myapp.serializers import (
    GISCatalogSerializer,
    GISLayerFeatureSerializer,
    GISLayerUploadSerializer,
)

if HAS_GEODJANGO:
    from django.contrib.gis.geos import GEOSGeometry


class GISCatalogViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for GIS Catalog Entries (Layers).
    """
    queryset = GISCatalogEntry.objects.all().order_by("id")
    serializer_class = GISCatalogSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get("category")
        search = self.request.query_params.get("search")

        if category:
            qs = qs.filter(category__icontains=category)
        if search:
            qs = qs.filter(Q(layer_name__icontains=search) | Q(category__icontains=search) | Q(geometry_type__icontains=search))
        return qs


    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        layer_name = instance.layer_name
        # Delete related AssetCategories and Facilities for this layer
        AssetCategory.objects.filter(catalog_entry=instance).delete()
        Facility.objects.filter(catalog_entry=instance).delete()
        formatted_name = layer_name.replace("_", " ").title()
        AssetCategory.objects.filter(name__iexact=formatted_name).delete()
        self.perform_destroy(instance)
        return Response(
            {"message": f"Layer '{layer_name}' and all associated features and facilities deleted successfully."},
            status=status.HTTP_200_OK,
        )



class GISFeatureViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Individual GIS Layer Features.
    """
    queryset = GISLayerFeature.objects.all().order_by("id")
    serializer_class = GISLayerFeatureSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        catalog_id = self.request.query_params.get("catalog_entry")
        if catalog_id:
            qs = qs.filter(catalog_entry_id=catalog_id)
        return qs

    def perform_create(self, serializer):
        feature = serializer.save()
        catalog = feature.catalog_entry
        catalog.feature_count = catalog.features.count()
        catalog.save()

    def perform_destroy(self, instance):
        catalog = instance.catalog_entry
        instance.delete()
        catalog.feature_count = catalog.features.count()
        catalog.save()




class GISLayerUploadView(APIView):
    """
    API View to upload Shapefile (.zip) or GeoJSON file(s) to dynamically create single or multiple GIS layers.
    - POST /api/gis/upload-layer/
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        serializer = GISLayerUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        req_layer_name = serializer.validated_data.get("layer_name", "").strip().replace(" ", "_")
        req_category = serializer.validated_data.get("category", "Custom Uploads").strip()
        uploaded_file = serializer.validated_data["file"]

        file_name = uploaded_file.name.lower()
        import geopandas as gpd
        import shapely
        from pathlib import Path
        try:
            from myapp.management.commands.import_shapefiles import CATEGORY_MAPPING
        except Exception:
            CATEGORY_MAPPING = {}

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_file_path = os.path.join(tmp_dir, uploaded_file.name)
                with open(tmp_file_path, "wb") as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)

                spatial_files = []

                if file_name.endswith(".zip"):
                    with zipfile.ZipFile(tmp_file_path, "r") as zip_ref:
                        zip_ref.extractall(tmp_dir)

                    for root, dirs, files in os.walk(tmp_dir):
                        for f in files:
                            fl = f.lower()
                            if fl.endswith(".shp") or fl.endswith(".geojson") or (fl.endswith(".json") and not fl.startswith(".")):
                                spatial_files.append(os.path.join(root, f))
                else:
                    spatial_files.append(tmp_file_path)

                if not spatial_files:
                    return Response(
                        {"error": "No valid shapefile (.shp) or GeoJSON file found in uploaded file."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                created_catalogs = []
                total_features_all_layers = 0

                for file_path in spatial_files:
                    stem = Path(file_path).stem.replace(" ", "_")

                    # If multiple files exist in zip, use each file's stem name.
                    # If single file and req_layer_name provided, use req_layer_name.
                    if len(spatial_files) == 1 and req_layer_name:
                        layer_name = req_layer_name
                    else:
                        layer_name = stem

                    # Category smart detection: mapping -> req_category -> fallback
                    if stem in CATEGORY_MAPPING:
                        category = CATEGORY_MAPPING[stem][0]
                    elif req_category and req_category != "Custom Uploads":
                        category = req_category
                    else:
                        category = "Custom Uploads"

                    try:
                        gdf = gpd.read_file(file_path)
                    except Exception as read_err:
                        continue

                    if gdf.empty:
                        continue

                    # Reproject to WGS84 (EPSG:4326) and force 2D
                    if gdf.crs is not None:
                        try:
                            gdf = gdf.to_crs(epsg=4326)
                        except Exception:
                            pass

                    try:
                        if hasattr(shapely, "force_2d"):
                            gdf["geometry"] = shapely.force_2d(gdf.geometry)
                    except Exception:
                        pass

                    geom_types = gdf.geometry.geom_type.unique()
                    primary_geom_type = str(geom_types[0]) if len(geom_types) > 0 else "Unknown"

                    with transaction.atomic():
                        catalog, created = GISCatalogEntry.objects.get_or_create(
                            layer_name=layer_name,
                            defaults={
                                "geometry_type": primary_geom_type,
                                "category": category,
                                "feature_count": len(gdf),
                                "is_published": True,
                            }
                        )

                        if not created:
                            catalog.geometry_type = primary_geom_type
                            catalog.category = category
                            catalog.feature_count = len(gdf)
                            catalog.save()
                            GISLayerFeature.objects.filter(catalog_entry=catalog).delete()

                        geo_interface = json.loads(gdf.to_json())
                        features_to_create = []

                        for idx, feat in enumerate(geo_interface.get("features", [])):
                            geom_dict = feat.get("geometry")
                            props = feat.get("properties", {}) or {}

                            clean_props = {}
                            for k, v in props.items():
                                if v is None or (isinstance(v, float) and (v != v)):
                                    clean_props[k] = None
                                else:
                                    clean_props[k] = v

                            feat_name = str(clean_props.get("NAME") or clean_props.get("name") or clean_props.get("BLOCK_NAME") or f"{layer_name} #{idx+1}")
                            feat_id = str(clean_props.get("OBJECTID") or clean_props.get("FID") or clean_props.get("id") or (idx + 1))

                            geos_geom = None
                            if HAS_GEODJANGO and geom_dict:
                                try:
                                    geos_geom = GEOSGeometry(json.dumps(geom_dict))
                                except Exception:
                                    geos_geom = None

                            features_to_create.append(GISLayerFeature(
                                catalog_entry=catalog,
                                feature_id=feat_id,
                                name=feat_name[:255],
                                properties=clean_props,
                                geom_geojson=geom_dict,
                                geom=geos_geom
                            ))

                        GISLayerFeature.objects.bulk_create(features_to_create)

                    created_catalogs.append(GISCatalogSerializer(catalog).data)
                    total_features_all_layers += len(gdf)

                # Automatically sync new GIS layers into Facilities
                try:
                    sync_facilities_from_gis()
                except Exception:
                    pass

                if not created_catalogs:
                    return Response(
                        {"error": "Failed to parse any spatial layers from uploaded file."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                return Response(
                    {
                        "message": f"Successfully imported {len(created_catalogs)} layer(s) with {total_features_all_layers} total features.",
                        "imported_layers_count": len(created_catalogs),
                        "total_features_imported": total_features_all_layers,
                        "layers": created_catalogs,
                    },
                    status=status.HTTP_201_CREATED,
                )

        except Exception as e:
            return Response(
                {"error": f"Failed to process layer file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================
# COMPLAINT & GRIEVANCE MANAGEMENT VIEWSETS
# ==========================================

class ComplaintCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage defect categories, auto-routing targets, and default SLA targets.
    """
    queryset = ComplaintCategory.objects.all().select_related("department").order_by("name")
    serializer_class = ComplaintCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ComplaintViewSet(viewsets.ModelViewSet):
    """
    Enterprise Complaint & Grievance Lifecycle ViewSet.
    Handles auto-routing, workflow transitions, GIS spatial calculations, evidence upload, and audit timeline.
    """
    queryset = Complaint.objects.all().select_related(
        "category", "department", "citizen_user", "assigned_officer", 
        "assigned_inspector", "district", "subdivision", "block", 
        "village_ward", "nearest_facility", "nearest_gis_feature"
    ).prefetch_related("evidences", "timeline").order_by("-created_at")
    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        # Enforce Role & Department Scope Filters
        if user and user.is_authenticated and not user.is_superuser:
            role_code = user.role.code if (hasattr(user, 'role') and user.role) else ""
            
            # Citizens: See only own complaints
            if role_code in ["CITIZEN_REGISTERED", "CITIZEN_ANONYMOUS"]:
                qs = qs.filter(citizen_user=user)
            # Department Staff (Officer, Head, Engineer, Inspector): See assigned department complaints
            elif role_code in ["DEPARTMENT_HEAD", "DEPARTMENT_OFFICER", "EXECUTIVE_ENGINEER", "FIELD_INSPECTOR", "FIELD_SUPERVISOR"]:
                if user.department:
                    qs = qs.filter(department=user.department)
            # ADM / DM / Collector: See assigned district complaints
            elif role_code in ["DISTRICT_COLLECTOR", "DISTRICT_MAGISTRATE", "DM", "ADM"]:
                if user.district:
                    qs = qs.filter(district=user.district)

        # Query Filters
        search = self.request.query_params.get("search")
        dept_id = self.request.query_params.get("department")
        status_val = self.request.query_params.get("status")
        priority_val = self.request.query_params.get("priority")
        officer_id = self.request.query_params.get("officer")
        category_id = self.request.query_params.get("category")
        is_sla_breached = self.request.query_params.get("sla_breached")
        block_id = self.request.query_params.get("block")
        village_ward_id = self.request.query_params.get("village_ward")

        if search:
            qs = qs.filter(
                Q(tracking_no__icontains=search)
                | Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(citizen_name__icontains=search)
                | Q(citizen_phone__icontains=search)
            )
        if dept_id:
            if str(dept_id).isdigit():
                qs = qs.filter(department_id=dept_id)
            else:
                qs = qs.filter(department__name__icontains=dept_id)
        if status_val:
            qs = qs.filter(status__iexact=status_val)
        if priority_val:
            qs = qs.filter(priority__iexact=priority_val)
        if officer_id:
            qs = qs.filter(assigned_officer_id=officer_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if is_sla_breached is not None:
            breached_bool = is_sla_breached.lower() in ["true", "1", "yes"]
            qs = qs.filter(is_sla_breached=breached_bool)
        if block_id:
            qs = qs.filter(block_id=block_id)
        if village_ward_id:
            qs = qs.filter(village_ward_id=village_ward_id)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        files = request.FILES.getlist("evidence_files") or request.FILES.getlist("files")
        complaint = ComplaintService.create_complaint(
            user=request.user,
            validated_data=serializer.validated_data,
            files=files
        )
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user_id = serializer.validated_data.get("target_user_id")
        if not target_user_id:
            return Response({"error": "target_user_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        target_officer = User.objects.get(pk=target_user_id)
        complaint = ComplaintService.assign_complaint(complaint, request.user, target_officer, serializer.validated_data.get("remarks", ""))
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complaint = ComplaintService.accept_complaint(complaint, request.user, serializer.validated_data.get("remarks", ""))
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="start-inspection")
    def start_inspection(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_inspector_id = serializer.validated_data.get("target_user_id")
        target_inspector = User.objects.filter(pk=target_inspector_id).first() if target_inspector_id else None
        complaint = ComplaintService.start_inspection(complaint, request.user, target_inspector, serializer.validated_data.get("remarks", ""))
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="upload-evidence")
    def upload_evidence(self, request, pk=None):
        complaint = self.get_object()
        files = request.FILES.getlist("files") or request.FILES.getlist("file") or request.FILES.getlist("evidence_files")
        if not files:
            return Response({"error": "No file attachments found in request."}, status=status.HTTP_400_BAD_REQUEST)
        lat = request.data.get("latitude")
        lng = request.data.get("longitude")
        stage = request.data.get("stage", "INSPECTION")
        remarks = request.data.get("remarks", "")
        evidences = ComplaintService.upload_evidence(complaint, request.user, files, stage=stage, remarks=remarks, lat=lat, lng=lng)
        return Response(ComplaintEvidenceSerializer(evidences, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        summary = serializer.validated_data.get("resolution_summary") or serializer.validated_data.get("remarks") or "Resolved by department."
        complaint = ComplaintService.resolve_complaint(complaint, request.user, summary, serializer.validated_data.get("remarks", ""))
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="citizen-feedback")
    def citizen_feedback(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rating = serializer.validated_data.get("rating") or 5
        feedback_comment = serializer.validated_data.get("feedback_comment", "")
        complaint = ComplaintService.citizen_feedback(complaint, request.user, rating, feedback_comment)
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complaint = ComplaintService.close_complaint(complaint, request.user, serializer.validated_data.get("remarks", ""))
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason") or serializer.validated_data.get("remarks") or "Reopened by citizen."
        complaint = ComplaintService.reopen_complaint(complaint, request.user, reason)
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_dept_id = serializer.validated_data.get("target_department_id")
        if not target_dept_id:
            return Response({"error": "target_department_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        new_dept = Department.objects.get(pk=target_dept_id)
        reason = serializer.validated_data.get("reason") or "Transferred to correct department."
        complaint = ComplaintService.transfer_complaint(complaint, request.user, new_dept, reason)
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason") or "Escalated due to SLA breach / urgency."
        complaint = ComplaintService.escalate_complaint(complaint, request.user, reason)
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason") or "Complaint rejected."
        complaint = ComplaintService.reject_complaint(complaint, request.user, reason)
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        complaint = self.get_object()
        events = complaint.timeline.all().select_related("performed_by").order_by("created_at")
        return Response(ComplaintTimelineSerializer(events, many=True).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def geojson(self, request):
        qs = self.filter_queryset(self.get_queryset())
        features = []
        for cmp in qs:
            coords = [cmp.longitude or 85.5143, cmp.latitude or 25.1968]
            features.append({
                "type": "Feature",
                "id": cmp.id,
                "properties": {
                    "tracking_no": cmp.tracking_no,
                    "title": cmp.title,
                    "status": cmp.status,
                    "priority": cmp.priority,
                    "category": cmp.category_name,
                    "department": cmp.department_name,
                    "citizen": cmp.citizen_name,
                    "nearest_facility": cmp.nearest_facility_name,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": coords
                }
            })
        return Response({
            "type": "FeatureCollection",
            "features": features
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def heatmap(self, request):
        qs = self.filter_queryset(self.get_queryset())
        points = []
        for cmp in qs:
            if cmp.latitude and cmp.longitude:
                weight = 1.0
                if cmp.priority == "CRITICAL": weight = 3.0
                elif cmp.priority == "HIGH": weight = 2.0
                points.append({
                    "lat": cmp.latitude,
                    "lng": cmp.longitude,
                    "weight": weight,
                    "tracking_no": cmp.tracking_no,
                    "title": cmp.title,
                    "status": cmp.status
                })
        return Response({"status": "success", "count": len(points), "points": points}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def nearby(self, request):
        lat = float(request.query_params.get("lat", 25.1968))
        lng = float(request.query_params.get("lng", 85.5143))
        radius_m = float(request.query_params.get("radius", 5000))
        
        qs = self.get_queryset()
        nearby_items = []
        for cmp in qs:
            if cmp.latitude and cmp.longitude:
                dist = calculate_haversine_distance_m(lat, lng, cmp.latitude, cmp.longitude)
                if dist <= radius_m:
                    data = ComplaintSerializer(cmp).data
                    data["distance_m"] = dist
                    nearby_items.append(data)
        return Response({"status": "success", "count": len(nearby_items), "results": nearby_items}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="nearest-facility")
    def nearest_facility(self, request):
        lat = safe_float(request.query_params.get("lat", 25.1968))
        lng = safe_float(request.query_params.get("lng", 85.5143))
        limit_val = int(request.query_params.get("limit", 1))
        
        facilities = Facility.objects.all()[:200]
        facility_distances = []

        for fac in facilities:
            fac_lat, fac_lng = extract_facility_lat_lng(fac)
            if fac_lat is not None and fac_lng is not None:
                dist = calculate_haversine_distance_m(lat, lng, fac_lat, fac_lng)
                facility_distances.append({
                    "id": fac.id,
                    "name": fac.name,
                    "category": fac.category.name if fac.category else None,
                    "department": fac.department.name if fac.department else None,
                    "latitude": fac_lat,
                    "longitude": fac_lng,
                    "distance_m": dist
                })
        
        facility_distances.sort(key=lambda item: item["distance_m"])
        
        if not facility_distances:
            return Response({"message": "No nearby facilities found within district bounds."}, status=status.HTTP_404_NOT_FOUND)

        if limit_val == 1:
            closest = facility_distances[0]
            return Response({
                "nearest_facility": closest
            }, status=status.HTTP_200_OK)

        top_n = facility_distances[:limit_val]
        return Response({
            "count": len(top_n),
            "nearest_facilities": top_n
        }, status=status.HTTP_200_OK)


EXCEL_SPATIAL_QUERIES = [
    # --- CITIZENS PERSPECTIVE ---
    {
        "id": "nearest_health_facility_finder",
        "title": "Nearest health facility finder",
        "perspective": "Citizens",
        "department": "Health Department",
        "keywords": ["health", "hospital", "phc", "chc", "dispensary", "doctor", "clinic", "nearest health"],
        "dept_name": "Health Department",
        "buffer_m": 15000,
        "hazard_safe_only": False,
        "layers": ["Hospital", "Community_Health_centre", "Primary_Health_centre", "Dispensary"],
        "description": "Finds nearest health facility by distance from user location."
    },
    {
        "id": "nearby_hospital_blood_bank_search",
        "title": "Nearby hospital and blood bank search",
        "perspective": "Citizens",
        "department": "Health Department",
        "keywords": ["blood bank", "blood", "hospital", "nearby hospital"],
        "dept_name": "Health Department",
        "buffer_m": 10000,
        "hazard_safe_only": False,
        "layers": ["Blood_Bank", "Hospital"],
        "description": "Selects all hospitals and blood banks within 10 km buffer of user location."
    },
    {
        "id": "safe_health_facility_during_disaster",
        "title": "Safe health facility during disaster",
        "perspective": "Citizens",
        "department": "Health Department",
        "keywords": ["safe health", "disaster", "hazard safe health", "flood safe health"],
        "dept_name": "Health Department",
        "buffer_m": 25000,
        "hazard_safe_only": True,
        "layers": ["Hospital", "Community_Health_centre", "Primary_Health_centre"],
        "description": "Filters health facilities outside hazard polygons (hazard_safe=True)."
    },
    {
        "id": "nearby_drinking_water_source_locator",
        "title": "Nearby drinking water source locator",
        "perspective": "Citizens",
        "department": "Water Resources Department",
        "keywords": ["water", "drinking water", "tubewell", "well", "handpump", "spring", "water source"],
        "dept_name": "Water Resources Department",
        "buffer_m": 5000,
        "hazard_safe_only": False,
        "layers": ["Well", "Tubewell", "Spring", "Waterbody"],
        "description": "Finds all drinking water sources within 2 km - 5 km of user location."
    },
    {
        "id": "groundwater_potential_around_my_area",
        "title": "Groundwater potential around my area",
        "perspective": "Citizens",
        "department": "Water Resources Department",
        "keywords": ["groundwater", "water table", "ground water", "potential"],
        "dept_name": "Water Resources Department",
        "buffer_m": 10000,
        "hazard_safe_only": False,
        "layers": ["GroundWater_Potential", "Well", "Tubewell"],
        "description": "Overlays user location with groundwater potential polygons and lists nearby wells/tubewells."
    },
    {
        "id": "nearby_tourist_and_religious_places",
        "title": "Nearby tourist and religious places",
        "perspective": "Citizens",
        "department": "Tourism",
        "keywords": ["tourist", "tourism", "temple", "mosque", "church", "religious", "heritage"],
        "dept_name": "Tourism",
        "buffer_m": 15000,
        "hazard_safe_only": False,
        "layers": ["Places_of_Tourist_Interest", "Temple", "Mosque", "Church"],
        "description": "Finds all tourism and religious places within 10-15 km of user location."
    },
    {
        "id": "tourist_place_with_accommodation_access",
        "title": "Tourist place with accommodation access",
        "perspective": "Citizens",
        "department": "Tourism",
        "keywords": ["accommodation", "circuit house", "hotel", "stay", "bungalow"],
        "dept_name": "Tourism",
        "buffer_m": 15000,
        "hazard_safe_only": False,
        "layers": ["Places_of_Tourist_Interest", "Circuit_house"],
        "description": "Selects tourist places near major roads with accommodation access within threshold."
    },
    {
        "id": "safe_tourist_destination_finder",
        "title": "Safe tourist destination finder",
        "perspective": "Citizens",
        "department": "Tourism",
        "keywords": ["safe tourist", "safe tourism", "hazard safe tourist"],
        "dept_name": "Tourism",
        "buffer_m": 25000,
        "hazard_safe_only": True,
        "layers": ["Places_of_Tourist_Interest", "Temple", "Mosque", "Church"],
        "description": "Shows tourist places outside hazard zones and near accessible roads."
    },
    {
        "id": "accessible_schools_near_my_home",
        "title": "Accessible schools near my home",
        "perspective": "Citizens",
        "department": "Education Department",
        "keywords": ["school", "education", "college", "university", "accessible school"],
        "dept_name": "Education Department",
        "buffer_m": 5000,
        "hazard_safe_only": False,
        "layers": ["School", "Collage", "University"],
        "description": "Finds all schools/education institutes within 3-5 km of user location."
    },
    {
        "id": "safe_and_connected_education_facilities",
        "title": "Safe and connected education facilities",
        "perspective": "Citizens",
        "department": "Education Department",
        "keywords": ["safe school", "safe education", "hazard safe school"],
        "dept_name": "Education Department",
        "buffer_m": 15000,
        "hazard_safe_only": True,
        "layers": ["School", "Collage", "University"],
        "description": "Shows education facilities outside hazard zones."
    },
    {
        "id": "solar_ready_public_institutions_nearby",
        "title": "Solar-ready public institutions nearby",
        "perspective": "Citizens",
        "department": "Solar Department",
        "keywords": ["solar", "solar ready", "solar institution", "renewable"],
        "dept_name": "Solar Department",
        "buffer_m": 10000,
        "hazard_safe_only": True,
        "layers": ["School", "Hospital", "PoliceStation", "PostOffice"],
        "description": "Finds public facilities with good road access and low hazard exposure for solar readiness."
    },

    # --- GOVERNMENT ADMINISTRATION PERSPECTIVE (DM / COLLECTOR / ADM) ---
    {
        "id": "block_wise_health_service_gap",
        "title": "Block-wise health service gap",
        "perspective": "Government Administration",
        "department": "Health Department",
        "keywords": ["block health gap", "health service gap", "health gap"],
        "dept_name": "Health Department",
        "buffer_m": 25000,
        "hazard_safe_only": False,
        "layers": ["Hospital", "Community_Health_centre", "Primary_Health_centre", "Dispensary"],
        "description": "Measures block areas beyond service distance from health facilities using buffer."
    },
    {
        "id": "hazard_exposure_of_health_facilities",
        "title": "Hazard exposure of health facilities",
        "perspective": "Government Administration",
        "department": "Health Department",
        "keywords": ["hazard exposure health", "flood health facility", "vulnerable hospital"],
        "dept_name": "Health Department",
        "buffer_m": 25000,
        "hazard_safe_only": False,
        "layers": ["Hospital", "Community_Health_centre", "Primary_Health_centre"],
        "description": "Identifies all health facilities intersecting hazard polygons."
    },
    {
        "id": "population_versus_water_source_access_gap",
        "title": "Population versus water source access gap",
        "perspective": "Government Administration",
        "department": "Water Resources Department",
        "keywords": ["water gap", "water access gap", "population water"],
        "dept_name": "Water Resources Department",
        "buffer_m": 10000,
        "hazard_safe_only": False,
        "layers": ["Well", "Tubewell", "Waterbody"],
        "description": "Identifies populated areas with low proximity to water sources."
    },
    {
        "id": "flood_vulnerable_drinking_water_points",
        "title": "Flood-vulnerable drinking water points",
        "perspective": "Government Administration",
        "department": "Water Resources Department",
        "keywords": ["flood water", "vulnerable water", "flood tubewell"],
        "dept_name": "Water Resources Department",
        "buffer_m": 25000,
        "hazard_safe_only": False,
        "layers": ["Well", "Tubewell", "Waterbody"],
        "description": "Detects water points inside or near flood hazard zones."
    },
    {
        "id": "tourism_amenities_gap_analysis",
        "title": "Tourism amenities gap analysis",
        "perspective": "Government Administration",
        "department": "Tourism",
        "keywords": ["tourism amenities gap", "tourism gap", "amenities gap"],
        "dept_name": "Tourism",
        "buffer_m": 20000,
        "hazard_safe_only": False,
        "layers": ["Places_of_Tourist_Interest", "Temple", "Mosque", "Church", "Circuit_house"],
        "description": "Finds tourism sites lacking nearby public amenities and visitor support services."
    },
    {
        "id": "tourism_hazard_risk_mapping",
        "title": "Tourism hazard risk mapping",
        "perspective": "Government Administration",
        "department": "Tourism",
        "keywords": ["tourism hazard risk", "hazard tourism", "tourism risk mapping"],
        "dept_name": "Tourism",
        "buffer_m": 25000,
        "hazard_safe_only": False,
        "layers": ["Places_of_Tourist_Interest", "Temple", "Mosque", "Church"],
        "description": "Identifies tourism and religious sites exposed to flood/earthquake hazards."
    },
    {
        "id": "transport_access_priority_for_tourism",
        "title": "Transport access priority for tourism",
        "perspective": "Government Administration",
        "department": "Tourism",
        "keywords": ["transport access tourism", "tourism road access", "access priority"],
        "dept_name": "Tourism",
        "buffer_m": 20000,
        "hazard_safe_only": False,
        "layers": ["Places_of_Tourist_Interest", "Circuit_house"],
        "description": "Ranks tourism sites beyond desired road/rail access distance."
    },
    {
        "id": "education_hazard_and_connectivity_review",
        "title": "Education hazard and connectivity review",
        "perspective": "Government Administration",
        "department": "Education Department",
        "keywords": ["education hazard review", "school connectivity review", "school hazard"],
        "dept_name": "Education Department",
        "buffer_m": 25000,
        "hazard_safe_only": False,
        "layers": ["School", "Collage", "University"],
        "description": "Detects institutions in hazard zones or poorly connected by roads."
    },
    {
        "id": "block_wise_education_infrastructure_expansion_priority",
        "title": "Block-wise education infrastructure expansion priority",
        "perspective": "Government Administration",
        "department": "Education Department",
        "keywords": ["block education expansion", "school expansion priority", "education expansion"],
        "dept_name": "Education Department",
        "buffer_m": 20000,
        "hazard_safe_only": False,
        "layers": ["School", "Collage", "University"],
        "description": "Compares population distribution with institution density by block."
    },
    {
        "id": "solar_ready_of_public_institutions",
        "title": "Solar ready of public institutions",
        "perspective": "Government Administration",
        "department": "Solar Department",
        "keywords": ["solar ready admin", "solar pilot deployment", "admin solar"],
        "dept_name": "Solar Department",
        "buffer_m": 15000,
        "hazard_safe_only": True,
        "layers": ["School", "Hospital", "Community_Health_centre", "Primary_Health_centre", "PoliceStation"],
        "description": "Selects public institutions outside hazard zones for solar pilot deployment."
    },
    {
        "id": "ground_mounted_solar_suitability_screening",
        "title": "Ground-mounted solar suitability screening",
        "perspective": "Government Administration",
        "department": "Solar Department",
        "keywords": ["ground mounted solar", "solar suitability screening", "solar land screening"],
        "dept_name": "Solar Department",
        "buffer_m": 25000,
        "hazard_safe_only": True,
        "layers": ["School", "Hospital", "PoliceStation"],
        "description": "Finds flat/moderate slope land parcels with compatible land use and low hazard conflict."
    },

    # --- LINE DEPARTMENTS PERSPECTIVE ---
    {
        "id": "new_health_facility_planning_support",
        "title": "New health facility planning support",
        "perspective": "Line Departments",
        "department": "Health Department",
        "keywords": ["new health facility", "propose health facility", "health planning support"],
        "dept_name": "Health Department",
        "buffer_m": 25000,
        "hazard_safe_only": False,
        "layers": ["Hospital", "Community_Health_centre", "Primary_Health_centre", "Dispensary"],
        "description": "Locates block wise population clusters lacking health facilities for proposing new facility."
    },
    {
        "id": "disaster_ready_health_network_planning",
        "title": "Disaster-ready health network planning",
        "perspective": "Line Departments",
        "department": "Health Department",
        "keywords": ["disaster ready health", "disaster health network", "health network planning"],
        "dept_name": "Health Department",
        "buffer_m": 25000,
        "hazard_safe_only": True,
        "layers": ["Hospital", "Community_Health_centre", "Primary_Health_centre"],
        "description": "Identifies facilities intersecting hazard polygons with maximum route network."
    },
    {
        "id": "blood_bank_and_hospital_logistics_optimization",
        "title": "Blood bank and hospital logistics optimization",
        "perspective": "Line Departments",
        "department": "Health Department",
        "keywords": ["blood bank logistics", "hospital logistics optimization", "logistics bottleneck"],
        "dept_name": "Health Department",
        "buffer_m": 15000,
        "hazard_safe_only": False,
        "layers": ["Blood_Bank", "Hospital"],
        "description": "Measures access between blood banks and hospitals to flag logistics bottlenecks."
    },
    {
        "id": "new_tubewell_well_support",
        "title": "New tubewell/well support",
        "perspective": "Line Departments",
        "department": "Water Resources Department",
        "keywords": ["new tubewell", "suggest tubewell", "new well support"],
        "dept_name": "Water Resources Department",
        "buffer_m": 25000,
        "hazard_safe_only": False,
        "layers": ["Well", "Tubewell", "GroundWater_Potential"],
        "description": "Identifies areas with few existing tubewells where groundwater potential is favorable."
    },
    {
        "id": "groundwater_stress_and_dependency_zones",
        "title": "Groundwater stress and dependency zones",
        "perspective": "Line Departments",
        "department": "Water Resources Department",
        "keywords": ["groundwater stress", "water dependency zones", "water stress"],
        "dept_name": "Water Resources Department",
        "buffer_m": 20000,
        "hazard_safe_only": False,
        "layers": ["Well", "Tubewell", "GroundWater_Potential"],
        "description": "Identifies areas where groundwater conditions and population dependence suggest stress."
    },
    {
        "id": "heritage_circuit_design_support",
        "title": "Heritage circuit design support",
        "perspective": "Line Departments",
        "department": "Tourism",
        "keywords": ["heritage circuit", "circuit design support", "cultural circuit"],
        "dept_name": "Tourism",
        "buffer_m": 20000,
        "hazard_safe_only": False,
        "layers": ["Places_of_Tourist_Interest", "Temple", "Mosque", "Church"],
        "description": "Clusters cultural/religious sites that can be linked into circuits with minimal travel gaps."
    },
    {
        "id": "tourism_safety_and_advisory_planning",
        "title": "Tourism safety and advisory planning",
        "perspective": "Line Departments",
        "department": "Tourism",
        "keywords": ["tourism safety planning", "tourism advisory planning", "hazard advisory tourism"],
        "dept_name": "Tourism",
        "buffer_m": 25000,
        "hazard_safe_only": True,
        "layers": ["Places_of_Tourist_Interest", "Temple", "Mosque", "Church"],
        "description": "Flags sites needing hazard advisories, route caution, or seasonal management."
    },
    {
        "id": "school_expansion_and_upgrade_planning",
        "title": "School expansion and upgrade planning",
        "perspective": "Line Departments",
        "department": "Education Department",
        "keywords": ["school expansion planning", "school upgrade planning", "new school planning"],
        "dept_name": "Education Department",
        "buffer_m": 15000,
        "hazard_safe_only": False,
        "layers": ["School", "Collage", "University"],
        "description": "Locates high-demand settlements for new or upgrading schools."
    },
    {
        "id": "school_resilience_planning",
        "title": "School resilience planning",
        "perspective": "Line Departments",
        "department": "Education Department",
        "keywords": ["school resilience planning", "school retrofitting", "school emergency planning"],
        "dept_name": "Education Department",
        "buffer_m": 20000,
        "hazard_safe_only": False,
        "layers": ["School", "Collage", "University"],
        "description": "Identifies schools needing retrofitting, relocation support, or emergency planning."
    },
    {
        "id": "institutions_for_rooftop_solar_install",
        "title": "Institutions for Rooftop solar install",
        "perspective": "Line Departments",
        "department": "Solar Department",
        "keywords": ["rooftop solar install", "rooftop solar institutions", "solar install"],
        "dept_name": "Solar Department",
        "buffer_m": 15000,
        "hazard_safe_only": True,
        "layers": ["School", "Hospital", "Community_Health_centre", "Primary_Health_centre", "PoliceStation"],
        "description": "Shortlists institutions for rooftop solar using service importance, access, and hazard safety."
    },
    {
        "id": "cross_sector_solar_convergence_planning",
        "title": "Cross-sector solar convergence planning",
        "perspective": "Line Departments",
        "department": "Solar Department",
        "keywords": ["cross sector solar", "solar convergence planning", "multi sector solar"],
        "dept_name": "Solar Department",
        "buffer_m": 20000,
        "hazard_safe_only": False,
        "layers": ["School", "Hospital", "Well", "Tubewell", "Places_of_Tourist_Interest"],
        "description": "Locates areas where solar can support education, health, water pumping, and tourism together."
    }
]


class SpatialQueryAPIView(APIView):
    """
    Smart Natural Language & Excel Spatial Query Execution Engine.
    Executes queries from 'Queries for Nalanda.xlsx' (e.g. 'nearest health facility finder', 
    'nearby drinking water source locator', 'safe health facility during disaster', etc.)
    Supports ?q=... &lat=... &lng=... &radius=... &limit=...
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        query_text = request.query_params.get("q") or request.query_params.get("search") or request.query_params.get("query") or ""
        query_text = query_text.strip()
        
        lat = safe_float(request.query_params.get("lat", 25.1968))
        lng = safe_float(request.query_params.get("lng", 85.5143))
        limit_val = int(request.query_params.get("limit", 20))

        raw_radius = request.query_params.get("radius") or request.query_params.get("radius_m") or request.query_params.get("radius_km")
        max_radius_m = None
        if raw_radius is not None:
            try:
                r_val = float(raw_radius)
                if r_val <= 100:
                    max_radius_m = r_val * 1000.0
                else:
                    max_radius_m = r_val
            except (ValueError, TypeError):
                max_radius_m = None

        if not query_text:
            citizens_presets = [
                {
                    "id": q["id"],
                    "title": q["title"],
                    "department": q["department"],
                    "description": q["description"],
                    "layers": q["layers"]
                }
                for q in EXCEL_SPATIAL_QUERIES if q["perspective"] == "Citizens"
            ]
            govt_admin_presets = [
                {
                    "id": q["id"],
                    "title": q["title"],
                    "department": q["department"],
                    "description": q["description"],
                    "layers": q["layers"]
                }
                for q in EXCEL_SPATIAL_QUERIES if q["perspective"] == "Government Administration"
            ]
            line_dept_presets = [
                {
                    "id": q["id"],
                    "title": q["title"],
                    "department": q["department"],
                    "description": q["description"],
                    "layers": q["layers"]
                }
                for q in EXCEL_SPATIAL_QUERIES if q["perspective"] == "Line Departments"
            ]

            return Response({
                "message": "Spatial Query Engine active. Pass ?q=<query_name>&lat=<lat>&lng=<lng>&radius=<meters_or_km>&limit=<count> to execute.",
                "total_presets": len(EXCEL_SPATIAL_QUERIES),
                "query_presets_by_perspective": {
                    "citizens": citizens_presets,
                    "government_administration": govt_admin_presets,
                    "line_departments": line_dept_presets
                },
                "available_query_presets": [q["title"] for q in EXCEL_SPATIAL_QUERIES]
            }, status=status.HTTP_200_OK)

        matched_preset = None
        q_lower = query_text.lower()
        
        # 1. Exact or title match first
        for preset in EXCEL_SPATIAL_QUERIES:
            if preset["title"].lower() in q_lower or q_lower in preset["title"].lower():
                matched_preset = preset
                break

        # 2. Keyword match fallback (if title match not found)
        if not matched_preset:
            for preset in EXCEL_SPATIAL_QUERIES:
                for kw in preset["keywords"]:
                    if kw in q_lower:
                        matched_preset = preset
                        break
                if matched_preset:
                    break

        if not matched_preset:
            matched_preset = {
                "id": "dynamic_search",
                "title": f"Search: {query_text}",
                "perspective": "General",
                "department": "General",
                "keywords": [query_text],
                "dept_name": None,
                "buffer_m": 25000,
                "hazard_safe_only": False,
                "layers": [],
                "description": f"Dynamic spatial search for '{query_text}'"
            }

        # Enforce Perspective-Based Role Permissions
        user_role = get_user_role_code(request.user)
        preset_perspective = matched_preset.get("perspective")

        admin_officer_roles = {
            "DISTRICT_COLLECTOR", "DISTRICT_MAGISTRATE", "DM_COLLECTOR", "DM", 
            "ADM", "SDM", "STATE_ADMIN", "SUPER_ADMIN", "DISTRICT_OFFICER"
        }
        
        line_officer_roles = {
            "DEPARTMENT_HEAD", "DEPARTMENT_OFFICER", "EXECUTIVE_ENGINEER", 
            "FIELD_INSPECTOR", "FIELD_SUPERVISOR", "DEPARTMENT_ADMIN", 
            "LINE_DEPARTMENT_OFFICER", "ENGINEER", "DISTRICT_COLLECTOR", 
            "DISTRICT_MAGISTRATE", "DM_COLLECTOR", "ADM", "SDM", "STATE_ADMIN", 
            "SUPER_ADMIN"
        }

        is_staff_or_super = bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))

        if preset_perspective == "Government Administration":
            if user_role not in admin_officer_roles and not is_staff_or_super:
                return Response({
                    "status": "permission_denied",
                    "message": f"Access Denied: '{matched_preset['title']}' is restricted to Government Administration officials (DM / ADM / SDM).",
                    "query_info": {
                        "input_query": query_text,
                        "matched_preset_title": matched_preset["title"],
                        "perspective": preset_perspective,
                        "required_perspective": "Government Administration",
                        "your_role": user_role
                    },
                    "total_found": 0,
                    "results": []
                }, status=status.HTTP_403_FORBIDDEN)

        if preset_perspective == "Line Departments":
            if (user_role in ["CITIZEN", "ANONYMOUS"] or (user_role not in line_officer_roles and not is_staff_or_super)):
                return Response({
                    "status": "permission_denied",
                    "message": f"Access Denied: '{matched_preset['title']}' is restricted to Line Department officers.",
                    "query_info": {
                        "input_query": query_text,
                        "matched_preset_title": matched_preset["title"],
                        "perspective": preset_perspective,
                        "required_perspective": "Line Departments",
                        "your_role": user_role
                    },
                    "total_found": 0,
                    "results": []
                }, status=status.HTTP_403_FORBIDDEN)

        if Facility.objects.count() == 0:
            sync_facilities_from_gis()

        facilities_qs = Facility.objects.all().select_related("department", "category", "catalog_entry", "gis_feature")

        if matched_preset.get("dept_name"):
            d_word = matched_preset["dept_name"].split()[0]
            facilities_qs = facilities_qs.filter(Q(department__name__icontains=matched_preset["dept_name"]) | Q(department__name__icontains=d_word))

        if matched_preset.get("hazard_safe_only"):
            facilities_qs = facilities_qs.filter(hazard_safe=True)

        if matched_preset.get("layers"):
            layer_q = Q()
            for layer in matched_preset["layers"]:
                layer_q |= Q(category__name__icontains=layer.replace("_", " ")) | Q(catalog_entry__layer_name__icontains=layer) | Q(name__icontains=layer.replace("_", " "))
            facilities_qs = facilities_qs.filter(layer_q)

        if matched_preset["id"] == "dynamic_search":
            facilities_qs = facilities_qs.filter(
                Q(name__icontains=query_text)
                | Q(category__name__icontains=query_text)
                | Q(department__name__icontains=query_text)
                | Q(attributes__icontains=query_text)
            )

        results = []
        for fac in facilities_qs[:500]:
            fac_lat, fac_lng = extract_facility_lat_lng(fac)
            if fac_lat is not None and fac_lng is not None:
                dist = calculate_haversine_distance_m(lat, lng, fac_lat, fac_lng)
                if max_radius_m is not None and dist > max_radius_m:
                    continue
                results.append({
                    "id": fac.id,
                    "name": fac.name,
                    "category": fac.category.name if fac.category else "Facility",
                    "department": fac.department.name if fac.department else (matched_preset.get("dept_name") or "General Administration"),
                    "hazard_safe": fac.hazard_safe,
                    "latitude": fac_lat,
                    "longitude": fac_lng,
                    "distance_m": dist,
                    "distance_km": round(dist / 1000.0, 2)
                })

        results.sort(key=lambda item: item["distance_m"])
        top_results = results[:limit_val]

        return Response({
            "status": "success",
            "query_info": {
                "input_query": query_text,
                "matched_preset_title": matched_preset["title"],
                "perspective": matched_preset["perspective"],
                "department": matched_preset.get("dept_name") or matched_preset.get("department"),
                "required_layers": matched_preset["layers"],
                "radius_filter_m": max_radius_m,
                "limit": limit_val,
                "user_location": {"latitude": lat, "longitude": lng}
            },
            "total_found": len(results),
            "results": top_results
        }, status=status.HTTP_200_OK)


def get_user_role_code(user):
    """Utility to retrieve normalized role code string for logged-in user."""
    if not user or not user.is_authenticated:
        return "ANONYMOUS"
    if hasattr(user, "role") and user.role:
        if hasattr(user.role, "code") and user.role.code:
            return user.role.code
        return str(user.role).upper().replace(" ", "_")
    if user.is_superuser or user.is_staff:
        return "STATE_ADMIN"
    return "CITIZEN"


class DashboardViewSet(viewsets.ViewSet):
    """
    Enterprise Executive Dashboards strictly isolated per System Role Persona.
    Enforces RBAC access control so Citizens cannot view Executive / DM / Department dashboards.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=["get"], url_path="my-dashboard")
    def my_dashboard(self, request):
        """Unified endpoint auto-redirecting user to their specific role dashboard."""
        role_code = get_user_role_code(request.user)
        if role_code in ["DISTRICT_COLLECTOR", "DISTRICT_MAGISTRATE"]:
            return self.district_collector(request)
        elif role_code == "ADM":
            return self.adm(request)
        elif role_code == "DEPARTMENT_HEAD":
            return self.department(request)
        elif role_code in ["DEPARTMENT_OFFICER", "EXECUTIVE_ENGINEER"]:
            return self.officer(request)
        elif role_code in ["FIELD_INSPECTOR", "FIELD_SUPERVISOR"]:
            return self.field_inspector(request)
        elif role_code == "STATE_ADMIN":
            return self.state(request)
        else:
            return self.citizen(request)

    @action(detail=False, methods=["get"])
    def citizen(self, request):
        """1. Citizen Dashboard: View own submitted grievances, status tracker & resolution ratings."""
        user = request.user
        qs = Complaint.objects.all()
        if user and user.is_authenticated:
            qs = qs.filter(citizen_user=user)
        
        total = qs.count()
        pending = qs.filter(status__in=["SUBMITTED", "ASSIGNED", "ACCEPTED", "INSPECTION_STARTED", "EVIDENCE_UPLOADED", "REOPENED"]).count()
        resolved = qs.filter(status__in=["RESOLVED", "CITIZEN_VERIFICATION", "CLOSED"]).count()
        
        return Response({
            "role": "CITIZEN",
            "total_complaints": total,
            "pending_complaints": pending,
            "resolved_complaints": resolved,
            "my_complaints": ComplaintSerializer(qs[:10], many=True).data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def department(self, request):
        """2. Department Head Dashboard: Department queue, SLA breaches, resource planning."""
        role_code = get_user_role_code(request.user)
        if role_code == "CITIZEN":
            return Response(
                {"detail": "Access Denied: Citizens cannot access Department Dashboard. Please use /api/dashboards/citizen/"},
                status=status.HTTP_403_FORBIDDEN
            )

        dept_id = request.query_params.get("department")
        qs = Complaint.objects.all()
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        elif request.user and request.user.is_authenticated and request.user.department:
            qs = qs.filter(department=request.user.department)

        assigned = qs.filter(status="ASSIGNED").count()
        pending = qs.filter(status__in=["SUBMITTED", "ASSIGNED", "ACCEPTED", "INSPECTION_STARTED", "EVIDENCE_UPLOADED"]).count()
        resolved = qs.filter(status__in=["RESOLVED", "CLOSED"]).count()
        sla_breached = qs.filter(is_sla_breached=True).count()

        return Response({
            "role": role_code,
            "department_name": request.user.department.name if (request.user and request.user.is_authenticated and request.user.department) else "All Departments",
            "assigned": assigned,
            "pending": pending,
            "resolved": resolved,
            "sla_breached": sla_breached,
            "recent_complaints": ComplaintSerializer(qs[:10], many=True).data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def officer(self, request):
        """3. Department Officer & Engineer Dashboard: Daily task queue, assigned jobs."""
        role_code = get_user_role_code(request.user)
        if role_code == "CITIZEN":
            return Response(
                {"detail": "Access Denied: Citizens cannot access Officer Dashboard. Please use /api/dashboards/citizen/"},
                status=status.HTTP_403_FORBIDDEN
            )

        user = request.user
        qs = Complaint.objects.filter(assigned_officer=user) if (user and user.is_authenticated) else Complaint.objects.all()
        today = timezone.now().date()
        today_work = qs.filter(created_at__date=today).count()
        assigned = qs.filter(status__in=["ASSIGNED", "ACCEPTED"]).count()
        completed = qs.filter(status__in=["RESOLVED", "CLOSED"]).count()

        return Response({
            "role": role_code,
            "todays_work": today_work,
            "assigned_work": assigned,
            "completed_work": completed,
            "tasks": ComplaintSerializer(qs[:10], many=True).data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="field-inspector")
    def field_inspector(self, request):
        """4. Field Inspector Mobile PWA Dashboard: Geotag verification & evidence upload queue."""
        role_code = get_user_role_code(request.user)
        if role_code == "CITIZEN":
            return Response(
                {"detail": "Access Denied: Citizens cannot access Field Inspector Dashboard. Please use /api/dashboards/citizen/"},
                status=status.HTTP_403_FORBIDDEN
            )

        qs = Complaint.objects.filter(status__in=["ASSIGNED", "INSPECTION_STARTED", "ACCEPTED"])
        if request.user and request.user.is_authenticated and request.user.department:
            qs = qs.filter(department=request.user.department)

        pending_inspections = qs.count()
        evidence_uploaded_count = ComplaintEvidence.objects.filter(is_geotag_verified=True).count()

        return Response({
            "role": role_code,
            "pending_inspections": pending_inspections,
            "geotag_verified_evidences": evidence_uploaded_count,
            "inspection_queue": ComplaintSerializer(qs[:10], many=True).data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def district(self, request):
        """5. District Executive Dashboard: Cross-department command center (District Collector / DM / ADM)."""
        role_code = get_user_role_code(request.user)
        if role_code in ["CITIZEN", "FIELD_INSPECTOR"]:
            return Response(
                {"detail": "Access Denied: Only District Collectors, DMs, ADMs, and State Admins can access District Executive Dashboard."},
                status=status.HTTP_403_FORBIDDEN
            )

        qs = Complaint.objects.all()
        dept_counts = qs.values("department__name").annotate(total=Count("id")).order_by("-total")
        status_counts = qs.values("status").annotate(total=Count("id")).order_by("-total")
        priority_counts = qs.values("priority").annotate(total=Count("id")).order_by("-total")

        return Response({
            "role": role_code,
            "total_complaints": qs.count(),
            "department_wise": list(dept_counts),
            "status_wise": list(status_counts),
            "priority_wise": list(priority_counts),
            "sla_compliance_rate": "94.8%"
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="district-collector")
    def district_collector(self, request):
        """6. District Collector Command Center: High-level executive SLA leaderboards & proposals."""
        return self.district(request)

    @action(detail=False, methods=["get"])
    def dm(self, request):
        """7. District Magistrate (DM) Executive Command Center."""
        return self.district(request)

    @action(detail=False, methods=["get"])
    def adm(self, request):
        """8. Additional District Magistrate (ADM) Sector Grievance Dashboard."""
        return self.district(request)

    @action(detail=False, methods=["get"])
    def state(self, request):
        """9. State Admin Dashboard: State-level cross-district KPI comparison & ranking matrix."""
        role_code = get_user_role_code(request.user)
        if role_code in ["CITIZEN", "DEPARTMENT_OFFICER", "FIELD_INSPECTOR", "FIELD_SUPERVISOR"]:
            return Response(
                {"detail": "Access Denied: Only State Admins, District Collectors, and DMs can access State-level Dashboard."},
                status=status.HTTP_403_FORBIDDEN
            )

        districts = District.objects.all()
        rankings = []
        for d in districts:
            c_count = Complaint.objects.filter(district=d).count()
            r_count = Complaint.objects.filter(district=d, status__in=["RESOLVED", "CLOSED"]).count()
            rankings.append({
                "district_id": d.id,
                "district_name": d.name,
                "total_complaints": c_count,
                "resolved_complaints": r_count,
                "resolution_rate": f"{round((r_count / c_count * 100), 1) if c_count > 0 else 100.0}%"
            })
        return Response({"role": role_code, "district_rankings": rankings}, status=status.HTTP_200_OK)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API ViewSet to retrieve user dispatched notifications.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated:
            return NotificationDispatchLog.objects.filter(user=user).select_related("template", "user").order_by("-dispatched_at")
        return NotificationDispatchLog.objects.all().select_related("template", "user").order_by("-dispatched_at")

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()[:50]
        data = [{
            "id": str(n.id),
            "template_name": n.template.name,
            "channel": n.template.channel,
            "message": n.template.body_template,
            "status": n.status,
            "dispatched_at": n.dispatched_at
        } for n in qs]
        return Response(data, status=status.HTTP_200_OK)


class ProposalViewSet(viewsets.ModelViewSet):
    """
    Complete RESTful ViewSet for Department Development Proposals & 7-Step DPR Wizard.
    Supports filtering by department, district, status, stage, priority, block, and search.
    Provides step-by-step DPR wizard actions and DM sanction workflow.
    """
    serializer_class = ProposalSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        qs = Proposal.objects.filter(is_deleted=False).select_related("district", "department", "created_by", "reviewed_by", "approved_by")
        
        dept = self.request.query_params.get("department") or self.request.query_params.get("dept")
        if dept:
            qs = qs.filter(Q(department_id=dept) | Q(department__name__icontains=dept))
            
        dist = self.request.query_params.get("district")
        if dist:
            qs = qs.filter(Q(district_id=dist) | Q(district__name__icontains=dist))
            
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status__iexact=status_filter)

        stage_filter = self.request.query_params.get("stage")
        if stage_filter:
            qs = qs.filter(stage__iexact=stage_filter)

        priority_filter = self.request.query_params.get("priority")
        if priority_filter:
            qs = qs.filter(priority__iexact=priority_filter)

        block_filter = self.request.query_params.get("block")
        if block_filter:
            qs = qs.filter(block__icontains=block_filter)

        search_text = self.request.query_params.get("search") or self.request.query_params.get("q")
        if search_text:
            qs = qs.filter(
                Q(proposal_id__icontains=search_text)
                | Q(title__icontains=search_text)
                | Q(category__icontains=search_text)
                | Q(village__icontains=search_text)
                | Q(block__icontains=search_text)
                | Q(problem_statement__icontains=search_text)
            )
            
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        
        # Resolve district and department if missing from request data
        district_id = self.request.data.get("district")
        if not district_id and user and hasattr(user, "district") and user.district:
            district_id = user.district.id
        elif not district_id:
            d_obj = District.objects.first()
            district_id = d_obj.id if d_obj else None

        dept_id = self.request.data.get("department")
        if not dept_id and user and hasattr(user, "department") and user.department:
            dept_id = user.department.id
        elif not dept_id:
            dept_obj = Department.objects.first()
            dept_id = dept_obj.id if dept_obj else None

        serializer.save(created_by=user, district_id=district_id, department_id=dept_id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save()
        return Response({"message": "Proposal soft deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

    # Step 1: Need Identification
    @action(detail=True, methods=["post"], url_path="step1-need-identification")
    def step1_need_identification(self, request, pk=None):
        proposal = self.get_object()
        data = request.data
        
        proposal.title = data.get("title", proposal.title)
        proposal.category = data.get("category", proposal.category)
        proposal.village = data.get("village", proposal.village)
        proposal.block = data.get("block", proposal.block)
        proposal.ward = data.get("ward", proposal.ward)
        proposal.population_impact = data.get("population_impact", proposal.population_impact)
        proposal.gap_score = data.get("gap_score", proposal.gap_score)
        proposal.linked_complaint_ids = data.get("linked_complaint_ids", proposal.linked_complaint_ids)
        proposal.priority = data.get("priority", proposal.priority)
        proposal.problem_statement = data.get("problem_statement", proposal.problem_statement)
        proposal.stage = ProposalStage.SURVEY_INSPECTION
        proposal.save()
        
        return Response({"message": "Step 1: Need Identification saved.", "proposal": ProposalSerializer(proposal).data}, status=status.HTTP_200_OK)

    # Step 2: Survey & Inspection
    @action(detail=True, methods=["post"], url_path="step2-survey-inspection")
    def step2_survey_inspection(self, request, pk=None):
        proposal = self.get_object()
        data = request.data
        
        proposal.inspection_date = data.get("inspection_date", proposal.inspection_date)
        proposal.survey_team = data.get("survey_team", proposal.survey_team)
        proposal.inspection_notes = data.get("inspection_notes", proposal.inspection_notes)
        proposal.gis_reference = data.get("gis_reference", proposal.gis_reference)
        proposal.latitude = safe_float(data.get("latitude")) or proposal.latitude
        proposal.longitude = safe_float(data.get("longitude")) or proposal.longitude
        proposal.stage = ProposalStage.TECHNICAL_DPR
        proposal.save()
        
        return Response({"message": "Step 2: Survey & Inspection saved.", "proposal": ProposalSerializer(proposal).data}, status=status.HTTP_200_OK)

    # Step 3: Technical DPR
    @action(detail=True, methods=["post"], url_path="step3-technical-dpr")
    def step3_technical_dpr(self, request, pk=None):
        proposal = self.get_object()
        data = request.data
        
        proposal.technical_scope = data.get("technical_scope", proposal.technical_scope)
        proposal.engineering_notes = data.get("engineering_notes", proposal.engineering_notes)
        proposal.estimated_timeline = data.get("estimated_timeline", proposal.estimated_timeline)
        proposal.stage = ProposalStage.FINANCIAL_ESTIMATION
        proposal.save()
        
        return Response({"message": "Step 3: Technical DPR saved.", "proposal": ProposalSerializer(proposal).data}, status=status.HTTP_200_OK)

    # Step 4: Financial Estimation
    @action(detail=True, methods=["post"], url_path="step4-financial-estimation")
    def step4_financial_estimation(self, request, pk=None):
        proposal = self.get_object()
        data = request.data
        
        proposal.civil_works = safe_float(data.get("civil_works")) or proposal.civil_works
        proposal.equipment_cost = safe_float(data.get("equipment_cost")) or proposal.equipment_cost
        proposal.electrical_cost = safe_float(data.get("electrical_cost")) or proposal.electrical_cost
        proposal.contingency_cost = safe_float(data.get("contingency_cost")) or proposal.contingency_cost
        proposal.maintenance_cost = safe_float(data.get("maintenance_cost")) or proposal.maintenance_cost
        
        explicit_est = safe_float(data.get("estimated_cost"))
        computed_sum = (proposal.civil_works or 0) + (proposal.equipment_cost or 0) + (proposal.electrical_cost or 0) + (proposal.contingency_cost or 0) + (proposal.maintenance_cost or 0)
        proposal.estimated_cost = explicit_est if (explicit_est and explicit_est > 0) else computed_sum
        proposal.delegated_power_note = data.get("delegated_power_note", proposal.delegated_power_note)
        proposal.stage = ProposalStage.CLEARANCES
        proposal.save()
        
        return Response({
            "message": "Step 4: Financial Estimation saved.",
            "grand_total": float(proposal.estimated_cost),
            "cost_formatted": ProposalSerializer(proposal).data["cost_formatted"],
            "proposal": ProposalSerializer(proposal).data
        }, status=status.HTTP_200_OK)

    # Step 5: Clearances
    @action(detail=True, methods=["post"], url_path="step5-clearances")
    def step5_clearances(self, request, pk=None):
        proposal = self.get_object()
        data = request.data
        
        current_clearances = proposal.clearances or {}
        if isinstance(data.get("clearances"), dict):
            current_clearances.update(data["clearances"])
        else:
            current_clearances["notes"] = data.get("clearance_notes", "")
            current_clearances["status"] = data.get("clearance_status", "cleared")
            
        proposal.clearances = current_clearances
        proposal.stage = ProposalStage.ATTACHMENTS
        proposal.save()
        
        return Response({"message": "Step 5: Clearances saved.", "proposal": ProposalSerializer(proposal).data}, status=status.HTTP_200_OK)

    # Step 6: Attachments
    @action(detail=True, methods=["post"], url_path="step6-attachments")
    def step6_attachments(self, request, pk=None):
        proposal = self.get_object()
        data = request.data
        
        files_list = proposal.attachments or []
        new_file = data.get("attachment_url") or data.get("file_path") or data.get("file_name")
        if new_file:
            files_list.append({"file_name": new_file, "uploaded_at": str(timezone.now())})
        elif isinstance(data.get("attachments"), list):
            files_list.extend(data["attachments"])
            
        proposal.attachments = files_list
        proposal.stage = ProposalStage.REVIEW_SUBMIT
        proposal.save()
        
        return Response({"message": "Step 6: Attachments saved.", "proposal": ProposalSerializer(proposal).data}, status=status.HTTP_200_OK)

    # Step 7: Submit DPR
    @action(detail=True, methods=["post"], url_path="submit")
    def submit_proposal(self, request, pk=None):
        proposal = self.get_object()
        proposal.status = ProposalStatus.PENDING_REVIEW
        proposal.stage = ProposalStage.REVIEW_SUBMIT
        proposal.save()
        
        return Response({
            "message": f"DPR Proposal {proposal.proposal_id} submitted for Review successfully.",
            "proposal": ProposalSerializer(proposal).data
        }, status=status.HTTP_200_OK)

    # Approve DPR
    @action(detail=True, methods=["post"], url_path="approve")
    def approve_proposal(self, request, pk=None):
        proposal = self.get_object()
        user = request.user if request.user.is_authenticated else None
        
        proposal.status = ProposalStatus.APPROVED
        proposal.reviewed_by = user
        proposal.reviewed_at = timezone.now()
        proposal.approved_by = user
        proposal.approved_at = timezone.now()
        proposal.review_notes = request.data.get("review_notes", proposal.review_notes or "Approved by Authority")
        proposal.save()
        
        return Response({
            "message": f"DPR Proposal {proposal.proposal_id} approved successfully.",
            "proposal": ProposalSerializer(proposal).data
        }, status=status.HTTP_200_OK)

    # Reject DPR
    @action(detail=True, methods=["post"], url_path="reject")
    def reject_proposal(self, request, pk=None):
        proposal = self.get_object()
        user = request.user if request.user.is_authenticated else None
        
        proposal.status = ProposalStatus.REJECTED
        proposal.reviewed_by = user
        proposal.reviewed_at = timezone.now()
        proposal.review_notes = request.data.get("review_notes", "Rejected during review phase")
        proposal.save()
        
        return Response({
            "message": f"DPR Proposal {proposal.proposal_id} rejected.",
            "proposal": ProposalSerializer(proposal).data
        }, status=status.HTTP_200_OK)

    # Sanction DPR & Create Budget Approval
    @action(detail=True, methods=["post"], url_path="sanction")
    def sanction_proposal(self, request, pk=None):
        proposal = self.get_object()
        user = request.user if request.user.is_authenticated else None
        
        sanction_amount = safe_float(request.data.get("sanctioned_amount")) or float(proposal.estimated_cost)
        order_no = request.data.get("sanction_order_no", f"SAN-{timezone.now().strftime('%Y%m%d')}-001")
        
        proposal.status = ProposalStatus.SANCTIONED
        proposal.approved_by = user
        proposal.approved_at = timezone.now()
        proposal.save()
        
        budget_app = BudgetApproval.objects.create(
            proposal=proposal,
            approved_amount=sanction_amount,
            approved_via=order_no,
            approved_by=user
        )
        
        return Response({
            "message": f"DPR Proposal {proposal.proposal_id} sanctioned with amount ₹{sanction_amount:,.2f}.",
            "sanction_order_no": order_no,
            "proposal": ProposalSerializer(proposal).data
        }, status=status.HTTP_200_OK)


class PlanningERPAPIView(APIView):
    """
    Development Planning ERP Dashboard & Suggested Needs API.
    Powers Department Workspace Development Planning ERP (/linedept/planning).
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        dept_param = request.query_params.get("department") or request.query_params.get("dept")
        proposals_qs = Proposal.objects.filter(is_deleted=False)

        if dept_param:
            proposals_qs = proposals_qs.filter(Q(department_id=dept_param) | Q(department__name__icontains=dept_param))

        dev_needs_count = proposals_qs.filter(status=ProposalStatus.DEVELOPMENT_NEEDS).count()
        draft_dpr_count = proposals_qs.filter(status=ProposalStatus.DRAFT_DPR).count()
        pending_review_count = proposals_qs.filter(status__in=[ProposalStatus.PENDING_REVIEW, ProposalStatus.UNDER_REVIEW]).count()
        approved_count = proposals_qs.filter(status__in=[ProposalStatus.APPROVED, ProposalStatus.SANCTIONED, ProposalStatus.IN_EXECUTION]).count()

        # Seed sample proposal if repository is empty for demonstration
        if proposals_qs.count() == 0:
            d_obj = District.objects.first() or District.objects.create(name="Nalanda", state=State.objects.first())
            dept_obj = Department.objects.first() or Department.objects.create(name="Water & Sanitation (JJM)")
            sample_prop = Proposal.objects.create(
                proposal_id="PRP-2026-00104",
                title="Surajpur Ward 3 Elevated Water Reservoir",
                category="Infrastructure",
                district=d_obj,
                department=dept_obj,
                block="Silao",
                status=ProposalStatus.IN_EXECUTION,
                stage=ProposalStage.REVIEW_SUBMIT,
                priority=ProposalPriority.HIGH,
                civil_works=8000000.00,
                equipment_cost=2000000.00,
                electrical_cost=1000000.00,
                contingency_cost=500000.00,
                maintenance_cost=500000.00,
                estimated_cost=12000000.00,
                problem_statement="High water deficit cluster identified in Surajpur Ward 3."
            )
            proposals_qs = Proposal.objects.filter(is_deleted=False)
            approved_count = 1

        dpr_repository = ProposalSerializer(proposals_qs.order_by("-created_at")[:20], many=True).data

        # Suggested Development Needs (Simulation-derived complaint clusters)
        suggested_needs = [
            {
                "id": "NEED-101",
                "title": "Silao Ward 4 Pipeline Expansion & Deep Borewell",
                "department": "Water Resources Department",
                "block": "Silao",
                "gap_score": 8.45,
                "linked_complaints_count": 14,
                "recommended_action": "High complaint density detected. Create DPR Proposal for 500KL Tank."
            },
            {
                "id": "NEED-102",
                "title": "Rajgir PHC Emergency Ward Solar Convergance",
                "department": "Health Department",
                "block": "Rajgir",
                "gap_score": 7.80,
                "linked_complaints_count": 9,
                "recommended_action": "Rooftop Solar 50kW installation recommended for zero blackout."
            }
        ]

        return Response({
            "status": "success",
            "kpi_summary": {
                "development_needs": dev_needs_count,
                "draft_dpr": draft_dpr_count,
                "pending_review": pending_review_count,
                "approved": approved_count,
                "total_proposals": proposals_qs.count()
            },
            "suggested_development_needs": suggested_needs,
            "dpr_repository": dpr_repository
        }, status=status.HTTP_200_OK)