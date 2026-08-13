from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from myapp.models import (
    State, District, SubDivision, Block, VillageWard, Department, DepartmentOfficer, AssetCategory,
    Role, Permission, RolePermission, User, UserDistrictScope, Facility, FacilityHistory,
    WorkflowInstance, WorkflowTransition, GapScore, Proposal, BudgetApproval,
    DocumentFile, NotificationTemplate, NotificationDispatchLog, AuditEventLog, Recommendation,
    GISCatalogEntry, GISDatasetVersionHistory, GISDataProvenance, GISProcessingJob, GISLayerFeature,
    Complaint, ComplaintCategory, ComplaintStatus, ComplaintEvidence, ComplaintPriority, ComplaintTimeline,
    ProjectExecution, SiteDiary, MeasurementBook, ProjectBill, ExecutionRisk, Report, Employee, EmployeeInvitation,
    StateBudget, DepartmentBudget, DistrictAllocation, SchemeMaster, FinancialLedgerEntry
)

try:
    from django.contrib.gis.admin import GISModelAdmin
    from django.contrib.gis.gdal import HAS_GDAL
    if not HAS_GDAL:
        GISModelAdmin = admin.ModelAdmin
except Exception:
    GISModelAdmin = admin.ModelAdmin


# ==========================================
# COMMON BASE ADMIN & ACTIONS
# ==========================================

@admin.action(description="Soft Delete Selected Records")
def soft_delete_selected(modeladmin, request, queryset):
    count = 0
    for obj in queryset:
        if hasattr(obj, "soft_delete"):
            obj.soft_delete()
            count += 1
    modeladmin.message_user(request, f"{count} records soft deleted successfully.")


@admin.action(description="Restore Selected Records")
def restore_selected(modeladmin, request, queryset):
    count = 0
    for obj in queryset:
        if hasattr(obj, "restore"):
            obj.restore()
            count += 1
    modeladmin.message_user(request, f"{count} records restored successfully.")


# ==========================================
# INLINES
# ==========================================

class UserDistrictScopeInline(admin.TabularInline):
    model = UserDistrictScope
    extra = 1
    autocomplete_fields = ["district", "department"]


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1
    autocomplete_fields = ["permission"]


class FacilityHistoryInline(admin.StackedInline):
    model = FacilityHistory
    extra = 0
    readonly_fields = ["valid_from", "valid_to", "snapshot"]
    can_delete = False


class WorkflowTransitionInline(admin.TabularInline):
    model = WorkflowTransition
    extra = 0
    readonly_fields = ["from_state", "to_state", "performed_by", "remarks", "transitioned_at"]
    can_delete = False


class BudgetApprovalInline(admin.StackedInline):
    model = BudgetApproval
    extra = 0


class GISDataProvenanceInline(admin.StackedInline):
    model = GISDataProvenance
    extra = 1


# ==========================================
# 1. ADMINISTRATIVE & MASTER HIERARCHY ADMIN
# ==========================================

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "created_at"]
    search_fields = ["name"]


@admin.register(District)
class DistrictAdmin(GISModelAdmin):
    list_display = ["id", "name", "state", "created_at"]
    search_fields = ["name"]
    list_filter = ["state"]
    autocomplete_fields = ["state"]
    gis_widget_kwargs = {"attrs": {"default_zoom": 10, "default_lon": 85.3, "default_lat": 25.2}}


@admin.register(SubDivision)
class SubDivisionAdmin(GISModelAdmin):
    list_display = ["id", "name", "district"]
    search_fields = ["name", "district__name"]
    list_filter = ["district"]
    autocomplete_fields = ["district"]
    gis_widget_kwargs = {"attrs": {"default_zoom": 11, "default_lon": 85.3, "default_lat": 25.2}}


@admin.register(Block)
class BlockAdmin(GISModelAdmin):
    list_display = ["id", "name", "subdivision", "created_at"]
    search_fields = ["name", "subdivision__name"]
    list_filter = ["subdivision__district"]
    autocomplete_fields = ["subdivision"]
    gis_widget_kwargs = {"attrs": {"default_zoom": 11, "default_lon": 85.3, "default_lat": 25.2}}


@admin.register(VillageWard)
class VillageWardAdmin(GISModelAdmin):
    list_display = ["id", "name", "block", "created_at"]
    search_fields = ["name", "block__name"]
    list_filter = ["block__subdivision__district"]
    autocomplete_fields = ["block"]
    gis_widget_kwargs = {"attrs": {"default_zoom": 12, "default_lon": 85.3, "default_lat": 25.2}}


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "description", "created_at"]
    search_fields = ["name"]


@admin.register(DepartmentOfficer)
class DepartmentOfficerAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "designation", "department", "email", "contact", "created_at"]
    search_fields = ["name", "designation", "email", "contact", "department__name"]
    list_filter = ["department"]
    autocomplete_fields = ["department"]


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "department", "created_at"]
    search_fields = ["name", "department__name"]
    list_filter = ["department"]
    autocomplete_fields = ["department"]


# ==========================================
# 2. RBAC & USER ADMIN
# ==========================================

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "code", "scope_level", "created_at"]
    search_fields = ["name", "code"]
    list_filter = ["scope_level"]
    inlines = [RolePermissionInline]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["id", "resource", "action", "created_at"]
    search_fields = ["resource", "action"]
    list_filter = ["resource", "action"]


from myapp.forms import CustomUserCreationForm, CustomUserChangeForm


@admin.register(User)
class UserAdmin(DefaultUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    list_display = ["id", "username", "email", "first_name", "last_name", "role", "state", "district", "department", "is_staff", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name", "phone", "designation"]
    list_filter = ["role", "state", "district", "department", "is_staff", "is_active"]
    inlines = [UserDistrictScopeInline]

    fieldsets = DefaultUserAdmin.fieldsets + (
        ("NDISP Enterprise Assignment", {
            "fields": ("state", "district", "department", "role", "designation", "phone")
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "first_name",
                "last_name",
                "role",
                "state",
                "district",
                "department",
                "designation",
                "phone",
                "password1",
                "password2",
            ),
        }),
    )


# ==========================================
# 3. ASSET & GIS FEATURE ADMIN
# ==========================================

@admin.register(Facility)
class FacilityAdmin(GISModelAdmin):
    list_display = ["id", "name", "category", "department", "district", "hazard_safe", "created_at"]
    search_fields = ["name", "district__name", "department__name", "category__name"]
    list_filter = ["department", "district", "category", "hazard_safe"]
    autocomplete_fields = ["district", "department", "category"]
    inlines = [FacilityHistoryInline]
    gis_widget_kwargs = {"attrs": {"default_zoom": 12, "default_lon": 85.3, "default_lat": 25.2}}


# ==========================================
# 4. WORKFLOW & TRANSACTION ADMIN
# ==========================================

@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = ["id", "workflow_type", "current_state", "sla_due_at", "created_at"]
    list_filter = ["workflow_type", "current_state"]
    search_fields = ["workflow_type", "current_state"]
    inlines = [WorkflowTransitionInline]


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ["id", "proposal_id", "title", "department", "block", "status", "stage", "priority", "estimated_cost", "is_deleted", "created_at"]
    search_fields = ["proposal_id", "title", "department__name", "district__name", "block", "village"]
    list_filter = ["is_deleted", "status", "stage", "priority", "department", "district", "block"]
    autocomplete_fields = ["district", "department", "created_by", "reviewed_by", "approved_by", "workflow_instance", "gap_score_ref"]
    inlines = [BudgetApprovalInline]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)


# ==========================================
# 5. DOCUMENT MANAGEMENT ADMIN
# ==========================================

@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    list_display = ["id", "file_name", "owner_type", "owner_id", "version", "uploaded_by", "created_at"]
    search_fields = ["file_name", "owner_type", "owner_id"]
    list_filter = ["owner_type"]


# ==========================================
# 6. NOTIFICATION & AUDIT ADMIN
# ==========================================

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "channel", "locale", "created_at"]
    list_filter = ["channel", "locale"]
    search_fields = ["name", "body_template"]


@admin.register(NotificationDispatchLog)
class NotificationDispatchLogAdmin(admin.ModelAdmin):
    list_display = ["id", "template", "user", "status", "dispatched_at"]
    list_filter = ["status", "template__channel"]
    search_fields = ["user__username", "status"]


@admin.register(AuditEventLog)
class AuditEventLogAdmin(admin.ModelAdmin):
    list_display = ["id", "action", "entity_type", "entity_id", "performed_by", "occurred_at"]
    list_filter = ["action", "entity_type", "occurred_at"]
    search_fields = ["entity_type", "entity_id", "performed_by__username"]
    readonly_fields = ["id", "entity_type", "entity_id", "action", "occurred_at", "performed_by", "before_state", "after_state"]


# ==========================================
# 7. ANALYTICS & GIS CATALOG ADMIN
# ==========================================

@admin.register(GapScore)
class GapScoreAdmin(admin.ModelAdmin):
    list_display = ["id", "district", "department", "score", "computed_at"]
    list_filter = ["district", "department"]
    search_fields = ["district__name", "department__name", "score"]


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ["id", "decision_class", "gap_score", "created_at"]
    search_fields = ["decision_class"]


@admin.register(GISCatalogEntry)
class GISCatalogEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "layer_name", "geometry_type", "category", "is_published"]
    list_filter = ["geometry_type", "category", "is_published"]
    search_fields = ["layer_name", "category"]
    inlines = [GISDataProvenanceInline]


@admin.register(GISProcessingJob)
class GISProcessingJobAdmin(admin.ModelAdmin):
    list_display = ["id", "job_type", "status", "started_at", "completed_at"]
    list_filter = ["job_type", "status"]


@admin.register(GISLayerFeature)
class GISLayerFeatureAdmin(admin.ModelAdmin):
    list_display = ["id", "feature_id", "name", "properties", "geom_geojson", "geom"]
    search_fields = ["feature_id", "name", "properties"]




# ==========================================
# 8. COMPLAINT MANAGEMENT ADMIN REGISTRATIONS
# ==========================================

@admin.register(ComplaintCategory)
class ComplaintCategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "department", "default_priority", "default_sla_hours", "icon", "created_at"]
    list_filter = ["department", "default_priority"]
    search_fields = ["name", "department__name"]


class ComplaintEvidenceInline(admin.TabularInline):
    model = ComplaintEvidence
    extra = 0
    readonly_fields = ["file_name", "file_type", "stage", "uploaded_by", "latitude", "longitude", "is_geotag_verified", "created_at"]


class ComplaintTimelineInline(admin.TabularInline):
    model = ComplaintTimeline
    extra = 0
    readonly_fields = ["action", "from_status", "to_status", "performed_by", "performer_role", "remarks", "created_at"]


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "tracking_no",
        "title",
        "category",
        "department",
        "status",
        "priority",
        "citizen_name",
        "assigned_officer",
        "is_sla_breached",
        "created_at",
    ]
    list_filter = ["status", "priority", "department", "is_sla_breached", "district"]
    search_fields = ["tracking_no", "title", "description", "citizen_name", "citizen_phone"]
    readonly_fields = ["tracking_no", "sla_deadline", "is_sla_breached", "resolved_at", "closed_at", "created_at", "updated_at"]
    inlines = [ComplaintEvidenceInline, ComplaintTimelineInline]
    ordering = ["-created_at"]


@admin.register(ComplaintEvidence)
class ComplaintEvidenceAdmin(admin.ModelAdmin):
    list_display = ["id", "complaint", "file_name", "file_type", "stage", "uploaded_by", "is_geotag_verified", "created_at"]
    list_filter = ["file_type", "stage", "is_geotag_verified"]
    search_fields = ["complaint__tracking_no", "file_name"]


@admin.register(ComplaintTimeline)
class ComplaintTimelineAdmin(admin.ModelAdmin):
    list_display = ["id", "complaint", "action", "from_status", "to_status", "performed_by", "performer_role", "created_at"]
    list_filter = ["action", "to_status"]
    search_fields = ["complaint__tracking_no", "remarks", "performer_role"]


# ==========================================
# 9. PROJECT EXECUTION ERP ADMIN
# ==========================================

@admin.register(ProjectExecution)
class ProjectExecutionAdmin(admin.ModelAdmin):
    list_display = ["id", "project_id", "title", "department", "block", "sanction_amount", "expenditure_amount", "progress_percentage", "status", "risk_level", "inspection_due", "created_at"]
    list_filter = ["status", "risk_level", "inspection_due", "department", "district"]
    search_fields = ["project_id", "title", "contractor_name", "block"]
    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)


@admin.register(SiteDiary)
class SiteDiaryAdmin(admin.ModelAdmin):
    list_display = ["id", "project", "log_date", "labour_count", "weather_condition", "progress_logged", "logged_by", "created_at"]
    list_filter = ["log_date", "weather_condition"]
    search_fields = ["project__project_id", "work_description"]


@admin.register(MeasurementBook)
class MeasurementBookAdmin(admin.ModelAdmin):
    list_display = ["id", "mb_number", "project", "item_description", "unit", "quantity_measured", "rate", "total_amount", "status", "measurement_date"]
    list_filter = ["status", "measurement_date"]
    search_fields = ["mb_number", "project__project_id", "item_description"]


@admin.register(ProjectBill)
class ProjectBillAdmin(admin.ModelAdmin):
    list_display = ["id", "bill_number", "project", "bill_type", "claimed_amount", "verified_amount", "net_payable_amount", "payment_status", "submission_date"]
    list_filter = ["bill_type", "payment_status"]
    search_fields = ["bill_number", "project__project_id", "transaction_reference"]


@admin.register(ExecutionRisk)
class ExecutionRiskAdmin(admin.ModelAdmin):
    list_display = ["id", "project", "risk_type", "severity", "risk_signal", "status", "reported_at"]
    list_filter = ["severity", "status", "risk_type"]
    search_fields = ["project__project_id", "risk_signal", "recommendation"]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "title", "category", "file_size_str", "download_format", "department", "district", "generated_at"]
    list_filter = ["category", "download_format", "generated_at"]
    search_fields = ["code", "title", "department__name"]


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["id", "employee_code", "full_name", "email", "designation", "office", "block", "status", "created_at"]
    list_filter = ["status", "department", "district"]
    search_fields = ["employee_code", "full_name", "email", "designation", "office"]


@admin.register(EmployeeInvitation)
class EmployeeInvitationAdmin(admin.ModelAdmin):
    list_display = ["id", "token", "email", "role", "invited_by", "status", "created_at", "expires_at"]
    list_filter = ["status", "role"]
    search_fields = ["email", "token"]


# ==========================================
# STATE GOVERNANCE BUDGET & FINANCE ADMIN
# ==========================================

@admin.register(StateBudget)
class StateBudgetAdmin(admin.ModelAdmin):
    list_display = ["id", "financial_year", "total_state_budget_cr", "department_allocation_cr", "district_allocation_cr", "total_sanctioned_cr", "total_released_cr", "total_utilized_cr", "updated_at"]
    search_fields = ["financial_year"]


@admin.register(DepartmentBudget)
class DepartmentBudgetAdmin(admin.ModelAdmin):
    list_display = ["id", "department", "financial_year", "authorized_budget_cr", "sanctioned_budget_cr", "released_budget_cr", "committed_budget_cr", "utilized_budget_cr", "utilization_percentage"]
    list_filter = ["financial_year", "department"]
    search_fields = ["department__name", "financial_year"]


@admin.register(DistrictAllocation)
class DistrictAllocationAdmin(admin.ModelAdmin):
    list_display = ["id", "district", "department", "financial_year", "allocation_amount_cr", "sanctioned_amount_cr", "utilized_amount_cr"]
    list_filter = ["financial_year", "district", "department"]
    search_fields = ["district__name", "department__name", "financial_year"]


@admin.register(SchemeMaster)
class SchemeMasterAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "name", "department", "category", "total_allocation_cr", "sanctioned_cr", "released_cr", "utilized_cr"]
    list_filter = ["department", "category"]
    search_fields = ["code", "name", "department__name"]


@admin.register(FinancialLedgerEntry)
class FinancialLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "transaction_id", "financial_year", "entry_type", "department", "district", "scheme", "amount_cr", "created_at"]
    list_filter = ["entry_type", "financial_year", "department", "district"]
    search_fields = ["transaction_id", "remarks", "department__name", "district__name"]

