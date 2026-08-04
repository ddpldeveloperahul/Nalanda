#!/usr/bin/env python
"""
import_layer.py

Standalone Django script to automatically unzip and import GIS Shapefiles into the 
Nalanda District Information System (NDIS) database.

Features:
- Accepts a .zip file path or directory (Defaults to DPMS_N A L A N D A (BIHAR)_SHAPEFILES.zip)
- Automatically unzips archives and scans for .shp shapefiles
- Reprojects shapefiles to WGS84 (EPSG:4326) and converts 3D geometries to 2D
- Creates GISCatalogEntry and GISLayerFeature records
- Syncs imported features into AssetCategory and Facility tables for the Web Portal
"""

import os
import sys
import glob
import json
import zipfile
import shutil
import tempfile
from pathlib import Path

# Initialize Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ndis.settings")
import django
django.setup()

from django.db import transaction
from django.conf import settings
import geopandas as gpd

from myapp.models import GISCatalogEntry, GISLayerFeature, HAS_GEODJANGO
if HAS_GEODJANGO:
    from django.contrib.gis.geos import GEOSGeometry

from myapp.views import sync_facilities_from_gis


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
    """Detect feature name from properties dictionary."""
    name_keys = [
        "NAME", "NAME_1", "BLOCK_NAME", "DIST_NAME", "NAME_EN", "BLOCK", 
        "VILL_NAME", "TITLE", "PO_NAME", "PS_NAME", "HOSP_NAME", "SCH_NAME"
    ]
    for key in name_keys:
        for pkey in properties.keys():
            if pkey.upper() == key and properties[pkey]:
                return str(properties[pkey]).strip()
    return fallback


def import_shapefiles_from_folder(extract_dir: Path):
    """Scan directory recursively for .shp shapefiles and import into DB."""
    shp_files = sorted(extract_dir.rglob("*.shp"))
    if not shp_files:
        print(f"[!] No .shp shapefiles found in {extract_dir}")
        return 0, 0

    print(f"[+] Found {len(shp_files)} shapefile layer(s) to process.")
    
    total_layers = 0
    total_features = 0

    for shp_path in shp_files:
        stem = shp_path.stem
        category, display_name = CATEGORY_MAPPING.get(stem, ("Other GIS Layers", stem.replace("_", " ")))
        print(f"\n--- Importing Layer: '{stem}' -> Category: [{category}] ---")

        try:
            gdf = gpd.read_file(shp_path)
            if gdf.empty:
                print(f"    [*] Skipping empty shapefile: {stem}")
                continue

            # Reproject to WGS84 (EPSG:4326) if CRS exists
            if gdf.crs is not None:
                try:
                    gdf = gdf.to_crs(epsg=4326)
                except Exception as crs_err:
                    print(f"    [!] CRS conversion warning for {stem}: {crs_err}")

            # Force 3D geometries to 2D
            try:
                import shapely
                if hasattr(shapely, "force_2d"):
                    gdf["geometry"] = shapely.force_2d(gdf.geometry)
            except Exception:
                pass

            geom_types = gdf.geometry.geom_type.unique()
            primary_geom_type = str(geom_types[0]) if len(geom_types) > 0 else "Unknown"

            with transaction.atomic():
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

                # Clean existing features before re-importing
                GISLayerFeature.objects.filter(catalog_entry=catalog).delete()

                features_to_create = []
                geo_interface = json.loads(gdf.to_json())

                for idx, feat in enumerate(geo_interface.get("features", [])):
                    geom_dict = feat.get("geometry")
                    props = feat.get("properties", {}) or {}

                    clean_props = {}
                    for k, v in props.items():
                        if v is None or (isinstance(v, float) and (v != v)):
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

            total_layers += 1
            total_features += len(gdf)
            print(f"    [+] Successfully imported {len(gdf)} features for '{stem}'")

        except Exception as e:
            print(f"    [!] Error importing shapefile '{stem}': {e}")

    return total_layers, total_features


def main():
    base_dir = Path(__file__).resolve().parent
    
    # 1. Determine input path (zip file or directory)
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
    else:
        # Default search paths
        default_zip = base_dir / "DPMS_N A L A N D A (BIHAR)_SHAPEFILES.zip"
        default_dir = base_dir / "DPMS_N A L A N D A (BIHAR)_SHAPEFILES"
        
        if default_zip.exists():
            target_path = default_zip
        elif default_dir.exists():
            target_path = default_dir
        else:
            print("[!] Error: No input ZIP file or shapefile directory provided and default file not found.")
            print("    Usage: python import_layer.py <path_to_zip_or_folder>")
            sys.exit(1)

    print(f"==================================================")
    print(f"       NDIS GIS LAYER SHAPEFILE IMPORTER         ")
    print(f"==================================================")
    print(f"[+] Target Input Path: {target_path}")

    # 2. Extract ZIP if input is a .zip archive
    if target_path.is_file() and target_path.suffix.lower() == ".zip":
        temp_dir = base_dir / "unzipped_shapefiles_temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[+] Unzipping shapefile archive '{target_path.name}' into temporary directory...")
        with zipfile.ZipFile(target_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        extract_folder = temp_dir
        cleanup_temp = True
    elif target_path.is_dir():
        extract_folder = target_path
        cleanup_temp = False
    else:
        print(f"[!] Invalid path: {target_path}")
        sys.exit(1)

    # 3. Import shapefiles into GISCatalogEntry & GISLayerFeature
    layers_count, features_count = import_shapefiles_from_folder(extract_folder)

    # 4. Clean up temp folder if created
    if cleanup_temp and extract_folder.exists():
        try:
            shutil.rmtree(extract_folder)
            print(f"[+] Cleaned up temporary extraction directory.")
        except Exception as err:
            print(f"[!] Temp cleanup warning: {err}")

    # 5. Sync imported GIS features into Facility table
    print("\n[+] Triggering automatic Facilities table sync...")
    synced_facilities = sync_facilities_from_gis()

    print("\n==================================================")
    print("             IMPORT SUMMARY REPORT                ")
    print("==================================================")
    print(f" Processed Layers   : {layers_count}")
    print(f" Total Features     : {features_count}")
    print(f" Synced Facilities  : {synced_facilities}")
    print(" Status             : SUCCESS")
    print("==================================================\n")


if __name__ == "__main__":
    main()
