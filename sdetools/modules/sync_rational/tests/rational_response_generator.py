from sdetools.sdelib.testlib.response_generator import ResponseGenerator
from sdetools.sdelib.commons import urlencode_str
import json


class RationalResponseGenerator(ResponseGenerator):
    def __init__(self, config, test_dir=None):
        #project_uri = '%s/%s' % (urlencode_str(config['github_repo_owner']), urlencode_str(config['alm_project']))
        #self.project_milestone = config['alm_project_version']
        self.username = config['alm_user']
        self.alm_server = config['alm_server']
        #self.alm_project = config['alm_project']
        resource_templates = ['sde_task1.json', 'sde_task.json', 'sde_proj.json', 'sde_app.json', 'rootservices.json', 'catalog.json', 'services.json', 'resourceshape.json', 'priorities.json', 'count.json', 'workitem.json']
        rest_api_targets = {
            '.*/rootservices': 'get_rootservices',
            '.*/oslc/workitems/catalog': 'get_catalog',
            '.*/oslc/contexts/_gkmCkniWEeOI1P1pr3yq5Q/workitems/services': 'get_services',
            '.*/oslc/context/_gkmCkniWEeOI1P1pr3yq5Q/shapes/workitems/task': 'get_resourceshape',
            '.*/oslc/enumerations/_gkmCkniWEeOI1P1pr3yq5Q/priority/priority.literal.l.*': 'get_priorities',
            '.*/oslc/contexts/_gkmCkniWEeOI1P1pr3yq5Q/workitems/workitems\\?oslc.where=dcterms:title=.*': 'get_count',
            '.*/resource/itemName/com.ibm.team.workitem.WorkItem/\\d*': 'get_workitem',
            '.*/oslc/contexts/_gkmCkniWEeOI1P1pr3yq5Q/workitems/task': 'post_workitem',
            #'.*/api/applications.*': 'sde_app',
            #'.*/api/projects.*': 'sde_proj',
            #'.*/api/tasks/.*': 'sde_task',
            #'.*/api/tasks(?!/).*': 'sde_tasks',
            #response doesn't matter, reusing sde_task response for simplicity
            #'.*/api/tasknotes/ide.*': 'sde_task'
        }
        super(RationalResponseGenerator, self).__init__(rest_api_targets, resource_templates, test_dir)

    def init_with_resources(self):
        #self.generator_add_resource('sde_task', resource_data=json.loads(open('./response/sde_task.json').read()))
        #self.generator_add_resource('sde_task1', resource_data=json.loads(open('./response/sde_task1.json').read()))
        #self.generator_add_resource('sde_proj', resource_data=json.loads(open('./response/sde_proj.json').read()))
        #self.generator_add_resource('sde_app', resource_data=json.loads(open('./response/sde_app.json').read()))
        self.generator_add_resource('rootservices', resource_data=json.loads(open('./response/rootservices.json').read()))
        self.generator_add_resource('catalog', resource_data=json.loads(open('./response/catalog.json').read()))
        self.generator_add_resource('services', resource_data=json.loads(open('./response/services.json').read()))
        self.generator_add_resource('resourceshape', resource_data=json.loads(open('./response/resourceshape.json').read()))
        self.generator_add_resource('priorities', resource_data=json.loads(open('./response/priorities.json').read()))
        self.generator_add_resource('count', resource_data=json.loads(open('./response/count.json').read()))
        self.generator_add_resource('workitem', resource_data=json.loads(open('./response/workitem.json').read()))

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