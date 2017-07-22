About
=====

This is a Python wrapper library for the `Stitch Labs API <https://developer.stitchlabs.com/>`_.

It supports retrieving paged lists of resources, walking the links collection to get affiliated resources, and the basic CRUD operations on a given resource.

This wrapper will always retrieve linked resources as side-loaded data, which allows walking the linked_resources. This means requests can be slower than strictly necessary, if side-loaded data is not required. More granular control over side-loading is a goal for a future relase.

Usage
=====

.. code:: python

    from stitch import StitchApi

    STITCH_AUTH_TOKEN = 'foo'

    stitch = StitchApi(STITCH_AUTH_TOKEN)

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
    res = stitch.Products.create({
        "name": "My special product",
        "links": {
            "Variants": [variant]
        }
    })

    # Now let's remove it
    stitch.Products.delete(res.id)
    
    # And, how about removing all the products? Dangerous!
    stitch.Products.delete_all()
    
    # Let's close SalesOrders that are shipped, but still open
    filter_ = {"and":[{"status_package":3},{"complete":0}]}
    def get_page_of_orders():
        return stitch.SalesOrders.page(page_num=1,
                                       page_size=50,
                                       filter_=filter_)
    orders = get_page_of_orders()
    while len(orders):
        print "Only %s more to go!" % stitch.SalesOrders.count(filter_=filter_)
        for o in orders:
            stitch.SalesOrders.update(o.id, {"complete": 1})
            print "Closed SalesOrder %s." % o.id
        orders = get_page_of_orders()
::


TODOs
=====

1. Add tests
2. Add CI
3. Release on PyPI
4. Add exhaustive list of resources that are exposed through the API
5. Write a proper edit/update wrapper (instead of _write)
6. Granular side-loading support
