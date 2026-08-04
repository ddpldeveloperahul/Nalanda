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
    """Official NDISP Blueprint Roles (Section 9.1)."""
    NATIONAL_ADMIN = "NATIONAL_ADMIN", "National Admin"
    STATE_ADMIN = "STATE_ADMIN", "State Admin"
    DISTRICT_COLLECTOR = "DISTRICT_COLLECTOR", "District Collector / DM"
    ADM = "ADM", "Additional District Magistrate (ADM)"
    DEPARTMENT_OFFICER = "DEPARTMENT_OFFICER", "Department Officer"
    FIELD_ENGINEER_DEO = "FIELD_ENGINEER_DEO", "Field Engineer / Data Entry Operator"
    CITIZEN_REGISTERED = "CITIZEN_REGISTERED", "Registered Citizen"
    CITIZEN_ANONYMOUS = "CITIZEN_ANONYMOUS", "Anonymous Citizen"


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


class Proposal(models.Model):
    """Department Development Proposal / Scheme Project Application."""
    title = models.CharField(max_length=255, verbose_name="Proposal Title")
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="proposals")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="proposals")
    workflow_instance = models.ForeignKey(WorkflowInstance, on_delete=models.SET_NULL, null=True, blank=True, related_name="proposals")
    gap_score_ref = models.ForeignKey(GapScore, on_delete=models.SET_NULL, null=True, blank=True, related_name="proposals")
    estimated_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Estimated Cost (INR)")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "txn_proposal"
        verbose_name = "Department Proposal"
        verbose_name_plural = "Department Proposals"

    def __str__(self) -> str:
        return self.title


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


class Citizengrievance(models.Model):
    """Citizen Public Grievance Submission."""
    tracking_no = models.CharField(max_length=50, unique=True, verbose_name="Tracking Number")
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name="grievances")
    citizen_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="grievances")
    citizen_name = models.CharField(max_length=150, verbose_name="Citizen Name")
    citizen_phone = models.CharField(max_length=20, verbose_name="Phone Number")
    workflow_instance = models.ForeignKey(WorkflowInstance, on_delete=models.SET_NULL, null=True, blank=True, related_name="grievances")
    description = models.TextField(verbose_name="Grievance Description")
    geom = get_spatial_field("point")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    
    is_deleted = models.BooleanField(default=False, verbose_name="Deleted")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Deleted At")
    
    class Meta:
        db_table = "txn_citizen_grievance"
        verbose_name = "Citizen grievance"
        verbose_name_plural = "Citizen grievances"

    def __str__(self) -> str:
        return f"Grievance {self.tracking_no} - {self.citizen_name}"


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
