import requests
import json


class StitchApiEntity(object):

    def __init__(self, resource, data, parent):
        self.resource = resource
        self.id = data.get('id')
        self.data = data
        self.links = self.data.get('links', {})
        self._parent_result = parent

    def get_linked(self, resource, drill=True):
        if resource not in self.links and drill:
            return self.detail().get_linked(resource, drill=False)

        linked_ids = [l['id'] for l in self.links.get(resource, [])]
        loaded_resources = self._parent_result.sideloaded.get(resource, {})
        relevant_resources = [e for k, e in loaded_resources.items() if k in linked_ids]
        return [StitchApiEntity(resource, e, self._parent_result) for e in relevant_resources]

    def detail(self):
        return self._parent_result._endpoint.get(self.id)

    def __repr__(self):
        return 'StitchApiEntity(%s, %s)' % (self.resource, self.data)


class StitchApiResult(object):

    def __init__(self, parsed_response, resource, parent):
        self._endpoint = parent
        self._resource = resource
        self._entities = [StitchApiEntity(resource, r, self) for r in parsed_response.get(resource, [])]
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
    WRITE = ('write', 'https://api-pub.stitchlabs.com/api2/v1/%s')

    def _request(self, action, data):
        data['action'] = action[0]
        uri = action[1] % self._resource
        try:
            response = requests.request("POST",
                                        uri,
                                        data=json.dumps(data),
                                        headers=self._headers)
        except Exception as e:
            print ('Request to %s with %s failed with: %s' % (uri, data, e))
            raise Exception('Request to %s with %s failed with: %s' % (uri, data, e))

        if response.status_code in [200, 201, 206]:
            try:
                return StitchApiResult(response.json(), self._resource, self)
            except Exception as e:
                print ('Failed to parse json response. Request to %s with %s returned non-json content: %s'
                         % (uri, data, response.content))
                Exception('Failed to parse json response. Request to %s with %s returned non-json content: %s'
                         % (uri, data, response.content))
        else:
            print ('Request to %s with %s returned status code %s and content %s'
                            % (uri, data, response.status_code, response.content))
            raise Exception('Request to %s with %s returned status code %s and content %s'
                            % (uri, data, response.status_code, response.content))

    def __init__(self, resource, headers):
        self._headers = headers
        self._resource = resource

    def _list(self, page_num=1, page_size=20, filter_=None, sort_=None):
        data = {
            'page_num': page_num,
            'page_size': page_size,
            'filter': filter_ or {},
            'sort': sort_ or {}
        }
        return self._request(self.READ, data)

    def page(self, page_num=1, page_size=20, filter_=None):
        return self._list(page_num, page_size, filter_)

    def page_count(self, page_size=20):
        return self._list(page_size=page_size).meta['last_page']

    def count(self, filter_=None):
        return int(self._list(page_size=1, filter_=filter_).meta['total'])

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


class StitchApi(object):

    RESOURCES = [
        'Products',
        'Variants',
        'SalesOrders',
        'Contacts',
        'ContactTags',
        'PurchaseOrders'
    ]

    def __init__(self, auth):
        headers = {
            'access_token': auth,
            'content-type': "application/json;charset=UTF-8",
            'cache-control': "no-cache",
        }
        for r in self.RESOURCES:
            setattr(self, r, StitchEndpoint(r, headers))
