from django.contrib import admin

from . import models

# Register your models here.


class SKUAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.save()
        from celery_tasks.html.tasks import generate_static_sku_detail_html
        generate_static_sku_detail_html.delay(obj.id)


class SKUSpecificationAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.save()
        from celery_tasks.html.tasks import generate_static_sku_detail_html
        generate_static_sku_detail_html.delay(obj.sku.id)

    def delete_model(self, request, obj):
        sku_id = obj.sku.id
        obj.delete()
        from celery_tasks.html.tasks import generate_static_sku_detail_html
        generate_static_sku_detail_html.delay(sku_id)


class SKUImageAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.save()
        from celery_tasks.html.tasks import generate_static_sku_detail_html
        generate_static_sku_detail_html.delay(obj.sku.id)

        # 设置SKU默认图片
        sku = obj.sku  # 获取图片所对应的sku
        if not sku.default_image_url:  # 如果当前sku没有默认的图片
            sku.default_image_url = obj.image.url   # 把当前的图片路径设置到sku中
            sku.save()

    def delete_model(self, request, obj):
        sku_id = obj.sku.id
        obj.delete()
        from celery_tasks.html.tasks import generate_static_sku_detail_html
        generate_static_sku_detail_html.delay(sku_id)


class GoodsCategoryAdmin(admin.ModelAdmin):
    # 模型站点管理类， 不只可以控制admin的页面显示样式，还可以监听它里面的数据变化
    def save_model(self, request, obj, form, change):
        """
        监听运营人员在admin界面点击了商品分类数据保存事件
        :param request: 本次保存的请求对象
        :param obj: 本次保存的模型对象
        :param form: 要进行修改的表单数据
        :param change: 是否要进行修改
        :return:
        """
        obj.save()
        from celery_tasks.html.tasks import generate_static_list_search_html
        generate_static_list_search_html.delay()

    def delete_model(self, request, obj):
        """
        监听运营人员在admin界面点击了商品分类数据保存事件
        :param request: 本次删除的请求对象
        :param obj: 本次删除的模型对象
        :return:
        """
        obj.delete()
        from celery_tasks.html.tasks import generate_static_list_search_html
        generate_static_list_search_html.delay()


admin.site.register(models.GoodsCategory)
admin.site.register(models.GoodsChannel)
admin.site.register(models.Goods)
admin.site.register(models.Brand)
admin.site.register(models.GoodsSpecification)
admin.site.register(models.SpecificationOption)
admin.site.register(models.SKU, SKUAdmin)
admin.site.register(models.SKUSpecification, SKUSpecificationAdmin)
admin.site.register(models.SKUImage, SKUImageAdmin)
