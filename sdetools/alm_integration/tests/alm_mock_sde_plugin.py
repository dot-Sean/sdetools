"""

   IMPORT THIS FILE BEFORE IMPORTING THE ALM CONNECTOR 

"""
from mock import patch
from json import JSONEncoder
import re

def mock_sde_connect(self):
	pass

def mock_is_sde_connected(self):
    return True
    
def mock_sde_get_tasks(self):
    tasklist = []
    tasklist.append(generate_sde_task(10))
    tasklist.append(generate_sde_task(9))
    tasklist.append(generate_sde_task(7))
    tasklist.append(generate_sde_task(5))
    tasklist.append(generate_sde_task(3))
    tasklist.append(generate_sde_task(1))

    return tasklist

def mock_sde_get_task(self, id):
    task_id = re.search('[0-9]*$', id).group(0)

    return generate_sde_task(int(task_id))

def mock_sde_update_task_status(self, task, status):
    pass

def mock_sde_get_task_content(self, task):
    return 'Task content'

def generate_sde_task(priority, project_id=1000):
    return {"status": "TODO",
            "contextrulesets": [],
            "timestamp": 1379518767,
            "note_count": 35,
            "implementations": [
                {
                    "contextrulesets": [],
                    "url": "https://www.sdelements.com/library/tasks/T21/django/",
                    "title": "I176: Django",
                    "id": "I176",
                    "content": "Implement content",
                    "slug": "django"
                },
                {
                    "contextrulesets": [],
                    "url": "https://www.sdelements.com/library/tasks/T21/manually-with-network-monitoring-tools/",
                    "title": "I389: Manually with network monitoring tools",
                    "id": "I389",
                    "content": "Testing description",
                    "slug": "manually-with-network-monitoring-tools"
                }
            ],
            "phase": "requirements",
            "id": "%d-T%d" % (project_id, priority),
            "categories": [
                "Cryptography",
                "Session Management",
                "Authentication"
            ],
            "priority": priority,
            "weakness": {
                "content": "Weakness description",
                "cwe": [
                    {
                        "url": "http://cwe.mitre.org/data/definitions/cwe_id",
                        "title": "External link to learn more",
                        "cwe_id": 319
                    }
                ],
                "id": "P%d" % priority,
                "title": "P%d: Weakness title" % priority
            },
            "title": "T%d: Task title" % priority,
            "url": "https://www.sdelements.com/library/tasks/T%d/" % priority,
            "age": "current",
            "project": project_id,
            "assigned_to": [],
            "content": "Security requirements description",
            "verification_coverage": [
                "No Automated Dynamic Analysis Coverage"
            ]
        }
        
# Patch SDE Calls
patch('sdetools.modules.sync_jira.jira_plugin.AlmConnector.sde_connect', mock_sde_connect).start()
patch('sdetools.modules.sync_jira.jira_plugin.AlmConnector.is_sde_connected', mock_is_sde_connected).start()
patch('sdetools.modules.sync_jira.jira_plugin.AlmConnector.sde_get_tasks', mock_sde_get_tasks).start()
patch('sdetools.modules.sync_jira.jira_plugin.AlmConnector.sde_get_task', mock_sde_get_task).start()
patch('sdetools.modules.sync_jira.jira_plugin.AlmConnector.sde_update_task_status', mock_sde_update_task_status).start()
patch('sdetools.modules.sync_jira.jira_plugin.AlmConnector.sde_get_task_content', mock_sde_get_task_content).start()
