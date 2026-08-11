import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
# Safe GeoDjango spatial field import
try:
    from django.conf import settings
    from django.contrib.gis.gdal.libgdal import lgdal
    from django.contrib.gis.db import models as gis_models
    _ = gis_models.PointField
    HAS_GEODJANGO = bool(lgdal and "django.contrib.gis" in getattr(settings, "INSTALLED_APPS", []))
except Exception:
    HAS_GEODJANGO = False


def get_spatial_field(field_type="geometry"):
    """
    Returns spatial GeoDjango field if GDAL C-library is available,
    otherwise falls back to JSONField for local environments without GDAL binaries.
    """
    if HAS_GEODJANGO:
        if field_type == "point":
            return gis_models.PointField(srid=4326, null=True, blank=True, verbose_name="Point Geometry")
        elif field_type == "multipolygon":
            return gis_models.MultiPolygonField(srid=4326, null=True, blank=True, verbose_name="MultiPolygon Geometry")
        else:
            return gis_models.GeometryField(srid=4326, null=True, blank=True, verbose_name="Geometry Location")
    else:
        return models.JSONField(default=dict, blank=True, null=True, help_text="GeoJSON Spatial Data", verbose_name="Spatial GeoJSON Data")


# ==========================================
# 0. ABSTRACT BASE MODELS
# ==========================================


# ==========================================
# 1. ADMINISTRATIVE & MASTER HIERARCHY (mst_*)
# ==========================================

class State(models.Model):
    """State Master Entity (e.g., Bihar)."""
    name = models.CharField(max_length=150, unique=True, verbose_name="State Name")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "mst_state"
        verbose_name = "State"
        verbose_name_plural = "States"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

class District(models.Model):
    """District Master Entity (e.g., Nalanda). Includes MultiPolygon spatial boundary."""
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="districts", verbose_name="State")
    name = models.CharField(max_length=150, verbose_name="District Name")
    geom = get_spatial_field("multipolygon")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "mst_district"
        verbose_name = "District"
        verbose_name_plural = "Districts"
        unique_together = ["state", "name"]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.state.name})"


class SubDivision(models.Model):
    """Sub-Division Master Entity (e.g., Rajgir, Biharsharif)."""
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="subdivisions", verbose_name="District")
    name = models.CharField(max_length=150, verbose_name="SubDivision Name")
    geom = get_spatial_field("multipolygon")

    class Meta:
        db_table = "mst_subdivision"
        verbose_name = "Sub-Division"
        verbose_name_plural = "Sub-Divisions"
        unique_together = ["district", "name"]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} - {self.district.name}"


class Block(models.Model):
    """Block Master Entity."""
    subdivision = models.ForeignKey(SubDivision, on_delete=models.CASCADE, related_name="blocks", verbose_name="Sub-Division")
    name = models.CharField(max_length=150, verbose_name="Block Name")
    geom = get_spatial_field("multipolygon")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "mst_block"
        verbose_name = "Block"
        verbose_name_plural = "Blocks"
        unique_together = ["subdivision", "name"]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} Block"


class VillageWard(models.Model):
    """Village or Ward Master Entity."""
    block = models.ForeignKey(Block, on_delete=models.CASCADE, related_name="villages_wards", verbose_name="Block")
    name = models.CharField(max_length=150, verbose_name="Village/Ward Name")
    geom = get_spatial_field("multipolygon")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "mst_village_ward"
        verbose_name = "Village/Ward"
        verbose_name_plural = "Villages & Wards"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.block.name})"


class Department(models.Model):
    """Line Department Master Entity (e.g., Health, Water Resources, Education, Tourism, Solar)."""
    name = models.CharField(max_length=150, unique=True, verbose_name="Department Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "mst_department"
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class DepartmentOfficer(models.Model):
    """Department Officer Registry per Department."""
    user = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="officer_profile", verbose_name="User Account")
    name = models.CharField(max_length=150, default="", verbose_name="Officer Name")
    designation = models.CharField(max_length=150, verbose_name="Designation")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="officers", verbose_name="Department")
    email = models.EmailField(blank=True, null=True, verbose_name="Email Address")
    contact = models.CharField(max_length=200, blank=True, null=True, verbose_name="Contact Details / Phone")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "mst_data_custodian"
        verbose_name = "Department Officer"
        verbose_name_plural = "Department Officers"

    def __str__(self) -> str:
        return f"{self.name} ({self.designation}) - {self.department.name}"



class AssetCategory(models.Model):
    """Asset Category (e.g., Hospital, School, Waterbody, Solar Site). Contains JSON schema for dynamic fields."""
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="categories", null=True, blank=True, verbose_name="Department")
    catalog_entry = models.ForeignKey("GISCatalogEntry", on_delete=models.CASCADE, null=True, blank=True, related_name="categories", verbose_name="GIS Catalog Layer")
    name = models.CharField(max_length=150, verbose_name="Category Name")
    field_schema = models.JSONField(default=dict, blank=True, help_text="JSON Schema specifying custom fields for this category", verbose_name="Field Schema (JSONB)")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    class Meta:
        db_table = "mst_asset_category"
        verbose_name = "Asset Category"
        verbose_name_plural = "Asset Categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name




# ==========================================
# 2. RBAC & CUSTOM USER MODEL (rbac_*, mst_user)
# ==========================================

class RoleName(models.TextChoices):
    """System Fixed Roles."""
    CITIZEN = "CITIZEN", "Citizen"
    DISTRICT_COLLECTOR = "DISTRICT_COLLECTOR", "District Collector"
    DISTRICT_MAGISTRATE = "DISTRICT_MAGISTRATE", "District Magistrate (DM)"
    ADM = "ADM", "Additional District Magistrate (ADM)"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD", "Department Head"
    DEPARTMENT_OFFICER = "DEPARTMENT_OFFICER", "Department Officer"
    EXECUTIVE_ENGINEER = "EXECUTIVE_ENGINEER", "Executive / Assistant Engineer"
    FIELD_INSPECTOR = "FIELD_INSPECTOR", "Field Inspector / Junior Engineer"
    FIELD_SUPERVISOR = "FIELD_SUPERVISOR", "Field Supervisor"
    STATE_ADMIN = "STATE_ADMIN", "State Admin"


class ScopeLevel(models.TextChoices):
    """Scope Levels per Blueprint Section 9.1."""
    NATIONAL = "NATIONAL", "National Scope (All States/Districts)"
    STATE = "STATE", "State Scope (All Districts in State)"
    DISTRICT = "DISTRICT", "District Scope (Assigned District, All Depts)"
    DEPARTMENT = "DEPARTMENT", "Department Scope (Assigned District + Dept)"
    SELF = "SELF", "Self Scope (Own Submissions)"
    ANONYMOUS = "ANONYMOUS", "Public Read-Only"


class Role(models.Model):
    """
    Role definition for RBAC based on Blueprint Section 9.1 & 9.5.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Role Name")
    code = models.CharField(max_length=50, choices=RoleName.choices, unique=True, null=True, blank=True, verbose_name="Role Code")
    scope_level = models.CharField(max_length=20, choices=ScopeLevel.choices, default=ScopeLevel.DISTRICT, verbose_name="Scope Level")
    description = models.TextField(blank=True, verbose_name="Role Description")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "rbac_role"
        verbose_name = "RBAC Role"
        verbose_name_plural = "RBAC Roles"

    def __str__(self) -> str:
        return f"{self.name} ({self.scope_level})"


class Permission(models.Model):
    """Granular Permission resource and action."""
    resource = models.CharField(max_length=100, verbose_name="Resource (e.g. facility, proposal)")
    action = models.CharField(max_length=50, verbose_name="Action (e.g. create, read, approve)")
    description = models.TextField(blank=True, verbose_name="Permission Description")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "rbac_permission"
        verbose_name = "RBAC Permission"
        verbose_name_plural = "RBAC Permissions"
        unique_together = ["resource", "action"]

    def __str__(self) -> str:
        return f"{self.resource}:{self.action}"


class RolePermission(models.Model):
    """Mapping between Roles and Permissions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="permission_roles")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "rbac_role_permission"
        unique_together = ["role", "permission"]

    def __str__(self) -> str:
        return f"{self.role.name} -> {self.permission}"


class User(AbstractUser):
    """
    Custom Enterprise User Model (mst_user).
    Inherits AbstractUser and SoftDeleteModel (UUID primary key, created_at, updated_at).
    Supports Blueprint Roles & Multi-Tenancy Scoping (National, State, District, Department).
    """
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name="users", verbose_name="Assigned State")
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True, related_name="users", verbose_name="Assigned District")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="users", verbose_name="Assigned Department")
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name="users", verbose_name="Assigned Role")
    designation = models.CharField(max_length=150, blank=True, verbose_name="Official Designation")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Phone Number")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "mst_user"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        role_name = self.role.name if self.role else "No Role"
        return f"{self.username} [{role_name}] ({self.get_full_name() or self.email})"

    @property
    def is_national_admin(self) -> bool:
        return bool(self.role and self.role.scope_level == ScopeLevel.NATIONAL)

    @property
    def is_state_admin(self) -> bool:
        return bool(self.role and self.role.scope_level == ScopeLevel.STATE)

    @property
    def is_district_collector(self) -> bool:
        return bool(self.role and self.role.code == RoleName.DISTRICT_COLLECTOR)

    @property
    def is_adm(self) -> bool:
        return bool(self.role and self.role.code == RoleName.ADM)

    @property
    def is_department_officer(self) -> bool:
        return bool(self.role and self.role.code == RoleName.DEPARTMENT_OFFICER)

    @property
    def is_field_engineer(self) -> bool:
        return bool(self.role and self.role.code == RoleName.FIELD_ENGINEER_DEO)


class UserDistrictScope(models.Model):
    """User District Scope mapping for multi-district or multi-department access (e.g. ADM covering multiple districts)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="district_scopes")
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="user_scopes")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, related_name="user_scopes")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "rbac_user_district_scope"
        unique_together = ["user", "district", "department"]

    def __str__(self) -> str:
        return f"{self.user.username} -> {self.district.name}"


# ==========================================
# 3. ASSET & GIS FEATURE MODULE (ast_*)
# ==========================================

# class IngestionBatch(models.Model):
#     """Shapefile/CSV/Excel batch import tracking."""
#     source_type = models.CharField(max_length=50, verbose_name="Source Type (CSV, SHP, GeoJSON)")
#     status = models.CharField(max_length=50, default="PENDING", verbose_name="Batch Status")
#     uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="ingestion_batches")
#     total_records = models.IntegerField(default=0)
#     processed_records = models.IntegerField(default=0)

#     created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
#     updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

#     class Meta:
#         db_table = "ast_ingestion_batch"
#         verbose_name = "Ingestion Batch"
#         verbose_name_plural = "Ingestion Batches"

#     def __str__(self) -> str:
#         return f"Batch {self.id} ({self.source_type}) - {self.status}"


class Facility(models.Model):
    """
    Generic Facility / Asset GIS Model (ast_facility).
    Supports Health, Water, Education, Tourism, Solar & District Assets.
    Includes spatial geometry field (SRID 4326) and JSONB attributes + hazard safety flags.
    """
    name = models.CharField(max_length=255, verbose_name="Facility Name")
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="facilities", verbose_name="District")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="facilities", verbose_name="Department")
    category = models.ForeignKey(AssetCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="facilities", verbose_name="Category")
    catalog_entry = models.ForeignKey("GISCatalogEntry", on_delete=models.CASCADE, null=True, blank=True, related_name="facilities", verbose_name="GIS Catalog Layer")
    gis_feature = models.ForeignKey("GISLayerFeature", on_delete=models.CASCADE, null=True, blank=True, related_name="facilities", verbose_name="Source GIS Feature")
    attributes = models.JSONField(default=dict, blank=True, verbose_name="Dynamic Attributes (JSONB)")
    geom = get_spatial_field("geometry")
    hazard_safe = models.BooleanField(null=True, blank=True, verbose_name="Is Hazard Safe?")
    hazard_flags = models.JSONField(default=dict, blank=True, verbose_name="Hazard Exposure Flags (JSONB)")
    # ingestion_batch = models.ForeignKey(IngestionBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name="facilities")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "ast_facility"
        verbose_name = "Facility / Spatial Asset"
        verbose_name_plural = "Facilities & Spatial Assets"
        indexes = [
            models.Index(fields=["district", "department"]),
            models.Index(fields=["hazard_safe"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.department.name})"


class FacilityHistory(models.Model):
    """SCD Type 2 Version History for Facility updates."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="history_records")
    valid_from = models.DateTimeField(default=timezone.now, verbose_name="Valid From")
    valid_to = models.DateTimeField(null=True, blank=True, verbose_name="Valid To")
    snapshot = models.JSONField(default=dict, verbose_name="Facility State Snapshot (JSONB)")
   
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    class Meta:
        db_table = "ast_facility_history"
        verbose_name = "Facility History Record"
        verbose_name_plural = "Facility History Records"
        ordering = ["-valid_from"]

    def __str__(self) -> str:
        return f"History for {self.facility.name} at {self.valid_from}"




# ==========================================
# 10. COMPLAINT & GRIEVANCE MANAGEMENT MODULE (cmp_*)
# ==========================================

class ComplaintStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    ASSIGNED = "ASSIGNED", "Assigned"
    ACCEPTED = "ACCEPTED", "Accepted"
    INSPECTION_STARTED = "INSPECTION_STARTED", "Inspection Started"
    EVIDENCE_UPLOADED = "EVIDENCE_UPLOADED", "Evidence Uploaded"
    RESOLVED = "RESOLVED", "Resolved"
    CITIZEN_VERIFICATION = "CITIZEN_VERIFICATION", "Citizen Verification"
    CLOSED = "CLOSED", "Closed"
    REOPENED = "REOPENED", "Reopened"
    ESCALATED = "ESCALATED", "Escalated"
    TRANSFERRED = "TRANSFERRED", "Transferred"
    REJECTED = "REJECTED", "Rejected"


class ComplaintPriority(models.TextChoices):
    LOW = "LOW", "Low (72h SLA)"
    MEDIUM = "MEDIUM", "Medium (48h SLA)"
    HIGH = "HIGH", "High (24h SLA)"
    CRITICAL = "CRITICAL", "Critical (6h SLA)"


class ComplaintCategory(models.Model):
    """
    Defect / Complaint Categories mapping auto-routing targets and default SLAs.
    """
    name = models.CharField(max_length=150, unique=True, verbose_name="Category Name")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="complaint_categories", verbose_name="Auto-Route Department")
    default_priority = models.CharField(max_length=20, choices=ComplaintPriority.choices, default=ComplaintPriority.MEDIUM, verbose_name="Default Priority")
    default_sla_hours = models.IntegerField(default=24, verbose_name="Default SLA (Hours)")
    icon = models.CharField(max_length=50, default="fa-circle-exclamation", verbose_name="FontAwesome Icon")
    description = models.TextField(blank=True, verbose_name="Description")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cmp_category"
        verbose_name = "Complaint Category"
        verbose_name_plural = "Complaint Categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} -> {self.department.name} ({self.default_sla_hours}h SLA)"


class Complaint(models.Model):
    """
    Core Complaint / Grievance Record for NDIS Enterprise Grievance Management.
    """
    tracking_no = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="Tracking Number")
    title = models.CharField(max_length=255, verbose_name="Complaint Title")
    description = models.TextField(verbose_name="Detailed Description")
    
    # Auto-routing & Department/Role mapping
    category = models.ForeignKey(ComplaintCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, related_name="complaints", verbose_name="Responsible Department")
    
    # Assignees & Citizen
    citizen_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="submitted_complaints")
    citizen_name = models.CharField(max_length=150, blank=True, default="", verbose_name="Citizen Name")
    citizen_phone = models.CharField(max_length=20, blank=True, default="", verbose_name="Phone Number")
    citizen_email = models.EmailField(blank=True, null=True, verbose_name="Email Address")
    is_identity_masked = models.BooleanField(default=False, verbose_name="Mask Identity on Public Portals")
    
    assigned_officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_complaints", verbose_name="Assigned Department Officer / Engineer")
    assigned_inspector = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="inspected_complaints", verbose_name="Assigned Field Inspector")
    
    # Workflow State & Priority
    status = models.CharField(max_length=30, choices=ComplaintStatus.choices, default=ComplaintStatus.SUBMITTED, db_index=True, verbose_name="Status")
    priority = models.CharField(max_length=20, choices=ComplaintPriority.choices, default=ComplaintPriority.MEDIUM, verbose_name="Priority")
    sla_target_hours = models.IntegerField(default=24, verbose_name="SLA Target (Hours)")
    sla_deadline = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="SLA Deadline")
    is_sla_breached = models.BooleanField(default=False, db_index=True, verbose_name="SLA Breached Flag")
    
    # GIS Spatial Coordinates & Nearest Administrative Units
    latitude = models.FloatField(null=True, blank=True, verbose_name="Latitude")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Longitude")
    geom = get_spatial_field("point")
    
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints")
    subdivision = models.ForeignKey(SubDivision, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints")
    block = models.ForeignKey(Block, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints")
    village_ward = models.ForeignKey(VillageWard, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints")
    
    nearest_facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name="nearest_complaints")
    nearest_facility_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nearest Facility Name")
    nearest_facility_distance_m = models.FloatField(null=True, blank=True, verbose_name="Distance to Nearest Facility (Meters)")
    nearest_gis_feature = models.ForeignKey("GISLayerFeature", on_delete=models.SET_NULL, null=True, blank=True, related_name="nearest_complaints")
    
    # Resolution & Feedback Details
    resolution_summary = models.TextField(blank=True, null=True, verbose_name="Resolution Summary")
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="Rejection Reason")
    transfer_reason = models.TextField(blank=True, null=True, verbose_name="Transfer Reason")
    escalation_reason = models.TextField(blank=True, null=True, verbose_name="Escalation Reason")
    
    rating = models.IntegerField(null=True, blank=True, verbose_name="Citizen Feedback Rating (1-5)")
    feedback_comment = models.TextField(blank=True, null=True, verbose_name="Citizen Feedback Comment")
    
    # Timestamps
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cmp_complaint"
        verbose_name = "Complaint / Grievance"
        verbose_name_plural = "Complaints & Grievances"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "department"]),
            models.Index(fields=["assigned_officer", "status"]),
            models.Index(fields=["citizen_user"]),
        ]

    def __str__(self) -> str:
        return f"{self.tracking_no} - {self.title} [{self.status}]"


class ComplaintEvidence(models.Model):
    """
    Multiple evidence attachments (Photos, Videos, PDFs, Geotagged images).
    """
    EVIDENCE_STAGE_CHOICES = [
        ("SUBMISSION", "Citizen Submission"),
        ("INSPECTION", "Field Inspection"),
        ("RESOLUTION", "Resolution Verification"),
    ]
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="evidences")
    file = models.FileField(upload_to="complaints/evidence/%Y/%m/")
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50, default="IMAGE")
    stage = models.CharField(max_length=20, choices=EVIDENCE_STAGE_CHOICES, default="SUBMISSION")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    latitude = models.FloatField(null=True, blank=True, verbose_name="EXIF Geotag Latitude")
    longitude = models.FloatField(null=True, blank=True, verbose_name="EXIF Geotag Longitude")
    is_geotag_verified = models.BooleanField(default=True, verbose_name="Geotag Matches Pin Tolerance")
    distance_from_pin_m = models.FloatField(null=True, blank=True, verbose_name="Distance from Pin (Meters)")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "cmp_evidence"
        verbose_name = "Complaint Evidence"
        verbose_name_plural = "Complaint Evidences"

    def __str__(self) -> str:
        return f"Evidence for {self.complaint.tracking_no} ({self.file_name})"


class ComplaintTimeline(models.Model):
    """
    Audit timeline recording every status transition, assignment, inspection, and comment.
    """
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="timeline")
    action = models.CharField(max_length=50, verbose_name="Action Taken")
    from_status = models.CharField(max_length=30, blank=True, null=True)
    to_status = models.CharField(max_length=30, blank=True, null=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    performer_role = models.CharField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "cmp_timeline"
        verbose_name = "Complaint Timeline Event"
        verbose_name_plural = "Complaint Timeline Events"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.action} on {self.complaint.tracking_no} by {self.performed_by}"

# ==========================================
# 4. WORKFLOW & TRANSACTION MODULE (txn_*)
# ==========================================

class WorkflowInstance(models.Model):
    """Generic State Machine Workflow Instance."""
    workflow_type = models.CharField(max_length=100, verbose_name="Workflow Type (PROPOSAL, GRIEVANCE, ALERT)")
    current_state = models.CharField(max_length=100, default="DRAFT", verbose_name="Current State")
    sla_due_at = models.DateTimeField(null=True, blank=True, verbose_name="SLA Due At")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "txn_workflow_instance"
        verbose_name = "Workflow Instance"
        verbose_name_plural = "Workflow Instances"

    def __str__(self) -> str:
        return f"{self.workflow_type} ({self.current_state})"


class WorkflowTransition(models.Model):
    """Workflow state transition audit log."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow_instance = models.ForeignKey(WorkflowInstance, on_delete=models.CASCADE, related_name="transitions")
    from_state = models.CharField(max_length=100, verbose_name="From State")
    to_state = models.CharField(max_length=100, verbose_name="To State")
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True, verbose_name="Transition Remarks")
    transitioned_at = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "txn_workflow_transition"
        verbose_name = "Workflow Transition"
        verbose_name_plural = "Workflow Transitions"
        ordering = ["-transitioned_at"]

    def __str__(self) -> str:
        return f"{self.from_state} -> {self.to_state}"


class GapScore(models.Model):
    """Analytics Deficit / Gap Score per District & Department."""
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="gap_scores")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="gap_scores")
    score = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Gap Score Metric")
    computed_at = models.DateTimeField(default=timezone.now)
    metrics = models.JSONField(default=dict, blank=True, verbose_name="Detailed Metrics (JSONB)")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    
    class Meta:
        db_table = "anl_gap_score"
        verbose_name = "Analytics Gap Score"
        verbose_name_plural = "Analytics Gap Scores"

    def __str__(self) -> str:
        return f"Gap Score {self.score} ({self.district.name} - {self.department.name})"


class ProposalStatus(models.TextChoices):
    DEVELOPMENT_NEEDS = "DEVELOPMENT_NEEDS", "Development Needs"
    DRAFT_DPR = "DRAFT_DPR", "Draft DPR"
    PENDING_REVIEW = "PENDING_REVIEW", "Pending Review"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    APPROVED = "APPROVED", "Approved"
    SANCTIONED = "SANCTIONED", "Sanctioned"
    REJECTED = "REJECTED", "Rejected"
    IN_EXECUTION = "IN_EXECUTION", "In Execution"


class ProposalPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class ProposalStage(models.TextChoices):
    NEED_IDENTIFICATION = "1_NEED_IDENTIFICATION", "1. Need Identification"
    SURVEY_INSPECTION = "2_SURVEY_INSPECTION", "2. Survey & Inspection"
    TECHNICAL_DPR = "3_TECHNICAL_DPR", "3. Technical DPR"
    FINANCIAL_ESTIMATION = "4_FINANCIAL_ESTIMATION", "4. Financial Estimation"
    CLEARANCES = "5_CLEARANCES", "5. Clearances"
    ATTACHMENTS = "6_ATTACHMENTS", "6. Attachments"
    REVIEW_SUBMIT = "7_REVIEW_SUBMIT", "7. Review & Submit"


class FundingSource(models.TextChoices):
    DISTRICT = "District", "District"
    STATE = "State", "State"
    CENTRAL = "Central", "Central"
    CSR = "CSR", "CSR"
    WORLD_BANK = "World Bank", "World Bank"
    ADB = "ADB", "ADB"
    OTHER = "Other", "Other"


class Proposal(models.Model):
    """Department Development Proposal / Scheme Project Application (DPR Wizard ERP)."""
    proposal_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Proposal ID (e.g. PRP-2026-00104)")
    title = models.CharField(max_length=255, verbose_name="Proposal Title")
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name="proposals", verbose_name="State")
    category = models.CharField(max_length=150, default="Infrastructure", verbose_name="Proposal Category")
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="proposals", verbose_name="District")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="proposals", verbose_name="Department")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_proposals", verbose_name="Created By")
    
    workflow_instance = models.ForeignKey(WorkflowInstance, on_delete=models.SET_NULL, null=True, blank=True, related_name="proposals")
    gap_score_ref = models.ForeignKey(GapScore, on_delete=models.SET_NULL, null=True, blank=True, related_name="proposals")
    
    status = models.CharField(max_length=50, choices=ProposalStatus.choices, default=ProposalStatus.DRAFT_DPR, verbose_name="Proposal Status")
    stage = models.CharField(max_length=50, choices=ProposalStage.choices, default=ProposalStage.NEED_IDENTIFICATION, verbose_name="Current DPR Stage")
    priority = models.CharField(max_length=20, choices=ProposalPriority.choices, default=ProposalPriority.MEDIUM, verbose_name="Priority Level")

    # Step 1: Need Identification
    village = models.CharField(max_length=150, blank=True, null=True, verbose_name="Village")
    block = models.CharField(max_length=150, blank=True, null=True, verbose_name="Block (e.g. Silao)")
    ward = models.CharField(max_length=150, blank=True, null=True, verbose_name="Ward")
    population_impact = models.IntegerField(default=0, verbose_name="Population Impact")
    gap_score = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, verbose_name="Gap Score Metric")
    linked_complaint = models.ForeignKey(Complaint, on_delete=models.SET_NULL, null=True, blank=True, related_name="proposals", verbose_name="Linked Primary Complaint")
    linked_complaint_ids = models.JSONField(default=list, blank=True, verbose_name="Linked Complaint IDs")
    problem_statement = models.TextField(blank=True, null=True, verbose_name="Problem Statement and Reason")

    # Step 2: Survey & Inspection
    inspection_date = models.DateField(blank=True, null=True, verbose_name="Inspection Date")
    survey_team = models.CharField(max_length=255, blank=True, null=True, verbose_name="Survey Team (Officers/Engineers)")
    inspection_notes = models.TextField(blank=True, null=True, verbose_name="Inspection Notes / Existing Infrastructure")
    gis_reference = models.CharField(max_length=255, blank=True, null=True, verbose_name="GIS Reference (Selected site)")
    latitude = models.FloatField(blank=True, null=True, verbose_name="Site Latitude")
    longitude = models.FloatField(blank=True, null=True, verbose_name="Site Longitude")

    # Step 3: Technical DPR
    technical_scope = models.TextField(blank=True, null=True, verbose_name="Technical Scope & Execution Method")
    engineering_notes = models.TextField(blank=True, null=True, verbose_name="Engineering Notes & Dependencies")
    estimated_timeline = models.CharField(max_length=100, default="90 days", verbose_name="Estimated Timeline")

    # Step 4: Financial Estimation
    civil_works = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Civil Works (INR)")
    equipment_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Equipment Cost (INR)")
    electrical_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Electrical Cost (INR)")
    contingency_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Contingency Cost (INR)")
    maintenance_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Maintenance Cost (INR)")
    estimated_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Grand Total Estimated Cost (INR)")
    delegated_power_note = models.CharField(max_length=255, default="Within DM delegated power", verbose_name="Delegated Power Note")

    # Step 5: Clearances
    funding_source = models.CharField(max_length=150, choices=FundingSource.choices, default=FundingSource.DISTRICT, verbose_name="Funding Source")
    clearances_notes = models.TextField(blank=True, null=True, verbose_name="Clearances & NOCs Notes")
    clearances = models.JSONField(default=dict, blank=True, verbose_name="Departmental Clearances (JSONB)")

    # Step 6: Attachments
    attachments = models.JSONField(default=list, blank=True, verbose_name="Attached DPR Files & Drawings")

    # Step 7: Review, Submission & Approvals
    review_notes = models.TextField(blank=True, null=True, verbose_name="Reviewer Notes / Observations")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_proposals", verbose_name="Reviewed By")
    reviewed_at = models.DateTimeField(blank=True, null=True, verbose_name="Reviewed At")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_proposals", verbose_name="Approved By")
    approved_at = models.DateTimeField(blank=True, null=True, verbose_name="Approved At")

    is_deleted = models.BooleanField(default=False, verbose_name="Deleted")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Deleted At")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "txn_proposal"
        verbose_name = "Department Proposal"
        verbose_name_plural = "Department Proposals"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Auto-calculate Grand Total cost if individual line items exist
        computed_total = (self.civil_works or 0) + (self.equipment_cost or 0) + (self.electrical_cost or 0) + (self.contingency_cost or 0) + (self.maintenance_cost or 0)
        if computed_total > 0 and (self.estimated_cost == 0 or self.estimated_cost != computed_total):
            self.estimated_cost = computed_total

        # Auto-generate proposal_id if missing
        if not self.proposal_id:
            import datetime, random
            year = datetime.datetime.now().year
            rand_code = random.randint(10000, 99999)
            self.proposal_id = f"PRP-{year}-{rand_code}"
            
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.proposal_id or 'PRP'} - {self.title} ({self.status})"


class BudgetApproval(models.Model):
    """Budget sanction for approved proposals."""
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name="budget_approvals")
    approved_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Approved Amount (INR)")
    approved_via = models.CharField(max_length=150, verbose_name="Sanction Order Number / Path")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "txn_budget_approval"
        verbose_name = "Budget Approval"
        verbose_name_plural = "Budget Approvals"

    def __str__(self) -> str:
        return f"Sanction {self.approved_amount} for {self.proposal.title}"


# class Citizengrievance(models.Model):
#     """Citizen Public Grievance Submission."""
#     tracking_no = models.CharField(max_length=50, unique=True, verbose_name="Tracking Number")
#     facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name="grievances")
#     citizen_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="grievances")
#     citizen_name = models.CharField(max_length=150, verbose_name="Citizen Name")
#     citizen_phone = models.CharField(max_length=20, verbose_name="Phone Number")
#     workflow_instance = models.ForeignKey(WorkflowInstance, on_delete=models.SET_NULL, null=True, blank=True, related_name="grievances")
#     description = models.TextField(verbose_name="Grievance Description")
#     geom = get_spatial_field("point")
    
#     created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
#     updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    
#     is_deleted = models.BooleanField(default=False, verbose_name="Deleted")
#     deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Deleted At")
    
#     class Meta:
#         db_table = "txn_citizen_grievance"
#         verbose_name = "Citizen grievance"
#         verbose_name_plural = "Citizen grievances"

#     def __str__(self) -> str:
#         return f"Grievance {self.tracking_no} - {self.citizen_name}"


# ==========================================
# 5. DOCUMENT MANAGEMENT MODULE (doc_*)
# ==========================================

class DocumentFile(models.Model):
    """Document / Photo / Geo-tagged image attachment entity."""
    owner_type = models.CharField(max_length=100, verbose_name="Owner Entity Type (FACILITY, PROPOSAL, GRIEVANCE)")
    owner_id = models.UUIDField(verbose_name="Owner Record UUID")
    file = models.FileField(upload_to="documents/%Y/%m/", verbose_name="File Attachment")
    file_name = models.CharField(max_length=255, verbose_name="File Name")
    version = models.IntegerField(default=1, verbose_name="File Version")
    signature_ref = models.CharField(max_length=255, blank=True, verbose_name="Digital Signature Reference")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    
   
    
    class Meta:
        db_table = "doc_file"
        verbose_name = "Document File"
        verbose_name_plural = "Document Files"
        indexes = [
            models.Index(fields=["owner_type", "owner_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.file_name} (v{self.version})"


# ==========================================
# 6. NOTIFICATION MODULE (ntf_*)
# ==========================================

class NotificationTemplate(models.Model):
    """Multi-channel notification message template."""
    CHANNEL_CHOICES = [
        ("EMAIL", "Email"),
        ("SMS", "SMS"),
        ("WHATSAPP", "WhatsApp"),
        ("PUSH", "Push Notification"),
    ]
    name = models.CharField(max_length=150, verbose_name="Template Name")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="EMAIL")
    locale = models.CharField(max_length=10, default="EN", verbose_name="Locale (EN, HI)")
    body_template = models.TextField(verbose_name="Body Template Text")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    

    class Meta:
        db_table = "ntf_template"
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"

    def __str__(self) -> str:
        return f"{self.name} ({self.channel} - {self.locale})"


class NotificationDispatchLog(models.Model):
    """Log of dispatched notifications."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, default="DISPATCHED")
    dispatched_at = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "ntf_dispatch_log"
        verbose_name = "Notification Dispatch Log"
        verbose_name_plural = "Notification Dispatch Logs"
        ordering = ["-dispatched_at"]

    def __str__(self) -> str:
        return f"Notification to {self.user.username} - {self.status}"


# ==========================================
# 7. AUDIT LOGGING MODULE (aud_*)
# ==========================================

class AuditEventLog(models.Model):
    """Immutable Audit Event Log (polymorphic tracking)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=100, db_index=True, verbose_name="Target Entity Type")
    entity_id = models.UUIDField(db_index=True, verbose_name="Target Entity UUID")
    action = models.CharField(max_length=50, verbose_name="Action (CREATE, UPDATE, DELETE, APPROVE)")
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    before_state = models.JSONField(default=dict, blank=True, verbose_name="Before State (JSONB)")
    after_state = models.JSONField(default=dict, blank=True, verbose_name="After State (JSONB)")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "aud_event_log"
        verbose_name = "Audit Event Log"
        verbose_name_plural = "Audit Event Logs"
        ordering = ["-occurred_at"]

    def __str__(self) -> str:
        return f"{self.action} on {self.entity_type}:{self.entity_id} at {self.occurred_at}"


# ==========================================
# 8. ANALYTICS & DECISION SUPPORT (anl_*)
# ==========================================

class Recommendation(models.Model):
    """Spatial Decision Support System (SDSS) Recommendation Output."""
    gap_score = models.ForeignKey(GapScore, on_delete=models.CASCADE, related_name="recommendations")
    decision_class = models.CharField(max_length=150, verbose_name="Decision Class (e.g. Recommend PHC, Solar Site)")
    spatial_evidence = models.JSONField(default=dict, verbose_name="Linked Spatial Evidence (JSONB)")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "anl_recommendation"
        verbose_name = "SDSS Recommendation"
        verbose_name_plural = "SDSS Recommendations"

    def __str__(self) -> str:
        return f"Recommendation ({self.decision_class}) for GapScore {self.gap_score.id}"


# ==========================================
# 9. GIS CATALOG & DATA PROVENANCE (gis_*)
# ==========================================

class GISCatalogEntry(models.Model):
    """Geospatial Catalog Entry for thematic map layers."""
    layer_name = models.CharField(max_length=150, unique=True, verbose_name="Layer Name")
    geometry_type = models.CharField(max_length=50, verbose_name="Geometry Type (Point, Line, Polygon, Raster)")
    category = models.CharField(max_length=100, verbose_name="Category (Health, Water, Hazard, Landuse, Admin, Infra)")
    feature_count = models.IntegerField(default=0, verbose_name="Feature Count")
    is_published = models.BooleanField(default=True, verbose_name="Is Published to GeoServer?")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, null=True, blank=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="Updated At")

    class Meta:
        db_table = "gis_catalog_entry"
        verbose_name = "GIS Catalog Entry"
        verbose_name_plural = "GIS Catalog Entries"
        ordering = ["category", "layer_name"]

    def __str__(self) -> str:
        return f"{self.layer_name} ({self.geometry_type}) - {self.feature_count} features"


class GISLayerFeature(models.Model):
    """Individual spatial feature record belonging to a GIS Layer from imported Shapefiles."""
    catalog_entry = models.ForeignKey(GISCatalogEntry, on_delete=models.CASCADE, related_name="features", verbose_name="GIS Layer Catalog")
    feature_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Feature Identifier")
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Feature Name")
    properties = models.JSONField(default=dict, blank=True, verbose_name="Attributes (JSONB)")
    geom_geojson = models.JSONField(default=dict, blank=True, null=True, verbose_name="GeoJSON Geometry (WGS84 EPSG:4326)")
    geom = get_spatial_field("geometry")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "gis_layer_feature"
        verbose_name = "GIS Layer Feature"
        verbose_name_plural = "GIS Layer Features"
        indexes = [
            models.Index(fields=["catalog_entry"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return f"{self.name or 'Feature'} [{self.catalog_entry.layer_name}]"



class GISDatasetVersionHistory(models.Model):
    """Raster / Vector dataset version history."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    catalog_entry = models.ForeignKey(GISCatalogEntry, on_delete=models.CASCADE, related_name="versions")
    version_no = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "gis_dataset_version_history"
        verbose_name = "GIS Dataset Version History"
        verbose_name_plural = "GIS Dataset Version Histories"

    def __str__(self) -> str:
        return f"{self.catalog_entry.layer_name} v{self.version_no}"


class GISDataProvenance(models.Model):
    """Data provenance & source metadata for spatial datasets."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    catalog_entry = models.ForeignKey(GISCatalogEntry, on_delete=models.CASCADE, related_name="provenance")
    source = models.CharField(max_length=255, verbose_name="Data Source (NRSC, Bhuvan, ESA, USGS, Survey of India)")
    license = models.CharField(max_length=100, blank=True, verbose_name="Data License")
    metadata_json = models.JSONField(default=dict, blank=True, verbose_name="Metadata (JSONB)")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "gis_data_provenance"
        verbose_name = "GIS Data Provenance"
        verbose_name_plural = "GIS Data Provenances"

    def __str__(self) -> str:
        return f"Provenance for {self.catalog_entry.layer_name} ({self.source})"


class GISProcessingJob(models.Model):
    """Async GIS Processing Job (NDVI calculation, LULC classification, buffer analysis)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_type = models.CharField(max_length=100, verbose_name="Job Type")
    status = models.CharField(max_length=50, default="PENDING", verbose_name="Status")
    params = models.JSONField(default=dict, blank=True, verbose_name="Parameters (JSONB)")
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "gis_processing_job"
        verbose_name = "GIS Processing Job"
        verbose_name_plural = "GIS Processing Jobs"

    def __str__(self) -> str:
        return f"{self.job_type} Job ({self.status})"


# ==========================================
# 10. PROJECT EXECUTION ERP MODELS
# ==========================================

class ProjectStatus(models.TextChoices):
    PLANNING = "planning", "Planning"
    IN_EXECUTION = "in_execution", "In Execution"
    COMPLETED = "completed", "Completed"
    SUSPENDED = "suspended", "Suspended"
    HANDED_OVER = "handed_over", "Handed Over"


class RiskSeverity(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class ProjectExecution(models.Model):
    """Sanctioned Government Project Execution ERP Entity."""
    project_id = models.CharField(max_length=50, unique=True, verbose_name="Project ID (e.g. PRJ-2026-00103)")
    proposal = models.ForeignKey(Proposal, on_delete=models.SET_NULL, null=True, blank=True, related_name="execution_projects", verbose_name="Linked DPR Proposal")
    title = models.CharField(max_length=255, verbose_name="Project Name")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects", verbose_name="Department")
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects", verbose_name="District")
    block = models.CharField(max_length=150, blank=True, verbose_name="Block")
    ward = models.CharField(max_length=100, blank=True, verbose_name="Ward")
    contractor_name = models.CharField(max_length=200, blank=True, verbose_name="Contractor Name")
    proposed_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Proposed Budget (INR)")
    sanction_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Sanctioned Budget (INR)")
    expenditure_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Budget Utilized (INR)")
    sanction_order_no = models.CharField(max_length=100, blank=True, verbose_name="Sanction Order No")
    sanctioned_at = models.DateTimeField(null=True, blank=True, verbose_name="Sanctioned At")
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Progress %")
    status = models.CharField(max_length=50, choices=ProjectStatus.choices, default=ProjectStatus.IN_EXECUTION, verbose_name="Execution Status")
    risk_level = models.CharField(max_length=20, choices=RiskSeverity.choices, default=RiskSeverity.LOW, verbose_name="Risk Level")
    inspection_due = models.BooleanField(default=False, verbose_name="Inspection Due")
    inspection_due_date = models.DateField(null=True, blank=True, verbose_name="Inspection Due Date")
    start_date = models.DateField(null=True, blank=True, verbose_name="Start Date")
    target_completion_date = models.DateField(null=True, blank=True, verbose_name="Target Completion Date")
    actual_completion_date = models.DateField(null=True, blank=True, verbose_name="Actual Completion Date")
    created_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_projects", verbose_name="Created By")
    is_deleted = models.BooleanField(default=False, verbose_name="Is Deleted")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "prj_project_execution"
        verbose_name = "Project Execution"
        verbose_name_plural = "Project Executions"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.project_id} - {self.title}"


def get_today_date():
    return timezone.now().date()


class SiteDiary(models.Model):
    """Daily Site Progress & Engineer Notes Log."""
    project = models.ForeignKey(ProjectExecution, on_delete=models.CASCADE, related_name="site_diaries", verbose_name="Project")
    log_date = models.DateField(default=get_today_date, verbose_name="Log Date")
    work_description = models.TextField(verbose_name="Engineer Notes / Work Executed")
    labour_count = models.IntegerField(default=0, verbose_name="Labour Count")
    materials_used = models.TextField(blank=True, verbose_name="Materials Used")
    weather_condition = models.CharField(max_length=100, default="Sunny", verbose_name="Weather Condition")
    progress_logged = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Progress % Logged")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name="Latitude")
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name="Longitude")
    logged_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="site_logs", verbose_name="Logged By")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "prj_site_diary"
        verbose_name = "Site Diary Log"
        verbose_name_plural = "Site Diary Logs"
        ordering = ["-log_date", "-created_at"]

    def __str__(self) -> str:
        return f"Log {self.log_date} - {self.project.project_id}"


class MeasurementBook(models.Model):
    """Government Measurement Book (MB) Verification Entries."""
    mb_number = models.CharField(max_length=50, unique=True, verbose_name="MB Entry Number")
    project = models.ForeignKey(ProjectExecution, on_delete=models.CASCADE, related_name="measurement_entries", verbose_name="Project")
    item_description = models.TextField(verbose_name="Quantity / Work Item Description")
    unit = models.CharField(max_length=50, default="Cum", verbose_name="Unit of Measurement")
    estimated_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0.000, verbose_name="Estimated Quantity")
    quantity_measured = models.DecimalField(max_digits=12, decimal_places=3, default=0.000, verbose_name="Quantity Measured / Executed")
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Rate per Unit (INR)")
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Total Valuation (INR)")
    measurement_date = models.DateField(default=get_today_date, verbose_name="Measurement Date")
    measured_by = models.CharField(max_length=150, blank=True, verbose_name="Measured By (Junior Engineer)")
    verified_by = models.CharField(max_length=150, blank=True, verbose_name="Verified By (Executive Engineer)")
    status = models.CharField(max_length=50, default="submitted", verbose_name="Verification Status")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "prj_measurement_book"
        verbose_name = "Measurement Book Entry"
        verbose_name_plural = "Measurement Book Entries"
        ordering = ["-measurement_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.mb_number} - {self.project.project_id}"


class ProjectBill(models.Model):
    """Running Account (RA) Bills & Payment Tracking."""
    bill_number = models.CharField(max_length=50, unique=True, verbose_name="Bill Number")
    project = models.ForeignKey(ProjectExecution, on_delete=models.CASCADE, related_name="bills", verbose_name="Project")
    bill_type = models.CharField(max_length=50, default="RA_BILL", verbose_name="Bill Type (RA / Advance / Final)")
    claimed_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Claimed Amount (INR)")
    verified_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Verified Amount (INR)")
    deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Deductions (TDS/Security) (INR)")
    net_payable_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Net Payable Amount (INR)")
    submission_date = models.DateField(default=get_today_date, verbose_name="Submission Date")
    payment_status = models.CharField(max_length=50, default="submitted", verbose_name="Payment Status")
    payment_date = models.DateField(null=True, blank=True, verbose_name="Payment Date")
    transaction_reference = models.CharField(max_length=100, blank=True, verbose_name="PFMS / Treasury Reference")
    remarks = models.TextField(blank=True, verbose_name="Remarks / Observations")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "prj_project_bill"
        verbose_name = "Project Bill & Payment"
        verbose_name_plural = "Project Bills & Payments"
        ordering = ["-submission_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.bill_number} - {self.project.project_id}"


class ExecutionRisk(models.Model):
    """Execution Risk Center - Schedule, Budget & Quality Risk Signals."""
    project = models.ForeignKey(ProjectExecution, on_delete=models.CASCADE, related_name="risk_signals", verbose_name="Project")
    risk_type = models.CharField(max_length=100, default="schedule_delay", verbose_name="Risk Category")
    severity = models.CharField(max_length=20, choices=RiskSeverity.choices, default=RiskSeverity.MEDIUM, verbose_name="Severity")
    risk_signal = models.TextField(verbose_name="Risk Signal / Issue Statement")
    recommendation = models.TextField(verbose_name="Recommendation / Mitigation Plan")
    status = models.CharField(max_length=50, default="active", verbose_name="Risk Status")
    reported_at = models.DateTimeField(default=timezone.now, verbose_name="Reported At")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "prj_execution_risk"
        verbose_name = "Execution Risk Signal"
        verbose_name_plural = "Execution Risk Signals"
        ordering = ["-reported_at"]

    def __str__(self) -> str:
        return f"Risk [{self.severity}] - {self.project.project_id}"


class ReportCategory(models.TextChoices):
    SLA_AUDIT = "SLA Audit", "SLA Audit"
    ASSET_AUDIT = "Asset Audit", "Asset Audit"
    GRIEVANCE_LOG = "Grievance Log", "Grievance Log"
    WORKFLOW_AUDIT = "Workflow Audit", "Workflow Audit"


class Report(models.Model):
    """Report Generation & Export Center Model."""
    code = models.CharField(max_length=50, unique=True, verbose_name="Report Code (e.g. REP-001)")
    title = models.CharField(max_length=255, verbose_name="Report Title")
    category = models.CharField(max_length=50, choices=ReportCategory.choices, default=ReportCategory.SLA_AUDIT, verbose_name="Category")
    file = models.FileField(upload_to="reports/", null=True, blank=True, verbose_name="Report File")
    file_size_str = models.CharField(max_length=50, default="2.4 MB", verbose_name="File Size (e.g. 2.4 MB)")
    download_format = models.CharField(max_length=20, default="PDF", verbose_name="Format (PDF/CSV)")

    generated_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Generated Date")
    generated_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_reports", verbose_name="Generated By")

    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports", verbose_name="District")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports", verbose_name="Department")

    class Meta:
        db_table = "rpt_report"
        verbose_name = "Report"
        verbose_name_plural = "Reports"
        ordering = ["code", "-generated_at"]

    def __str__(self) -> str:
        return f"{self.code} - {self.title}"


class EmployeeStatus(models.TextChoices):
    INVITED = "invited", "Invited"
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"


class EmployeeInvitationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    EXPIRED = "expired", "Expired"
    CANCELLED = "cancelled", "Cancelled"


class Employee(models.Model):
    """
    Employee Profile Model per enterprise architecture rules.
    Links 1-to-1 to User (User -> Role -> Permissions is authoritative).
    """
    user = models.OneToOneField("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="employee_profile")
    employee_code = models.CharField(max_length=50, unique=True, verbose_name="Employee Code (e.g. GOV-100101)")

    full_name = models.CharField(max_length=255, verbose_name="Full Name")
    email = models.EmailField(unique=True, verbose_name="Official Email")
    designation = models.CharField(max_length=100, verbose_name="Designation")

    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, related_name="employees")
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name="employees")
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True, related_name="employees")

    office = models.CharField(max_length=255, null=True, blank=True, default="District Water Office")
    block = models.CharField(max_length=100, null=True, blank=True, default="Silao")

    reports_to = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="subordinates")

    status = models.CharField(max_length=20, choices=EmployeeStatus.choices, default=EmployeeStatus.INVITED)
    invited_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "emp_employee"
        verbose_name = "Employee Profile"
        verbose_name_plural = "Employee Profiles"
        ordering = ["employee_code", "-created_at"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.employee_code})"

    @property
    def role(self):
        """Authoritative RBAC Role comes from User -> Role."""
        return self.user.role if (self.user and hasattr(self.user, 'role')) else None

    @property
    def role_name(self) -> str:
        """Authoritative Role Name from User -> Role."""
        if self.user and self.user.role:
            return self.user.role.name
        # Fallback for pending invitation
        inv = getattr(self, 'invitation', None)
        if inv and inv.role:
            return inv.role.name
        return "Department Officer"


class EmployeeInvitation(models.Model):
    """
    Employee Secure Invitation Lifecycle Model.
    Tracks token, recipient email, assigned RBAC role, status and timestamps.
    """
    token = models.CharField(max_length=100, unique=True, default=uuid.uuid4, db_index=True)
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="invitation")
    email = models.EmailField()
    role = models.ForeignKey("Role", on_delete=models.CASCADE, related_name="invitations")
    invited_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_invitations")

    status = models.CharField(max_length=20, choices=EmployeeInvitationStatus.choices, default=EmployeeInvitationStatus.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "emp_invitation"
        verbose_name = "Employee Invitation"
        verbose_name_plural = "Employee Invitations"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Invitation for {self.email} [{self.status}] (Role: {self.role.name})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at


