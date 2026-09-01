# NDIS & Nalanda GIS Portal - Enterprise Backend API & System Guide

Welcome to the **Nalanda District Geospatial Decision Support System (DDSS) & E-Governance Platform** complete architecture and REST API documentation. This platform powers evidence-based district administration decision making, multi-layer compound spatial analytics, need-based gap and priority scoring, health decision analytics, structured citizen location feedback, truthful EXIF photo verification, 25m spatial deduplication, facilities directory sync, an end-to-end multi-role **Complaint Management & Infrastructure Grievance System**, **Development Planning ERP with 7-Step DPR Wizard**, **Government Project Execution & Contract Monitoring ERP**, **Enterprise Reports Export Center**, **Line Department Staff Directory & Onboarding**, and **State Governance Budget & Finance Module** for Bihar district administration.

---

## 📋 Table of Contents

1. [Architecture & System Overview](#1-architecture--system-overview)
2. [Quickstart & Deployment Guide](#2-quickstart--deployment-guide)
3. [Official System Fixed Roles (State & District Levels)](#3-official-system-fixed-roles-state--district-levels)
4. [Authentication & JWT Token Security](#4-authentication--jwt-token-security)
5. [Complaint Management & Auto-Routing System](#5-complaint-management--auto-routing-system)
   - [5.1 Workflow State Machine](#51-workflow-state-machine)
   - [5.2 Auto-Routing Engine & SLA Targets](#52-auto-routing-engine--sla-targets)
   - [5.3 Geotagged Evidence Verification](#53-geotagged-evidence-verification)
   - [5.4 Spatial GIS & Nearest Facility Calculations](#54-spatial-gis--nearest-facility-calculations)
   - [5.5 Complaint API Endpoints](#55-complaint-api-endpoints)
6. [Development Planning ERP & 7-Step DPR Wizard Module](#6-development-planning-erp--7-step-dpr-wizard-module)
7. [Government Project Execution & Contract Monitoring ERP Module](#7-government-project-execution--contract-monitoring-erp-module)
   - [7.1 Project KPI Summary & Running Projects](#71-project-kpi-summary--running-projects)
   - [7.2 Site Diary & Daily Progress Logging](#72-site-diary--daily-progress-logging)
   - [7.3 Electronic Measurement Book (e-MB)](#73-electronic-measurement-book-e-mb)
   - [7.4 Financial Bill Processing & Approval Workflow](#74-financial-bill-processing--approval-workflow)
   - [7.5 Automated Execution Risk Signals](#75-automated-execution-risk-signals)
8. [Enterprise Reports Generation & Export Center Module](#8-enterprise-reports-generation--export-center-module)
9. [Line Department Staff Directory & Employee Onboarding Module](#9-line-department-staff-directory--employee-onboarding-module)
10. [State Governance Budget & Finance Module](#10-state-governance-budget--finance-module)
11. [Executive Analytics Dashboards & Notifications](#11-executive-analytics-dashboards--notifications)
12. [Geospatial & Shapefile Management Module](#12-geospatial--shapefile-management-module)
13. [Facilities Directory & SCD Type 2 Audit Module](#13-facilities-directory--scd-type-2-audit-module)
14. [Smart Spatial Query Engine & User Management Modules](#14-smart-spatial-query-engine--user-management-modules)
15. [Django Admin Panel Integration](#15-django-admin-panel-integration)
16. [Web UI Portals Matrix](#16-web-ui-portals-matrix)
17. [Complete Master REST API Reference Table](#17-complete-master-rest-api-reference-table)

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

### 2.2 Database Migration & Seeding Commands
```bash
# 1. Run database migrations
python manage.py migrate

# 2. Seed 10 Fixed System Roles
python manage.py seed_roles

# 3. Seed Defect Categories & SLA Defaults
python manage.py seed_complaint_categories

# 4. Seed Line Department Employee Profiles
python manage.py seed_employees

# 5. Seed Government Project Execution ERP Data (Projects, Site Diaries, MB, Bills, Risks)
python manage.py seed_project_erp

# 6. Seed Enterprise Reports Center Catalog Data
python manage.py seed_reports

# 7. Ingest GIS Shapefiles & Sync 8,334 Facilities (Optional)
python import_layer.py

# 8. Start local development server
python manage.py runserver
```

---

## 3. Official System Fixed Roles (State & District Levels)

The system enforces 16 official fixed roles with defined scope levels across citizens, department staff, district administrators, and state governance:

| # | Role Name | Role Code | Scope Level | Access Scope & Permissions |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Citizen** | `CITIZEN` | `SELF` | Public grievance submission, view own complaints, reopen, submit 1-5 star ratings |
| **2** | **District Collector** | `DISTRICT_COLLECTOR` | `DISTRICT` | District command center, SLA leaderboards, executive oversight |
| **3** | **District Magistrate (DM)** | `DISTRICT_MAGISTRATE` | `DISTRICT` | District Magistrate approvals, executive override, financial bill & DPR sanction |
| **4** | **Additional District Magistrate (ADM)** | `ADM` | `DISTRICT` | Delegated administrative oversight & sector grievance monitoring |
| **5** | **Department Head** | `DEPARTMENT_HEAD` | `DEPARTMENT` | Line department queue management, officer tasking, employee onboarding, financial bill review |
| **6** | **Department Officer** | `DEPARTMENT_OFFICER` | `DEPARTMENT` | Manage assigned complaints queue, schedule inspections, resolve tickets |
| **7** | **Executive / Assistant Engineer** | `EXECUTIVE_ENGINEER` | `DEPARTMENT` | Executive Engineer job execution, site progress, e-MB verification & bill submission |
| **8** | **Field Inspector / Junior Engineer** | `FIELD_INSPECTOR` | `DEPARTMENT` | Field inspector mobile PWA, site geotag verification & evidence upload |
| **9** | **Field Supervisor** | `FIELD_SUPERVISOR` | `DEPARTMENT` | Field operations supervision & inspection report verification |
| **10** | **State Super Admin** | `STATE_SUPER_ADMIN` | `STATE` | State Super Admin with full system level administration and governance |
| **11** | **State Admin** | `STATE_ADMIN` | `STATE` | State-level cross-district KPI comparison, radar analytics & administration |
| **12** | **State Finance Admin** | `STATE_FINANCE_ADMIN` | `STATE` | State Finance Admin for scheme budget mapping, fund releases & financial ledger |
| **13** | **State Department Admin** | `STATE_DEPARTMENT_ADMIN` | `STATE` | State Department Admin for sector-wide line department oversight (Health, Education, PWD) |
| **14** | **State Monitoring Officer** | `STATE_MONITORING_OFFICER` | `STATE` | State Monitoring & Evaluation Officer for project & grievance audit tracking |
| **15** | **State GIS Admin** | `STATE_GIS_ADMIN` | `STATE` | State GIS & Asset Management Administrator for geospatial layer cataloging |
| **16** | **System Administrator** | `SYSTEM_ADMINISTRATOR` | `STATE` | System Administrator for user directory, workflow authority & security settings |

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

### 4.4 Authenticated User Profile API
- **Endpoint:** `GET /api/auth/me/`
- **Response:** Current logged-in user details with role code, scope, and department details.

### 4.5 Change Password API
- **Endpoint:** `POST /api/auth/change-password/`
- **Auth Required:** Bearer Token
- **Request Body:**
  ```json
  {
    "old_password": "CurrentPassword123!",
    "new_password": "NewSecurePassword123!",
    "confirm_password": "NewSecurePassword123!"
  }
  ```
- **Response (`200 OK`):** `"message": "Password changed successfully."`

### 4.6 Forgot Password Request OTP API
- **Endpoint:** `POST /api/auth/forgot-password/` (or `/api/auth/forgot-password/request-otp/`)
- **Auth Required:** Public
- **Request Body:** Accepts Username **OR** Email.
  ```json
  {
    "identifier": "sunita_devi"
  }
  ```
- **Response (`200 OK`):** Generates 6-digit OTP valid for 10 minutes and logs dispatch.

### 4.7 Reset Password with OTP API
- **Endpoint:** `POST /api/auth/forgot-password/reset/` (or `/api/auth/reset-password/`)
- **Auth Required:** Public
- **Request Body:**
  ```json
  {
    "identifier": "sunita_devi",
    "otp": "482910",
    "new_password": "NewSecurePassword123!",
    "confirm_password": "NewSecurePassword123!"
  }
  ```
- **Response (`200 OK`):** `"message": "Password reset successfully. You can now login with your new password."`

### 4.8 Logout API
- **Endpoint:** `POST /api/auth/logout/`
- **Request Body:** `{"refresh": "<refresh_token>"}`
- **Response (`200 OK`):** Blacklists refresh token for secure session termination.

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
- **Department Complaint Breakdown:** `GET /api/department/{department_id}/complain/` *(Also supports name e.g. `/api/department/Health/complain/`)*

#### Spatial & Heatmap Endpoints
- **GeoJSON Export:** `GET /api/complaints/geojson/`
- **GIS Heatmap Points:** `GET /api/complaints/heatmap/`
- **Nearby Search:** `GET /api/complaints/nearby/?lat=25.0291&lng=85.4281&radius=5000`
- **Nearest Facility:** `GET /api/complaints/nearest-facility/?lat=25.0291&lng=85.4281`

---

## 6. Development Planning ERP & 7-Step DPR Wizard Module

### 6.1 Planning Dashboard ERP
- **Endpoint:** `GET /api/planning/dashboard/`
- **Description:** Returns KPI metrics (`development_needs`, `draft_dpr`, `pending_review`, `approved`), grievance cluster recommendations (`suggested_development_needs`), and active DPR proposal repository.

### 6.2 Proposals ViewSet & 7-Step DPR Lifecycle Actions
- **Proposals Endpoint:** `GET` / `POST` / `PUT` / `PATCH` / `DELETE` `/api/proposals/` & `/api/proposals/{id}/`
- **DPR Wizard Steps:**
  1. `POST /api/proposals/`: Step 1 - Need Identification (`title`, `category`, `village`, `block`, `population_impact`, `gap_score`, `linked_complaint_ids`).
  2. `POST /api/proposals/{id}/step2-survey-inspection/`: Step 2 - Survey & Site Inspection notes & GIS location coordinates.
  3. `POST /api/proposals/{id}/step3-technical-dpr/`: Step 3 - Technical Scope & engineering specifications.
  4. `POST /api/proposals/{id}/step4-financial-estimation/`: Step 4 - Financial estimation breakdown (civil, electrical, equipment, contingency, maintenance).
  5. `POST /api/proposals/{id}/step5-clearances/`: Step 5 - Environmental & land clearances checklist.
  6. `POST /api/proposals/{id}/step6-attachments/`: Step 6 - Upload DPR drawing PDFs & CAD attachments.
  7. `POST /api/proposals/{id}/submit/`: Step 7 - Submit DPR proposal for review (`DRAFT_DPR` $\rightarrow$ `PENDING_REVIEW`).

### 6.3 DM Approval & Proposal Negotiation Module
- **Direct Approval:** `POST /api/proposals/{id}/approve/`
  - Approves proposal directly, sets `status = "APPROVED"`, and marks `approval_mode = "DIRECT"`.
- **Negotiation Counter-Offer:** `POST /api/proposals/{id}/negotiation/` (or `POST /api/proposals/{id}/negotiation-response/`)
  - Initiates or responds to negotiation counter-offers between DM and Department Head.
  - Payload parameters: `action` (`COUNTER_OFFER`, `ACCEPT`, `REJECT`), `proposed_amount`, `proposed_timeline_days`, `proposed_scope`, `remarks`.
  - **Financial Audit Rule:** Strictly preserves original `estimated_cost` (e.g. ₹8 Cr) for historical audit. Saves agreed terms to `agreed_amount` (e.g. ₹6 Cr), `agreed_timeline_days`, `agreed_scope`, and `approval_mode = "NEGOTIATED"`.
- **Negotiation History:** `GET /api/proposals/{id}/negotiations/` & `GET /api/proposal-negotiations/`
  - Retrieves full multi-round negotiation trajectory and audit trail.

### 6.4 Proposal Budget Release Module (One-Time & Installment-wise)
- **Release Budget Endpoint:** `POST /api/proposals/{id}/release/`
  - **Mode 1: One-Time Full Release** (`"release_type": "FULL"`): Replaces budget in a single transaction, setting `release_status = "FULLY_RELEASED"` and `status = "FUNDS_RELEASED"`.
  - **Mode 2: Installment-wise Release** (`"release_type": "INSTALLMENT"`): Replaces budget in tranches (e.g. 1st Tranche 30%, 2nd Tranche 70%), updating `released_amount`, `remaining_amount`, and setting `release_status = "PARTIALLY_RELEASED"`.
  - **Date & Timestamp Tracking:** Every release record includes `release_date` (`YYYY-MM-DD`) and ISO `released_at` timestamp.
  - **Strict Validations:** Locks proposal to `INSTALLMENT` mode once installment releases have started (prevents switching to `FULL`), and rejects releases when budget is exhausted (`100%` released).
- **Release History Endpoint:** `GET /api/proposals/{id}/releases/` & `GET /api/proposal-releases/`
  - Fetches complete list of release tranches, order numbers, released amounts, and remaining balance summary.

---

## 7. Government Project Execution & Contract Monitoring ERP Module

The Project Execution ERP module manages running infrastructure projects from sanction through field execution, daily site diaries, electronic Measurement Books (e-MB), financial bill submissions, and risk tracking.

### 7.1 Project KPI Summary & Running Projects
- **Project List & Create:** `GET` / `POST` `/api/projects/`
  - Filters: `department`, `district`, `status`, `risk` / `risk_level`, `search`.
- **Project KPI Summary:** `GET /api/projects/summary/`
  - Returns total running projects, completed projects, inspection due count, budget utilization formatted in Cr/Lakh, total claimed bill amounts, total net payable amounts, and project lists grouped by status.
- **Budget Sanction Action:** `POST /api/projects/{id}/sanction/`
  - Sanctions project budget, assigns sanction order number (`SAN-2026-NLD-XXX`), and transitions status to `IN_EXECUTION`.

### 7.2 Hierarchical 2-Level Work Assignment & Officer Field Review
- **Combined Work Assignment Action:** `POST /api/projects/{id}/assign-work/`
  - Department Head / DM assigns project work to Department Officer, Junior Engineer, and Contractor simultaneously.
  - Parameters: `assigned_officer_id`, `assigned_engineer_id`, `contractor_name`, `assignment_notes`, `target_completion_date`.
- **Level 1 Officer Assignment Action:** `POST /api/projects/{id}/assign-officer/`
  - Department Head assigns project responsibility to Nodal Department Officer.
  - Parameters: `assigned_officer_id`, `assignment_notes`, `target_completion_date`.
- **Level 2 Field Engineer Assignment Action:** `POST /api/projects/{id}/assign-engineer/`
  - Department Officer assigns Junior Engineer (JE) / Field Inspector and Contractor.
  - Parameters: `assigned_engineer_id`, `contractor_name`, `field_assignment_notes`, `target_completion_date`.
- **Officer Review Action:** `POST /api/projects/{id}/officer-review/`
  - Department Officer reviews field work progress, Site Diaries, and Measurement Books.
  - Parameters: `officer_review_status` (`APPROVED` / `REJECTED`), `remarks`.

### 7.3 Site Diary & Daily Progress Logging
- **Site Diary CRUD:** `GET` / `POST` `/api/site-diaries/` & `/api/site-diaries/{id}/`
- **Daily Progress Action:** `POST /api/projects/{id}/daily-progress/`
  - Logs daily physical progress %, deployed labour count, materials consumed, weather condition, and optional execution risk signal.

### 7.4 Department Head Final Completion Verification
- **Verify Completion Action:** `POST /api/projects/{id}/verify-completion/`
  - **Verification Safeguards:** Checks that progress is 100%, Site Diary exists, e-MB record exists, and no unresolved `CRITICAL` risk signals remain.
  - **Approval Effect:** Sets `completion_verification_status = "APPROVED"`, transitions project status to `completed`, records `actual_completion_date`, and updates linked proposal.

### 7.3 Electronic Measurement Book (e-MB)
- **MB Entries Endpoint:** `GET` / `POST` / `PUT` / `PATCH` / `DELETE` `/api/measurement-books/` & `/api/measurement-books/{id}/`
  - Records item descriptions, unit of measurement, measured quantities, item rates, total calculated amounts, measuring officer (JE/AE), and verifying engineer (EE).

### 7.4 Financial Bill Processing & Approval Workflow
- **Project Bills Endpoint:** `GET` / `POST` / `PUT` / `PATCH` / `DELETE` `/api/bills/` & `/api/bills/{id}/`
- **RBAC Financial Access Control:** Restricted to District Magistrate (DM) and Department Heads. Department Heads see bills scoped to their department; DM has district-wide financial authorization access.
- **Bill Fields:** Bill number (`RA-BILL-2026-XXX`), bill type (`ADVANCE_BILL`, `RUNNING_BILL`, `FINAL_BILL`), claimed amount, verified amount, deductions, net payable amount, payment status (`draft`, `pending_approval`, `approved`, `disbursed`, `rejected`), PFMS transaction reference.

### 7.5 Automated Execution Risk Signals
- **Execution Risks Endpoint:** `GET` / `POST` / `PUT` / `PATCH` / `DELETE` `/api/execution-risks/` & `/api/execution-risks/{id}/`
  - Filters by project and severity (`low`, `medium`, `high`, `critical`).
  - Records active risk signals (e.g. monsoon waterlogging, material delivery delay), recommendations, and resolution status.

### 7.6 Budget Utilization & Verified Expenditure Module
- **Record Verified Expenditure:** `POST /api/projects/{id}/expenditure/`
  - **RBAC Enforced:** Strictly restricted to `DEPARTMENT_OFFICER` belonging to the exact department of the project.
  - **Validations:** `amount > 0`, `cumulative expenditure <= released amount`, `cumulative expenditure <= sanctioned amount`, `duplicate reference_no not allowed`.
  - **Effect:** Preserves transaction history in `ProjectExpenditure` model and cumulatively updates `ProjectExecution.expenditure_amount`.
- **Get Budget Utilization Summary:** `GET /api/projects/{id}/budget-utilization/`
  - Returns `sanctioned_amount`, `released_amount`, `utilized_amount`, `remaining_amount`, `utilization_percentage`, `utilization_status` (`NOT_UTILIZED`, `PARTIALLY_UTILIZED`, `FULLY_UTILIZED`, `EXCEEDED`), `verified_by`, `verified_at`, and full transaction history.
- **Expenditure History CRUD:** `GET /api/project-expenditures/?project={id}`

---

## 8. Enterprise Reports Generation & Export Center Module

Path Prefix: `/api/reports/`

### 8.1 Overview & Report Categories
Provides a central repository for scheduled and on-demand government audit and operational reports across 4 primary categories:
1. **`SLA Audit`**: Monthly line department SLA breach rate, resolution speed, and escalation metrics.
2. **`Asset Audit`**: Geotagged facility & asset verification logs with PostGIS coordinate validation.
3. **`Grievance Log`**: Citizen complaint volume, status breakdown, and satisfaction ratings.
4. **`Workflow Audit`**: Immutable audit logs of state machine transitions and officer handoffs.

### 8.2 API Endpoints
- **Report List & Search:** `GET /api/reports/?category=sla_audit&department=6`
- **Generate On-Demand Report Action:** `POST /api/reports/generate/`
  - **Request Body:** `{"type": "sla_audit", "department": 6, "district": 25}`
  - **Response (`201 Created`):** Instantly creates report record with code (`REP-XXX`), formatted file size, and PDF/CSV download path.
- **Download Report Document:** `GET /api/reports/{id}/download/`
  - Serves generated PDF or CSV document file.

### 8.3 Web UI Portals
- **Enterprise Reports Center:** `http://127.0.0.1:8000/reports/` and `/linedept/reports/`

---

## 9. Line Department Staff Directory & Employee Onboarding Module

Path Prefix: `/api/employees/`

### 9.1 Enterprise Architecture & Role Binding
- 1-to-1 linkage between `Employee` profile and `User` account (`User -> Role -> Permissions` is the single source of truth for authorization).
- Department & District boundaries are enforced based on logged-in Department Head credentials.

### 9.2 Secure Onboarding Lifecycle
$$\text{INVITED} \longrightarrow \text{PENDING} \longrightarrow \text{ACCEPTED} \longrightarrow \text{USER CREATED} \longrightarrow \text{ROLE ASSIGNED} \longrightarrow \text{ACTIVE}$$

### 9.3 API Endpoints
- **Employee Directory List & Search:** `GET /api/employees/?search=Vijay&role=DEPARTMENT_OFFICER&status=active`
- **Create / Update Employee Profile:** `POST` / `PUT` / `PATCH` / `DELETE` `/api/employees/` & `/api/employees/{id}/`
- **Issue Secure Onboarding Invitation Action:** `POST /api/employees/invite/`
  - **Request Body:**
    ```json
    {
      "email": "anil.mehta@nalanda.gov.in",
      "full_name": "Anil Mehta",
      "designation": "Assistant Engineer",
      "office": "District Water Office",
      "block": "Silao",
      "role": "DEPARTMENT_OFFICER",
      "reports_to": 1
    }
    ```
  - **Response (`201 Created`):** Generates 7-day secure UUID token, creates `EmployeeInvitation` record, sets status to `INVITED`, and logs `INVITATION_CREATED` audit event.
- **Accept Invitation Action:** `POST /api/employees/accept-invite/`
  - Validates token, creates `User` account with password, assigns RBAC role, updates Employee status to `ACTIVE`, and sets `joined_at` timestamp.

### 9.4 Web UI Portals
- **Staff Directory & Employee Management:** `http://127.0.0.1:8000/employees/` and `/linedept/employees/`

---

## 10. State Governance Budget & Finance Module

Path Prefix: `/api/state-budget/`

### 10.1 Master Governance Dashboard & Budget Flow
Tracks the complete state financial workflow:
$$\text{Budget Provision} \longrightarrow \text{Authorization} \longrightarrow \text{Allocation} \longrightarrow \text{Sanction} \longrightarrow \text{Release} \longrightarrow \text{Commitment} \longrightarrow \text{Utilization}$$

### 10.2 KPI Summary Band Metrics & Filter Matrix
- **`total_state_budget`**: Total annual state budget provision (e.g., `₹4,800.00 Cr` for FY 2026-27).
- **`department_allocation`**: Departmental authorized budget allocations (`₹4,600.00 Cr`, `98% of provision`).
- **`district_allocation`**: District-wise authorized allocations across departments (`₹899.00 Cr`, `20% of authorized`).
- **`total_sanctioned`**: Total competent authority approvals (`₹4.00 Cr`).
- **`total_released`**: Total fund releases (`₹3,900 Cr`).
- **`total_committed`**: Financial obligations against released funds (`₹3,200 Cr`).
- **`total_utilized`**: Actual expenditure utilized (`₹2,850 Cr`, `73% of released`).
- **`available_balance`**: Unsanctioned available balance (`₹4,596.00 Cr`, `authorized - sanctioned`).
- **`unreleased_balance`**: Sanctioned unreleased balance (`₹4.00 Cr`, `sanctioned - released`).
- **Filter Parameters:** `financial_year`, `department` (e.g. `Health & Family Welfare`, `School Education`, `Public Works Department`, `Electricity Board`, `Urban Local Body / Sanitation`, `Solar & Renewable Energy`, `Tourism & Heritage Development`, `Water & Sanitation (Jal Jeevan Mission)`), `district` (10 monitored units), `scheme` (14 state/central schemes).

### 10.3 REST API Endpoints & RBAC Authorization Rules

> [!IMPORTANT]
> **Strict RBAC Security Enforcement**: All State Budget APIs require **JWT Bearer Token Authentication** and are restricted exclusively to authorized roles: **`STATE_FINANCE_ADMIN`**, **`STATE_SUPER_ADMIN`**, **`STATE_ADMIN`**, and **`SYSTEM_ADMINISTRATOR`**. Unauthenticated requests return `401 Unauthorized`. Unauthorized roles (e.g., `CITIZEN` or `DEPARTMENT_OFFICER`) receive `403 Forbidden` (`Access Denied: Only State Finance Administrators and State Super Admins can access or modify State Budget data.`).

#### 1. Master State Budget Summary & Analytics API
- **Endpoint:** `GET /api/state-budget/summary/` or `GET /api/state-budget/`
- **Auth Required:** `Bearer (State Finance Admin / State Super Admin)`
- **Query Filters:** `?financial_year=2026-27`, `?department=Health`, `?district=Nalanda`, `?scheme=Ayushman`

#### 2. Master State Budget CRUD (`/api/state-budgets/`)
- **List All:** `GET /api/state-budgets/`
- **Retrieve Single:** `GET /api/state-budgets/{id}/`
- **Create Master Budget:** `POST /api/state-budgets/`
  - **Request Body (JSON):**
    ```json
    {
      "financial_year": "2027-28",
      "total_state_budget_cr": 5200.00,
      "department_allocation_cr": 5000.00,
      "district_allocation_cr": 1100.00,
      "total_sanctioned_cr": 10.00,
      "total_released_cr": 4200.00,
      "total_committed_cr": 3500.00,
      "total_utilized_cr": 3100.00,
      "available_balance_cr": 4990.00,
      "unreleased_balance_cr": 10.00,
      "active_projects_count": 12,
      "at_risk_projects_count": 3,
      "pending_approvals_count": 5
    }
    ```
- **Update Master Budget:** `PUT /api/state-budgets/{id}/` or `PATCH /api/state-budgets/{id}/`
- **Delete Master Budget:** `DELETE /api/state-budgets/{id}/` (Returns `204 No Content`)

#### 3. Department Budget CRUD (`/api/department-budgets/`)
- **Create Department Budget:** `POST /api/department-budgets/`
  - **Request Body (JSON):**
    ```json
    {
      "department": 13,
      "financial_year": "2026-27",
      "authorized_budget_cr": 950.00,
      "sanctioned_budget_cr": 890.00,
      "released_budget_cr": 800.00,
      "committed_budget_cr": 720.00,
      "utilized_budget_cr": 680.00
    }
    ```

#### 4. District Allocation CRUD (`/api/district-allocations/`)
- **Create District Allocation:** `POST /api/district-allocations/`
  - **Request Body (JSON):**
    ```json
    {
      "district": 25,
      "department": 13,
      "financial_year": "2026-27",
      "allocation_amount_cr": 150.00,
      "sanctioned_amount_cr": 130.00,
      "utilized_amount_cr": 110.00
    }
    ```

#### 5. Scheme Master CRUD (`/api/schemes/`)
- **Create Scheme Master Record:** `POST /api/schemes/`
  - **Request Body (JSON):**
    ```json
    {
      "code": "SCH-HEALTH-005",
      "name": "Mukhyamantri Health Infrastructure Scheme",
      "department": 13,
      "category": "State Sponsored",
      "total_allocation_cr": 350.00,
      "sanctioned_cr": 320.00,
      "released_cr": 290.00,
      "utilized_cr": 240.00
    }
    ```

#### 6. Financial Ledger Log CRUD (`/api/financial-ledger/`)
- **Create Financial Ledger Entry:** `POST /api/financial-ledger/`
  - **Request Body (JSON):**
    ```json
    {
      "transaction_id": "TXN-FIN-2026-099",
      "financial_year": "2026-27",
      "entry_type": "SANCTION",
      "department": 13,
      "district": 25,
      "amount_cr": 45.00,
      "remarks": "Sanction order issued for primary health center construction."
    }
    ```

---

## 11. Executive Analytics Dashboards & Notifications

Path Prefix: `/api/dashboards/` & `/api/notifications/`

- `GET /api/dashboards/my-dashboard/` $\rightarrow$ Unified auto-routing dashboard tailored to logged-in user's role
- `GET /api/dashboards/citizen/` $\rightarrow$ Citizen personal grievance stats, status tracker & feedback
- `GET /api/dashboards/department/` $\rightarrow$ Department queue, assigned, pending, resolved & SLA breached counts
- `GET /api/dashboards/officer/` $\rightarrow$ Officer daily work queue & assigned task execution
- `GET /api/dashboards/field-inspector/` $\rightarrow$ Field Mobile PWA inspection queue & geotag evidence verification
- `GET /api/dashboards/district/` $\rightarrow$ District department-wise, status-wise & priority-wise breakdown
- `GET /api/dashboards/district-collector/` $\rightarrow$ District Collector Command Center & SLA leaderboards
- `GET /api/dashboards/dm/` $\rightarrow$ District Magistrate Executive Command Center
- `GET /api/dashboards/adm/` $\rightarrow$ Additional District Magistrate Sector Grievance Dashboard
- `GET /api/dashboards/state/` $\rightarrow$ State Admin cross-district KPI comparison & ranking matrix
- `GET /api/notifications/` $\rightarrow$ Dispatched notifications list for current logged-in user

---

## 11. Geospatial & Shapefile Management Module

Path Prefix: `/api/gis/`

- **Catalog Entry List:** `GET /api/gis/catalog/`
- **GeoJSON Layer Features:** `GET /api/gis/layers/{layer_name}/`
- **Dynamic Shapefile Upload:** `POST /api/gis/upload-layer/` *(Accepts `.zip` shapefile bundles, auto-reprojects to WGS84 EPSG:4326)*
- **Catalog CRUD:** `/api/gis/catalog-crud/`
- **Spatial Feature CRUD:** `/api/gis/features/`

---

## 12. Facilities Directory & SCD Type 2 Audit Module

Path Prefix: `/api/facilities/`

- **List & Filter Facilities:** `GET /api/facilities/?search=hospital&category=1` (Public `AllowAny` access enabled for unauthenticated map display)
- **Facility CRUD:** `/api/facilities/{id}/`
- **GeoJSON Facility Export:** `GET /api/facilities/geojson/`
- **Bulk GIS Layer Sync:** `POST /api/facilities/bulk-sync-gis/`
- **Audit Version History (SCD Type 2):** `GET /api/facilities/{id}/history/`

---

## 13. Smart Spatial Query Engine, Department Indicators & Feedback Analytics

### 13.1 Smart Natural Language Spatial Query Engine
- **Primary Endpoint:** `GET /api/spatial-query/` (Alias Routes: `GET /api/spatial-analysis/query/` and `POST /api/spatial-analysis/query/`)
- **Description:** Executes multi-sector natural language spatial queries, GIS radius searches, and attribute filters across 3 official perspectives (**Citizens**, **Government Administration**, **Line Departments**).
- **Supported Query Capabilities (91+ Pre-Configured Queries):**
  - **57 Multi-Sector Queries:** Covers Health (1-8), Education (9-13), Water (14-19), PWD/Roads (20-24), Urban (25-28), Electricity/Energy (29-32), Forest/Environment (33-35), Tourism (36-38), Cross-Department (39-47), and Multi-Sector Executive Decision Questions (48-57).
  - **34 Official Preset Queries (`Queries for Nalanda.pdf`):** Full intent matching for citizen facility finders, government administration gap analyses, and line department planning supports.
- **Real Haversine Distance & Radius Filter Engine:** Computes real Haversine distance (`d_km`) between user coordinates (`lat`, `lng`) and target facilities/villages, filtering results dynamically within requested `radius` (km).
- **Query Parameters:** `q` / `search`, `lat` (e.g. `25.198`), `lng` (e.g. `85.514`), `radius` (e.g. `5`), `limit` (e.g. `20`).

### 13.2 Department-Specific Decision Indicators
- **Education Indicators API (`GET /api/education/indicators/`):** Returns `sanctioned_teachers`, `available_teachers`, `teacher_vacancies`, `teacher_vacancy_percentage`, `student_enrolment`, `classroom_count`, `drinking_water_status`, and `separate_girls_toilet`.
- **Health Staffing & Facility Indicators API (`GET /api/health/staffing/`):** Returns doctor/nurse vacancies, ICU bed availability, patient visits, ambulance count, and medicine stockouts.
- **Water Infrastructure Indicators API (`GET /api/water/indicators/`):** Returns water coverage %, daily supply hours, non-functional water sources, and household tap coverage.
- **PWD Road Infrastructure Indicators API (`GET /api/pwd/indicators/`):** Returns unpaved road %, bridge gap locations, and all-weather road connectivity.
- **Urban Development Indicators API (`GET /api/urban/indicators/`):** Returns sewerage coverage %, waste collection %, and sanitation complaint density.

### 13.3 Citizen Feedback Real-Time Analytics API
- **Endpoint:** `GET /api/feedback/analytics/`
- **Description:** Returns 100% dynamic, real-time database aggregations for citizen location feedback.
- **Query Filters:** `?start_date=20-08-2026&end_date=25-08-2026&department=13`
- **Flexible Date Parsing:** Supports both `DD-MM-YYYY` (e.g., `20-08-2026`) and ISO `YYYY-MM-DD` (e.g., `2026-08-20`) formats.
- **Metrics Calculated:** Real response count (`total_responses`), average rating score, active block ratings, question-level response distributions, and daily response time-series trends.

### 13.4 User Directory & Department Users API
- **User Directory CRUD:** `GET` / `POST` / `PUT` / `PATCH` / `DELETE` `/api/users/` & `/api/users/{id}/`
- **Department-Wise Users Endpoint:** `GET /api/department/{department_id}/users/`

---

## 14. Django Admin Panel Integration

Registered Models in Django Admin (`http://127.0.0.1:8000/admin/`):
- **`ComplaintCategoryAdmin`**: Category, department, default priority, default SLA hours, FontAwesome icons.
- **`ComplaintAdmin`**: Complaint lifecycle, SLA breach flags, assigned officers.
  - **`ComplaintEvidenceInline`**: View attached geotagged evidence images & EXIF coordinates.
  - **`ComplaintTimelineInline`**: View complete immutable audit log history.
- **`ProjectExecutionAdmin`**: Running projects, sanction amounts, expenditure, progress %, risk levels.
- **`ReportAdmin`**: Generated report catalog, downloadable PDF/CSV files, category tagging.
- **`EmployeeAdmin`**: Staff profile directory, 1-to-1 user bindings, invitation status tracking.

---

## 15. Web UI Portals Matrix

| # | Web Portal Name | URL Route | Target Audience | Primary Features |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Interactive GIS Map Portal** | `/` or `/map/` | Public / Officers / Admins | Leaflet.js spatial vector layers, basemap toggle, spatial pin inspection, buffer search |
| **2** | **Facilities Directory Portal** | `/facilities/` | Public / Administrators | Search 8,334+ facilities, modal editor, SCD Type 2 version history viewer |
| **3** | **Enterprise Reports Center** | `/reports/` or `/linedept/reports/` | Department Heads / Admins | On-demand PDF/CSV report generation, SLA audit logs, asset verification records |
| **4** | **Staff Directory & Onboarding** | `/employees/` or `/linedept/employees/` | Department Heads / HR | Employee profile management, secure 7-day token invitations, RBAC role assignment |
| **5** | **Glassmorphic Single Sign-On** | `/login/` & `/signup/` | All Registered Users | Tabbed authentication card, dynamic role & department selectors, password toggles |

---

## 16. Complete Master REST API Reference Table

### 16.1 Authentication, Roles & User Directory APIs
| Path | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/auth/signup/` | `POST` | Public | Register new user account with role selection |
| `/api/auth/login/` | `POST` | Public | Obtain JWT Access (30m) & Refresh tokens (Username or Email) |
| `/api/auth/token/refresh/` | `POST` | Public | Refresh expired JWT access token |
| `/api/auth/me/` | `GET` | Bearer | Retrieve authenticated user profile & permissions |
| `/api/auth/change-password/` | `POST` | Bearer | Change password for authenticated user account |
| `/api/auth/forgot-password/` | `POST` | Public | Request 6-digit OTP for password recovery (by username or email) |
| `/api/auth/forgot-password/reset/` | `POST` | Public | Reset password using verified 6-digit OTP |
| `/api/auth/logout/` | `POST` | Bearer / Public | Logout user and blacklist JWT refresh token |
| `/api/auth/roles/` | `GET` | Public | List system roles |
| `/api/users/` | `GET` / `POST` | Bearer / Admin | User directory CRUD list & create (filters: `search`, `department`, `role`, `district`) |
| `/api/users/{id}/` | `GET` / `PUT` / `PATCH` / `DELETE` | Bearer / Admin | Retrieve, update, patch, or soft delete user account |
| `/api/department/{department_id}/users/` | `GET` | Bearer / Public | Get department-wise user list with role breakdown |

### 16.2 Smart Natural Language Spatial Query Engine APIs
| Path | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/spatial-query/` | `GET` | Public / Bearer | Smart Natural Language Spatial Query Engine (`?q=...`, `?lat=...`, `?lng=...`, `?radius=...`) |
| `/api/spatial-analysis/query/` | `GET` / `POST` | Public / Bearer | Multi-Layer Compound Spatial Query Engine (Natural Language GET & Compound Attribute JSON POST) |
| `/api/spatial-query/query/` | `GET` / `POST` | Public / Bearer | Shortcut Alias endpoint matching `/api/spatial-analysis/query/` |

### 16.3 Multi-Sector Gap Analysis & Gap Priority Decision Engine APIs
| Path | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/gap-priority/` | `GET` / `POST` | Public / Bearer | Master Gap Priority Dashboard & Weighted Need Matrix Engine |
| `/api/gap-priority/rankings/` | `GET` | Public / Bearer | Top Priority Infrastructure Deficit Rankings |
| `/api/gap-priority/overview/` | `GET` | Public / Bearer | Executive Overview KPIs for Sector Gap Priorities |
| `/api/gap-priority/map/` | `GET` | Public / Bearer | Spatial Map Points with Gap Score Weights & Color Coding (`#ef4444`, `#f97316`) |
| `/api/priority-locations/rankings/` | `GET` | Public / Bearer | Alias endpoint for Priority Location Gap Rankings |
| `/api/gap-analysis/` | `GET` / `POST` | Public / Bearer | Gap Analysis Location Repository List & Create |
| `/api/gap-analysis/{location_id}/` | `GET` / `PUT` / `DELETE` | Public / Bearer | Retrieve, update, or delete specific Gap Analysis location record |
| `/api/gap-analysis/rankings/` | `GET` | Public / Bearer | Alias route for Gap Analysis Priority Rankings |
| `/api/priority-locations/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Priority Location CRUD ViewSet (`?department=...`, `?district=...`) |
| `/api/ddst/departments/` | `GET` | Public / Bearer | Line Department Metadata Directory for DDST/DDSS decision engine |
| `/api/ddst/department/{department_code}/dashboard/` | `GET` | Public / Bearer | Department-Specific Executive Decision Dashboard KPIs |
| `/api/ddst/dashboard/` | `GET` | Public / Bearer | District Magistrate Multi-Department Decision Matrix Dashboard |
| `/api/ddss/dashboard/` | `GET` | Public / Bearer | Alias route for DM Executive Decision Support System Dashboard |

### 16.4 Line Department Indicator, Workload & Sector Telemetry APIs
| Path | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/health/facilities/` | `GET` | Public / Bearer | Health Sector Facilities list (`?department=...`) |
| `/api/health/staffing/` | `GET` / `POST` / `PUT` | Public / Bearer | Health Department Staffing & Doctor/Nurse Vacancies Indicator |
| `/api/health/staffing/{id}/` | `GET` / `PUT` / `DELETE` | Public / Bearer | Health Staffing detail retrieve, update, or delete |
| `/api/health/human-resources/` | `GET` | Public / Bearer | Alias endpoint for Health Human Resources & Staffing |
| `/api/health/telemetry/` | `GET` | Public / Bearer | Alias endpoint for Health Infrastructure Telemetry |
| `/api/health/workload/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Health OPD/IPD Patient Workload Visits Indicator (`?period=...`) |
| `/api/health/workload/{id}/` | `GET` / `PUT` / `DELETE` | Public / Bearer | Health Workload detail retrieve, update, or delete |
| `/api/health/infrastructure/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Health ICU Beds & Oxygen Plant Infrastructure Indicator |
| `/api/health/infrastructure/{id}/` | `GET` / `PUT` / `DELETE` | Public / Bearer | Health Infrastructure detail retrieve, update, or delete |
| `/api/health/medicines/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Health Medicine Warehouse Stockout Indicator |
| `/api/health/medicines/{id}/` | `GET` / `PUT` / `DELETE` | Public / Bearer | Health Medicine Stock detail retrieve, update, or delete |
| `/api/medicines/` | `GET` | Public / Bearer | Alias endpoint for Health Medicine Stockouts |
| `/api/health/ambulances/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Health Emergency Ambulance Fleet Availability Indicator |
| `/api/health/ambulances/{id}/` | `GET` / `PUT` / `DELETE` | Public / Bearer | Health Ambulance detail retrieve, update, or delete |
| `/api/ambulances/` | `GET` | Public / Bearer | Alias endpoint for Ambulance Fleet Availability |
| `/api/health/vaccination/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Health Immunization & Vaccination Coverage Indicator |
| `/api/health/vaccination/{id}/` | `GET` / `PUT` / `DELETE` | Public / Bearer | Health Vaccination detail retrieve, update, or delete |
| `/api/vaccinations/` | `GET` | Public / Bearer | Alias endpoint for Vaccination Coverage |
| `/api/health/risk/` | `GET` | Public / Bearer | Health Epidemic & Disease Surveillance Risk Signal |
| `/api/disease-surveillance/` | `GET` | Public / Bearer | Alias endpoint for Disease Surveillance Risk |
| `/api/education/indicators/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Education Department Indicators (Teacher Vacancies %, Enrolment, Classrooms) |
| `/api/education/indicators/{id}/` | `GET` / `PUT` / `DELETE` | Public / Bearer | Education Indicator detail retrieve, update, or delete |
| `/api/education/schools/` | `GET` | Public / Bearer | Alias endpoint for Education School Indicators |
| `/api/education/telemetry/` | `GET` | Public / Bearer | Alias endpoint for Education Facility Telemetry |
| `/api/water/indicators/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Water Resources & JJM Indicators (Water Coverage %, Daily Hours, Non-Functional) |
| `/api/water/indicators/{id}/` | `GET` / `PUT` / `DELETE` | Public / Bearer | Water Indicator detail retrieve, update, or delete |
| `/api/water/schemes/` | `GET` | Public / Bearer | Alias endpoint for Water Har Ghar Nal Ka Jal Schemes |
| `/api/water/sources/` | `GET` | Public / Bearer | Alias endpoint for Water Sources Telemetry |
| `/api/water/telemetry/` | `GET` | Public / Bearer | Alias endpoint for Water Facility Telemetry |
| `/api/road/indicators/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Public Works Department Road Indicators (Unpaved %, Bridge Gap Count) |
| `/api/road/indicators/{id}/` | `GET` / `PUT` / `DELETE` | Public / Bearer | Road Indicator detail retrieve, update, or delete |
| `/api/pwd/indicators/` | `GET` | Public / Bearer | Alias endpoint for PWD Road Indicators |
| `/api/pwd/telemetry/` | `GET` | Public / Bearer | Alias endpoint for PWD Road Infrastructure Telemetry |
| `/api/urban/indicators/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Urban Development & Sanitation Indicators (Sewerage Coverage %, Waste Collection %) |
| `/api/urban/telemetry/` | `GET` | Public / Bearer | Alias endpoint for Urban Infrastructure Telemetry |
| `/api/ddst/indicators/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Universal Multi-Department Indicator API |
| `/api/ddst/indicators/{id}/` | `GET` / `PUT` / `DELETE` | Public / Bearer | Universal Department Indicator detail retrieve, update, or delete |
| `/api/forest/` | `GET` | Public / Bearer | Forest Cover & Environmental Greenery Data API |

### 16.5 Development Planning & DPR Proposal ERP APIs
| Path | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/planning/dashboard/` | `GET` | Public / Bearer | Development Planning ERP dashboard KPIs, suggested needs & DPR repository |
| `/api/proposals/` | `GET` / `POST` | Bearer | DPR Proposals CRUD list & create (filters: `department`, `district`, `status`, `stage`, `priority`, `block`, `search`) |
| `/api/proposal/` | `GET` / `POST` | Bearer | Alias endpoint for DPR Proposals |
| `/api/proposals/{id}/` | `GET` / `PUT` / `PATCH` / `DELETE` | Bearer | Proposal details retrieve, update, and soft delete |
| `/api/proposals/{id}/step2-survey-inspection/` | `POST` | Bearer | Step 2: Save Survey & Site Inspection notes and GIS coordinates |
| `/api/proposals/{id}/step3-technical-dpr/` | `POST` | Bearer | Step 3: Save Technical Scope and engineering specifications |
| `/api/proposals/{id}/step4-financial-estimation/` | `POST` | Bearer | Step 4: Save Financial Line Items and auto-compute Grand Total |
| `/api/proposals/{id}/step5-clearances/` | `POST` | Bearer | Step 5: Save Clearances checklist |
| `/api/proposals/{id}/step6-attachments/` | `POST` | Bearer | Step 6: Upload DPR drawings and attachments |
| `/api/proposals/{id}/submit/` | `POST` | Bearer | Step 7: Submit DPR proposal for review (`DRAFT_DPR` -> `PENDING_REVIEW`) |
| `/api/proposals/{id}/approve/` | `POST` | Bearer | Approve DPR proposal directly (`approval_mode = DIRECT`) |
| `/api/proposals/{id}/reject/` | `POST` | Bearer | Reject DPR proposal with review notes |
| `/api/proposals/{id}/sanction/` | `POST` | Bearer | Sanction proposal budget & issue sanction order |
| `/api/proposals/{id}/negotiation/` | `POST` | Bearer | Send DM / Dept Head negotiation counter-offer or accept/reject |
| `/api/proposals/{id}/negotiation-response/` | `POST` | Bearer | Respond to negotiation counter-offer |
| `/api/proposals/{id}/negotiations/` | `GET` | Bearer | Retrieve full multi-round negotiation history for proposal |
| `/api/proposal-negotiations/` | `GET` / `POST` | Bearer | Proposal negotiations CRUD ViewSet (`?proposal=<id>`) |
| `/api/proposals/{id}/release/` | `POST` | Bearer | Release proposal budget (One-Time `FULL` or `INSTALLMENT`-wise tranches) |
| `/api/proposals/{id}/releases/` | `GET` | Bearer | Retrieve full fund release tranches history with date & timestamp |
| `/api/proposal-releases/` | `GET` / `POST` | Bearer | Proposal fund releases CRUD ViewSet (`?proposal=<id>`) |

### 16.6 Project Execution, e-MB & Financial ERP APIs
| Path | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/projects/` | `GET` / `POST` | Bearer | Project Execution ERP CRUD list & create (filters: `department`, `district`, `status`, `risk`, `search`) |
| `/api/project/` | `GET` / `POST` | Bearer | Alias endpoint for Project Execution |
| `/api/projects/{id}/` | `GET` / `PUT` / `PATCH` / `DELETE` | Bearer | Project details retrieve, update, and soft/hard delete |
| `/api/projects/summary/` | `GET` | Bearer | Aggregate execution KPIs (running count, budget utilized, bill totals, net payable) |
| `/api/projects/{id}/sanction/` | `POST` | Bearer | Sanction project budget amount & issue sanction order number |
| `/api/projects/{id}/assign-work/` | `POST` | Bearer | Combined Work Assignment Action (Dept Officer + Engineer + Contractor) |
| `/api/projects/{id}/assign-officer/` | `POST` | Bearer | Level 1 Assignment Action (Dept Head -> Nodal Dept Officer) |
| `/api/projects/{id}/assign-engineer/` | `POST` | Bearer | Level 2 Assignment Action (Dept Officer -> Junior Engineer & Contractor) |
| `/api/projects/{id}/daily-progress/` | `POST` | Bearer | Log daily physical progress %, labour deployed, materials used, and site diary entry |
| `/api/projects/{id}/officer-review/` | `POST` | Bearer | Department Officer Field Work Review Action (`APPROVED` / `REJECTED`) |
| `/api/projects/{id}/verify-completion/` | `POST` | Bearer | Department Head Final Completion Verification & Project Completion |
| `/api/projects/{id}/expenditure/` | `POST` / `GET` | Bearer (Dept Officer) | Record & list verified expenditure / budget utilization transactions |
| `/api/projects/{id}/expenditure/{exp_id}/` | `GET` / `PUT` / `PATCH` / `DELETE` | Bearer (Dept Officer) | Retrieve, update, patch, or delete specific project expenditure item |
| `/api/projects/{id}/budget-utilization/` | `GET` | Bearer | Get complete budget utilization summary (sanctioned, released, utilized, remaining, %) |
| `/api/project-expenditures/` | `GET` / `POST` / `PUT` / `DELETE` | Bearer | Project Expenditures Standalone CRUD ViewSet (`?project=<id>`) |
| `/api/site-diaries/` | `GET` / `POST` | Bearer | Site Diary CRUD list and create |
| `/api/measurement-books/` | `GET` / `POST` | Bearer | Electronic Measurement Book (e-MB) CRUD list and create |
| `/api/bills/` | `GET` / `POST` | Bearer (DM/Dept Head) | Project Bills CRUD list and create (financial authorization workflow) |
| `/api/bills/{id}/` | `GET` / `PUT` / `PATCH` / `DELETE` | Bearer (DM/Dept Head) | Bill details retrieve, update, patch, or delete |
| `/api/execution-risks/` | `GET` / `POST` | Bearer | Execution Risk signals CRUD list and create |

### 16.7 State Governance Master Budget & Finance APIs
| Path | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/state-budget/summary/` | `GET` | Bearer (State Finance Admin) | Master State Governance Budget Dashboard Summary API (`?financial_year=...`, `?department=...`, `?district=...`, `?scheme=...`) |
| `/api/state-budget/` | `GET` | Bearer (State Finance Admin) | State Governance Budget overview list |
| `/api/state-budgets/` | `GET` / `POST` / `PUT` / `DELETE` | Bearer (State Finance Admin) | State Master Budget CRUD ViewSet |
| `/api/department-budgets/` | `GET` / `POST` / `PUT` / `DELETE` | Bearer (State Finance Admin) | Department Budget allocations, sanctions, and utilization CRUD |
| `/api/district-allocations/` | `GET` / `POST` / `PUT` / `DELETE` | Bearer (State Finance Admin) | District Budget allocations CRUD |
| `/api/schemes/` | `GET` / `POST` / `PUT` / `DELETE` | Bearer (State Finance Admin) | State & Central Schemes Master repository CRUD |
| `/api/financial-ledger/` | `GET` / `POST` / `PUT` / `DELETE` | Bearer (State Finance Admin) | Financial Ledger transaction entries CRUD |

### 16.8 Citizen Grievances, SLA Audit & Spatial Heatmap APIs
| Path | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
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
| `/api/department/{department_id}/complain/` | `POST` | Bearer / Public | Single complaint creation for specific department |
| `/api/department/{department_id}/complaints/` | `GET` | Bearer / Public | Complaints list for specific department |
| `/api/departments/{department_id}/complain/` | `POST` | Bearer / Public | Alias route for department complaint submission |

### 16.9 Citizen Perception Feedback & Analytics APIs
| Path | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/feedback/questions/` | `GET` / `POST` | Public / Bearer | Citizen Feedback Questions Directory |
| `/api/feedback/responses/` | `GET` / `POST` | Public / Bearer | Citizen Location Feedback Responses List & Create |
| `/api/feedback/aggregation/` | `GET` | Public / Bearer | Aggregated Feedback Ratings by Location & Block |
| `/api/feedback/analytics/` | `GET` | Public / Bearer | Dynamic Citizen Location Feedback Real-Time Analytics (`?start_date=...`, `?end_date=...`, `?department=...`) |

### 16.10 GIS Validation, Geotag Verification & Vector Layer APIs
| Path | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/gis/validate-coordinate/` | `POST` | Public / Bearer | Validate if coordinates (lat, lng) lie within Bihar/Nalanda bounds |
| `/api/gis/check-duplicate/` | `POST` | Public / Bearer | Check for existing duplicate spatial asset within buffer distance |
| `/api/evidence/verify-geotag/` | `POST` | Public / Bearer | Extract EXIF metadata & verify image geotag location |
| `/api/gis/catalog/` | `GET` | Public | List published GIS layer catalog (65 total layers) |
| `/api/gis/catalog-crud/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | GIS Catalog Entry CRUD ViewSet |
| `/api/gis/features/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Individual GIS Layer Features CRUD ViewSet (`?catalog_entry=...`, `?layer_name=...`) |
| `/api/gis/features/geojson/` | `GET` | Public | Export filtered GIS features as standard GeoJSON FeatureCollection |
| `/api/gis/features/bulk-create/` | `POST` | Public / Bearer | Bulk create GIS features for catalog entry |
| `/api/gis/layers/{layer_name}/` | `GET` | Public | Fetch vector layer GeoJSON by shapefile layer name |
| `/api/gis/upload-layer/` | `POST` | Bearer / Public | Upload shapefile `.zip` bundle & auto-ingest features |

### 16.11 Facilities Directory & SCD Type 2 Audit APIs
| Path | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/facilities/` | `GET` / `POST` | Public | Facilities directory list and create (Public `AllowAny` enabled for map display) |
| `/api/facilities/{id}/` | `GET` / `PUT` / `DELETE` | Public | Facility retrieve, update, delete |
| `/api/facilities/geojson/` | `GET` | Public | Export 73,400+ facilities as GeoJSON FeatureCollection |
| `/api/facilities/sync-gis/` | `POST` | Public / Bearer | Bulk sync GIS layer features into Facilities directory |
| `/api/facilities/{id}/history/` | `GET` | Public / Bearer | Audit version history viewer (SCD Type 2 snapshots) |
| `/api/asset-categories/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Asset Categories CRUD ViewSet |

### 16.12 Dashboards, Notifications, Reports & Spatial Entities APIs
| Path | Method | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/dashboards/citizen/` | `GET` | Bearer / Public | Citizen portal metrics summary |
| `/api/dashboards/department/` | `GET` | Bearer / Public | Department queue & SLA metrics |
| `/api/dashboards/officer/` | `GET` | Bearer / Public | Today's officer work queue |
| `/api/dashboards/district/` | `GET` | Bearer / Public | District-wide department & status metrics |
| `/api/dashboards/state/` | `GET` | Bearer / Public | District rankings comparison matrix |
| `/api/dashboards/` | `GET` / `POST` | Bearer / Public | Dashboards CRUD ViewSet |
| `/api/notifications/` | `GET` | Bearer | List dispatched notifications |
| `/api/reports/` | `GET` / `POST` | Bearer / Public | Enterprise Reports catalog list & create (filters: `category`, `department`) |
| `/api/reports/generate/` | `POST` | Bearer / Public | Generate on-demand report action (`sla_audit`, `asset_audit`, `grievance`, `workflow`) |
| `/api/reports/{id}/download/` | `GET` | Bearer / Public | Download generated PDF / CSV report document file |
| `/api/employees/` | `GET` / `POST` | Bearer / Public | Line Department Employee Directory CRUD list & create |
| `/api/employees/{id}/` | `GET` / `PUT` / `PATCH` / `DELETE` | Bearer / Public | Retrieve, update, patch, or delete employee profile |
| `/api/employees/invite/` | `POST` | Bearer / Public | Issue secure 7-day UUID onboarding invitation token |
| `/api/employees/accept-invite/` | `POST` | Public | Accept onboarding invitation, set password, and activate user account |
| `/api/departments/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Department Master CRUD ViewSet |
| `/api/department-officers/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Department Nodal Officers CRUD ViewSet |
| `/api/states/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | States Master CRUD ViewSet |
| `/api/districts/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Districts Master CRUD ViewSet |
| `/api/blocks/` | `GET` / `POST` / `PUT` / `DELETE` | Public / Bearer | Blocks Master CRUD ViewSet |