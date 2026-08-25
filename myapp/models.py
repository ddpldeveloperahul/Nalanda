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
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Department Code")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    is_line_department = models.BooleanField(default=True, verbose_name="Is Line Department")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "mst_department"
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.code and self.name:
            import re
            cleaned = re.sub(r'[^A-Z0-9_]', '', self.name.upper().replace(' ', '_').replace('&', 'AND'))
            self.code = cleaned[:50]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} ({self.code or 'N/A'})"


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
    STATE_SUPER_ADMIN = "STATE_SUPER_ADMIN", "State Super Admin"
    STATE_ADMIN = "STATE_ADMIN", "State Admin"
    STATE_FINANCE_ADMIN = "STATE_FINANCE_ADMIN", "State Finance Admin"
    STATE_DEPARTMENT_ADMIN = "STATE_DEPARTMENT_ADMIN", "State Department Admin"
    STATE_MONITORING_OFFICER = "STATE_MONITORING_OFFICER", "State Monitoring Officer"
    STATE_GIS_ADMIN = "STATE_GIS_ADMIN", "State GIS Admin"
    SYSTEM_ADMINISTRATOR = "SYSTEM_ADMINISTRATOR", "System Administrator"



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


class PasswordResetOTP(models.Model):
    """
    OTP storage for User Password Reset requests.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_otps")
    email = models.EmailField(db_index=True)
    otp = models.CharField(max_length=10)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "auth_password_reset_otp"
        verbose_name = "Password Reset OTP"
        verbose_name_plural = "Password Reset OTPs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"OTP for {self.email} ({self.otp}) - Used: {self.is_used}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at


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
    UNDER_NEGOTIATION = "UNDER_NEGOTIATION", "Under Negotiation"
    APPROVED = "APPROVED", "Approved"
    SANCTIONED = "SANCTIONED", "Sanctioned"
    PARTIALLY_RELEASED = "PARTIALLY_RELEASED", "Partially Released"
    FUNDS_RELEASED = "FUNDS_RELEASED", "Funds Released"
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

    approval_mode = models.CharField(
        max_length=20,
        choices=[
            ("DIRECT", "Direct Approval"),
            ("NEGOTIATED", "Negotiated Approval"),
        ],
        null=True,
        blank=True,
        verbose_name="Approval Mode",
    )

    agreed_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Agreed Amount (INR)",
    )

    agreed_timeline_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Agreed Timeline (Days)",
    )

    agreed_scope = models.TextField(
        null=True,
        blank=True,
        verbose_name="Agreed Scope",
    )

    released_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="Cumulative Released Amount (INR)",
    )

    release_status = models.CharField(
        max_length=30,
        choices=[
            ("NOT_RELEASED", "Not Released"),
            ("PARTIALLY_RELEASED", "Partially Released"),
            ("FULLY_RELEASED", "Fully Released"),
        ],
        default="NOT_RELEASED",
        verbose_name="Fund Release Status",
    )

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
        self.sync_execution_project()

    def sync_execution_project(self):
        try:
            from myapp.models import ProjectExecution, ProjectStatus, ProposalStatus
            allowed_statuses = [
                ProposalStatus.SANCTIONED,
                ProposalStatus.APPROVED,
                ProposalStatus.PARTIALLY_RELEASED,
                ProposalStatus.FUNDS_RELEASED,
                ProposalStatus.IN_EXECUTION,
                "SANCTIONED",
                "APPROVED",
                "PARTIALLY_RELEASED",
                "FUNDS_RELEASED",
                "IN_EXECUTION",
            ]
            if self.status not in allowed_statuses:
                ProjectExecution.objects.filter(proposal=self).delete()
                return None

            proj = ProjectExecution.objects.filter(proposal=self).first()
            p_id = f"PRJ-{self.proposal_id.replace('PRP-', '')}" if self.proposal_id else f"PRJ-2026-{self.id:05d}"
            
            if not proj:
                if ProjectExecution.objects.filter(project_id=p_id).exists():
                    p_id = f"PRJ-2026-{self.id:05d}"
                proj = ProjectExecution.objects.create(
                    proposal=self,
                    project_id=p_id,
                    title=self.title or "Proposal Project",
                    department=self.department,
                    district=self.district,
                    block=self.block or "",
                    ward=self.ward or "",
                    proposed_amount=self.agreed_amount or self.estimated_cost or 0,
                    sanction_amount=self.agreed_amount or self.estimated_cost or 0,
                    status=ProjectStatus.IN_EXECUTION,
                    created_by=self.created_by,
                )
            else:
                proj.title = self.title or proj.title
                proj.department = self.department or proj.department
                proj.district = self.district or proj.district
                if self.block:
                    proj.block = self.block
                if self.ward:
                    proj.ward = self.ward
                eff_cost = self.agreed_amount or self.estimated_cost
                if eff_cost and eff_cost > 0:
                    proj.proposed_amount = eff_cost
                    if not proj.sanction_amount or proj.sanction_amount == 0:
                        proj.sanction_amount = eff_cost
                proj.save()
            return proj
        except Exception:
            return None

    def __str__(self) -> str:
        return f"{self.proposal_id or 'PRP'} - {self.title} ({self.status})"


class ProposalNegotiation(models.Model):
    """
    Stores negotiation/counter-offer history for a Proposal.

    Actions: COUNTER_OFFER, ACCEPT, REJECT, WITHDRAW
    Statuses: OPEN, COUNTERED, ACCEPTED, REJECTED, WITHDRAWN
    """

    ACTION_CHOICES = [
        ("COUNTER_OFFER", "Counter Offer"),
        ("ACCEPT", "Accept"),
        ("REJECT", "Reject"),
        ("WITHDRAW", "Withdraw"),
    ]

    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("COUNTERED", "Countered"),
        ("ACCEPTED", "Accepted"),
        ("REJECTED", "Rejected"),
        ("WITHDRAWN", "Withdrawn"),
    ]

    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.CASCADE,
        related_name="negotiations",
        verbose_name="Proposal",
    )

    proposed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposal_negotiations",
        verbose_name="Proposed By",
    )

    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        default="COUNTER_OFFER",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="OPEN",
    )

    negotiation_round = models.PositiveIntegerField(
        default=1,
        verbose_name="Negotiation Round Number",
    )

    proposed_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Proposed Amount",
    )

    proposed_timeline_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Proposed Timeline (Days)",
    )

    proposed_scope = models.TextField(
        null=True,
        blank=True,
        verbose_name="Proposed Scope",
    )

    remarks = models.TextField(
        blank=True,
        default="",
        verbose_name="Remarks",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "txn_proposal_negotiation"
        ordering = ["created_at"]

    def __str__(self):
        return (
            f"{self.proposal.proposal_id or 'PRP'} - Round {self.negotiation_round} - "
            f"{self.action} - {self.status} - "
            f"₹{self.proposed_amount or 0}"
        )


class ProposalFundRelease(models.Model):
    """
    Stores Fund Release Tranches / Installments for a Proposal.
    Supports both One-Time Full Release and Installment-wise Release.
    """

    RELEASE_TYPE_CHOICES = [
        ("FULL", "One-Time Full Release"),
        ("INSTALLMENT", "Installment-wise Release"),
    ]

    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.CASCADE,
        related_name="fund_releases",
        verbose_name="Proposal",
    )

    release_type = models.CharField(
        max_length=20,
        choices=RELEASE_TYPE_CHOICES,
        default="FULL",
        verbose_name="Release Type",
    )

    installment_number = models.PositiveIntegerField(
        default=1,
        verbose_name="Installment Number",
    )

    installment_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        verbose_name="Installment Name / Tranche",
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Released Amount (INR)",
    )

    release_order_no = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Release Order Number",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description / Remarks",
    )

    released_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="released_proposal_funds",
        verbose_name="Released By",
    )

    released_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Released At",
    )

    class Meta:
        db_table = "txn_proposal_fund_release"
        ordering = ["installment_number", "released_at"]

    def __str__(self):
        return (
            f"{self.proposal.proposal_id or 'PRP'} - "
            f"Installment {self.installment_number} - "
            f"₹{self.amount:,.2f}"
        )


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


from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=GISLayerFeature)
@receiver(post_delete, sender=GISLayerFeature)
def sync_catalog_feature_count(sender, instance, **kwargs):
    if instance and getattr(instance, "catalog_entry_id", None):
        try:
            catalog = instance.catalog_entry
            if catalog:
                real_count = catalog.features.count()
                if catalog.feature_count != real_count:
                    catalog.feature_count = real_count
                    catalog.save(update_fields=["feature_count", "updated_at"])
        except Exception:
            pass




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

    # Work Assignment Fields (Tier 1: Dept Head -> Dept Officer | Tier 2: Dept Officer -> Engineer/JE)
    assigned_officer = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_officer_projects", verbose_name="Assigned Department Officer")
    assigned_engineer = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_engineer_projects", verbose_name="Assigned Engineer")
    assigned_at = models.DateTimeField(null=True, blank=True, verbose_name="Work Assigned At")
    officer_assigned_at = models.DateTimeField(null=True, blank=True, verbose_name="Officer Assigned At")
    engineer_assigned_at = models.DateTimeField(null=True, blank=True, verbose_name="Engineer Assigned At")
    assignment_notes = models.TextField(blank=True, null=True, verbose_name="Department Head Assignment Notes")
    field_assignment_notes = models.TextField(blank=True, null=True, verbose_name="Field Engineer Assignment Notes")

    # Department Officer Review Fields
    officer_review_status = models.CharField(max_length=30, blank=True, null=True, choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")], verbose_name="Officer Review Status")
    officer_reviewed_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="officer_reviewed_projects", verbose_name="Officer Reviewed By")
    officer_reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Officer Reviewed At")
    officer_review_remarks = models.TextField(blank=True, null=True, verbose_name="Officer Review Remarks")

    # Department Head Completion Verification Fields
    completion_verification_status = models.CharField(max_length=30, blank=True, null=True, choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")], verbose_name="Completion Verification Status")
    completion_verified_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True, related_name="completion_verified_projects", verbose_name="Completion Verified By")
    completion_verified_at = models.DateTimeField(null=True, blank=True, verbose_name="Completion Verified At")
    completion_verification_remarks = models.TextField(blank=True, null=True, verbose_name="Completion Verification Remarks")

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


class ProjectExpenditure(models.Model):
    """
    Tracks verified expenditure transactions logged by Department Officers against Project Execution.
    Supports budget utilization audit trail and remaining budget calculation.
    """
    EXPENSE_TYPE_CHOICES = [
        ("CIVIL_WORK", "Civil Work"),
        ("ELECTRICAL_WORK", "Electrical Work"),
        ("EQUIPMENT", "Equipment & Machinery"),
        ("MATERIAL", "Material Supply"),
        ("LABOUR", "Labour & Manpower"),
        ("MISC", "Miscellaneous"),
    ]

    project = models.ForeignKey(
        ProjectExecution,
        on_delete=models.CASCADE,
        related_name="expenditures",
        verbose_name="Project Execution",
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Expenditure Amount (INR)",
    )

    expenditure_date = models.DateField(
        default=get_today_date,
        verbose_name="Expenditure Date",
    )

    expense_type = models.CharField(
        max_length=50,
        choices=EXPENSE_TYPE_CHOICES,
        default="CIVIL_WORK",
        verbose_name="Expense Type",
    )

    reference_no = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Reference Order / Voucher Number",
    )

    remarks = models.TextField(
        blank=True,
        default="",
        verbose_name="Verification Remarks",
    )

    verified_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_project_expenditures",
        verbose_name="Verified By (Department Officer)",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Recorded At",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
    )

    class Meta:
        db_table = "prj_project_expenditure"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project.project_id} - {self.reference_no} - ₹{self.amount:,.2f}"


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


# ==========================================
# STATE GOVERNANCE BUDGET & FINANCE MODULE
# ==========================================

class StateBudget(models.Model):
    """
    State Governance Master Budget Model for Annual Budget Provision, Authorizations & Releases.
    Traceable to the Financial Ledger.
    """
    financial_year = models.CharField(max_length=20, default="2026-27", verbose_name="Financial Year (e.g. 2026-27)")
    total_state_budget_cr = models.DecimalField(max_digits=14, decimal_places=2, default=4800.00, verbose_name="Total State Budget (₹ Cr)")
    department_allocation_cr = models.DecimalField(max_digits=14, decimal_places=2, default=4600.00, verbose_name="Department Allocation (₹ Cr)")
    district_allocation_cr = models.DecimalField(max_digits=14, decimal_places=2, default=899.00, verbose_name="District Allocation (₹ Cr)")
    total_sanctioned_cr = models.DecimalField(max_digits=14, decimal_places=2, default=4.00, verbose_name="Total Sanctioned (₹ Cr)")
    total_released_cr = models.DecimalField(max_digits=14, decimal_places=2, default=3900.00, verbose_name="Total Released (₹ Cr)")
    total_committed_cr = models.DecimalField(max_digits=14, decimal_places=2, default=3200.00, verbose_name="Total Committed (₹ Cr)")
    total_utilized_cr = models.DecimalField(max_digits=14, decimal_places=2, default=2850.00, verbose_name="Total Utilized (₹ Cr)")
    available_balance_cr = models.DecimalField(max_digits=14, decimal_places=2, default=4596.00, verbose_name="Available Balance (₹ Cr)")
    unreleased_balance_cr = models.DecimalField(max_digits=14, decimal_places=2, default=4.00, verbose_name="Unreleased Balance (₹ Cr)")

    active_projects_count = models.IntegerField(default=10, verbose_name="Active Projects Count")
    at_risk_projects_count = models.IntegerField(default=4, verbose_name="At Risk Projects Count")
    pending_approvals_count = models.IntegerField(default=4, verbose_name="Pending Approvals Count")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fin_state_budget"
        verbose_name = "State Master Budget"
        verbose_name_plural = "State Master Budgets"

    @property
    def available_balance(self):
        tot = self.total_state_budget_cr or 0
        dept = self.department_allocation_cr or 0
        return tot - dept

    def save(self, *args, **kwargs):
        if self.total_state_budget_cr is not None and self.department_allocation_cr is not None:
            self.available_balance_cr = self.total_state_budget_cr - self.department_allocation_cr
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"State Budget FY {self.financial_year} (₹{self.total_state_budget_cr} Cr)"


class DepartmentBudget(models.Model):
    """
    Department-wise Budget Allocation, Sanction, Release & Utilization.
    """
    financial_year = models.CharField(max_length=20, default="2026-27")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="state_budgets")
    authorized_budget_cr = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Authorized Budget (₹ Cr)")
    sanctioned_budget_cr = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Sanctioned Budget (₹ Cr)")
    released_budget_cr = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Released Budget (₹ Cr)")
    committed_budget_cr = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Committed Budget (₹ Cr)")
    utilized_budget_cr = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Utilized Budget (₹ Cr)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fin_department_budget"
        verbose_name = "Department Budget"
        verbose_name_plural = "Department Budgets"
        unique_together = ("department", "financial_year")

    def __str__(self) -> str:
        return f"{self.department.name} - FY {self.financial_year} (₹{self.authorized_budget_cr} Cr)"

    @property
    def utilization_percentage(self) -> float:
        if self.released_budget_cr and self.released_budget_cr > 0:
            return round(float(self.utilized_budget_cr / self.released_budget_cr) * 100, 1)
        if self.authorized_budget_cr and self.authorized_budget_cr > 0:
            return round(float(self.utilized_budget_cr / self.authorized_budget_cr) * 100, 1)
        return 0.0


class DistrictAllocation(models.Model):
    """
    District-wise Allocation & Financial Release Breakdown across Departments.
    """
    financial_year = models.CharField(max_length=20, default="2026-27")
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="state_allocations")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="district_allocations")
    allocation_amount_cr = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Allocation Amount (₹ Cr)")
    sanctioned_amount_cr = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Sanctioned Amount (₹ Cr)")
    utilized_amount_cr = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Utilized Amount (₹ Cr)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fin_district_allocation"
        verbose_name = "District Budget Allocation"
        verbose_name_plural = "District Budget Allocations"

    def __str__(self) -> str:
        return f"{self.district.name} Allocation - FY {self.financial_year} (₹{self.allocation_amount_cr} Cr)"


class SchemeMaster(models.Model):
    """
    State & Central Sponsored Schemes Master & Budget Repository.
    """
    code = models.CharField(max_length=50, unique=True, verbose_name="Scheme Code")
    name = models.CharField(max_length=255, verbose_name="Scheme Name")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="schemes")
    category = models.CharField(max_length=100, default="State Sponsored", verbose_name="Scheme Category")

    total_allocation_cr = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Total Allocation (₹ Cr)")
    sanctioned_cr = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Sanctioned Amount (₹ Cr)")
    released_cr = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Released Amount (₹ Cr)")
    utilized_cr = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Utilized Amount (₹ Cr)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fin_scheme_master"
        verbose_name = "Scheme Master"
        verbose_name_plural = "Scheme Master Records"

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class FinancialLedgerEntry(models.Model):
    """
    State Governance Financial Ledger Transaction Entry.
    """
    ENTRY_TYPE_CHOICES = (
        ("PROVISION", "Budget Provision"),
        ("AUTHORIZATION", "Authorization"),
        ("ALLOCATION", "Department Allocation"),
        ("SANCTION", "Authority Sanction"),
        ("RELEASE", "Fund Release"),
        ("COMMITMENT", "Financial Commitment"),
        ("UTILIZATION", "Expenditure Utilization"),
        ("RE_APPROPRIATION", "Re-appropriation Transfer"),
    )

    transaction_id = models.CharField(max_length=50, unique=True, verbose_name="Transaction Ref ID")
    financial_year = models.CharField(max_length=20, default="2026-27")
    entry_type = models.CharField(max_length=50, choices=ENTRY_TYPE_CHOICES, default="ALLOCATION")

    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    scheme = models.ForeignKey(SchemeMaster, on_delete=models.SET_NULL, null=True, blank=True)

    amount_cr = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Amount (₹ Cr)")
    remarks = models.TextField(blank=True, verbose_name="Transaction Remarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fin_ledger_entry"
        verbose_name = "Financial Ledger Entry"
        verbose_name_plural = "Financial Ledger Entries"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.entry_type}] {self.transaction_id} - ₹{self.amount_cr} Cr"


# ==========================================
# 12. DISTRICT GEOSPATIAL DECISION SUPPORT SYSTEM (DDSS) MODELS
# ==========================================

class HealthFacilityIndicator(models.Model):
    """
    Facility-level readiness metrics for Health Decision Workspace.
    """
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="health_indicators", verbose_name="Facility")
    period = models.CharField(max_length=20, default="2026-Q3", verbose_name="Reporting Period")

    bed_count = models.PositiveIntegerField(default=0, verbose_name="Total General Beds")
    icu_bed_count = models.PositiveIntegerField(default=0, verbose_name="ICU Beds Available")
    nicu_bed_count = models.PositiveIntegerField(default=0, verbose_name="NICU Beds Available")
    oxygen_status = models.CharField(max_length=30, choices=[("AVAILABLE", "Available"), ("DEFICIT", "Deficit"), ("CRITICAL", "Critical")], default="AVAILABLE")
    toilet_status = models.CharField(max_length=30, choices=[("ADEQUATE", "Adequate"), ("INSUFFICIENT", "Insufficient"), ("NONE", "None")], default="ADEQUATE")
    ramp_status = models.CharField(max_length=30, choices=[("FUNCTIONAL", "Functional"), ("NON_FUNCTIONAL", "Non-Functional"), ("MISSING", "Missing")], default="FUNCTIONAL")
    testing_equipment_status = models.CharField(max_length=30, choices=[("OPERATIONAL", "Operational"), ("PARTIAL", "Partial Deficit"), ("DEFICIT", "Major Deficit")], default="OPERATIONAL")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hlth_facility_indicator"
        verbose_name = "Health Facility Indicator"
        verbose_name_plural = "Health Facility Indicators"

    def __str__(self):
        return f"{self.facility.name} - {self.period}"


class HealthStaffing(models.Model):
    """
    Cadre-wise human resource availability and vacancies (Doctors, Nurses, Lab Techs, ASHA/ANM).
    """
    CADRE_CHOICES = [
        ("DOCTOR", "Medical Officer / Doctor"),
        ("NURSE", "Staff Nurse / ANM"),
        ("LAB_TECH", "Lab Technician"),
        ("ASHA", "ASHA Worker"),
        ("ADMIN_STAFF", "Administrative Staff"),
    ]
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="staffing_records", verbose_name="Facility")
    village_ward = models.ForeignKey(VillageWard, on_delete=models.SET_NULL, null=True, blank=True, related_name="asha_staffing")
    cadre = models.CharField(max_length=40, choices=CADRE_CHOICES, default="DOCTOR")
    sanctioned_count = models.PositiveIntegerField(default=0)
    available_count = models.PositiveIntegerField(default=0)
    vacancy_count = models.PositiveIntegerField(default=0)
    as_of_date = models.DateField(default=get_today_date)

    class Meta:
        db_table = "hlth_staffing"
        verbose_name = "Health Staffing"
        verbose_name_plural = "Health Staffing Records"

    def save(self, *args, **kwargs):
        self.vacancy_count = max(0, self.sanctioned_count - self.available_count)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.facility.name} - {self.cadre}: {self.available_count}/{self.sanctioned_count}"


class HealthWorkload(models.Model):
    """
    Patient visits, admissions, and capacity pressure burden.
    """
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="workload_records")
    period = models.CharField(max_length=20, default="2026-08")
    patient_visits = models.PositiveIntegerField(default=0, verbose_name="OPD Patient Visits")
    admissions = models.PositiveIntegerField(default=0, verbose_name="IPD Admissions")
    referrals = models.PositiveIntegerField(default=0, verbose_name="Patient Referrals Out")
    capacity_pressure = models.CharField(max_length=30, choices=[("NORMAL", "Normal"), ("MODERATE", "Moderate Pressure"), ("HIGH", "High Pressure"), ("CRITICAL", "Critical Overload")], default="NORMAL")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hlth_workload"
        verbose_name = "Health Workload"
        verbose_name_plural = "Health Workload Records"


class MedicineStock(models.Model):
    """
    Critical and routine medicine inventory & warehouse stockout tracking.
    """
    STOCK_TYPE_CHOICES = [("CRITICAL", "Critical Emergency Medicine"), ("ROUTINE", "Routine Essential Medicine"), ("VACCINE", "Vaccine Cold-Chain")]
    STOCK_STATUS_CHOICES = [("ADEQUATE", "Adequate Stock"), ("LOW", "Low Stock Warning"), ("STOCKOUT", "Critical Stockout")]

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="medicine_stocks")
    medicine_name = models.CharField(max_length=150, verbose_name="Medicine Name")
    stock_type = models.CharField(max_length=30, choices=STOCK_TYPE_CHOICES, default="ROUTINE")
    quantity = models.PositiveIntegerField(default=0)
    minimum_quantity = models.PositiveIntegerField(default=100)
    days_of_stock = models.PositiveIntegerField(default=30)
    stock_status = models.CharField(max_length=30, choices=STOCK_STATUS_CHOICES, default="ADEQUATE")
    as_of = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hlth_medicine_stock"
        verbose_name = "Medicine Stock"
        verbose_name_plural = "Medicine Stock Records"

    def save(self, *args, **kwargs):
        if self.quantity == 0:
            self.stock_status = "STOCKOUT"
        elif self.quantity < self.minimum_quantity:
            self.stock_status = "LOW"
        else:
            self.stock_status = "ADEQUATE"
        super().save(*args, **kwargs)


class Ambulance(models.Model):
    """
    Emergency ambulance vehicles and service coverage bindings.
    """
    STATUS_CHOICES = [("AVAILABLE", "Available / Operational"), ("ON_CALL", "On Emergency Call"), ("MAINTENANCE", "Under Maintenance")]

    ambulance_code = models.CharField(max_length=50, unique=True)
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name="ambulances")
    village_ward = models.ForeignKey(VillageWard, on_delete=models.SET_NULL, null=True, blank=True)
    driver_phone = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="AVAILABLE")
    geom = get_spatial_field("point")

    class Meta:
        db_table = "hlth_ambulance"
        verbose_name = "Ambulance"
        verbose_name_plural = "Ambulances"


class VaccinationMetric(models.Model):
    """
    Immunization and vaccination coverage metrics by geography.
    """
    block = models.ForeignKey(Block, on_delete=models.CASCADE, related_name="vaccination_metrics")
    period = models.CharField(max_length=20, default="2026-Q3")
    target_population = models.PositiveIntegerField(default=1000)
    vaccinated_count = models.PositiveIntegerField(default=850)
    coverage_percent = models.FloatField(default=85.0)

    class Meta:
        db_table = "hlth_vaccination_metric"
        verbose_name = "Vaccination Metric"
        verbose_name_plural = "Vaccination Metrics"

    def save(self, *args, **kwargs):
        if self.target_population > 0:
            self.coverage_percent = round((self.vaccinated_count / self.target_population) * 100.0, 2)
        super().save(*args, **kwargs)


class DiseaseRiskEvent(models.Model):
    """
    Seasonal disease outbreak clusters and high-risk spatial observations.
    """
    disease_name = models.CharField(max_length=150, verbose_name="Disease / Outbreak Name")
    risk_level = models.CharField(max_length=30, choices=[("LOW", "Low Risk"), ("MEDIUM", "Medium Cluster"), ("HIGH", "High Outbreak"), ("CRITICAL", "Critical Outbreak")], default="MEDIUM")
    affected_cases = models.PositiveIntegerField(default=1)
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    block = models.ForeignKey(Block, on_delete=models.SET_NULL, null=True, blank=True)
    season = models.CharField(max_length=50, default="Monsoon 2026")
    geom = get_spatial_field("point")
    observed_at = models.DateField(default=get_today_date)

    class Meta:
        db_table = "hlth_disease_risk_event"
        verbose_name = "Disease Risk Event"
        verbose_name_plural = "Disease Risk Events"


class GapModelVersion(models.Model):
    """
    Stores explainable gap computation weights and versioning rules per department.
    """
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="gap_models")
    version = models.CharField(max_length=30, default="v1.0")
    weights = models.JSONField(default=dict, help_text="Component weights JSON (w1..w8)")
    description = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ddss_gap_model_version"
        verbose_name = "Gap Model Version"
        verbose_name_plural = "Gap Model Versions"

    def __str__(self):
        dept_str = self.department.code if self.department else "ALL"
        return f"Gap Model {self.version} [{dept_str}] ({'Active' if self.is_active else 'Inactive'})"


class PriorityLocation(models.Model):
    """
    Ranked decision-support priority location with explainable gap breakdown and intervention linkage.
    """
    PRIORITY_CHOICES = [
        ("P1", "P1 / CRITICAL"),
        ("P2", "P2 / HIGH"),
        ("P3", "P3 / MEDIUM"),
        ("P4", "P4 / LOW"),
    ]

    title = models.CharField(max_length=255, verbose_name="Location / Need Title")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="priority_locations")
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    block = models.ForeignKey(Block, on_delete=models.SET_NULL, null=True, blank=True)
    village_ward = models.ForeignKey(VillageWard, on_delete=models.SET_NULL, null=True, blank=True)
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name="priority_records")

    gap_score = models.FloatField(default=0.0, verbose_name="Composite Gap Score (0-100)")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="P2")
    component_scores = models.JSONField(default=dict, help_text="Breakdown of demand, capacity, accessibility, HR, medicine, coverage, citizen feedback gaps")
    reason_codes = models.JSONField(default=list, help_text="Reason codes explaining score")
    recommended_action = models.TextField(blank=True, null=True)
    model_version = models.CharField(max_length=30, default="v1.0")

    geom = get_spatial_field("point")
    linked_proposal = models.ForeignKey("Proposal", on_delete=models.SET_NULL, null=True, blank=True, related_name="linked_priority_locations")
    linked_project = models.ForeignKey("ProjectExecution", on_delete=models.SET_NULL, null=True, blank=True, related_name="linked_priority_locations")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ddss_priority_location"
        verbose_name = "Priority Location"
        verbose_name_plural = "Priority Locations"
        ordering = ["-gap_score"]

    def __str__(self):
        return f"[{self.priority}] {self.title} (Gap: {self.gap_score})"


class FeedbackQuestionSet(models.Model):
    """
    Structured questionnaire sets for citizen location feedback.
    """
    title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    service_type = models.CharField(max_length=100, default="HEALTHCARE_SERVICE")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "fb_question_set"
        verbose_name = "Feedback Question Set"
        verbose_name_plural = "Feedback Question Sets"


class FeedbackQuestion(models.Model):
    """
    Individual structured question with predefined options.
    """
    question_set = models.ForeignKey(FeedbackQuestionSet, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    response_type = models.CharField(max_length=30, choices=[("SINGLE_CHOICE", "Single Choice Rating"), ("RATING_5", "1 to 5 Star Rating"), ("TEXT", "Text Note")], default="SINGLE_CHOICE")
    options = models.JSONField(default=list, help_text="Predefined option strings e.g. ['Very Good', 'Good', 'Average', 'Poor', 'Very Poor']")

    class Meta:
        db_table = "fb_question"
        verbose_name = "Feedback Question"
        verbose_name_plural = "Feedback Questions"


class FeedbackResponse(models.Model):
    """
    Geotagged citizen perception response to structured questions.
    """
    question = models.ForeignKey(FeedbackQuestion, on_delete=models.CASCADE, related_name="responses")
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name="feedback_responses")
    village_ward = models.ForeignKey(VillageWard, on_delete=models.SET_NULL, null=True, blank=True)
    citizen_session_id = models.CharField(max_length=100, blank=True, null=True)
    response_value = models.CharField(max_length=255)
    sentiment_score = models.FloatField(default=3.0, help_text="1.0 (Very Poor) to 5.0 (Very Good)")
    geom = get_spatial_field("point")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "fb_response"
        verbose_name = "Feedback Response"
        verbose_name_plural = "Feedback Responses"
        ordering = ["-created_at"]


class GeotagVerification(models.Model):
    """
    Truthful EXIF metadata extraction and spatial boundary/distance verification log.
    """
    VERIFICATION_STATUS_CHOICES = [
        ("VERIFIED", "Verified (EXIF GPS & Boundary Matched)"),
        ("REVIEW", "Review Required (Distance Offset or Border Warning)"),
        ("REJECTED", "Rejected (No EXIF GPS / Out of Boundary / Far Distance)"),
    ]

    photo_path = models.CharField(max_length=500)
    exif_latitude = models.FloatField(null=True, blank=True)
    exif_longitude = models.FloatField(null=True, blank=True)
    submitted_latitude = models.FloatField(null=True, blank=True)
    submitted_longitude = models.FloatField(null=True, blank=True)
    distance_offset_meters = models.FloatField(null=True, blank=True)
    inside_district = models.BooleanField(default=True)
    is_duplicate_25m = models.BooleanField(default=False)
    status = models.CharField(max_length=30, choices=VERIFICATION_STATUS_CHOICES, default="VERIFIED")
    failure_reason = models.TextField(blank=True, null=True)
    verified_at = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "gis_geotag_verification"
        verbose_name = "Geotag Verification Log"
        verbose_name_plural = "Geotag Verification Logs"


class SpatialQuery(models.Model):
    """
    Saved Multi-Layer Compound Spatial Queries for Administrators.
    """
    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    query_json = models.JSONField(default=dict)
    is_shared = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gis_spatial_query"
        verbose_name = "Spatial Query"
        verbose_name_plural = "Spatial Queries"


# ==========================================
# 13. MULTI-DEPARTMENT DDSS INDICATORS & SPECIALIZED MODELS
# ==========================================

class DepartmentIndicator(models.Model):
    """
    Common decision-support indicator repository for ANY line department.
    Traceable to: Department, State, District, Block, Location/Facility, Period, Source.
    """
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("VERIFIED", "Verified"),
        ("PUBLISHED", "Published"),
        ("ARCHIVED", "Archived"),
    ]

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="indicators", verbose_name="Line Department")
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="department_indicators")
    block = models.ForeignKey(Block, on_delete=models.SET_NULL, null=True, blank=True, related_name="department_indicators")
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name="department_indicators")
    village_ward = models.ForeignKey(VillageWard, on_delete=models.SET_NULL, null=True, blank=True)

    indicator_code = models.CharField(max_length=100, db_index=True, verbose_name="Indicator Code (e.g. TEACHER_VACANCY, WATER_COVERAGE, ROAD_ACCESSIBILITY)")
    indicator_name = models.CharField(max_length=200, verbose_name="Indicator Name")
    value = models.FloatField(default=0.0, verbose_name="Numeric Value")
    unit = models.CharField(max_length=50, default="count", verbose_name="Unit of Measurement")
    period = models.CharField(max_length=30, default="2026-08", verbose_name="Reporting Period")
    source = models.CharField(max_length=200, default="Line Department MIS", verbose_name="Data Source")
    source_record_id = models.CharField(max_length=100, blank=True, null=True)
    source_as_of = models.DateField(null=True, blank=True, verbose_name="Data As Of Date")
    data_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="VERIFIED")
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_indicators")
    verified_at = models.DateTimeField(null=True, blank=True)

    geom = get_spatial_field("point")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Additional Metadata (JSONB)")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ddss_department_indicator"
        verbose_name = "Department Indicator"
        verbose_name_plural = "Department Indicators"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.department.code}] {self.indicator_code}: {self.value} {self.unit} ({self.period})"


class EducationFacilityIndicator(models.Model):
    """
    Specialized decision indicators for Education Department.
    """
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="education_indicators")
    period = models.CharField(max_length=20, default="2026-08")
    sanctioned_teachers = models.PositiveIntegerField(default=10)
    available_teachers = models.PositiveIntegerField(default=7)
    teacher_vacancies = models.PositiveIntegerField(default=3)
    student_enrolment = models.PositiveIntegerField(default=320)
    classroom_count = models.PositiveIntegerField(default=8)
    drinking_water_status = models.BooleanField(default=True)
    separate_girls_toilet = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "edu_facility_indicator"
        verbose_name = "Education Facility Indicator"
        verbose_name_plural = "Education Facility Indicators"

    def save(self, *args, **kwargs):
        self.teacher_vacancies = max(0, self.sanctioned_teachers - self.available_teachers)
        super().save(*args, **kwargs)

    @property
    def teacher_vacancy_percentage(self) -> float:
        if self.sanctioned_teachers > 0:
            return round((self.teacher_vacancies / self.sanctioned_teachers) * 100.0, 1)
        return 0.0


class WaterFacilityIndicator(models.Model):
    """
    Specialized decision indicators for Water Resources / Jal Jeevan Mission.
    """
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name="water_indicators")
    village_ward = models.ForeignKey(VillageWard, on_delete=models.SET_NULL, null=True, blank=True)
    period = models.CharField(max_length=20, default="2026-08")
    household_coverage_percent = models.FloatField(default=75.0)
    functional_tap_connections = models.PositiveIntegerField(default=250)
    non_functional_sources_count = models.PositiveIntegerField(default=2)
    daily_supply_hours = models.FloatField(default=4.0)
    water_quality_status = models.CharField(max_length=30, choices=[("SAFE", "Safe Drinking Water"), ("TURBID", "High Turbidity"), ("CONTAMINATED", "Contaminated / Deficit")], default="SAFE")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wtr_facility_indicator"
        verbose_name = "Water Facility Indicator"
        verbose_name_plural = "Water Facility Indicators"

    @property
    def coverage_gap(self) -> float:
        return round(max(0.0, 100.0 - self.household_coverage_percent), 1)

    @property
    def source_gap(self) -> float:
        return round(self.non_functional_sources_count * 25.0, 1)

    @property
    def supply_gap(self) -> float:
        return round(max(0.0, (8.0 - self.daily_supply_hours) * 12.5), 1)


class RoadIndicator(models.Model):
    """
    Specialized decision indicators for Public Works Department (PWD).
    """
    road_name = models.CharField(max_length=200, verbose_name="Road / Connectivity Name")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    road_length_km = models.FloatField(default=12.5)
    paved_length_km = models.FloatField(default=8.0)
    unpaved_poor_length_km = models.FloatField(default=4.5)
    accessibility_status = models.CharField(max_length=30, choices=[("GOOD", "All-Weather Good Access"), ("MODERATE", "Fair Access"), ("POOR", "Poor Monsoon Accessibility")], default="POOR")
    bridge_gap_count = models.PositiveIntegerField(default=1)
    geom = get_spatial_field("geometry")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pwd_road_indicator"
        verbose_name = "Road Indicator"
        verbose_name_plural = "Road Indicators"

    @property
    def paved_percentage(self) -> float:
        if self.road_length_km > 0:
            return round((self.paved_length_km / self.road_length_km) * 100.0, 1)
        return 0.0

    @property
    def poor_road_percentage(self) -> float:
        if self.road_length_km > 0:
            return round((self.unpaved_poor_length_km / self.road_length_km) * 100.0, 1)
        return 0.0

    @property
    def accessibility_score(self) -> float:
        base = 80.0 if self.accessibility_status == "GOOD" else (50.0 if self.accessibility_status == "MODERATE" else 20.0)
        penalty = self.bridge_gap_count * 15.0
        return round(max(0.0, base - penalty), 1)



