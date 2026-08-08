# NDIS & Nalanda GIS Portal - Enterprise Backend API & System Guide

Welcome to the **Nalanda District Information System (NDIS) & GIS Portal** complete architecture and REST API documentation. This platform powers spatial governance, thematic GIS infrastructure layer management, facilities directory sync, and an end-to-end multi-role **Complaint Management & Infrastructure Grievance System** for Bihar district administration.

---

## 📋 Table of Contents

1. [Architecture & System Overview](#1-architecture--system-overview)
2. [Quickstart & Deployment Guide](#2-quickstart--deployment-guide)
3. [Official 10 System Fixed Roles](#3-official-10-system-fixed-roles)
4. [Authentication & JWT Token Security](#4-authentication--jwt-token-security)
5. [Complaint Management & Auto-Routing System](#5-complaint-management--auto-routing-system)
   - [5.1 Workflow State Machine](#51-workflow-state-machine)
   - [5.2 Auto-Routing Engine & SLA Targets](#52-auto-routing-engine--sla-targets)
   - [5.3 Geotagged Evidence Verification](#53-geotagged-evidence-verification)
   - [5.4 Spatial GIS & Nearest Facility Calculations](#54-spatial-gis--nearest-facility-calculations)
   - [5.5 Complaint API Endpoints](#55-complaint-api-endpoints)
6. [Executive Analytics Dashboards & Notifications](#6-executive-analytics-dashboards--notifications)
7. [Geospatial & Shapefile Management Module](#7-geospatial--shapefile-management-module)
8. [Facilities Directory & SCD Type 2 Audit Module](#8-facilities-directory--scd-type-2-audit-module)
9. [Django Admin Panel Integration](#9-django-admin-panel-integration)
10. [Web UI Portals](#10-web-ui-portals)
11. [Smart Spatial Query Engine & User Management Modules](#11-smart-spatial-query-engine--user-management-modules)
12. [Complete REST API Reference Table](#12-complete-rest-api-reference-table)

---

## 1. Architecture & System Overview

- **Backend Framework:** Django 4.2+ (Python 3.10) & Django REST Framework (DRF)
- **Database Engine:** PostgreSQL 15+ with PostGIS Extension (fallback to JSONB spatial fields if GDAL binaries are absent)
- **GIS Processing:** GeoPandas, Shapely, PyProj (automatic EPSG:4326 WGS84 reprojection and 3D to 2D geometry flattening)
- **Authentication Security:** JWT (`rest_framework_simplejwt`) with 30-minute access token lifetime, token rotation, and blacklisting via `token_blacklist`
- **UI System:** Glassmorphism Vanilla CSS3, HTML5, Leaflet.js with OpenStreetMap, ESRI Satellite, and Carto Dark basemaps

---

## 2. Quickstart & Deployment Guide

### 2.1 Virtual Environment & Requirements
```bash
# 1. Clone repository & enter workspace directory
cd e:/Nalanda/ndis

# 2. Create Python virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

### 2.2 Database Migration & Seeding
```bash
# 1. Run database migrations
python manage.py migrate

# 2. Seed 10 Fixed System Roles & Defect Categories
python manage.py seed_complaint_categories

# 3. Ingest GIS Shapefiles & Sync 8,334 Facilities (Optional)
python import_layer.py

# 4. Start local development server
python manage.py runserver
```

---

## 3. Official 10 System Fixed Roles

The system enforces 10 fixed roles with defined scope levels across citizens, department staff, and district administrators:

| # | Role Name | Role Code | Scope Level | Access Scope & Permissions |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Citizen** | `CITIZEN` | `SELF` | Public grievance submission, view own complaints, reopen, submit 1-5 star ratings |
| **2** | **District Collector** | `DISTRICT_COLLECTOR` | `DISTRICT` | District command center, SLA leaderboards, executive oversight |
| **3** | **District Magistrate (DM)** | `DISTRICT_MAGISTRATE` | `DISTRICT` | District Magistrate approvals, executive override, proposal review |
| **4** | **Additional District Magistrate (ADM)** | `ADM` | `DISTRICT` | Delegated administrative oversight & sector grievance monitoring |
| **5** | **Department Head** | `DEPARTMENT_HEAD` | `DEPARTMENT` | Line department queue management, officer tasking, resource allocation |
| **6** | **Department Officer** | `DEPARTMENT_OFFICER` | `DEPARTMENT` | Manage assigned complaints queue, schedule inspections, resolve tickets |
| **7** | **Executive / Assistant Engineer** | `EXECUTIVE_ENGINEER` | `DEPARTMENT` | Assistant/Executive Engineer job execution & material inspection logging |
| **8** | **Field Inspector / Junior Engineer** | `FIELD_INSPECTOR` | `DEPARTMENT` | Field inspector mobile PWA, site geotag verification & evidence upload |
| **9** | **Field Supervisor** | `FIELD_SUPERVISOR` | `DEPARTMENT` | Field operations supervision & inspection report verification |
| **10** | **State Admin** | `STATE_ADMIN` | `STATE` | State-level cross-district KPI comparison & radar analytics |

---

## 4. Authentication & JWT Token Security

Path Prefix: `/api/auth/`

### 4.1 Signup API
- **Endpoint:** `POST /api/auth/signup/`
- **Request Body:**
  ```json
  {
    "username": "sunita_devi",
    "email": "sunita.devi@bihar.gov.in",
    "password": "SecurePassword123!",
    "confirm_password": "SecurePassword123!",
    "first_name": "Sunita",
    "last_name": "Devi",
    "phone": "+919835210492",
    "role": "CITIZEN"
  }
  ```
- **Response (`201 Created`):** Returns user profile & JWT access/refresh tokens.

### 4.2 Login API
- **Endpoint:** `POST /api/auth/login/`
- **Request Body:** Supports Username **OR** Email.
  ```json
  {
    "username": "sunita_devi",
    "password": "SecurePassword123!"
  }
  ```

### 4.3 Token Refresh API
- **Endpoint:** `POST /api/auth/token/refresh/`
- **Request Body:** `{"refresh": "<refresh_token>"}`

---

## 5. Complaint Management & Auto-Routing System

Path Prefix: `/api/complaints/`

### 5.1 Workflow State Machine
$$\text{SUBMITTED} \longrightarrow \text{ASSIGNED} \longrightarrow \text{ACCEPTED} \longrightarrow \text{INSPECTION\_STARTED} \longrightarrow \text{EVIDENCE\_UPLOADED} \longrightarrow \text{RESOLVED} \longrightarrow \text{CITIZEN\_VERIFICATION} \longrightarrow \text{CLOSED}$$

*(Special transitions supported: `REOPENED`, `TRANSFERRED`, `ESCALATED`, `REJECTED`).*

### 5.2 Auto-Routing Engine & SLA Targets
Defect Category automatically routes tickets to responsible line departments and SLA deadlines:
- **`Broken Handpump / Borewell Defect`** $\rightarrow$ Water Resources Department (SLA: 24h)
- **`Piped Water Leakage / Contamination`** $\rightarrow$ Water Resources Department (SLA: 12h)
- **`Garbage Accumulation / Sanitation`** $\rightarrow$ Urban Development & Infra (SLA: 24h)
- **`Non-Functional Street Light`** $\rightarrow$ Urban Development & Infra (SLA: 48h)
- **`Transformer Failure / Power Outage`** $\rightarrow$ Public Works & Transport Dept (SLA: 6h)
- **`Hospital Staff / Oxygen / Facility Issue`** $\rightarrow$ Health Department (SLA: 12h)
- **`School Infrastructure / Roof / Sanitation`** $\rightarrow$ Education Department (SLA: 48h)
- **`Road Potholes / Damaged Bridge`** $\rightarrow$ Public Works & Transport Dept (SLA: 72h)

### 5.3 Geotagged Evidence Verification
When photos/videos are uploaded via `POST /api/complaints/{id}/upload-evidence/`:
- Photo EXIF coordinates are checked against the complaint pin location.
- Distance is computed: if distance $\le 100\text{m}$, `is_geotag_verified = True`.

### 5.4 Spatial GIS & Nearest Facility Calculations
For every dropped pin location (`latitude, longitude`):
- GeoDjango Point geometry (`geom`) is auto-created.
- PostGIS calculates nearest spatial facility (e.g. *Primary Health Centre, Islampur [203m away]*) and sets `nearest_facility_distance_m`.

### 5.5 Complaint API Endpoints

#### Create Complaint (Submit Ticket)
- **Endpoint:** `POST /api/complaints/`
- **Request Body (JSON / Multipart):**
  ```json
  {
    "title": "Broken Handpump at Rajgir Ward 02",
    "description": "Submersible motor burnt out. Over 400 households without potable water.",
    "category": 1,
    "latitude": 25.02911,
    "longitude": 85.42816,
    "district": 1,
    "block": 1,
    "village_ward": 2,
    "citizen_name": "Sunita Devi",
    "citizen_phone": "+919835210492"
  }
  ```

#### State Transition Action Endpoints
- **Assign:** `POST /api/complaints/{id}/assign/` `{"target_user_id": 2, "remarks": "..."}`
- **Accept:** `POST /api/complaints/{id}/accept/` `{"remarks": "..."}`
- **Start Inspection:** `POST /api/complaints/{id}/start-inspection/` `{"target_user_id": 5}`
- **Upload Evidence:** `POST /api/complaints/{id}/upload-evidence/` *(Multipart `files`)*
- **Resolve:** `POST /api/complaints/{id}/resolve/` `{"resolution_summary": "..."}`
- **Citizen Feedback:** `POST /api/complaints/{id}/citizen-feedback/` `{"rating": 5, "feedback_comment": "..."}`
- **Close:** `POST /api/complaints/{id}/close/`
- **Reopen:** `POST /api/complaints/{id}/reopen/` `{"reason": "..."}`
- **Transfer:** `POST /api/complaints/{id}/transfer/` `{"target_department_id": 3}`
- **Escalate:** `POST /api/complaints/{id}/escalate/` `{"reason": "..."}`
- **Reject:** `POST /api/complaints/{id}/reject/` `{"reason": "..."}`
- **Timeline Log:** `GET /api/complaints/{id}/timeline/`
- **Department Complaint Breakdown & List:** `GET /api/department/{department_id}/complain/` *(Also supports name e.g. `/api/department/Health/complain/`)*

#### Spatial & Heatmap Endpoints
- **GeoJSON Export:** `GET /api/complaints/geojson/`
- **GIS Heatmap Points:** `GET /api/complaints/heatmap/`
- **Nearby Search:** `GET /api/complaints/nearby/?lat=25.0291&lng=85.4281&radius=5000`
- **Nearest Facility:** `GET /api/complaints/nearest-facility/?lat=25.0291&lng=85.4281`

---

## 6. Executive Analytics Dashboards & Notifications (Strict Role RBAC)

- `GET /api/dashboards/my-dashboard/` $\rightarrow$ Unified auto-routing dashboard tailored to logged-in user's role
- `GET /api/dashboards/citizen/` $\rightarrow$ Citizen personal grievance stats, status tracker & feedback *(Citizen access only)*
- `GET /api/dashboards/department/` $\rightarrow$ Department queue, assigned, pending, resolved & SLA breached counts *(Department Head)*
- `GET /api/dashboards/officer/` $\rightarrow$ Officer daily work queue & assigned task execution *(Department Officer / Engineers)*
- `GET /api/dashboards/field-inspector/` $\rightarrow$ Field Mobile PWA inspection queue & geotag evidence verification
- `GET /api/dashboards/district/` $\rightarrow$ District department-wise, status-wise & priority-wise breakdown *(Collector / DM / ADM)*
- `GET /api/dashboards/district-collector/` $\rightarrow$ District Collector Command Center & SLA leaderboards
- `GET /api/dashboards/dm/` $\rightarrow$ District Magistrate Executive Command Center
- `GET /api/dashboards/adm/` $\rightarrow$ Additional District Magistrate Sector Grievance Dashboard
- `GET /api/dashboards/state/` $\rightarrow$ State Admin cross-district KPI comparison & ranking matrix
- `GET /api/notifications/` $\rightarrow$ Dispatched notifications list for current logged-in user

---

## 7. Geospatial & Shapefile Management Module

- **Catalog Entry List:** `GET /api/gis/catalog/`
- **GeoJSON Layer Features:** `GET /api/gis/layers/{layer_name}/`
- **Dynamic Shapefile Upload:** `POST /api/gis/upload-layer/` *(Accepts `.zip` shapefile bundles)*
- **Catalog CRUD:** `/api/gis/catalog-crud/`
- **Spatial Feature CRUD:** `/api/gis/features/`

---

## 8. Facilities Directory & SCD Type 2 Audit Module

- **List & Filter Facilities:** `GET /api/facilities/?search=hospital&category=1`
- **Facility CRUD:** `/api/facilities/{id}/`
- **GeoJSON Facility Export:** `GET /api/facilities/geojson/`
- **Bulk GIS Layer Sync:** `POST /api/facilities/bulk-sync-gis/`
- **Audit Version History (SCD Type 2):** `GET /api/facilities/{id}/history/`

---

## 9. Django Admin Panel Integration

Registered Models in Django Admin (`/admin/`):
- **`ComplaintCategoryAdmin`**: Category, department, default priority, default SLA hours, FontAwesome icons.
- **`ComplaintAdmin`**: Complaint lifecycle, SLA breach flags, assigned officers.
  - **`ComplaintEvidenceInline`**: View attached geotagged evidence images & EXIF coordinates.
  - **`ComplaintTimelineInline`**: View complete immutable audit log history.
- **`ComplaintEvidenceAdmin`**: Standalone evidence attachment audit table.
- **`ComplaintTimelineAdmin`**: Standalone workflow event log table.

---

## 10. Web UI Portals

1. **Interactive GIS Map Portal**: `http://127.0.0.1:8000/` (Leaflet.js spatial layer toggle, basemap switcher, pin inspection).
2. **Facilities Directory Portal**: `http://127.0.0.1:8000/facilities/` (Facility search, modal editor, audit history viewer).
3. **Glassmorphic Single Sign-On Portal**: `http://127.0.0.1:8000/login/` & `/signup/` (Tab switcher, dynamic role & department dropdowns, password visibility toggles, session card).

---

## 11. Smart Spatial Query Engine & User Management Modules

### 11.1 Smart Natural Language & Excel Spatial Query Engine
- **Endpoint:** `GET /api/spatial-query/`
- **Description:** Executes natural language and preset spatial queries directly from `Queries for Nalanda.xlsx` across 3 distinct perspectives: **Citizens**, **Government Administration**, and **Line Departments**.
- **Supported Query Parameters:**
  - `q` / `search`: Search query title or keyword (e.g. `"nearest health facility finder"`, `"nearby drinking water source locator"`, `"block-wise health service gap"`, `"institutions for rooftop solar install"`, `"Groundwater stress and dependency zones"`).
  - `lat` & `lng`: User current location / pin latitude & longitude (e.g., `lat=25.0319&lng=85.4164`).
  - `radius`: Distance threshold filter in meters or kilometers (e.g., `radius=5000` for 5 km).
  - `limit`: Top N nearest facilities count (e.g., `limit=5`).
- **RBAC Perspective Permissions:**
  - **Citizens Queries**: Public Access (`200 OK` for everyone).
  - **Government Administration Queries**: Restricted to DM, Collector, ADM, SDM (`403 Forbidden` for Citizens).
  - **Line Departments Queries**: Restricted to Line Department Officers, Executive Engineers, Department Heads (`403 Forbidden` for Citizens).

### 11.2 Complete User Directory & Department Users API
- **User CRUD Endpoint:** `GET` / `POST` / `PUT` / `PATCH` / `DELETE` `/api/users/` & `/api/users/{id}/`
  - Supports full user account management, soft deletion, and multi-field filtering by `search`, `department`, `role`, and `district`.
- **Department-Wise Users Endpoint:** `GET /api/department/{department_id}/users/`
  - Returns total user count and detailed user listings filtered by specific Department ID with role metadata.

### 11.3 Development Planning ERP & 7-Step DPR Wizard Module
- **Planning Dashboard ERP Endpoint:** `GET /api/planning/dashboard/`
  - Powers `/linedept/planning`. Returns KPI summary metrics (`development_needs`, `draft_dpr`, `pending_review`, `approved`), simulation-derived complaint clusters (`suggested_development_needs`), and the DPR repository table.
- **Proposals ViewSet Endpoint:** `GET` / `POST` / `PUT` / `PATCH` / `DELETE` `/api/proposals/` & `/api/proposals/{id}/`
  - Supports filtering by `department`, `district`, `status`, `stage`, `priority`, `block`, `search`.
- **7-Step DPR Wizard Actions:**
  - `POST /api/proposals/{id}/step1-need-identification/`: Need identification (village, block, ward, population impact, gap score, problem statement).
  - `POST /api/proposals/{id}/step2-survey-inspection/`: Survey & site inspection (inspection date, team, notes, GIS location coordinates).
  - `POST /api/proposals/{id}/step3-technical-dpr/`: Technical scope, engineering notes, timeline.
  - `POST /api/proposals/{id}/step4-financial-estimation/`: Financial estimation breakdown (civil, equipment, electrical, contingency, maintenance) with auto-calculated Grand Total.
  - `POST /api/proposals/{id}/step5-clearances/`: Environmental & land clearances checklist.
  - `POST /api/proposals/{id}/step6-attachments/`: DPR drawing PDF and attachment uploads.
  - `POST /api/proposals/{id}/submit/`: Submit DPR for review (`DRAFT_DPR` -> `PENDING_REVIEW`).
- **DM Sanction & Approval Workflow Actions:**
  - `POST /api/proposals/{id}/approve/`: Approve DPR proposal.
  - `POST /api/proposals/{id}/reject/`: Reject DPR proposal with review notes.
  - `POST /api/proposals/{id}/sanction/`: Sanction budget & issue sanction order.

---

## 12. Complete REST API Reference Table

| Path | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/auth/signup/` | `POST` | Public | Register new user account |
| `/api/auth/login/` | `POST` | Public | Obtain JWT Access (30m) & Refresh tokens |
| `/api/auth/token/refresh/` | `POST` | Public | Refresh expired JWT access token |
| `/api/auth/me/` | `GET` | Bearer | Retrieve authenticated user profile |
| `/api/auth/roles/` | `GET` | Public | List system roles |
| `/api/users/` | `GET` / `POST` | Bearer / Admin | Complete User directory CRUD list & create (filters: `search`, `department`, `role`, `district`) |
| `/api/users/{id}/` | `GET` / `PUT` / `PATCH` / `DELETE` | Bearer / Admin | Retrieve, update, patch, or soft delete user account |
| `/api/department/{department_id}/users/` | `GET` | Bearer | Get department-wise user list with role breakdown |
| `/api/spatial-query/` | `GET` | Bearer / Public | Smart Natural Language & Excel Spatial Query Engine (`?q=...`, `?lat=...`, `?lng=...`, `?radius=...`, `?limit=...`, RBAC perspective filter) |
| `/api/planning/dashboard/` | `GET` | Bearer / Public | Development Planning ERP dashboard KPIs, suggested needs & DPR repository |
| `/api/proposals/` | `GET` / `POST` | Bearer | Proposals CRUD list & create (filters: `department`, `district`, `status`, `stage`, `priority`, `block`, `search`) |
| `/api/proposals/{id}/` | `GET` / `PUT` / `PATCH` / `DELETE` | Bearer | Proposal details retrieve, update, and soft delete |
| `/api/proposals/{id}/step1-need-identification/` | `POST` | Bearer | Step 1: Save Need Identification fields |
| `/api/proposals/{id}/step2-survey-inspection/` | `POST` | Bearer | Step 2: Save Survey & Site Inspection notes and GIS coordinates |
| `/api/proposals/{id}/step3-technical-dpr/` | `POST` | Bearer | Step 3: Save Technical Scope and engineering notes |
| `/api/proposals/{id}/step4-financial-estimation/` | `POST` | Bearer | Step 4: Save Financial Line Items and auto-compute Grand Total |
| `/api/proposals/{id}/step5-clearances/` | `POST` | Bearer | Step 5: Save Clearances checklist |
| `/api/proposals/{id}/step6-attachments/` | `POST` | Bearer | Step 6: Upload DPR drawings and attachments |
| `/api/proposals/{id}/submit/` | `POST` | Bearer | Step 7: Submit DPR proposal for review |
| `/api/proposals/{id}/approve/` | `POST` | Bearer | Approve DPR proposal |
| `/api/proposals/{id}/reject/` | `POST` | Bearer | Reject DPR proposal with reason |
| `/api/proposals/{id}/sanction/` | `POST` | Bearer | Sanction proposal budget & create sanction order |
| `/api/complaints/` | `GET` | Bearer / Public | List complaints filtered by role/department scope |
| `/api/complaints/` | `POST` | Bearer | Submit complaint with auto-routing & spatial calculations |
| `/api/complaints/{id}/assign/` | `POST` | Bearer | Assign ticket to officer / engineer |
| `/api/complaints/{id}/accept/` | `POST` | Bearer | Accept assigned ticket |
| `/api/complaints/{id}/start-inspection/` | `POST` | Bearer | Start site inspection phase |
| `/api/complaints/{id}/upload-evidence/` | `POST` | Bearer | Upload geotagged photos/videos/PDFs |
| `/api/complaints/{id}/resolve/` | `POST` | Bearer | Resolve complaint with summary |
| `/api/complaints/{id}/citizen-feedback/` | `POST` | Bearer | Submit 1-5 star rating & feedback |
| `/api/complaints/{id}/close/` | `POST` | Bearer | Close verified complaint |
| `/api/complaints/{id}/reopen/` | `POST` | Bearer | Reopen unresolved complaint |
| `/api/complaints/{id}/transfer/` | `POST` | Bearer | Transfer complaint to another department |
| `/api/complaints/{id}/escalate/` | `POST` | Bearer | Escalate ticket to ADM / DM |
| `/api/complaints/{id}/reject/` | `POST` | Bearer | Reject complaint with reason |
| `/api/complaints/{id}/timeline/` | `GET` | Bearer | Fetch immutable audit timeline log |
| `/api/complaints/geojson/` | `GET` | Public / Bearer | Export complaints as GeoJSON FeatureCollection |
| `/api/complaints/heatmap/` | `GET` | Public / Bearer | Fetch weighted spatial points for heatmaps |
| `/api/complaints/nearby/` | `GET` | Public / Bearer | Query complaints within spatial radius (m) |
| `/api/complaints/nearest-facility/` | `GET` | Public / Bearer | Calculate distance & return top N nearest spatial facilities |
| `/api/dashboards/citizen/` | `GET` | Bearer / Public | Citizen portal metrics summary |
| `/api/dashboards/department/` | `GET` | Bearer / Public | Department queue & SLA metrics |
| `/api/dashboards/officer/` | `GET` | Bearer / Public | Today's officer work queue |
| `/api/dashboards/district/` | `GET` | Bearer / Public | District-wide department & status metrics |
| `/api/dashboards/state/` | `GET` | Bearer / Public | District rankings comparison matrix |
| `/api/notifications/` | `GET` | Bearer | List dispatched notifications |
| `/api/facilities/` | `GET` / `POST` | Bearer / Public | Facilities directory list and create |
| `/api/facilities/{id}/` | `GET` / `PUT` / `DELETE` | Bearer / Public | Facility retrieve, update, delete |
| `/api/facilities/geojson/` | `GET` | Public | Export facilities as GeoJSON FeatureCollection |
| `/api/gis/catalog/` | `GET` | Public | List published GIS layer catalog |
| `/api/gis/layers/{layer}/` | `GET` | Public | Fetch vector layer GeoJSON |
| `/api/gis/upload-layer/` | `POST` | Bearer | Upload shapefile `.zip` bundle |