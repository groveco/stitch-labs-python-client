from django.conf import settings

stitch = StitchApi(settings.STITCH_AUTH_TOKEN)

# How many products do we have?
stitch.Products.count()

# How many archived products do we have?
stitch.Products.count(filter_={"and":[{"archived":1}]})

# Great. Let's check the stock level of a variant. Note this will do 2 requests
stitch.Products.page()[0].get_linked('Variants')[0].get_linked('WarehouseStockLevels')[0].data

# Let's create something
variant = {
        "links": {
            "AttributeOptions": [
                {
                    "scent": "delicious",
                }
            ]
        },
        "quantity": "20",
        "cost": "10",
        "sku": "xx-yy-zz"
    }
res = stitch.Products.create({"name": "My special product", "links": {"Variants": [variant]}})

# Now let's remove it
stitch.Products.delete(res.id)