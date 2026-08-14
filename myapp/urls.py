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
router.register(r'dashboards', views.DashboardViewSet, basename='dashboards')
router.register(r'notifications', views.NotificationViewSet, basename='notifications')
router.register(r'projects', views.ProjectExecutionViewSet, basename='projects')
router.register(r'project', views.ProjectExecutionViewSet, basename='project')
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
    path('api/auth/forgot-password/request-otp/', views.ForgotPasswordRequestAPIView.as_view(), name='forgot-password-request-otp'),
    path('api/auth/forgot-password/reset/', views.ResetPasswordWithOTPAPIView.as_view(), name='forgot-password-reset'),
    path('api/auth/reset-password/', views.ResetPasswordWithOTPAPIView.as_view(), name='reset-password'),
    path('api/auth/change-password/', views.ChangePasswordAPIView.as_view(), name='change-password'),
    path('api/auth/logout/', views.LogoutAPIView.as_view(), name='logout'),
    
    # State Governance Budget & Finance Master Endpoints
    path('api/state-budget/summary/', views.StateBudgetAPIView.as_view(), name='state-budget-summary'),
    path('api/state-budget/', views.StateBudgetAPIView.as_view(), name='state-budget'),

    # GIS Read & Layer Display Endpoints
    path('api/gis/catalog/', views.GISCatalogListView.as_view(), name='gis-catalog-list'),
    path('api/gis/layers/<str:layer_name>/', views.GISLayerGeoJSONView.as_view(), name='gis-layer-geojson'),
    path('api/gis/upload-layer/', views.GISLayerUploadView.as_view(), name='gis-layer-upload'),

    # Department Specific Complaints & Users APIs
    path('api/department/<str:department_id>/complain/', views.DepartmentComplaintsAPIView.as_view(), name='department-complaints-singular'),
    path('api/department/<str:department_id>/complaints/', views.DepartmentComplaintsAPIView.as_view(), name='department-complaints-plural'),
    path('api/departments/<str:department_id>/complain/', views.DepartmentComplaintsAPIView.as_view(), name='departments-complaints-singular'),
    path('api/department/<str:department_id>/users/', views.DepartmentUsersAPIView.as_view(), name='department-users'),
    path('api/departments/<str:department_id>/users/', views.DepartmentUsersAPIView.as_view(), name='departments-users'),

    # GIS Spatial Query Engine & Planning ERP
    path('api/spatial-query/', views.SpatialQueryAPIView.as_view(), name='spatial-query'),
    path('api/planning/dashboard/', views.PlanningERPAPIView.as_view(), name='planning-dashboard'),

    # GIS RESTful CRUD ViewSets
    path('api/', include(router.urls)),
]
