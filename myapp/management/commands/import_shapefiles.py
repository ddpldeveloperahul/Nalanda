import os
import glob
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

import geopandas as gpd

from myapp.models import GISCatalogEntry, GISLayerFeature, HAS_GEODJANGO
if HAS_GEODJANGO:
    from django.contrib.gis.geos import GEOSGeometry


CATEGORY_MAPPING = {
    # Admin & Boundaries
    "District_boundary": ("Administrative & Boundaries", "District Boundary"),
    "Block_boundary": ("Administrative & Boundaries", "Block Boundary"),
    "Headquarters": ("Administrative & Boundaries", "Administrative Headquarters"),
    "RF_PF_boundary": ("Administrative & Boundaries", "Reserved & Protected Forest Boundary"),
    "Rural_population": ("Demographics & Admin", "Rural Population"),
    "Urban_population": ("Demographics & Admin", "Urban Population"),
    
    # Health & Medical
    "Hospital": ("Health & Medical", "Hospitals"),
    "Blood_Bank": ("Health & Medical", "Blood Banks"),
    "Community_Health_centre": ("Health & Medical", "Community Health Centres"),
    "Dispensary": ("Health & Medical", "Dispensaries"),
    "Primary_Health_centre": ("Health & Medical", "Primary Health Centres"),
    "Veterinary_Hospital": ("Health & Medical", "Veterinary Hospitals"),

    # Education
    "School": ("Education", "Schools"),
    "Collage": ("Education", "Colleges"),
    "University": ("Education", "Universities"),

    # Transport
    "National_Highway": ("Transportation", "National Highways"),
    "State_Highway": ("Transportation", "State Highways"),
    "Other_Roads": ("Transportation", "Other Roads Network"),
    "Railway_line": ("Transportation", "Railway Lines"),
    "Railway_station": ("Transportation", "Railway Stations"),

    # Hydrology & Water
    "River": ("Hydrology & Water", "Rivers (Polygons)"),
    "River_line": ("Hydrology & Water", "River Lines"),
    "Canal_poly": ("Hydrology & Water", "Canals"),
    "Waterbody": ("Hydrology & Water", "Water Bodies"),
    "Well": ("Hydrology & Water", "Wells"),
    "Tubewell": ("Hydrology & Water", "Tubewells"),
    "Spring": ("Hydrology & Water", "Springs"),
    "Water_Table_Contour": ("Hydrology & Water", "Water Table Contours"),
    "GroundWater_Potential": ("Hydrology & Water", "Groundwater Potential Zones"),

    # Environment & Land Use
    "Soil": ("Environment & Land Use", "Soil Types"),
    "Slope": ("Environment & Land Use", "Slope Topography"),
    "Relief": ("Environment & Land Use", "Terrain Relief"),
    "Rocks": ("Environment & Land Use", "Geological Rock Formations"),
    "Landuse_NALANDA_NRSC": ("Environment & Land Use", "Land Use Land Cover (NRSC)"),
    "Isohyet_Lines": ("Environment & Land Use", "Isohyet Rainfall Lines"),
    "Isotherm_Lines": ("Environment & Land Use", "Isotherm Temperature Lines"),
    "Rainfall_Zone": ("Environment & Land Use", "Rainfall Zones"),

    # Hazards
    "Flood_hazard": ("Hazards & Climate", "Flood Hazard Zones"),
    "Earthquake": ("Hazards & Climate", "Earthquake Hazard Zones"),
    "Wind_Hazard": ("Hazards & Climate", "Wind Hazard Zones"),

    # Civic & Infrastructure
    "Bank": ("Civic & Infrastructure", "Banks & Financial Services"),
    "Church": ("Civic & Infrastructure", "Churches"),
    "Circuit_house": ("Civic & Infrastructure", "Circuit Houses"),
    "Industry": ("Civic & Infrastructure", "Industrial Units"),
    "Inspection_Bungalow": ("Civic & Infrastructure", "Inspection Bungalows"),
    "Market": ("Civic & Infrastructure", "Markets & Commercial Nodes"),
    "Mosque": ("Civic & Infrastructure", "Mosques"),
    "Occupational_Structure": ("Civic & Infrastructure", "Occupational Structure"),
    "Places_of_Tourist_Interest": ("Civic & Infrastructure", "Tourist Attractions"),
    "PoliceStation": ("Civic & Infrastructure", "Police Stations"),
    "PostOffice": ("Civic & Infrastructure", "Post Offices"),
    "Temple": ("Civic & Infrastructure", "Temples"),
}


def extract_feature_name(properties: dict, fallback: str) -> str:
    """Helper to detect feature name from properties dictionary."""
    name_keys = ["NAME", "NAME_1", "BLOCK_NAME", "DIST_NAME", "NAME_EN", "BLOCK", "VILL_NAME", "TITLE", "PO_NAME", "PS_NAME", "HOSP_NAME", "SCH_NAME"]
    for key in name_keys:
        for pkey in properties.keys():
            if pkey.upper() == key and properties[pkey]:
                return str(properties[pkey]).strip()
    return fallback


class Command(BaseCommand):
    help = "Imports shapefiles from DPMS_N A L A N D A (BIHAR)_SHAPEFILES directory into GISCatalogEntry and GISLayerFeature models."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            help="Custom path to shapefile directory",
        )
        parser.add_argument(
            "--layer",
            type=str,
            help="Specific layer stem name to import (e.g. Block_boundary)",
        )

    def handle(self, *args, **options):
        shp_dir_arg = options.get("dir")
        target_layer = options.get("layer")

        if shp_dir_arg:
            shp_dir = Path(shp_dir_arg)
        else:
            shp_dir = settings.BASE_DIR.parent / "DPMS_N A L A N D A (BIHAR)_SHAPEFILES"

        if not shp_dir.exists():
            self.stderr.write(self.style.ERROR(f"Shapefile directory does not exist: {shp_dir}"))
            return

        shp_files = sorted(glob.glob(str(shp_dir / "*.shp")))
        if not shp_files:
            self.stderr.write(self.style.ERROR(f"No shapefiles found in: {shp_dir}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {len(shp_files)} shapefiles in '{shp_dir.name}'."))

        for shp_path_str in shp_files:
            shp_path = Path(shp_path_str)
            stem = shp_path.stem

            if target_layer and stem.lower() != target_layer.lower():
                continue

            category, display_name = CATEGORY_MAPPING.get(stem, ("Other GIS Layers", stem.replace("_", " ")))

            self.stdout.write(f"\nProcessing layer: {stem} -> Category: [{category}]")

            try:
                gdf = gpd.read_file(shp_path)
                if gdf.empty:
                    self.stdout.write(self.style.WARNING(f"Skipping empty shapefile: {stem}"))
                    continue

                # Reproject to WGS84 (EPSG:4326) if not already
                if gdf.crs is not None:
                    try:
                        gdf = gdf.to_crs(epsg=4326)
                    except Exception as crs_err:
                        self.stderr.write(self.style.WARNING(f"CRS conversion warning for {stem}: {crs_err}"))

                # Convert 3D geometries (Z dimension) to 2D for PostGIS compatibility
                try:
                    import shapely
                    if hasattr(shapely, "force_2d"):
                        gdf["geometry"] = shapely.force_2d(gdf.geometry)
                except Exception:
                    pass
                
                geom_types = gdf.geometry.geom_type.unique()
                primary_geom_type = str(geom_types[0]) if len(geom_types) > 0 else "Unknown"

                with transaction.atomic():
                    # Create or update catalog entry
                    catalog, created = GISCatalogEntry.objects.get_or_create(
                        layer_name=stem,
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

                    # Clear existing features for clean re-import
                    GISLayerFeature.objects.filter(catalog_entry=catalog).delete()

                    features_to_create = []
                    geo_interface = json.loads(gdf.to_json())

                    for idx, feat in enumerate(geo_interface.get("features", [])):
                        geom_dict = feat.get("geometry")
                        props = feat.get("properties", {}) or {}

                        # Clean properties (remove NaN or Non-serializable)
                        clean_props = {}
                        for k, v in props.items():
                            if v is None or (isinstance(v, float) and (v != v)): # NaN check
                                clean_props[k] = None
                            else:
                                clean_props[k] = v

                        feat_name = extract_feature_name(clean_props, f"{stem} #{idx + 1}")
                        feat_id = str(clean_props.get("OBJECTID") or clean_props.get("FID") or clean_props.get("id") or (idx + 1))

                        geos_geom = None
                        if HAS_GEODJANGO and geom_dict:
                            try:
                                geos_geom = GEOSGeometry(json.dumps(geom_dict))
                            except Exception:
                                geos_geom = None

                        feature_obj = GISLayerFeature(
                            catalog_entry=catalog,
                            feature_id=feat_id,
                            name=feat_name[:255],
                            properties=clean_props,
                            geom_geojson=geom_dict,
                            geom=geos_geom
                        )
                        features_to_create.append(feature_obj)

                        if len(features_to_create) >= 1000:
                            GISLayerFeature.objects.bulk_create(features_to_create)
                            features_to_create = []

                    if features_to_create:
                        GISLayerFeature.objects.bulk_create(features_to_create)

                self.stdout.write(self.style.SUCCESS(f"Successfully imported {len(gdf)} features for layer '{stem}'."))

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error importing {stem}: {str(e)}"))

        # Trigger automatic sync into Facilities
        from myapp.views import sync_facilities_from_gis
        synced = sync_facilities_from_gis()
        self.stdout.write(self.style.SUCCESS(f"\nAll shapefiles import complete! Synced {synced} new features into Facilities."))
