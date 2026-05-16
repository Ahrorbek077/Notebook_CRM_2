from django.urls import path
from . import views

app_name = 'company'

urlpatterns = [
    # Web sahifalar
    path('',                                  views.CompanyListView.as_view(),          name='list'),
    path('branch/<int:pk>/',                  views.BranchDetailView.as_view(),         name='branch-detail'),

    # Company AJAX
    path('api/create/',                       views.CompanyCreateView.as_view(),        name='api-create'),
    path('api/<int:pk>/edit/',                views.CompanyEditView.as_view(),           name='api-edit'),
    path('api/<int:pk>/delete/',              views.CompanyDeleteView.as_view(),         name='api-delete'),

    # Branch AJAX
    path('api/branch/create/',                views.BranchCreateView.as_view(),         name='branch-create'),
    path('api/branch/<int:pk>/edit/',         views.BranchEditView.as_view(),           name='branch-edit'),
    path('api/branch/<int:pk>/delete/',       views.BranchDeleteView.as_view(),         name='branch-delete'),
    path('api/branch/<int:pk>/pay/',          views.BranchPayView.as_view(),            name='branch-pay'),

    # Batch Return (xarid qaytarish)
    path('api/batch/<int:batch_id>/return/',             views.BatchReturnView.as_view(),            name='batch-return'),

    # Branch Product CRUD
    path('api/branch/<int:branch_pk>/product/add/',     views.BranchProductCreateView.as_view(),   name='branch-product-add'),
    path('api/product/<int:pk>/update/',                views.BranchProductUpdateView.as_view(),   name='branch-product-update'),
    path('api/product/<int:pk>/delete/',                views.BranchProductDeleteView.as_view(),   name='branch-product-delete'),
    path('api/product/<int:pk>/purchase/',              views.BranchProductPurchaseView.as_view(), name='branch-product-purchase'),
]
