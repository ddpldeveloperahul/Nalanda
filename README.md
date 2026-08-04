# NDIS & Nalanda GIS Portal - Backend API Integration Guide

Welcome to the **Nalanda District Information System (NDIS) & GIS Portal** API documentation. This comprehensive guide details all backend endpoints, data models, request/response formats, authentication flows, shapefile file upload mechanisms, facility management modules, and frontend integration guidelines for developers building frontend or mobile applications.

---

## Table of Contents

1. [Architecture & System Overview](#1-architecture--system-overview)
2. [Base URL & Request Headers](#2-base-url--request-headers)
3. [Authentication & User Management Module](#3-authentication--user-management-module)
4. [Governance & Department Management Module](#4-governance--department-management-module)
   - [4.1 Departments API](#41-departments-api)
   - [4.2 Department Officers API](#42-department-officers-api)
   - [4.3 Asset Categories API](#43-asset-categories-api)
5. [Geospatial & Shapefile Management Module](#5-geospatial--shapefile-management-module)
   - [5.1 Categorized Layer Catalog API](#51-categorized-layer-catalog-api)
   - [5.2 GeoJSON Layer Vector API](#52-geojson-layer-vector-api)
   - [5.3 Dynamic Shapefile / GeoJSON File Upload API](#53-dynamic-shapefile--geojson-file-upload-api)
   - [5.4 GIS Catalog CRUD API](#54-gis-catalog-crud-api)
   - [5.5 GIS Spatial Feature CRUD API](#55-gis-spatial-feature-crud-api)
6. [Facility & Infrastructure Management Module](#6-facility--infrastructure-management-module)
   - [6.1 Facility Listing & Filtering API](#61-facility-listing--filtering-api)
   - [6.2 Facility CRUD API](#62-facility-crud-api)
   - [6.3 GeoJSON Facility Export API](#63-geojson-facility-export-api)
   - [6.4 Bulk GIS Layer Sync API](#64-bulk-gis-layer-sync-api)
   - [6.5 Facility Version History & Audit Log (SCD Type 2)](#65-facility-version-history--audit-log-scd-type-2)
7. [Web Portals & Interactive Dashboards](#7-web-portals--interactive-dashboards)
   - [7.1 Interactive GIS Map Portal](#71-interactive-gis-map-portal)
   - [7.2 Facility Search & Management UI Portal](#72-facility-search--management-ui-portal)
8. [Error Handling & HTTP Status Codes](#8-error-handling--http-status-codes)
9. [Frontend & Leaflet.js Integration Quickstart](#9-frontend--leafletjs-integration-quickstart)

---

## 1. Architecture & System Overview

- **Framework:** Django 5.2 (Python 3.10) & Django REST Framework (DRF)
- **Database:** PostgreSQL with PostGIS extension (Fallback to JSONB spatial storage)
- **GIS Engine:** GeoPandas, Shapely, PyProj (Automatic WGS84 `EPSG:4326` projection & 2D conversion)
- **Environment Diagnostics:** Automatic PROJ_LIB / GDAL environment configuration for Windows & Linux
- **Authentication:** JWT (JSON Web Tokens via `rest_framework_simplejwt`)
- **Map Frontend:** Leaflet.js with OpenStreetMap, ESRI Satellite, and Carto Dark tiles

---

## 2. Base URL & Request Headers

- **Development Base URL:** `http://127.0.0.1:8000`
- **API Prefix:** `/api/`

### Common Headers

- **For Standard JSON Requests:**
  ```http
  Content-Type: application/json
  Accept: application/json
  ```
- **For Authenticated Endpoints:**
  ```http
  Authorization: Bearer <your_access_token>
  ```
- **For File Uploads (Shapefile Zip / GeoJSON):**
  ```http
  Content-Type: multipart/form-data
  ```

---

## 3. Authentication & User Management Module

Path prefix: `/api/auth/`

### 3.1 User Registration (Signup)
Registers a new user account (Citizens, Field Engineers, Department Officers, Admins).

- **Endpoint:** `POST /api/auth/signup/`
- **Authentication:** None (Public)
- **Request Body:**
  ```json
  {
    "username": "rahul_officer",
    "email": "rahul.officer@bihar.gov.in",
    "password": "SecurePassword123",
    "confirm_password": "SecurePassword123",
    "first_name": "Rahul",
    "last_name": "Kumar",
    "phone": "+919876543210",
    "designation": "Executive Engineer",
    "role": "DEPARTMENT_OFFICER",
    "department": 1,
    "district": 1,
    "state": 1
  }
  ```
- **Response (`201 Created`):**
  ```json
  {
    "message": "User registered successfully.",
    "user": {
      "id": 5,
      "username": "rahul_officer",
      "email": "rahul.officer@bihar.gov.in",
      "first_name": "Rahul",
      "last_name": "Kumar",
      "designation": "Executive Engineer",
      "role": 2,
      "role_info": { "name": "Department Officer", "code": "DEPARTMENT_OFFICER" },
      "department_name": "Health Department"
    },
    "tokens": {
      "access": "eyJhbGciOiJIUzI1NiIsIn...",
      "refresh": "eyJhbGciOiJIUzI1NiIsIn..."
    }
  }
  ```

---

### 3.2 User Login
Authenticates a user with `username` or `email` and password, returning JWT access & refresh tokens.

- **Endpoint:** `POST /api/auth/login/`
- **Authentication:** None (Public)
- **Request Body:**
  ```json
  {
    "username": "rahul_officer",
    "password": "SecurePassword123"
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "message": "Login successful.",
    "user": {
      "id": 5,
      "username": "rahul_officer",
      "email": "rahul.officer@bihar.gov.in",
      "first_name": "Rahul",
      "last_name": "Kumar",
      "role_info": { "code": "DEPARTMENT_OFFICER", "name": "Department Officer" }
    },
    "tokens": {
      "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
      "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
    }
  }
  ```

---

### 3.3 JWT Token Refresh
Refreshes an expired JWT access token using a valid refresh token.

- **Endpoint:** `POST /api/auth/token/refresh/`
- **Authentication:** None (Public)
- **Request Body:**
  ```json
  {
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
  }
  ```

---

### 3.4 User Profile Inspection
Retrieves current authenticated user's profile details.

- **Endpoint:** `GET /api/auth/me/`
- **Authentication:** Required (`Bearer <access_token>`)
- **Response (`200 OK`):** Returns complete user profile JSON.

---

## 4. Governance & Department Management Module

Manage Line Departments, Department Nodal Officers, and Asset Categories.

### 4.1 Departments API

Base Route: `/api/departments/`

| Action | HTTP Method | Endpoint | Query Parameters | Description |
|---|---|---|---|---|
| **List** | `GET` | `/api/departments/` | `?search=Health` | Search/list departments |
| **Create** | `POST` | `/api/departments/` | - | Create line department |
| **Retrieve** | `GET` | `/api/departments/{id}/` | - | Get department details |
| **Update** | `PUT`/`PATCH` | `/api/departments/{id}/` | - | Modify department |
| **Delete** | `DELETE` | `/api/departments/{id}/` | - | Remove department |

#### POST Request Body Example:
```json
{
  "name": "Renewable Energy Department",
  "description": "Department responsible for Solar & Clean Energy Initiatives"
}
```

---

### 4.2 Department Officers API

Base Route: `/api/department-officers/`

| Action | HTTP Method | Endpoint | Query Parameters | Description |
|---|---|---|---|---|
| **List** | `GET` | `/api/department-officers/` | `?search=Rahul` or `?department=1` | Filter/search department officers |
| **Create** | `POST` | `/api/department-officers/` | - | Add a new department officer |
| **Retrieve** | `GET` | `/api/department-officers/{id}/` | - | Officer details |
| **Update** | `PUT`/`PATCH` | `/api/department-officers/{id}/` | - | Modify officer record |
| **Delete** | `DELETE` | `/api/department-officers/{id}/` | - | Remove officer record |

#### POST Request Body Example:
```json
{
  "name": "Er. Rahul Kumar",
  "designation": "Executive Engineer",
  "department": 1,
  "email": "rahul.kumar@bihar.gov.in",
  "contact": "+91 9876543210",
  "user": null
}
```

---

### 4.3 Asset Categories API

Base Route: `/api/asset-categories/`

| Action | HTTP Method | Endpoint | Query Parameters | Description |
|---|---|---|---|---|
| **List** | `GET` | `/api/asset-categories/` | `?search=Solar` or `?department=1` | Filter asset categories |
| **Create** | `POST` | `/api/asset-categories/` | - | Create category with JSON schema |
| **Retrieve** | `GET` | `/api/asset-categories/{id}/` | - | Get category & field schema |
| **Update** | `PUT`/`PATCH` | `/api/asset-categories/{id}/` | - | Modify asset category |
| **Delete** | `DELETE` | `/api/asset-categories/{id}/` | - | Remove category |

#### POST Request Body Examples:

**1. Basic Category (Empty Schema):**
```json
{
  "department": 1,
  "name": "Hospital",
  "field_schema": {}
}
```

**2. Dynamic Schema Category (Custom Fields):**
```json
{
  "department": 1,
  "name": "Hospital",
  "field_schema": {
    "hospital_name": {
      "type": "string",
      "required": true
    },
    "hospital_type": {
      "type": "choice",
      "choices": [
        "Government",
        "Private"
      ]
    },
    "beds": {
      "type": "integer"
    },
    "contact_number": {
      "type": "string"
    }
  }
}
```

---

## 5. Geospatial & Shapefile Management Module

All GIS layers, shapefile ingestion engines, vector tile streams, and spatial feature APIs.

### 5.1 Categorized Layer Catalog API
Fetches all published GIS layers grouped by thematic categories with feature counts for map sidebar rendering.

- **Endpoint:** `GET /api/gis/catalog/`
- **Authentication:** None (Public Map Access)
- **Response (`200 OK`):**
  ```json
  {
    "status": "success",
    "total_layers": 52,
    "categories": {
      "Administrative & Boundaries": [
        {
          "id": 1,
          "layer_name": "District_boundary",
          "display_name": "District boundary",
          "category": "Administrative & Boundaries",
          "geometry_type": "Polygon",
          "feature_count": 1
        },
        {
          "id": 2,
          "layer_name": "Block_boundary",
          "display_name": "Block boundary",
          "category": "Administrative & Boundaries",
          "geometry_type": "Polygon",
          "feature_count": 20
        }
      ],
      "Health & Medical": [
        {
          "id": 3,
          "layer_name": "Hospital",
          "display_name": "Hospital",
          "category": "Health & Medical",
          "geometry_type": "Point",
          "feature_count": 7
        }
      ]
    }
  }
  ```

---

### 5.2 GeoJSON Layer Vector API
Serves complete WGS84 (`EPSG:4326`) GeoJSON `FeatureCollection` for a requested layer to render directly on Leaflet / OpenLayers maps.

- **Endpoint:** `GET /api/gis/layers/{layer_name}/`
- **Example:** `GET /api/gis/layers/Block_boundary/`
- **Response (`200 OK`):**
  ```json
  {
    "type": "FeatureCollection",
    "layer_name": "Block_boundary",
    "category": "Administrative & Boundaries",
    "geometry_type": "Polygon",
    "feature_count": 20,
    "features": [
      {
        "type": "Feature",
        "id": "2",
        "properties": {
          "Block_Name": "Asthawan",
          "District_N": "Nalanda",
          "State_UT_N": "Bihar",
          "Block_Area": 140.26,
          "feature_name": "Asthawan",
          "layer_name": "Block_boundary"
        },
        "geometry": {
          "type": "Polygon",
          "coordinates": [[[85.602, 25.215], [85.612, 25.225], ...]]
        }
      }
    ]
  }
  ```

---

### 5.3 Dynamic Shapefile / GeoJSON File Upload API
Ingests single or multi-layer Shapefile `.zip` archives or `.geojson` files.
- Automatically unzips archives.
- Auto-detects single or multiple shapefiles inside the zip.
- Reprojects Web Mercator (`EPSG:3857`) or any local projection to WGS84 (`EPSG:4326`).
- Converts 3D/Z geometries to 2D for PostGIS compatibility.
- Smart auto-categorization (e.g. `Hospital.shp` -> `Health & Medical`, `School.shp` -> `Education`).

- **Endpoint:** `POST /api/gis/upload-layer/`
- **Content-Type:** `multipart/form-data`
- **Form Data Fields:**
  - `layer_name` *(Text, Optional)*: Custom layer name (e.g. `Solar_Power_Plants`). Optional if zip contains multiple shapefiles.
  - `category` *(Text, Optional)*: Category name (e.g. `Renewable Energy`). Defaults to smart detection or `Custom Uploads`.
  - `file` *(File, Required)*: `.zip` shapefile archive or `.geojson` file.

- **Response (`201 Created`):**
  ```json
  {
    "message": "Successfully imported 2 layer(s) with 87 total features.",
    "imported_layers_count": 2,
    "total_features_imported": 87,
    "layers": [
      {
        "id": 55,
        "layer_name": "Hospital",
        "display_name": "Hospital",
        "geometry_type": "Point",
        "category": "Health & Medical",
        "feature_count": 7
      },
      {
        "id": 56,
        "layer_name": "School",
        "display_name": "School",
        "geometry_type": "Point",
        "category": "Education",
        "feature_count": 80
      }
    ]
  }
  ```

---

### 5.4 GIS Catalog CRUD API

Base Route: `/api/gis/catalog-crud/`

| Action | HTTP Method | Endpoint | Query Parameters | Description |
|---|---|---|---|---|
| **List** | `GET` | `/api/gis/catalog-crud/` | `?search=Health` or `?category=Health` | Filter & search catalog layers |
| **Create** | `POST` | `/api/gis/catalog-crud/` | - | Create layer catalog entry manually |
| **Retrieve** | `GET` | `/api/gis/catalog-crud/{id}/` | - | Layer catalog entry details |
| **Update** | `PUT`/`PATCH` | `/api/gis/catalog-crud/{id}/` | - | Modify layer metadata |
| **Delete** | `DELETE` | `/api/gis/catalog-crud/{id}/` | - | Delete layer catalog entry and associated features |

---

### 5.5 GIS Spatial Feature CRUD API

Base Route: `/api/gis/features/`

| Action | HTTP Method | Endpoint | Query Parameters | Description |
|---|---|---|---|---|
| **List** | `GET` | `/api/gis/features/` | `?catalog_entry={id}` | Filter features by catalog layer ID |
| **Create** | `POST` | `/api/gis/features/` | - | Add an individual spatial feature |
| **Retrieve** | `GET` | `/api/gis/features/{id}/` | - | Spatial feature details |
| **Update** | `PUT`/`PATCH` | `/api/gis/features/{id}/` | - | Update attributes or GeoJSON geometry |
| **Delete** | `DELETE` | `/api/gis/features/{id}/` | - | Remove spatial feature |

#### POST Request Body Example:
```json
{
  "catalog_entry": 3,
  "feature_id": "HOSP-01",
  "name": "Sadar Hospital Bihar Sharif",
  "properties": {
    "type": "Government District Hospital",
    "capacity_beds": 300,
    "contact": "+91 6112 234567"
  },
  "geom_geojson": {
    "type": "Point",
    "coordinates": [85.5143, 25.1968]
  }
}
```

---

## 6. Facility & Infrastructure Management Module

Manage physical assets and infrastructure facilities (Hospitals, Schools, Banks, Churches, Solar Power Sites, Waterbodies, etc.) with spatial coordinates, dynamic custom attributes, and SCD Type 2 audit version history.

Base Route: `/api/facilities/`

### 6.1 Facility Listing & Filtering API

Supports rich search across facility names, dynamic JSON attributes, administrative boundaries, categories, GIS catalog layers, and hazard safety flags.

- **Endpoint:** `GET /api/facilities/`
- **Query Parameters:**

| Parameter | Type | Example Value | Description |
|---|---|---|---|
| `search` | String | `?search=hospital` | Global search across name, attributes, and tags |
| `district` | Integer | `?district=1` | Filter by District ID |
| `department` | Integer | `?department=2` | Filter by Department ID |
| `category` | Integer | `?category=3` | Filter by Asset Category ID |
| `catalog_entry` | Integer | `?catalog_entry=15` | Filter by GIS Layer Catalog ID |
| `hazard_safe` | Boolean | `?hazard_safe=true` | Filter by hazard safety compliance (`true`/`false`) |

#### Common Search Filter Examples:
```http
GET /api/facilities/?search=hospital
GET /api/facilities/?search=bank
GET /api/facilities/?search=school
GET /api/facilities/?district=1
GET /api/facilities/?department=2
GET /api/facilities/?category=3
GET /api/facilities/?catalog_entry=15
GET /api/facilities/?hazard_safe=true
```

#### Response (`200 OK`):
```json
[
  {
    "id": 102,
    "name": "Sadar Hospital Bihar Sharif",
    "district": 1,
    "district_name": "Nalanda",
    "department": 2,
    "department_name": "Health Department",
    "category": 3,
    "category_name": "Hospital",
    "catalog_entry": 15,
    "layer_name": "Hospital",
    "gis_feature": 450,
    "attributes": {
      "beds": 300,
      "hospital_type": "Government",
      "emergency": "24x7"
    },
    "geom": {
      "type": "Point",
      "coordinates": [85.5143, 25.1968]
    },
    "hazard_safe": true,
    "created_at": "2026-08-03T10:15:30Z",
    "updated_at": "2026-08-03T10:15:30Z"
  }
]
```

---

### 6.2 Facility CRUD API

| Action | HTTP Method | Endpoint | Description |
|---|---|---|---|
| **List** | `GET` | `/api/facilities/` | List and search facilities |
| **Create** | `POST` | `/api/facilities/` | Create a new facility record |
| **Retrieve** | `GET` | `/api/facilities/{id}/` | Retrieve facility details |
| **Update** | `PUT`/`PATCH` | `/api/facilities/{id}/` | Update facility (Triggers automatic snapshot version in `FacilityHistory`) |
| **Delete** | `DELETE` | `/api/facilities/{id}/` | Delete facility record |

#### POST Request Body Example:
```json
{
  "name": "Primary Health Centre Asthawan",
  "district": 1,
  "department": 2,
  "category": 3,
  "catalog_entry": 15,
  "attributes": {
    "hospital_type": "Government PHC",
    "beds": 30,
    "contact": "+91 6112 245678"
  },
  "geom": {
    "type": "Point",
    "coordinates": [85.602, 25.215]
  },
  "hazard_safe": true
}
```

---

### 6.3 GeoJSON Facility Export API

Exports all facilities matching current query filters as a standardized GeoJSON `FeatureCollection` for mapping frameworks.

- **Endpoint:** `GET /api/facilities/geojson/`
- **Query Parameters:** Accepts all filtering parameters (`search`, `district`, `department`, `category`, `catalog_entry`, `hazard_safe`).
- **Example:** `GET /api/facilities/geojson/?category=3&hazard_safe=true`
- **Response (`200 OK`):**
  ```json
  {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "id": 102,
        "properties": {
          "name": "Sadar Hospital Bihar Sharif",
          "category": "Hospital",
          "department": "Health Department",
          "district": "Nalanda",
          "hazard_safe": true,
          "attributes": {
            "beds": 300,
            "hospital_type": "Government"
          }
        },
        "geometry": {
          "type": "Point",
          "coordinates": [85.5143, 25.1968]
        }
      }
    ]
  }
  ```

---

### 6.4 Bulk GIS Layer Sync API

Scans all imported `GISLayerFeature` vector records across the system, maps them to their respective `GISCatalogEntry` and `AssetCategory`, and bulk-ingests them as `Facility` records.

- **Endpoint:** `POST /api/facilities/sync-gis/`
- **Authentication:** Public / Admin
- **Request Body:** `{}`
- **Response (`200 OK`):**
  ```json
  {
    "message": "Successfully synced 8254 GIS layer features into Facilities.",
    "synced_facilities_count": 8254,
    "total_facilities": 8254
  }
  ```

---

### 6.5 Facility Version History & Audit Log (SCD Type 2)

Every time a `Facility` record is updated (`PUT` or `PATCH`), a point-in-time snapshot of the prior state is stored in `FacilityHistory`. This endpoint returns the historical timeline of changes.

- **Endpoint:** `GET /api/facilities/{id}/history/`
- **Response (`200 OK`):**
  ```json
  [
    {
      "id": 1,
      "facility": 102,
      "snapshot": {
        "id": 102,
        "name": "Sadar Hospital",
        "attributes": { "beds": 250 },
        "updated_at": "2026-08-03T10:00:00Z"
      },
      "created_at": "2026-08-03T11:20:00Z"
    }
  ]
  ```

---

## 7. Web Portals & Interactive Dashboards

The backend includes built-in interactive web applications built with HTML5, CSS3, Vanilla JavaScript, and Leaflet.js:

### 7.1 Interactive GIS Map Portal
- **URL:** `http://127.0.0.1:8000/map/` or `http://127.0.0.1:8000/`
- **Features:**
  - Collapsible category accordion rendering 50+ shapefile layers.
  - Multi-basemap support (OpenStreetMap, ESRI Satellite, Carto Dark).
  - Feature selection with modal attribute table display.

### 7.2 Facility Search & Management UI Portal
- **URL:** `http://127.0.0.1:8000/facilities/` or `http://127.0.0.1:8000/facilities/search/`
- **Features:**
  - Real-time search across facility names, categories, and custom attributes.
  - Interactive Filter Bar by Department, District, Category, and GIS Layer.
  - Dynamic Form Modal generation based on `AssetCategory` JSON Schema.
  - Leaflet Mini-Map Modal for visual coordinate verification.
  - Version History Audit Timeline Modal.
  - One-click GeoJSON Export download.

---

## 8. Error Handling & HTTP Status Codes

The API returns standard HTTP status codes and uniform JSON error objects:

| Status Code | Meaning | Cause / Description |
|---|---|---|
| `200 OK` | Request Succeeded | Successful `GET`, `PUT`, `PATCH`, or `DELETE` operation. |
| `201 Created` | Resource Created | Successful `POST` creation or file import. |
| `400 Bad Request` | Validation Error | Missing required fields, invalid JSON, or unparseable shapefile. |
| `401 Unauthorized` | Auth Required | Missing or invalid `Bearer <access_token>` in header. |
| `404 Not Found` | Resource Not Found | Requested layer, department, or facility ID does not exist. |
| `500 Server Error` | Backend Exception | Unexpected server-side failure. Check server logs. |

### Standard Error Payload Format:
```json
{
  "error": "Layer 'Invalid_Layer' not found or not published."
}
```

---

## 9. Frontend & Leaflet.js Integration Quickstart

### Example: Searching Facilities and Rendering on Map

```javascript
// 1. Search Facilities by keyword or filters
async function searchFacilities(query = 'hospital', categoryId = null) {
    let url = `http://127.0.0.1:8000/api/facilities/?search=${encodeURIComponent(query)}`;
    if (categoryId) {
        url += `&category=${categoryId}`;
    }
    const res = await fetch(url);
    const facilities = await res.json();
    console.log("Found facilities:", facilities.length);
    return facilities;
}

// 2. Fetch GeoJSON and Render on Leaflet Map
async function renderFacilitiesGeoJSON(mapInstance, categoryId) {
    const url = `http://127.0.0.1:8000/api/facilities/geojson/?category=${categoryId}`;
    const res = await fetch(url);
    const geojson = await res.json();

    const layer = L.geoJSON(geojson, {
        onEachFeature: (feature, layer) => {
            const p = feature.properties;
            layer.bindPopup(`
                <div style="font-family: sans-serif;">
                    <h3 style="margin:0 0 5px 0;">${p.name}</h3>
                    <p style="margin:0; font-size:12px; color:#64748b;">${p.category} | ${p.department}</p>
                </div>
            `);
        }
    }).addTo(mapInstance);

    if (layer.getBounds().isValid()) {
        mapInstance.fitBounds(layer.getBounds());
    }
}
```