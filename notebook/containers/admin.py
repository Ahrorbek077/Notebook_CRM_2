from django.contrib import admin
from .models import ContainerType, BranchContainerStock, ClientContainer, ContainerTransaction


@admin.register(ContainerType)
class ContainerTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'business', 'is_active', 'created_at')
    list_filter = ('business', 'is_active')
    search_fields = ('name',)


@admin.register(BranchContainerStock)
class BranchContainerStockAdmin(admin.ModelAdmin):
    list_display = ('branch', 'container_type', 'quantity', 'updated_at')
    list_filter = ('branch', 'container_type')


@admin.register(ClientContainer)
class ClientContainerAdmin(admin.ModelAdmin):
    list_display = ('client', 'container_type', 'quantity', 'updated_at')
    list_filter = ('container_type',)
    search_fields = ('client__name',)


@admin.register(ContainerTransaction)
class ContainerTransactionAdmin(admin.ModelAdmin):
    list_display = ('client', 'container_type', 'action', 'quantity', 'branch', 'user', 'created_at')
    list_filter = ('action', 'container_type', 'branch')
    search_fields = ('client__name',)
    readonly_fields = [f.name for f in ContainerTransaction._meta.fields]
