from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from myapp.models import (
    State, District, SubDivision, Block, VillageWard, Department, DepartmentOfficer, AssetCategory,
    Role, Permission, RolePermission, User, UserDistrictScope,Facility, FacilityHistory,
    WorkflowInstance, WorkflowTransition, GapScore, Proposal, BudgetApproval, Citizengrievance,
    DocumentFile, NotificationTemplate, NotificationDispatchLog, AuditEventLog, Recommendation,
    GISCatalogEntry, GISDatasetVersionHistory, GISDataProvenance, GISProcessingJob,GISLayerFeature
)

try:
    from django.contrib.gis.admin import GISModelAdmin
    # Test if GDAL works
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
    list_display = ["name", "created_at"]
    search_fields = ["name"]


@admin.register(District)
class DistrictAdmin(GISModelAdmin):
    list_display = ["name", "state", "created_at"]
    search_fields = ["name"]
    list_filter = ["state"]
    autocomplete_fields = ["state"]
    gis_widget_kwargs = {"attrs": {"default_zoom": 10, "default_lon": 85.3, "default_lat": 25.2}}


@admin.register(SubDivision)
class SubDivisionAdmin(GISModelAdmin):
    list_display = ["name", "district"]
    search_fields = ["name", "district__name"]
    list_filter = ["district"]
    autocomplete_fields = ["district"]
    gis_widget_kwargs = {"attrs": {"default_zoom": 11, "default_lon": 85.3, "default_lat": 25.2}}


@admin.register(Block)
class BlockAdmin(GISModelAdmin):
    list_display = ["name", "subdivision", "created_at"]
    search_fields = ["name", "subdivision__name"]
    list_filter = ["subdivision__district"]
    autocomplete_fields = ["subdivision"]
    gis_widget_kwargs = {"attrs": {"default_zoom": 11, "default_lon": 85.3, "default_lat": 25.2}}


@admin.register(VillageWard)
class VillageWardAdmin(GISModelAdmin):
    list_display = ["name", "block", "created_at"]
    search_fields = ["name", "block__name"]
    list_filter = ["block__subdivision__district"]
    autocomplete_fields = ["block"]
    gis_widget_kwargs = {"attrs": {"default_zoom": 12, "default_lon": 85.3, "default_lat": 25.2}}


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name","description", "created_at"]
    search_fields = ["name"]


@admin.register(DepartmentOfficer)
class DepartmentOfficerAdmin(admin.ModelAdmin):
    list_display = ["name", "designation", "department", "email", "contact", "created_at"]
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
    list_display = ["name", "code", "scope_level", "created_at"]
    search_fields = ["name", "code"]
    list_filter = ["scope_level"]
    inlines = [RolePermissionInline]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["resource", "action", "created_at"]
    search_fields = ["resource", "action"]
    list_filter = ["resource", "action"]


from myapp.forms import CustomUserCreationForm, CustomUserChangeForm


@admin.register(User)
class UserAdmin(DefaultUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    list_display = ["username", "email", "first_name", "last_name", "role", "state", "district", "department", "is_staff", "is_active"]
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

# @admin.register(IngestionBatch)
# class IngestionBatchAdmin(admin.ModelAdmin):
#     list_display = ["id", "source_type", "status", "uploaded_by", "total_records", "processed_records", "created_at"]
#     list_filter = ["source_type", "status"]
#     search_fields = ["source_type", "status"]


@admin.register(Facility)
class FacilityAdmin(GISModelAdmin):
    list_display = ["id","name", "category", "department", "district", "hazard_safe", "created_at"]
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
    list_display = ["title", "department", "district", "estimated_cost", "created_at"]
    search_fields = ["title", "department__name", "district__name"]
    list_filter = ["department", "district"]
    autocomplete_fields = ["district", "department", "workflow_instance", "gap_score_ref"]
    inlines = [BudgetApprovalInline]


@admin.register(Citizengrievance)
class CitizencomplainAdmin(GISModelAdmin):
    list_display = ["tracking_no", "citizen_name", "citizen_phone", "facility", "is_deleted", "created_at"]
    search_fields = ["tracking_no", "citizen_name", "citizen_phone", "description"]
    list_filter = ["is_deleted", "created_at"]
    autocomplete_fields = ["facility", "citizen_user", "workflow_instance"]
    actions = [soft_delete_selected, restore_selected]
    gis_widget_kwargs = {"attrs": {"default_zoom": 12, "default_lon": 85.3, "default_lat": 25.2}}


# ==========================================
# 5. DOCUMENT MANAGEMENT ADMIN
# ==========================================

@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    list_display = ["file_name", "owner_type", "owner_id", "version", "uploaded_by", "created_at"]
    search_fields = ["file_name", "owner_type", "owner_id"]
    list_filter = ["owner_type"]


# ==========================================
# 6. NOTIFICATION & AUDIT ADMIN
# ==========================================

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "channel", "locale", "created_at"]
    list_filter = ["channel", "locale"]
    search_fields = ["name", "body_template"]


@admin.register(NotificationDispatchLog)
class NotificationDispatchLogAdmin(admin.ModelAdmin):
    list_display = ["template", "user", "status", "dispatched_at"]
    list_filter = ["status", "template__channel"]
    search_fields = ["user__username", "status"]


@admin.register(AuditEventLog)
class AuditEventLogAdmin(admin.ModelAdmin):
    list_display = ["action", "entity_type", "entity_id", "performed_by", "occurred_at"]
    list_filter = ["action", "entity_type", "occurred_at"]
    search_fields = ["entity_type", "entity_id", "performed_by__username"]
    readonly_fields = ["id", "entity_type", "entity_id", "action", "occurred_at", "performed_by", "before_state", "after_state"]


# ==========================================
# 7. ANALYTICS & GIS CATALOG ADMIN
# ==========================================

@admin.register(GapScore)
class GapScoreAdmin(admin.ModelAdmin):
    list_display = ["district", "department", "score", "computed_at"]
    list_filter = ["district", "department"]
    search_fields = ["district__name", "department__name", "score"]



@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ["decision_class", "gap_score", "created_at"]
    search_fields = ["decision_class"]


@admin.register(GISCatalogEntry)
class GISCatalogEntryAdmin(admin.ModelAdmin):
    list_display = ["id","layer_name", "geometry_type", "category", "is_published"]
    list_filter = ["geometry_type", "category", "is_published"]
    search_fields = ["layer_name", "category"]
    inlines = [GISDataProvenanceInline]


@admin.register(GISProcessingJob)
class GISProcessingJobAdmin(admin.ModelAdmin):
    list_display = ["job_type", "status", "started_at", "completed_at"]
    list_filter = ["job_type", "status"]

@admin.register(GISLayerFeature)
class GISLayerFeatureAdmin(admin.ModelAdmin):
    list_display = ["feature_id", "name", "properties", "geom_geojson","geom"]
    # list_filter = ["name", "layer"]
    # search_fields = ["id", "name"]