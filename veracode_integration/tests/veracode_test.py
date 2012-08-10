#NOTE: Before running ensure that the options are set
#properly in the configuration file

import sys, os, unittest
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from veracode_integration.veracode_integrator import VeracodeIntegrator
from sdelib.conf_mgr import config
from xml.dom import minidom

CONF_FILE_LOCATION = 'test_settings.conf'

class TestVeracode(unittest.TestCase):
     def setUp(self):
          self.integrator = VeracodeIntegrator(config)
          config.parse_config_file(CONF_FILE_LOCATION)
          self.integrator.init_plugin()
          self.assertTrue(True)

     def execute_import_findings(self, commit):

          try:
              task_list = self.integrator.plugin.get_task_list()
          except:
              assertTrue(False)

          total_nontest_tasks = 0
          for task in task_list:
              if(task['phase'] in ['testing']):
                  continue
              total_nontest_tasks += 1

          self.integrator.load_mapping_from_xml()
          self.integrator.parse()
          findings = self.integrator.get_findings()
          xml_findings_count=0
          try:
              base = minidom.parse(config['report_xml'])
              xml_findings_count = len(base.getElementsByTagName('flaw'))
          except:
              self.assertTrue(False)
          self.assertTrue( xml_findings_count == len(findings)  )

          result = self.integrator.import_findings(commit)
          self.assertTrue(result.error_count==0)
          all_tasks_sanity_check = (len(result.noflaw_tasks)+len(result.affected_tasks)) == total_nontest_tasks
          self.assertTrue(all_tasks_sanity_check)
          self.assertTrue(result.error_cwes_unmapped==0)

          if(not commit):
              return

          for task_id in result.noflaw_tasks:
              api_result = self.integrator.plugin.get_notes("T%d"%task_id)
              notes = api_result['notes']
              last_note = notes[len(notes)-1]
              self.assertTrue(last_note['text'].find(result.import_datetime) > -1 )
              self.assertTrue(last_note['status'] == "DONE")

          for task_id in result.affected_tasks:
              api_result = self.integrator.plugin.get_notes("T%d"%task_id)
              notes = api_result['notes']
              last_note = notes[len(notes)-1]
              self.assertTrue(last_note['text'].find(result.import_datetime) > -1 )
              self.assertTrue(last_note['status'] == "TODO")

     def test_run_uncommitted(self):
          self.execute_import_findings(False)

     def test_run_commit(self):
          self.execute_import_findings(True)
    
if __name__ == "__main__":
    unittest.main()

