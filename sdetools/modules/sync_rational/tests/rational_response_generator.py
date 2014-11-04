from sdetools.sdelib.testlib.response_generator import ResponseGenerator, RESPONSE_HEADERS


class RationalResponseGenerator(ResponseGenerator):
    def __init__(self, config, test_dir=None):
        self.username = config['alm_user']
        self.alm_server = config['alm_server']
        self.alm_project = config['alm_project']

        resource_templates = [
            'rootservices.json',
            'identity.json',
            'catalog.json',
            'services.json',
            'resourceshape.json',
            'priorities.json',
            'count.json',
            'workitem.json'
        ]
        rest_api_targets = {
            '.*/rootservices': 'get_rootservices',
            '.*/oslc/workitems/catalog': 'get_catalog',
            '.*/oslc/contexts/[^/]+/workitems/services': 'get_services',
            '.*/oslc/context/[^/]+/shapes/workitems/task': 'get_resourceshape',
            '.*/oslc/enumerations/[^/]+/priority/priority.literal.l.*': 'get_priorities',
            '.*/oslc/contexts/[^/]+/workitems/workitems\\?oslc.where=dcterms:title=.*': 'get_count',
            '.*/resource/itemName/com.ibm.team.workitem.WorkItem/\\d*': 'update_workitem',
            '.*/oslc/contexts/[^/]+/workitems/task': 'post_workitem',
            '.*/authenticated/identity': 'authenticate_identity',
        }
        super(RationalResponseGenerator, self).__init__(rest_api_targets, resource_templates, test_dir)

    def init_with_resources(self):
        """Loads the default responses"""

        for x in ['rootservices',
                  'catalog',
                  'services',
                  'identity',
                  'resourceshape',
                  'priorities',
                  'count']:
            self.generator_add_resource(x, resource_data=self.get_json_from_file(x))

    """
       Response functions
    """

    def authenticate_identity(self, target, flag, data, method):
        if not flag:
            response = self.generator_get_all_resource('identity')
            headers = [
                {'set-cookie': 'JazzFormAuth=Form'}
            ]
            return response, headers
        else:
            self.raise_error('404')

    def get_rootservices(self, target, flag, data, method):
        if not flag:
            return RESPONSE_HEADERS, self.generator_get_all_resource('rootservices')[0]
        else:
            self.raise_error('404')

    def get_catalog(self, target, flag, data, method):
        if not flag:
            catalog = self.generator_get_all_resource('catalog')[0]
            catalog['oslc:serviceProvider'][0]['dcterms:title'] = self.alm_project
            return RESPONSE_HEADERS, catalog
        else:
            self.raise_error('404')

    def get_services(self, target, flag, data, method):
        if not flag:
            return RESPONSE_HEADERS, self.generator_get_all_resource('services')[0]
        else:
            self.raise_error('404')

    def get_resourceshape(self, target, flag, data, method):
        if not flag:
            return RESPONSE_HEADERS, self.generator_get_all_resource('resourceshape')[0]
        else:
            self.raise_error('404')

    def get_priorities(self, target, flag, data, method):
        if not flag:
            return RESPONSE_HEADERS, self.generator_get_all_resource('priorities')[0]
        else:
            self.raise_error('404')

    def get_count(self, target, flag, data, method):
        if not flag:
            count = len(self.generator_get_all_resource('workitem'))
            res = self.generator_get_all_resource('count')[0]
            res['oslc:responseInfo']['oslc:totalCount'] = count
            return RESPONSE_HEADERS, res
        else:
            self.raise_error('404')

    def update_workitem(self, target, flag, data, method):
        if not flag:
            task_id = target.rsplit('/', 1)[1]
            if method == 'GET':
                res = self.generator_get_resource('workitem', str(task_id))
            elif method == 'DELETE':
                self.generator_remove_resource('workitem', task_id)
                res = ''
            return RESPONSE_HEADERS, res
        else:
            self.raise_error('404')

    def post_workitem(self, target, flag, data, method):
        if not flag:
            res = self.generate_resource_from_template('workitem', data)
            self.generator_add_resource('workitem', res['dcterms:identifier'], resource_data=res)
            return RESPONSE_HEADERS, res
        else:
            self.raise_error('404')
