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
router.register(r'districts', views.DistrictViewSet, basename='districts')
router.register(r'department-officers', views.DepartmentOfficerViewSet, basename='department-officers')
router.register(r'asset-categories', views.AssetCategoryViewSet, basename='asset-categories')
router.register(r'facilities', views.FacilityViewSet, basename='facilities')



urlpatterns = [
    path('', views.index, name='index'),
    path('map/', views.index, name='map-view'),
    path('facilities/', views.facilities_page, name='facilities-page'),
    path('facilities/search/', views.facilities_page, name='facilities-search'),
    path('api/auth/signup/', views.SignupView.as_view(), name='signup'),
    path('api/auth/login/', views.LoginView.as_view(), name='login'),
    path('api/auth/me/', views.UserProfileView.as_view(), name='user-profile'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # GIS Read & Layer Display Endpoints
    path('api/gis/catalog/', views.GISCatalogListView.as_view(), name='gis-catalog-list'),
    path('api/gis/layers/<str:layer_name>/', views.GISLayerGeoJSONView.as_view(), name='gis-layer-geojson'),
    path('api/gis/upload-layer/', views.GISLayerUploadView.as_view(), name='gis-layer-upload'),
    
    #GIS RESTful CRUD ViewSets
    path('api/', include(router.urls)),
]


