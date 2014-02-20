from sdetools.sdelib.testlib.response_generator import ResponseGenerator


class RationalResponseGenerator(ResponseGenerator):
    def __init__(self, config, test_dir=None):
        self.username = config['alm_user']
        self.alm_server = config['alm_server']
        resource_templates = ['rootservices.json', 'catalog.json', 'services.json', 'resourceshape.json', 'priorities.json', 'count.json', 'workitem.json']
        rest_api_targets = {
            '.*/rootservices': 'get_rootservices',
            '.*/oslc/workitems/catalog': 'get_catalog',
            '.*/oslc/contexts/_gkmCkniWEeOI1P1pr3yq5Q/workitems/services': 'get_services',
            '.*/oslc/context/_gkmCkniWEeOI1P1pr3yq5Q/shapes/workitems/task': 'get_resourceshape',
            '.*/oslc/enumerations/_gkmCkniWEeOI1P1pr3yq5Q/priority/priority.literal.l.*': 'get_priorities',
            '.*/oslc/contexts/_gkmCkniWEeOI1P1pr3yq5Q/workitems/workitems\\?oslc.where=dcterms:title=.*': 'get_count',
            '.*/resource/itemName/com.ibm.team.workitem.WorkItem/\\d*': 'get_workitem',
            '.*/oslc/contexts/_gkmCkniWEeOI1P1pr3yq5Q/workitems/task': 'post_workitem',
        }
        super(RationalResponseGenerator, self).__init__(rest_api_targets, resource_templates, test_dir)

    def init_with_resources(self):
        for x in ['rootservices', 'catalog', 'services', 'resourceshape', 'priorities', 'count', 'workitem']:
            self.generator_add_resource(x, resource_data=self.get_json_from_file(x))

    def raise_error(self, error_code, message=None):
        if message is None:
            if error_code == '401':
                message = {
                    "message": "Requires authentication",
                }
            elif error_code == '404':
                message = {
                    "message": "Not found",
                }
            elif error_code == '422':
                message = {
                    "message": "Validation Failed",
                    "errors": [{
                        "resource": "Issue",
                        "field": "title",
                        "code": "missing_field"
                    }]
                }
            else:
                message = {
                    "message": "Error",
                }
        super(RationalResponseGenerator, self).raise_error(error_code, message['message'])

    """
       Response functions
    """

    def get_rootservices(self, target, flag, data, method):
        if not flag:
            return self.generator_get_all_resource('rootservices')[0]
        else:
            self.raise_error('404')

    def get_catalog(self, target, flag, data, method):
        if not flag:
            return self.generator_get_all_resource('catalog')[0]
        else:
            self.raise_error('404')

    def get_services(self, target, flag, data, method):
        if not flag:
            return self.generator_get_all_resource('services')[0]
        else:
            self.raise_error('404')

    def get_resourceshape(self, target, flag, data, method):
        if not flag:
            return self.generator_get_all_resource('resourceshape')[0]
        else:
            self.raise_error('404')

    def get_priorities(self, target, flag, data, method):
        if not flag:
            return self.generator_get_all_resource('priorities')[0]
        else:
            self.raise_error('404')

    def get_count(self, target, flag, data, method):
        if not flag:
            return self.generator_get_all_resource('count')[0]
        else:
            self.raise_error('404')

    def get_workitem(self, target, flag, data, method):
        if not flag:
            res = self.generator_get_all_resource('workitem')[0]
            #print res
            return res
        else:
            self.raise_error('404')

    def post_workitem(self, target, flag, data, method):
        #print method
        if not flag:
            res = self.generator_get_all_resource('workitem')[0]
            for x in data:
                res[x] = data[x]
            self.generator_update_resource('workitem', '0', update_args=res)
            return res
        else:
            self.raise_error('404')


    def sde_app(self, target, flag, data, method):
        if not flag:
            return self.generator_get_all_resource('sde_app')[0]
        else:
            self.raise_error('404')

    def sde_proj(self, target, flag, data, method):
        if not flag:
            return self.generator_get_all_resource('sde_proj')[0]
        else:
            self.raise_error('404')

    def sde_tasks(self, target, flag, data, method):
        if not flag:
            return self.generator_get_all_resource('sde_task')[0]
        else:
            self.raise_error('404')

    def sde_task(self, target, flag, data, method):
        if method == 'PUT':
            if not flag:
                res = self.generator_get_all_resource('sde_task1')[0]
                for x in data:
                    res[x] = data[x]
                self.generator_update_resource('sde_task1', '0', update_args=res)
                return res
            else:
                self.raise_error('404')
        else:
            if not flag:
                return self.generator_get_all_resource('sde_task1')[0]
            else:
                self.raise_error('404')