from __future__ import (absolute_import, division, print_function)
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
import json
import requests
import sys
import csv
import io
import os
from ansible.utils.display import Display
display = Display()

if 'D42_SKIP_SSL_CHECK' in os.environ and os.environ['D42_SKIP_SSL_CHECK'] == 'True':
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

if 'D42_URL' not in os.environ:
    print('Please set D42_URL environ.')
    sys.exit()

if 'D42_USER' not in os.environ:
    print('Please set D42_USER environ.')
    sys.exit()

if 'D42_PWD' not in os.environ:
    print('Please set D42_PWD environ.')
    sys.exit()


__metaclass__ = type


class LookupModule(LookupBase):

    @staticmethod
    def get_list_from_csv(text):
        f = io.StringIO(text)
        output_list = []
        dict_reader = csv.DictReader(f, quotechar='"', delimiter=',', quoting=csv.QUOTE_ALL, skipinitialspace=True,
                                     dialect='excel')
        for item in dict_reader:
            output_list.append(item)

        if len(output_list) == 1:
            output_list = [output_list, ]

        return output_list

    def run(self, terms, variables=None, **kwargs):
        conf = {
            'D42_URL': os.environ['D42_URL'],
            'D42_USER': os.environ['D42_USER'],
            'D42_PWD': os.environ['D42_PWD']
        }

        if terms[1] == "password":
            return self.get_user_pass(conf, terms[0], terms[2])
        elif terms[1] == "doql":
            return self.run_doql(conf, terms[0], terms[2])

    def get_user_pass(self, conf, device, username):
        url = conf['D42_URL'] + "/api/1.0/passwords/?plain_text=yes&device=" + device + "&username=" + username
        resp = requests.request("GET",
                                url,
                                auth=(conf['D42_USER'], conf['D42_PWD']),
                                verify=False)

        if resp.status_code != 200:
            raise AnsibleError("API Call failed with status code: " + str(resp.status_code))
        if not resp.text:
            raise AnsibleError("Something went wrong!")

        req = json.loads(resp.text)
        req = req["Passwords"]
        if req:
            if len(req) > 1:
                raise AnsibleError("Multiple users found for device: %s" % device)
            return [req[0]["password"]]
        else:
            raise AnsibleError("No password found for user: %s and device: %s" % (username, device))

    def run_doql(self, conf, query, output_type):
        url = conf['D42_URL'] + "/services/data/v1.0/query/"

        post_data = {
            "query": query.replace("@", "'"),
            "header": 'yes' if output_type == 'list_dicts' else 'no'
        }

        resp = requests.request("POST", url, auth=(conf['D42_USER'], conf['D42_PWD']), data=post_data, verify=False)

        if resp.status_code != 200:
            raise AnsibleError("API Call failed with status code: " + str(resp.status_code))

        if output_type == 'string':
            return [resp.text.replace('\n', ''), ]
        elif output_type == 'list':
            return resp.text.split('\n')

        return self.get_list_from_csv(resp.text)
