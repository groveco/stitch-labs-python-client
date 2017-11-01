import requests
import json
import logging


logger = logging.getLogger('stitch')


class StitchException(Exception):
    pass


class StitchUnauthorizedException(StitchException):
    pass


class StitchTooManyRequestsException(StitchException):
    pass


class StitchBadGatewayException(StitchException):
    pass


class StitchApiEntity(object):

    def __init__(self, resource, data, parent):
        self.resource = resource
        self.id = data.get('id')
        self.data = data
        self.links = self.data.get('links', {})
        self._parent_result = parent

    def get_linked(self, resource, drill=True, filter_=None):
        if resource not in self.links and drill:
            return self.detail().get_linked(resource, drill=False, filter_=filter_)

        linked_ids = [l['id'] for l in self.links.get(resource, [])]
        loaded_resources = self._parent_result.sideloaded.get(resource, {})
        relevant_resources = [e for k, e in loaded_resources.items() if k in linked_ids]
        entities = [StitchApiEntity(resource, e, self._parent_result) for e in relevant_resources]
        if filter_ is not None:
            return [e for e in entities if filter_(e)]
        return entities

    def detail(self):
        return self._parent_result._endpoint.get(self.id)

    def __repr__(self):
        return 'StitchApiEntity(%s, %s)' % (self.resource, self.data)


class StitchApiResult(object):

    def __init__(self, parsed_response, resource, parent):
        self._endpoint = parent
        self._resource = resource
        parsed_resource = parsed_response[resource]

        if isinstance(parsed_resource, dict):
            self._entities = [StitchApiEntity(resource, parsed_resource, self)]
        elif isinstance(parsed_resource, list):
            self._entities = [StitchApiEntity(resource, r, self) for r in parsed_resource]

        self.meta = parsed_response.get('meta', {})
        self.sideloaded = {k: v for k, v in parsed_response.items() if k not in ['meta', self._resource]}

    def __iter__(self):
        for entity in self._entities:
            yield entity

    def __len__(self):
        return len(self._entities)

    def __getitem__(self, ii):
        return self._entities[ii]


class StitchEndpoint(object):

    READ = ('read', 'https://api-pub.stitchlabs.com/api2/v2/%s')
    READ_DETAIL = ('read', 'https://api-pub.stitchlabs.com/api2/v2/%s/detail')
    READ_REPORTS = ('read', 'https://api-pub.stitchlabs.com/api2/v2/%s/reports')
    WRITE = ('write', 'https://api-pub.stitchlabs.com/api2/v1/%s')

    def __init__(self, resource, headers):
        self._headers = headers
        self._resource = resource

    def _request(self, action, data):
        data['action'] = action[0]
        uri = action[1] % self._resource
        data = json.dumps(data)
        try:
            response = requests.request("POST",
                                        uri,
                                        data=data,
                                        headers=self._headers)
            logger.info('STITCH API REQUEST: %s %s\n'
                        'DATA="%s" \n'
                        'RESPONSE="%s"' % (response.status_code, uri, data, response.content))
        except Exception as e:
            raise Exception('Request to %s with %s failed with: %s' % (uri, data, e))

        if response.status_code in [200, 201, 206]:
            try:
                return StitchApiResult(response.json(), self._resource, self)
            except Exception as e:
                raise Exception('Failed to parse json response. Request to %s with %s returned non-json content: %s'
                         % (uri, data, response.content))
        elif response.status_code == 401:
            raise StitchUnauthorizedException('URL:%s DATA:%s RESPONSE:%s' % (uri, data, response.content))
        elif response.status_code == 429:
            raise StitchTooManyRequestsException('URL:%s DATA:%s RESPONSE:%s' % (uri, data, response.content))
        elif response.status_code in [502, 504]:
            raise StitchBadGatewayException('URL:%s DATA:%s RESPONSE:%s' % (uri, data, response.content))
        else:
            raise StitchException('STATUS:%s URL:%s DATA:%s RESPONSE:%s' % (response.status_code, uri, data, response.content))

    def _list(self, page_num=1, page_size=20, filter_=None, sort_=None):
        data = {
            'page_num': page_num,
            'page_size': page_size,
            'filter': filter_ or {},
            'sort': sort_ or {}
        }
        return self._request(self.READ, data)

    def page(self, page_num=1, page_size=20, filter_=None, sort_=None):
        return self._list(page_num, page_size, filter_, sort_)

    def page_count(self, page_size=20, filter_=None):
        return int(self._list(page_size=page_size, filter_=filter_).meta['last_page'])

    def count(self, filter_=None):
        return int(self._list(page_size=1, filter_=filter_).meta['total'])

    def _reports(self, page_num=1, page_size=20, filter_=None, sort_=None, **kwargs):
        data = {
            'page_num': page_num,
            'page_size': page_size,
            'filter': filter_ or {},
            'sort': sort_ or {}
        }

        data.update(kwargs)

        return self._request(self.READ_REPORTS, data)

    def reports_page(self, page_num=1, page_size=20, filter_=None, sort_=None, **kwargs):
        return self._reports(page_num, page_size, filter_, sort_, **kwargs)

    def reports_page_count(self, page_num=1, page_size=20, filter_=None, sort_=None, **kwargs):
        return int(self._reports(page_num, page_size, filter_, sort_, **kwargs).meta['last_page'])

    def reports_count(self, page_num=1, page_size=20, filter_=None, sort_=None, **kwargs):
        return int(self._reports(page_num, page_size, filter_, sort_, **kwargs).meta['total'])

    def get(self, id):
        data = {self._resource: [{'id': id}]}
        resp = self._request(self.READ_DETAIL, data)
        return resp[0] if resp and len(resp) else None

    def _write(self, data):
        data = {self._resource: [data]}
        resp = self._request(self.WRITE, data)
        return resp[0] if resp and len(resp) else None

    def delete(self, id):
        return self._write({'id': id, 'delete': 1})

    def delete_all(self):
        while self.count():
            for p in self.page(page_size=50):
                self.delete(p.id)

    def create(self, data):
        return self._write(data)

    def update(self, id, data):
        data['id'] = id
        return self._write(data)

    def bulk_update(self, bulk_action, data):
        data = {self._resource: data}
        data['bulk_action'] = bulk_action
        resp = self._request(self.WRITE, data)
        return resp if resp and len(resp) else None


class StitchApi(object):

    # Note that Attributes do not support any WRITE operations
    RESOURCES = [
        'Attributes',
        'Contacts',
        'ContactTags',
        'Invoices',
        'InvoicePayments',
        'Products',
        'PurchaseOrders',
        'SalesOrders',
        'Variants',
    ]

    def __init__(self, auth):
        headers = {
            'access_token': auth,
            'content-type': "application/json;charset=UTF-8",
            'cache-control': "no-cache",
        }
        for r in self.RESOURCES:
            setattr(self, r, StitchEndpoint(r, headers))
