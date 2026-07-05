from django.contrib import admin

from hw_radar.catalog.models import (
    Category,
    DriveSpec,
    DriveUnit,
    Manufacturer,
    ProductAlias,
    ProductFamily,
    ProductModel,
    ProductVariant,
    SourceSite,
)

admin.site.register(Category)
admin.site.register(Manufacturer)
admin.site.register(ProductFamily)
admin.site.register(ProductModel)
admin.site.register(ProductVariant)
admin.site.register(DriveSpec)
admin.site.register(ProductAlias)
admin.site.register(DriveUnit)
admin.site.register(SourceSite)
