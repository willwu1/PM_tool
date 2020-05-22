import pandas as pd
import re
import argparse
import jenkins
import os
import datetime
import base64
import json
import requests
import logging
import sys
from testrail_jira import myjira


# Testrail variables
PROJECT_FFV = 1
TEST_SUITE_ATOM = 13
TEST_SUITE_UEFI = 9
TEST_SUITE_BMC = 2
TEST_SUITE_DAE_ATOM = 1478
TEST_SUITE_DAE_BMC = 1477
CI_JIRA_URL = 
testrail_url = 

# Const
os.environ.setdefault("PYTHONHTTPSVERIFY", "0")
FIRST_BUILD_COLUMN = 7
VALUABLE_RATE = {"Daily_CI_Redfish": 0.6,
                 "Daily_CI_DAE": 0.8,
                 "Weekly_Stress_DAE": 0.3}
jirafics_dict = {}
BUG_DICT = {}


class Testclient(object):
    """
    testrail client, send request, and get info and data
    """
    def __init__(self, base_url):
        self.user = 
        self.password = 
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

    def __send_request(self, method, uri, data):
        url = self.__url + uri
        logging.debug(url)
        if sys.version_info[0] < 3:
            auth = base64.b64encode('%s:%s' % (self.user, self.password))
            payload = bytes(json.dumps(data))
        else:
            auth = str(
                base64.b64encode(
                    bytes('%s:%s' % (self.user, self.password), 'utf-8')
                ),
                'ascii'
            ).strip()
            payload = bytes(json.dumps(data), 'utf-8')
        headers = {'Authorization': 'Basic ' + auth}

        if method == 'POST':
            if uri[:14] == 'add_attachment':    # add_attachment API method
                files = {'attachment': (open(data, 'rb'))}
                response = requests.post(url, headers=headers, files=files, verify=False)
                files['attachment'].close()
            else:
                headers['Content-Type'] = 'application/json'
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


def connect_to_jenkins():
    server = jenkins.Jenkins(, username=,
                             password=')
    print("connect to Jenkins server done")
    print(server.get_version())
    return server


def get_case_id_from_string(casename):
    """
    get case id from casename
    """
    searchObj = re.search('(C[0-9]{2,20})', casename, re.M | re.I)
    if searchObj:
        return searchObj.group(1)
    else:
        return None


def get_bugs_from_jira():
    JQL = "project = atom and Status != completed and issueType = bug and summary ~ 'CI bug fix'"
    issuedata = myjira.search_issues(JQL)
    for issue in issuedata:
        caseid = get_case_id_from_string(issue.fields.summary)
        if caseid:
            BUG_DICT[caseid] = issue.key


def write_column_data():
    # save for new testresult table
    data = pd.read_csv("TestResults.csv", keep_default_na=False,)
    data.head()

    caseid = []
    ten_fail_list = []
    all_fail_list = []
    all_run_list = []
    passrate = []
    rowlength = len(data.index)
    for i in range(0, rowlength):
        casename = data.loc[i].at['Class']
        caseid.append(get_case_id_from_string(casename))

    for index, row in data.iterrows():
        rowlist = row.to_list()
        ten_fail = 0
        all_fail = 0
        all_run = 0
        current_passrate = 0
        for result in rowlist[1:]:
            if result in ['FAILED', 'BLOCKED']:
                all_run += 1
                all_fail += 1
                if all_run < 11:
                    ten_fail += 1
            elif result in ['PASSED']:
                all_run += 1
        ten_fail_list.append(ten_fail)
        all_fail_list.append(all_fail)
        all_run_list.append(all_run)
        if all_run:
            current_passrate = (all_run - all_fail) / all_run
        passrate.append(current_passrate)

    data.insert(1, "Test Run", all_run_list)
    data.insert(1, "PassRate", passrate)
    data.insert(1, "Fail time in last ten runs", ten_fail_list)
    data.insert(1, "Fail time in all runs", all_fail_list)
    data.insert(0, "caseid", caseid)
    # import pdb
    # pdb.set_trace()
    # displaying datdf = df.drop('column_name', 1)a frame again - Output 2
    data.head()

    data.to_csv('test2result.csv', index=False)


def update_analysis_data(dataf, worksheet, recent_build=1024):
    """
    dataf:  dataframe of case
    recent_build:  recent build number def
    """
    all_fail_list = []
    ten_fail_list = []
    thirty_fail_list = []
    current_passrate_list = []
    all_run_list = []
    jira_list = []
    for index, row in dataf.iterrows():
        rowlist = row.to_list()
        if jirafics_dict and rowlist[0] in jirafics_dict.keys():
            # worksheet.write("B{}".format(index + 2), jirafics_dict[rowlist[0]])
            jira_list.append(jirafics_dict[rowlist[0]])
        elif BUG_DICT and rowlist[0] in BUG_DICT.keys():
            jira_list.append(BUG_DICT[rowlist[0]])
        else:
            jira_list.append("no ticket")


        ten_fail = 0
        all_fail = 0
        all_run = 0
        thirty_fail = 0
        current_passrate = 0
        for result in rowlist[FIRST_BUILD_COLUMN:]:
            if all_run >= recent_build:
                break
            if result in ['FAILED', 'BLOCKED']:
                all_run += 1
                all_fail += 1
                if all_run < 11:
                    ten_fail += 1
                if all_run < 31:
                    thirty_fail += 1
            elif result in ['PASSED']:
                all_run += 1
        if all_run:
            current_passrate = "{:.2%}".format((all_run - all_fail) / all_run)
        all_fail_list.append(all_fail)
        ten_fail_list.append(ten_fail)
        thirty_fail_list.append(thirty_fail)
        current_passrate_list.append(current_passrate)
        all_run_list.append(all_run)

    for i in range(len(all_run_list)):
        cell_jira_issue = 'B{}'.format(i+2)
        cell_all_fail = 'C{}'.format(i+2)
        cell_thirty_fail = 'D{}'.format(i+2)
        cell_ten_fail = "E{}".format(i+2)
        cell_passrate = "F{}".format(i+2)
        cell_allrun = "G{}".format(i+2)
        if 'ATOM' in jira_list[i]:
            atomurl = '{}'.format(jira_list[i])
            worksheet.write_url(cell_jira_issue, atomurl, string=jira_list[i])
        else:
            worksheet.write(cell_jira_issue, jira_list[i])
        worksheet.write(cell_all_fail, all_fail_list[i])
        worksheet.write(cell_thirty_fail, thirty_fail_list[i])
        worksheet.write(cell_ten_fail, ten_fail_list[i])
        worksheet.write(cell_passrate, current_passrate_list[i])
        worksheet.write(cell_allrun, all_run_list[i])


def get_last_build_number(jenkins_server, job_name):
    build_info = jenkins_server.get_job_info(name=job_name)
    # first_build = build_info['firstBuild']['number']
    return build_info['lastBuild']['number']


def get_new_build_data(dataframe, cases):
    """
    get cases result and check if there is new cases
    """
    cases_map = {}
    build_list = []
    for case in cases:
        caseid = get_case_id_from_string(case['name'])
        cases_map[caseid] = case['status']
        if case['errorDetails']:
            searchObj = re.search('(JIRAFICS-[0-9]{2,20})', case['errorDetails'], re.M|re.I)
            if searchObj:
                buginfo = myjira.issue(searchObj.group(1))
                if jirafics_dict.get(caseid):
                    continue
                if buginfo and buginfo.fields.status.name in ['Closed', 'Fixed']:
                    jirafics_dict[caseid] = searchObj.group(1) + " -- fixed still fail"
                else:
                    jirafics_dict[caseid] = searchObj.group(1) + " -- known fw issue"
    rowlength = len(dataframe.index)
    for i in range(0, rowlength):
        caseid = dataframe.loc[i].at['caseid']
        status = cases_map.get(caseid)
        if status:
            cases_map.pop(caseid)
            if status in ['REGRESSION']:
                status = 'FAILED'
            elif status in ['FIXED']:
                status = 'PASSED'
            build_list.append(status)
        else:
            build_list.append('N/A')
    return build_list, cases_map


def update_case_sheet_data(jenkins_server, datacase, databuild, job_name, valid_buid):
    last_build_jenkens = get_last_build_number(jenkins_server, job_name)
    new_build_list = []
    last_buid_in_local = int(datacase.columns[FIRST_BUILD_COLUMN])
    if (last_build_jenkens > last_buid_in_local):
        for i in range(last_buid_in_local + 1, last_build_jenkens + 1):
            build_number = i
            # if build number can not find in jenkens , it will return None
            build_test_result = jenkins_server.get_build_test_report(name=job_name, number=build_number)
            if build_test_result and len(build_test_result['suites'][0]['cases']) > valid_buid:
                build_info = jenkins_server.get_build_info(name=job_name, number=build_number)

                release = build_info["description"]
                enclosure = build_info["displayName"].split(" ")[4]
                rack = build_info["displayName"].split(" ")[5]
                pass_count = build_test_result["passCount"]
                fail_count = build_test_result["failCount"]
                skip_count = build_test_result["skipCount"]
                float_passrate = (float)(pass_count + skip_count) / (pass_count + fail_count + skip_count)
                # valuable build passrate
                if float_passrate < VALUABLE_RATE[job_name]:
                    continue
                # TODO  wait for fkp2 fixed
                if "fkp2" in enclosure:
                    continue
                passrate = "{:.2%}".format(float_passrate)

                builddate = datetime.datetime.fromtimestamp(build_info['timestamp'] / 1e3)
                builddate = builddate.date()
                build_msg = [builddate, release, enclosure, rack, pass_count, fail_count, skip_count, passrate]
                databuild.insert(1, build_number, build_msg)

                if build_test_result['suites'][0]['cases']:
                    new_build_list, new_cases_info = get_new_build_data(datacase, build_test_result['suites'][0]['cases'])
                    datacase.insert(FIRST_BUILD_COLUMN, build_number, new_build_list)
                    if new_cases_info:
                        for key in new_cases_info:
                            new_case = {}
                            new_case['caseid'] = key
                            new_case[build_number] = new_cases_info[key]
                            datacase = datacase.append(new_case, ignore_index=True)

    datacase = datacase.fillna('N/A')
    datacase = datacase.sort_values('caseid')
    return datacase, databuild


def check_miss_build(jenkins_server, datacase, databuild, job_name, valid_buid):
    last_build = int(datacase.columns[FIRST_BUILD_COLUMN])
    for build_number in range(last_build - 6, last_build):
        if build_number in datacase.columns[FIRST_BUILD_COLUMN:(FIRST_BUILD_COLUMN + 6)]:
            continue
        else:
            build_test_result = jenkins_server.get_build_test_report(name=job_name, number=build_number)
            if build_test_result and len(build_test_result['suites'][0]['cases']) > valid_buid:
                build_info = jenkins_server.get_build_info(name=job_name, number=build_number)

                release = build_info["description"]
                enclosure = build_info["displayName"].split(" ")[4]
                rack = build_info["displayName"].split(" ")[5]
                pass_count = build_test_result["passCount"]
                fail_count = build_test_result["failCount"]
                skip_count = build_test_result["skipCount"]
                float_passrate = (float)(pass_count + skip_count) / (pass_count + fail_count + skip_count)
                # valuable build passrate
                if float_passrate < VALUABLE_RATE[job_name]:
                    continue
                # TODO  wait for fkp2 fixed
                if "fkp2" in enclosure:
                    continue
                passrate = "{:.2%}".format(float_passrate)

                builddate = datetime.datetime.fromtimestamp(build_info['timestamp'] / 1e3)
                builddate = builddate.date()
                build_msg = [builddate, release, enclosure, rack, pass_count, fail_count, skip_count, passrate]
                databuild.insert(1, build_number, build_msg)

                if build_test_result['suites'][0]['cases']:
                    new_build_list, new_cases_info = get_new_build_data(datacase, build_test_result['suites'][0]['cases'])
                    datacase.insert(FIRST_BUILD_COLUMN, build_number, new_build_list)
                    if new_cases_info:
                        for key in new_cases_info:
                            new_case = {}
                            new_case['caseid'] = key
                            new_case[build_number] = new_cases_info[key]
                            datacase = datacase.append(new_case, ignore_index=True)
    datacase = datacase.fillna('N/A')
    datacase = datacase.sort_values('caseid')
    return datacase, databuild


def update_excel_and_fill_na(jenkins_server, job_name='Daily_CI_DAE', buildtime=1024, valid_buid=100):
    # dataf = pd.read_csv("case1test.csv", keep_default_na=False)
    # new_info = {'caseid': 'C1200000', '134': 'PASSED'}
    # dataf = dataf.append(new_info, ignore_index=True)
    # dataf = dataf.fillna('N/A')
    # dataf.to_csv('test2result.csv', index=False)
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    all_data = pd.ExcelFile(final_file)
    # sheet_names = all_data.sheet_names  # see all sheet names
    # for name in sheet_names:

    datacase = all_data.parse('daecaseinfo')
    databuild = all_data.parse('daebuildinfo')
    backloginfo = all_data.parse('Backlog Case Number')
    redfishdatacase = all_data.parse('redfishcaseinfo')
    redfishdatabuild = all_data.parse('redfishbuildinfo')
    daestresscase = all_data.parse('daestresscase')
    daestressbuild = all_data.parse('daestressbuild')


    datacase, databuild = update_case_sheet_data(jenkins_server, datacase, databuild, "Daily_CI_DAE", 100)
    redfishdatacase, redfishdatabuild = update_case_sheet_data(jenkins_server, redfishdatacase, redfishdatabuild, "Daily_CI_Redfish", 30)
    daestresscase, daestressbuild = update_case_sheet_data(jenkins_server, daestresscase, daestressbuild, "Weekly_Stress_DAE", 6)

    datacase, databuild = check_miss_build(jenkins_server, datacase, databuild, "Daily_CI_DAE", 100)
    redfishdatacase, redfishdatabuild = check_miss_build(jenkins_server, redfishdatacase, redfishdatabuild, "Daily_CI_Redfish", 30)
    daestresscase, daestressbuild = check_miss_build(jenkins_server, daestresscase, daestressbuild, "Weekly_Stress_DAE", 6)

    dae_sheet_info, dpe_sheet_info = get_backlog_cases_sheet_info()
    writer = pd.ExcelWriter(final_file, engine='xlsxwriter')
    # Get the xlsxwriter objects from the dataframe writer object.
    workbook = writer.book

    # Convert the dataframe to an XlsxWriter Excel object.
    datacase.to_excel(writer, sheet_name='daecaseinfo', index=False)
    databuild.to_excel(writer, sheet_name='daebuildinfo', index=False)
    redfishdatacase.to_excel(writer, sheet_name='redfishcaseinfo', index=False)
    redfishdatabuild.to_excel(writer, sheet_name='redfishbuildinfo', index=False)
    daestresscase.to_excel(writer, sheet_name='daestresscase', index=False)
    daestressbuild.to_excel(writer, sheet_name='daestressbuild', index=False)
    backloginfo.to_excel(writer, sheet_name='Backlog Case Number', index=False)

    worksheet1 = writer.sheets['daecaseinfo']
    update_analysis_data(datacase, worksheet1, buildtime)

    worksheet2 = writer.sheets['redfishcaseinfo']
    update_analysis_data(redfishdatacase, worksheet2, buildtime)

    worksheet3 = writer.sheets['Backlog Case Number']

    worksheet4 = writer.sheets['daestresscase']
    update_analysis_data(daestresscase, worksheet4, buildtime)

    for i in range(len(dae_sheet_info)):
        cell = 'B{}'.format(i+3)
        worksheet3.write(cell, dae_sheet_info[i])
    for i in range(len(dpe_sheet_info)):
        cell = 'D{}'.format(i+3)
        worksheet3.write(cell, dpe_sheet_info[i])

    # Light red fill with dark red text.
    format1 = workbook.add_format({'bg_color':   '#FFC7CE',
                                   'font_color': '#9C0006'})

    # Light yellow fill with dark yellow text.
    format2 = workbook.add_format({'bg_color':   '#FFEB9C',
                                   'font_color': '#9C6500'})

    # Green fill with dark green text.
    format3 = workbook.add_format({'bg_color':   '#C6EFCE',
                                   'font_color': '#006100'})

    for nworksheet in [worksheet1, worksheet2, worksheet4]:
        # Apply a conditional format to the cell range.
        # worksheet.conditional_format('G2:BB151', {'type': '3_color_scale'})
        nworksheet.conditional_format('G2:CA300', {'type':     'text',
                                                   'criteria': 'containing',
                                                   'value':    'PASSED',
                                                   'format':   format3})
        nworksheet.conditional_format('G2:CA300', {'type':     'text',
                                                   'criteria': 'containing',
                                                   'value':    'SKIPPED',
                                                   'format':   format2})
        nworksheet.conditional_format('G2:EE300', {'type':     'text',
                                                   'criteria': 'containing',
                                                   'value':    'FAILED',
                                                   'format':   format1})

        nworksheet.conditional_format('B2:B1000', {'type':     'text',
                                                   'criteria': 'containing',
                                                   'value':    'fixed',
                                                   'format':   format1})
        nworksheet.conditional_format('B2:B1000', {'type':     'text',
                                                   'criteria': 'containing',
                                                   'value':    'known',
                                                   'format':   format2})
        nworksheet.conditional_format('B2:B1000', {'type':     'text',
                                                   'criteria': 'containing',
                                                   'value':    'ATOM',
                                                   'format':   format2})
        nworksheet.conditional_format('E2:E1000', {'type':     'cell',
                                                   'criteria': '>',
                                                   'value':    1,
                                                   'format':   format1})

    writer.save()


def get_position(column_list, datacase):
    position_list = []
    for column_value in column_list:
        intloc = datacase.columns.get_loc(column_value)
        from xlsxwriter.utility import xl_col_to_name
        position = '{}2'.format(xl_col_to_name(intloc))
        position_list.append(position)
    return position_list


def filter_phase_cases(cases, platform, exclude_redfish=True, automatable=None, physical=None):
    """
    filter cases according request
    physical: need physical access 1: yes, 2: No
    platform: test cases run platform
    exclude_redfish: if exclude refish cases
    automatable:  unknown:1  No:2  Yes:3
    tag: redfish:[6], Ses : [7]
    """
    case_list = []
    for case in cases:
        case_tag = case.get('custom_ffv_cpu_specific')
        if automatable and case['custom_ffv_automatable'] != automatable:
            continue
        if exclude_redfish and (case_tag == [6] or case_tag == [7]):
            continue
        if physical and case['custom_ffv_need_physical_access'] != physical:
            continue
        # check if two list have the same value
        if not set(case['custom_ffvplatform']) & set(platform):
            continue
        case_list.append(case)
    return case_list


def get_backlog_cases_info(option='length'):
    """
    get cases info from testrail
    option: return cases info or length or others
    """
    testrail_obj = Testclient(testrail_url)
    # dae data
    dae_suite = [TEST_SUITE_DAE_BMC, TEST_SUITE_DAE_ATOM]
    # Fornax Kepler, Fornax Kosmos, Indus
    dae_platform = [20, 21, 22]
    total_dae_cases = []
    for suite in dae_suite:
        case_filter = '&suite_id={}'.format(suite)
        all_dae_cases = testrail_obj.get_cases(PROJECT_FFV, case_filter)
        total_dae_cases += filter_phase_cases(all_dae_cases, dae_platform)

    dae_phase_one_auto_cases = filter_phase_cases(total_dae_cases, dae_platform, automatable=3, physical=2)
    dae_phase_two_auto_cases = filter_phase_cases(total_dae_cases, dae_platform, automatable=3, physical=1)

    # dpe data
    dpe_suite = [TEST_SUITE_BMC, TEST_SUITE_UEFI]
    # Warnado 2U2N, Warnado EX, Warnado Bolero, Protoss Entry, Protoss Enterprise, Riptide
    dpe_platform = [12, 15, 18, 19, 13, 17]
    total_dpe_cases = []
    for suite in dpe_suite:
        case_filter = '&suite_id={}'.format(suite)
        all_dpe_cases = testrail_obj.get_cases(PROJECT_FFV, case_filter)
        total_dpe_cases += filter_phase_cases(all_dpe_cases, dpe_platform)

    dpe_phase_one_auto_cases = filter_phase_cases(total_dpe_cases, dpe_platform, automatable=3, physical=2)
    dpe_phase_two_auto_cases = filter_phase_cases(total_dpe_cases, dpe_platform, automatable=3, physical=1)

    if option == 'length':
        dae_info = [len(total_dae_cases), len(dae_phase_one_auto_cases), len(dae_phase_two_auto_cases)]
        dpe_info = [len(total_dpe_cases), len(dpe_phase_one_auto_cases), len(dpe_phase_two_auto_cases)]
        return dae_info, dpe_info
    else:
        dae_info = [total_dae_cases, dae_phase_one_auto_cases, dae_phase_two_auto_cases]
        dpe_info = [total_dpe_cases, dpe_phase_one_auto_cases, dpe_phase_two_auto_cases]
        return dae_info, dpe_info


def get_backlog_cases_sheet_info(dae_eol=0, dpe_eol=0):
    dae_info, dpe_info = get_backlog_cases_info()
    dae_phase_one_autorate = "{:.2%}".format((dae_info[1] + dae_eol) / (dae_eol + dae_info[0]))
    dae_phase_two_autorate = "{:.2%}".format((dae_info[2] + dae_info[1] + dae_eol) / (dae_eol + dae_info[0]))
    dae_info += [dae_eol, dae_phase_one_autorate, dae_phase_two_autorate]

    dpe_phase_one_autorate = "{:.2%}".format((dpe_info[1] + dpe_eol) / (dpe_eol + dpe_info[0]))
    dpe_phase_two_autorate = "{:.2%}".format((dpe_info[2] + dpe_info[1] + dpe_eol) / (dpe_eol + dpe_info[0]))
    dpe_info += [dpe_eol, dpe_phase_one_autorate, dpe_phase_two_autorate]
    return dae_info, dpe_info


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='automate analysis test case result')

    parser.add_argument("-n", "--nbuild", type=int, help="case last build number")
    parser.add_argument("-v", "--valid", type=int, help="valid case number to check if it is useful build")
    parser.add_argument("-j", "--job", type=str, help="job name of the build")
    parser.add_argument("-f", "--fname", type=str,  help="file name of source excel")
    parser.add_argument("-b", "--backlog", help="backlog case analysis")
    commandList = parser.parse_args()
    nbuild = 1024
    RESULT_FILE = "case_analysis_result.xlsx"
    valid_build = 100
    if commandList.fname:
        RESULT_FILE = commandList.fname
    if commandList.nbuild:
        nbuild = commandList.nbuild
    if commandList.valid:
        valid_build = commandList.valid
    if not commandList.job:
        job_name = 'Daily_CI_DAE'
    else:
        job_name = commandList.job
    jenkins_server = connect_to_jenkins()

    THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
    final_file = os.path.join(THIS_FOLDER, RESULT_FILE)
    get_bugs_from_jira()

    update_excel_and_fill_na(jenkins_server, job_name, nbuild, valid_build)
    print(jirafics_dict)
