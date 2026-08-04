from django.shortcuts import render
from django.db.models import Q
from rest_framework import status, permissions, viewsets


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
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
)



def index(request):
    return render(request, "index.html")

def facilities_page(request):
    return render(request, "facilities.html")

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
    - GET /api/departments/ : List all departments (filter ?search=Health)
    - POST /api/departments/ : Create department
    - GET /api/departments/<id>/ : Retrieve department
    - PUT/PATCH /api/departments/<id>/ : Update department
    - DELETE /api/departments/<id>/ : Delete department
    """
    queryset = Department.objects.all().order_by("id")
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs


class DistrictViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Master Districts.
    - GET /api/districts/ : List all districts
    """
    queryset = District.objects.all().select_related("state").order_by("name")
    serializer_class = DistrictSerializer
    permission_classes = [permissions.AllowAny]




class DepartmentOfficerViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Department Officers / Nodal Officers.
    - GET /api/department-officers/ : List all officers (filter ?search=Rahul or ?department=1)
    - POST /api/department-officers/ : Create officer
    - GET /api/department-officers/<id>/ : Retrieve officer
    - PUT/PATCH /api/department-officers/<id>/ : Update officer
    - DELETE /api/department-officers/<id>/ : Delete officer
    """
    queryset = DepartmentOfficer.objects.all().order_by("id")
    serializer_class = DepartmentOfficerSerializer
    permission_classes = [permissions.AllowAny]

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
    - GET /api/asset-categories/ : List all asset categories (filter ?search=Hospital or ?department=1)
    - /api/asset-categories/ : Create asset category
    - GET /api/asset-categories/<id>/ : Retrieve asset category
    - PUT/PATCH /api/asset-categories/<id>/ : Update asset category
    - DELETE /api/asset-categories/<id>/ : Delete asset category
    """
    queryset = AssetCategory.objects.all().select_related("department", "catalog_entry").order_by("name")
    serializer_class = AssetCategorySerializer
    permission_classes = [permissions.AllowAny]

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
    - GET /api/facilities/ : List facilities (Supports ?search=Hospital, ?district=1, ?department=1, ?category=1, ?catalog_entry=1, ?hazard_safe=true)
    - POST /api/facilities/ : Create facility
    - GET /api/facilities/<id>/ : Retrieve facility
    - PUT/PATCH /api/facilities/<id>/ : Update facility (automatically creates FacilityHistory snapshot)
    - DELETE /api/facilities/<id>/ : Delete facility
    - GET /api/facilities/geojson/ : Export facilities as GeoJSON FeatureCollection for Web Maps
    - GET /api/facilities/<id>/history/ : Retrieve SCD Type 2 version history records
    - POST /api/facilities/sync-gis/ : Sync GIS layer features into Facilities
    """
    queryset = Facility.objects.all().select_related("district", "department", "category", "catalog_entry", "gis_feature").order_by("id")
    serializer_class = FacilitySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        if Facility.objects.count() == 0:
            sync_facilities_from_gis()

        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        district_id = self.request.query_params.get("district")
        dept_id = self.request.query_params.get("department")
        category_id = self.request.query_params.get("category")
        catalog_entry_id = self.request.query_params.get("catalog_entry")
        hazard_safe = self.request.query_params.get("hazard_safe")

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(attributes__icontains=search))
        if district_id:
            qs = qs.filter(district_id=district_id)
        if dept_id:
            qs = qs.filter(department_id=dept_id)
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
    - GET /api/gis/catalog-crud/ : List all layers
    - POST /api/gis/catalog-crud/ : Create a new layer catalog entry
    - GET /api/gis/catalog-crud/<id>/ : Retrieve catalog entry details
    - PUT/PATCH /api/gis/catalog-crud/<id>/ : Update catalog entry
    - DELETE /api/gis/catalog-crud/<id>/ : Delete layer and all its features
    """
    queryset = GISCatalogEntry.objects.all().order_by("id")
    serializer_class = GISCatalogSerializer
    permission_classes = [permissions.AllowAny]

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
    - GET  : List all features (filter with ?catalog_entry=<id>)
    - POST /api/gis/features/ : Create a new feature in a layer
    - GET /api/gis/features/<id>/ : Retrieve feature details
    - PUT/PATCH /api/gis/features/<id>/ : Updat/api/gis/features/e feature properties/geometry
    - DELETE /api/gis/features/<id>/ : Delete feature
    """
    queryset = GISLayerFeature.objects.all().order_by("id")
    serializer_class = GISLayerFeatureSerializer
    permission_classes = [permissions.AllowAny]

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
    permission_classes = [permissions.AllowAny]
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