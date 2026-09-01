from django.urls import path, include
# pyrefly: ignore [missing-import]
from rest_framework.routers import DefaultRouter
# pyrefly: ignore [missing-import]
from rest_framework_simplejwt.views import TokenRefreshView
from myapp import views

router = DefaultRouter()
router.register(r'gis/catalog-crud', views.GISCatalogViewSet, basename='gis-catalog-crud')
router.register(r'gis/features', views.GISFeatureViewSet, basename='gis-feature')
router.register(r'departments', views.DepartmentViewSet, basename='departments')
router.register(r'states', views.StateViewSet, basename='states')
router.register(r'districts', views.DistrictViewSet, basename='districts')
router.register(r'blocks', views.BlockViewSet, basename='blocks')
router.register(r'department-officers', views.DepartmentOfficerViewSet, basename='department-officers')
router.register(r'asset-categories', views.AssetCategoryViewSet, basename='asset-categories')
router.register(r'facilities', views.FacilityViewSet, basename='facilities')
router.register(r'complaint-categories', views.ComplaintCategoryViewSet, basename='complaint-categories')
router.register(r'complaints', views.ComplaintViewSet, basename='complaints')
router.register(r'users', views.UserViewSet, basename='users')
router.register(r'proposals', views.ProposalViewSet, basename='proposals')
router.register(r'proposal', views.ProposalViewSet, basename='proposal')
router.register(r'proposal-negotiations', views.ProposalNegotiationViewSet, basename='proposal-negotiations')
router.register(r'proposal-releases', views.ProposalFundReleaseViewSet, basename='proposal-releases')
router.register(r'dashboards', views.DashboardViewSet, basename='dashboards')
router.register(r'notifications', views.NotificationViewSet, basename='notifications')
router.register(r'projects', views.ProjectExecutionViewSet, basename='projects')
router.register(r'project', views.ProjectExecutionViewSet, basename='project')
router.register(r'project-expenditures', views.ProjectExpenditureViewSet, basename='project-expenditures')
router.register(r'site-diaries', views.SiteDiaryViewSet, basename='site-diaries')
router.register(r'measurement-books', views.MeasurementBookViewSet, basename='measurement-books')
router.register(r'bills', views.ProjectBillViewSet, basename='project-bills')
router.register(r'execution-risks', views.ExecutionRiskViewSet, basename='execution-risks')
router.register(r'reports', views.ReportViewSet, basename='reports')
router.register(r'employees', views.EmployeeViewSet, basename='employees')
router.register(r'state-budgets', views.StateBudgetViewSet, basename='state-budgets')
router.register(r'department-budgets', views.DepartmentBudgetViewSet, basename='department-budgets')
router.register(r'district-allocations', views.DistrictAllocationViewSet, basename='district-allocations')
router.register(r'schemes', views.SchemeMasterViewSet, basename='schemes')
router.register(r'financial-ledger', views.FinancialLedgerViewSet, basename='financial-ledger')
router.register(r'priority-locations', views.PriorityLocationViewSet, basename='priority-locations')
router.register(r'ddst/indicators', views.DepartmentIndicatorViewSet, basename='ddst-indicators')

urlpatterns = [
    path('', views.index, name='index'),
    path('map/', views.index, name='map-view'),
    path('facilities/', views.facilities_page, name='facilities-page'),
    path('facilities/search/', views.facilities_page, name='facilities-search'),
    path('reports/', views.reports_page, name='reports-page'),
    path('linedept/reports/', views.reports_page, name='linedept-reports-page'),
    path('employees/', views.employees_page, name='employees-page'),
    path('linedept/employees/', views.employees_page, name='linedept-employees-page'),
    path('login/', views.login_page, name='login-page'),
    path('signup/', views.signup_page, name='signup-page'),
    path('forgot-password/', views.forgot_password_page, name='forgot-password-page'),
    path('api/auth/signup/', views.SignupView.as_view(), name='signup'),
    path('api/auth/login/', views.LoginView.as_view(), name='login'),
    path('api/auth/me/', views.UserProfileView.as_view(), name='user-profile'),
    path('api/auth/roles/', views.RoleListView.as_view(), name='roles-list'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('api/auth/forgot-password/', views.ForgotPasswordRequestAPIView.as_view(), name='forgot-password-request'),
    path('api/auth/forgot-password/reset/', views.ResetPasswordWithOTPAPIView.as_view(), name='forgot-password-reset'),
    path('api/auth/change-password/', views.ChangePasswordAPIView.as_view(), name='change-password'),
    path('api/auth/logout/', views.LogoutAPIView.as_view(), name='logout'),
    
    # State Governance Budget & Finance Master Endpoints
    path('api/state-budget/summary/', views.StateBudgetAPIView.as_view(), name='state-budget-summary'),
    path('api/state-budget/', views.StateBudgetAPIView.as_view(), name='state-budget'),

    # DDSS Multi-Department & Decision APIs
    path('api/ddst/departments/', views.LineDepartmentListAPIView.as_view(), name='ddst-departments'),
    path('api/ddst/department/<str:department_code>/dashboard/', views.DepartmentDashboardAPIView.as_view(), name='ddst-department-dashboard'),
    path('api/ddst/dashboard/', views.DMDecisionDashboardAPIView.as_view(), name='ddst-dashboard-alias'),
    path('api/ddss/dashboard/', views.DMDecisionDashboardAPIView.as_view(), name='ddss-dashboard'),
    path('api/gap-analysis/', views.GapAnalysisAPIView.as_view(), name='gap-analysis-list'),
    path('api/gap-analysis/<int:location_id>/', views.GapAnalysisAPIView.as_view(), name='gap-analysis-detail'),
    path('api/gap-analysis/rankings/', views.GapPriorityDashboardAPIView.as_view(), name='gap-analysis-rankings'),
    path('api/gap-priority/', views.GapPriorityDashboardAPIView.as_view(), name='gap-priority-dashboard'),
    path('api/gap-priority/<int:pk>/', views.GapPriorityDashboardAPIView.as_view(), name='gap-priority-detail'),
    path('api/gap-priority/rankings/', views.GapPriorityDashboardAPIView.as_view(), name='gap-priority-rankings'),
    path('api/gap-priority/overview/', views.GapPriorityDashboardAPIView.as_view(), name='gap-priority-overview'),
    path('api/gap-priority/map/', views.GapPriorityDashboardAPIView.as_view(), name='gap-priority-map'),
    path('api/priority-locations/rankings/', views.GapPriorityDashboardAPIView.as_view(), name='priority-locations-rankings'),
    path('gap-priority-tester/', views.gap_priority_tester, name='gap-priority-tester'),
    path('spatial-analysis-tester/', views.spatial_analysis_tester, name='spatial-analysis-tester'),

    # DDSS Health Sector & Spatial Query APIs
    path('api/spatial-analysis/query/', views.SpatialAnalysisQueryAPIView.as_view(), name='spatial-analysis-query'),
    path('api/spatial-query/', views.SpatialAnalysisQueryAPIView.as_view(), name='spatial-query-alias'),
    path('api/spatial-query/query/', views.SpatialAnalysisQueryAPIView.as_view(), name='spatial-query-query-alias'),
    path('api/query/', views.SpatialAnalysisQueryAPIView.as_view(), name='query-alias'),
    path('api/saved-queries/', views.SpatialAnalysisQueryAPIView.as_view(), name='saved-queries-alias'),
    path('api/gis/catalog/', views.GISCatalogAPIView.as_view(), name='gis-catalog-master'),
    path('api/health/facilities/', views.HealthFacilitiesAPIView.as_view(), name='health-facilities'),
    path('api/health/staffing/', views.HealthStaffingAPIView.as_view(), name='health-staffing'),
    path('api/health/staffing/<int:pk>/', views.HealthStaffingAPIView.as_view(), name='health-staffing-detail'),
    path('api/health/human-resources/', views.HealthStaffingAPIView.as_view(), name='health-human-resources-alias'),
    path('api/health/telemetry/', views.HealthInfrastructureAPIView.as_view(), name='health-telemetry-alias'),
    path('api/health/workload/', views.HealthWorkloadAPIView.as_view(), name='health-workload'),
    path('api/health/workload/<int:pk>/', views.HealthWorkloadAPIView.as_view(), name='health-workload-detail'),
    path('api/health/infrastructure/', views.HealthInfrastructureAPIView.as_view(), name='health-infrastructure'),
    path('api/health/infrastructure/<int:pk>/', views.HealthInfrastructureAPIView.as_view(), name='health-infrastructure-detail'),
    path('api/health/medicines/', views.HealthMedicinesAPIView.as_view(), name='health-medicines'),
    path('api/health/medicines/<int:pk>/', views.HealthMedicinesAPIView.as_view(), name='health-medicines-detail'),
    path('api/medicines/', views.HealthMedicinesAPIView.as_view(), name='medicines-alias'),
    path('api/health/ambulances/', views.HealthAmbulancesAPIView.as_view(), name='health-ambulances'),
    path('api/health/ambulances/<int:pk>/', views.HealthAmbulancesAPIView.as_view(), name='health-ambulances-detail'),
    path('api/ambulances/', views.HealthAmbulancesAPIView.as_view(), name='ambulances-alias'),
    path('api/health/vaccination/', views.HealthVaccinationAPIView.as_view(), name='health-vaccination'),
    path('api/health/vaccination/<int:pk>/', views.HealthVaccinationAPIView.as_view(), name='health-vaccination-detail'),
    path('api/vaccinations/', views.HealthVaccinationAPIView.as_view(), name='vaccinations-alias'),
    path('api/health/risk/', views.HealthRiskAPIView.as_view(), name='health-risk'),
    path('api/disease-surveillance/', views.HealthRiskAPIView.as_view(), name='disease-surveillance-alias'),

    # DDSS Education, Water, Road (PWD) & Universal Multi-Department Indicator APIs
    path('api/education/indicators/', views.EducationFacilityIndicatorAPIView.as_view(), name='education-indicators'),
    path('api/education/indicators/<int:pk>/', views.EducationFacilityIndicatorAPIView.as_view(), name='education-indicators-detail'),
    # path('api/education/indicator/', views.EducationFacilityIndicatorAPIView.as_view(), name='education-indicator-singular'),
    path('api/education/schools/', views.EducationFacilityIndicatorAPIView.as_view(), name='education-schools-alias'),
    path('api/education/telemetry/', views.EducationFacilityIndicatorAPIView.as_view(), name='education-telemetry-alias'),
    path('api/water/indicators/', views.WaterFacilityIndicatorAPIView.as_view(), name='water-indicators'),
    path('api/water/indicators/<int:pk>/', views.WaterFacilityIndicatorAPIView.as_view(), name='water-indicators-detail'),
    path('api/water/schemes/', views.WaterFacilityIndicatorAPIView.as_view(), name='water-schemes-alias'),
    path('api/water/sources/', views.WaterFacilityIndicatorAPIView.as_view(), name='water-sources-alias'),
    path('api/water/telemetry/', views.WaterFacilityIndicatorAPIView.as_view(), name='water-telemetry-alias'),
    path('api/forest/', views.ForestCoverAPIView.as_view(), name='forest-cover'),
    path('api/road/indicators/', views.RoadIndicatorAPIView.as_view(), name='road-indicators'),
    path('api/road/indicators/<int:pk>/', views.RoadIndicatorAPIView.as_view(), name='road-indicators-detail'),
    path('api/pwd/indicators/', views.RoadIndicatorAPIView.as_view(), name='pwd-indicators'),
    path('api/pwd/telemetry/', views.RoadIndicatorAPIView.as_view(), name='pwd-telemetry-alias'),
    path('api/urban/indicators/', views.DepartmentIndicatorAPIView.as_view(), name='urban-indicators-alias'),
    path('api/urban/telemetry/', views.DepartmentIndicatorAPIView.as_view(), name='urban-telemetry-alias'),
    path('api/ddst/indicators/', views.DepartmentIndicatorAPIView.as_view(), name='ddst-indicators-apiview'),
    path('api/ddst/indicators/<int:pk>/', views.DepartmentIndicatorAPIView.as_view(), name='ddst-indicators-apiview-detail'),

    # Citizen Perception Feedback & Validation APIs
    path('api/feedback/questions/', views.FeedbackQuestionsAPIView.as_view(), name='feedback-questions'),
    path('api/feedback/responses/', views.FeedbackResponseAPIView.as_view(), name='feedback-responses'),
    path('api/feedback/aggregation/', views.FeedbackAggregationAPIView.as_view(), name='feedback-aggregation'),
    path('api/feedback/analytics/', views.FeedbackAnalyticsAPIView.as_view(), name='feedback-analytics'),
    path('api/gis/validate-coordinate/', views.GISValidateCoordinateAPIView.as_view(), name='gis-validate-coordinate'),
    path('api/gis/check-duplicate/', views.GISCheckDuplicateAPIView.as_view(), name='gis-check-duplicate'),
    path('api/evidence/verify-geotag/', views.EvidenceVerifyGeotagAPIView.as_view(), name='evidence-verify-geotag'),

    # GIS Read & Layer Display Endpoints
    path('api/gis/catalog/', views.GISCatalogListView.as_view(), name='gis-catalog-list'),
    path('api/gis/layers/<str:layer_name>/', views.GISLayerGeoJSONView.as_view(), name='gis-layer-geojson'),
    path('api/gis/upload-layer/', views.GISLayerUploadView.as_view(), name='gis-layer-upload'),

    # Department Complaints & Users APIs
    path('api/department/<str:department_id>/complain/', views.DepartmentComplaintsAPIView.as_view(), name='department-complaints-singular'),
    path('api/department/<str:department_id>/complaints/', views.DepartmentComplaintsAPIView.as_view(), name='department-complaints-plural'),
    path('api/departments/<str:department_id>/complain/', views.DepartmentComplaintsAPIView.as_view(), name='departments-complaints-singular'),
    path('api/department/<str:department_id>/users/', views.DepartmentUsersAPIView.as_view(), name='department-users'),

    # GIS Spatial Query Engine & Planning ERP
    path('api/planning/dashboard/', views.PlanningERPAPIView.as_view(), name='planning-dashboard'),

    # GIS RESTful CRUD ViewSets
    path('api/', include(router.urls)),
]
