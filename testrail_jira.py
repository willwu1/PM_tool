import base64
import json
import requests
import datetime
import logging
import os
import yaml
import sys
import argparse
from jira.client import JIRA
from jira.client import GreenHopper

# Testrail variables
PROJECT_FFV = 1
TEST_SUITE_ATOM = 13
TEST_SUITE_UEFI = 9
TEST_SUITE_BMC = 2
TEST_SUITE_DAE_ATOM = 1477
TEST_SUITE_DAE_BMC = 1478
CI_JIRA_URL = xxx
testrail_url = xxxxx

"""
testrail_jira.log format
infrasim@infrasim:~$ cat .testrail_jira.conf
jira:
    url:   xxxx
    user_name:  111111
    user_key: xxxxxxxxx
"""


def get_jira_config():
    """
    get jira config from config file, contain url , name, password
    """
    jira_config = {}
    conf_path = '{}/.testrail_jira.conf'.format(os.path.expanduser('~'))
    if os.path.isfile(conf_path):
        with open(conf_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        print("No Confluence config file.")
        sys.exit(1)

    jira_config['url'] = config['jira'].get('url')
    jira_config['user'] = config['jira'].get('user_name')
    jira_config['pwd'] = config['jira'].get('user_key')
    return jira_config


file_path = '{}/testrail_jira.log'.format(os.path.expanduser('~'))
logging.basicConfig(level=logging.DEBUG,
                    filename=file_path)

jira_config = get_jira_config()
jira_pwd = (base64.b64decode(jira_config['pwd'])).decode('utf-8')
myjira = JIRA(
    jira_config['url'],
    basic_auth=(jira_config['user'], (base64.b64decode(jira_config['pwd'])).decode('utf-8')),
    logging=True,
    validate=True,
    async_=True,
    async_workers=20,
    options={'verify': False},
)

greenhopper = GreenHopper(
    options={'server': CI_JIRA_URL, 'verify': False},
    basic_auth=(jira_config['user'], jira_pwd)
)


class Testclient(object):
    """
    testrail client, send request, and get info and data
    """
    def __init__(self, base_url):
        self.user = xxxxxxxxx
        self.password = xxxxxxxxx
        if not base_url.endswith('/'):
            base_url += '/'
        self.__url = base_url + 'index.php?/api/v2/'

    def send_get(self, uri, filepath=None):
        """Issue a GET request (read) against the API.

        Args:
            uri: The API method to call including parameters, e.g. get_case/1.
            filepath: The path and file name for attachment download; used only
                for 'get_attachment/:attachment_id'.

        Returns:
            A dict containing the result of the request.
        """
        return self.__send_request('GET', uri, filepath)

    def get_cases(self, project_id, case_filter=None):
        rest_uri = 'get_cases/{}{}'.format(project_id, case_filter)
        return self.send_get(rest_uri)

    def get_case(self, case_id):
        rest_uri = 'get_case/{}'.format(case_id)
        return self.send_get(rest_uri)

    def send_post(self, uri, data):
        """Issue a POST request (write) against the API.

        Args:
            uri: The API method to call, including parameters, e.g. add_case/1.
            data: The data to submit as part of the request as a dict; strings
                must be UTF-8 encoded. If adding an attachment, must be the
                path to the file.

        Returns:
            A dict containing the result of the request.
        """
        return self.__send_request('POST', uri, data)

    def __send_request(self, method, uri, data):
        url = self.__url + uri
        logging.debug(url)

        auth = str(
            base64.b64encode(
                bytes('%s:%s' % (self.user, self.password), 'utf-8')
            ),
            'ascii'
        ).strip()
        headers = {'Authorization': 'Basic ' + auth}

        if method == 'POST':
            if uri[:14] == 'add_attachment':    # add_attachment API method
                files = {'attachment': (open(data, 'rb'))}
                response = requests.post(url, headers=headers, files=files, verify=False)
                files['attachment'].close()
            else:
                headers['Content-Type'] = 'application/json'
                payload = bytes(json.dumps(data), 'utf-8')
                response = requests.post(url, headers=headers, data=payload, verify=False)
        else:
            headers['Content-Type'] = 'application/json'
            response = requests.get(url, headers=headers, verify=False)

        if response.status_code > 201:
            try:
                error = response.json()
            except Exception:     # response.content not formatted as JSON
                error = str(response.content)
                raise Exception('TestRail API returned HTTP %s (%s)' % (response.status_code, error))
        else:
            if uri[:15] == 'get_attachment/':   # Expecting file, not JSON
                try:
                    open(data, 'wb').write(response.content)
                    return (data)
                except Exception:
                    return ("Error saving attachment.")
            else:
                return response.json()


def same_time_check(test_createtime, expect_date):
    """
    check if test_createtime is the same with expect date
    """
    timestamp = datetime.datetime.fromtimestamp(test_createtime)
    if timestamp.date() == expect_date:
        return True
    else:
        return False


def check_new_case_create_issue(cases, timestamp, suite):
    """
    filter cases and find if there is case's created time match
    check if case could automatable , automate value :
    unknown:1  No:2  Yes:3
    """
    for case in cases:
        case_tr_id = case['id']
        if same_time_check(case['created_on'], timestamp) and (case['custom_ffv_automatable'] == 3):
            try:
                summary = '[{}]-{}'.format(case['id'], case['title'])
                logging.debug(summary)
                description = case.get('custom_preconds')
                if not description:
                    description = 'test case script'
                issue_dict_info = {
                    'project': {'key': 'ATOM'},
                    'summary': summary,
                    'description': description,
                    'issuetype': {'name': 'Test Case Script'},
                    'customfield_10006': 2,
                    'components': [{'name': 'DAE script'}],
                }
                new_issue = myjira.create_issue(fields=issue_dict_info)
                logging.debug('case {} : create jira story success {}'.format(case_tr_id, new_issue.key))

                issue_list = []
                issue_list.append(new_issue.key)
                if suite == TEST_SUITE_DAE_ATOM:
                    greenhopper.add_issues_to_epic('ATOM-4496', issue_list)
                elif suite == TEST_SUITE_DAE_BMC:
                    greenhopper.add_issues_to_epic('ATOM-4581', issue_list)

            except Exception as errorinfo:
                logging.error('case {} : create jira story fail on {}'.format(case_tr_id, timestamp))
                logging.error(errorinfo)


def filter_testrail_and_create_issue(day):
    """
    filter all suites and check if there is cases created on the day
    """
    testrail_obj = Testclient(testrail_url)
    suites = [TEST_SUITE_BMC, TEST_SUITE_UEFI, TEST_SUITE_ATOM, TEST_SUITE_DAE_ATOM, TEST_SUITE_DAE_BMC]
    for suite in suites:
        case_filter = '&suite_id={}'.format(suite)
        cases = testrail_obj.get_cases(PROJECT_FFV, case_filter)
        check_new_case_create_issue(cases, day, suite)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='sycn testrail cases to jira tool')

    parser.add_argument("-d", "--date", type=str,
                        help="date of testrail update time, example 2020-3-22")

    commandList = parser.parse_args()
    if not commandList.date:
        timestamp = datetime.datetime.today()
    else:
        timestamp = datetime.datetime.strptime(commandList.date, '%Y-%m-%d')
    timestamp = timestamp.date()
    logging.debug('update date: {}'.format(timestamp))
    create_case_issue = {}
    filter_testrail_and_create_issue(timestamp)
