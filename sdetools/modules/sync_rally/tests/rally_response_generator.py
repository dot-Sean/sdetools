import re

from sdetools.sdelib.testlib.response_generator import ResponseGenerator


class RallyResponseGenerator(ResponseGenerator):
    API_VERSION = '1.39'
    BASE_PATH = 'slm/webservice/%s' % API_VERSION

    def __init__(self, config, test_dir=None):
        base_path = 'slm/webservice/1.39'
        statuses = ['Defined', 'Completed', 'Accepted']
        rest_api_targets = {
            '/%s/task\.js' % base_path: 'get_tasks',
            '/%s/subscription\.js' % base_path: 'get_subscription',
            '/%s/project\.js' % base_path: 'get_project',
            '/%s/hierarchicalrequirement\.js' % base_path: 'get_requirements',
            '/%s/hierarchicalrequirement/[0-9]+\.js' % base_path: 'call_card',
            '/%s/hierarchicalrequirement/create\.js' % base_path: 'create_card',
            '/%s/typedefinition/[0-9]+\.js' % base_path: 'get_type_definition_by_id',
            '/%s/typedefinition\.js' % base_path: 'get_type_definitions'
        }
        super(RallyResponseGenerator, self).__init__(rest_api_targets, statuses, test_dir)

    """
       Response functions 
    """
    def get_type_definition_by_id(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                definition_id = re.search('[0-9]+(?=\.js$)', target).group(0)

                if definition_id == '14409160065':
                    return self.get_json_from_file('hierarchical_requirement_definition')
                else:
                    self.raise_error('404')
            self.raise_error('405')
        else:
            self.raise_error('401')

    def get_type_definitions(self, target, flag, data, method):
        if not flag:
            if method == 'GET':
                response = self._generate_query_result()
                params = self.get_url_parameters(target)
                query = params.get('query')

                if query:
                    query = self._parse_rally_query(query[0])

                    if query.get('Name') == '"Hierarchical Requirement"':
                        result = self._generate_result(query.get('Name'), 'HierarchicalRequirement', '14409160065')
                        response['QueryResult']['TotalResultCount'] = 1
                        response['QueryResult']['Results'].append(result)

                return response
            self.raise_error('405')
        else:
            self.raise_error('401')

    def get_tasks(self, target, flag, data, method):
        if not flag:
            return self.get_json_from_file('task')
        else:
            self.raise_error('401')

    def get_subscription(self, target, flag, data, method):
        if not flag:
            return self.get_json_from_file('subscription')
        else:
            self.raise_error('401')

    def get_project(self, target, flag, data, method):
        if not flag:
            return self.get_json_from_file('project')
        else:
            self.raise_error('401')

    def get_requirements(self, target, flag, data, method):
        if not flag:
            params = self.get_url_parameters(target)
            task_number = self.extract_task_number_from_title(params['query'][0])
            task = self.generator_get_task(task_number)
            requirements = self.get_json_from_file('hierarchical_requirements')

            if task:
                result = requirements['QueryResult']['Results'][0]
                new_ref = re.sub('[0-9]+(?=\.js)', task_number, result['_ref'])
                result['_ref'] = new_ref
                result['_refObjectName'] = task['name']
            else:
                requirements['QueryResult']['TotalResultCount'] = 0
                requirements['QueryResult']['Results'] = []

            return requirements
        else:
            self.raise_error('401')

    def call_card(self, target, flag, data, method):
        if not flag:
            task_number = re.search('[0-9]+(?=\.js$)', target).group(0)
            task = self.generator_get_task(task_number)

            if not task:
                self.raise_error('405')
            if method == 'GET':
                card = self.get_json_from_file('card')
                card_data = card['HierarchicalRequirement']
                card_data['FormattedID'] = task_number
                new_ref = re.sub('[0-9]+(?=\.js$)', task_number, card_data['_ref'])
                card_data['_ref'] = new_ref
                card_data['ScheduleState'] = task['status']
                card_data['_refObjectName'] = task['name']
                card_data['Name'] = task['name']

                return card
            elif method == 'POST':
                new_status = data['HierarchicalRequirement']['ScheduleState']
                self.generator_update_task(task_number, 'status', new_status)

                return None
        else:
            self.raise_error('404')

    def create_card(self, target, flag, data, method):
        if not flag:
            create_args = data['HierarchicalRequirement']
            task_number = self.extract_task_number_from_title(create_args['Name'])
            task = self.generator_get_task(task_number)

            if not task:
                self.generator_add_task(task_number, create_args['Name'])
                return self.get_json_from_file('create_result')
            else:
                self.raise_error('405')
        else:
            self.raise_error('401')

    # Generator Functions
    def _generate_query_result(self):
        return self.get_json_from_file('queryresult')

    def _generate_result(self, object_name, object_type, ref_id):
        return {
            "_rallyAPIMajor": 1,
            "_rallyAPIMinor": 39,
            "_ref": "https://rally1.rallydev.com/slm/webservice/1.39/typedefinition/%s.js" % ref_id,
            "_refObjectName": object_name,
            "_type": object_type
        }

    @staticmethod
    def _parse_rally_query(query):
        """ Converts a rally query into a python dict.
            E.g. (Name = "Requirement") -> {'Name': 'Requirement'}
        """
        query = re.findall('(?<=\()[^()]*(?=\))', query)
        query = [re.split('\s*contains\s*|\s*=\s*', q) for q in query]

        return dict(query)