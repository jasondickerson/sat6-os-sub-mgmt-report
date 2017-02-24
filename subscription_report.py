#!/usr/bin/python
import sys
import re
import os
import base64
import csv
import datetime
import socket
import smtplib
from ConfigParser import SafeConfigParser
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    import requests
except ImportError:
    print "Please install the python-requests module."
    sys.exit(-1)

config_file = os.path.dirname(os.path.abspath(__file__)) + '/subscription_report.cfg'
today = datetime.date.today().strftime('%Y%m%d')

good_config = True
if os.path.isfile(config_file):
    config = SafeConfigParser()
    try:
        config.read(config_file)
    except:
        print 'Bad Configuration File.'
        good_config = False
        sys.exit(1)

    if config.has_section('authentication'):
        if config.has_option('authentication', 'satellite_list'):
            satellite_list = config.get('authentication', 'satellite_list').split(',')
        else:
            print 'Configuration section:  authentication.  satellite_list option is missing.'
            good_config = False
        if config.has_option('authentication', 'username'):
            username = config.get('authentication', 'username')
        else:
            print 'Configuration section:  authentication.  username option is missing.'
            good_config = False
        if config.has_option('authentication', 'password_b64'):
            password = base64.b64decode(config.get('authentication', 'password_b64'))
        else:
            print 'Configuration section:  authentication.  password_b64 is missing.'
            good_config = False
    else:
        print 'Configuration file is missing authentication section.'
        good_config = False

    if config.has_section('evidence_file'):
        if config.has_option('evidence_file', 'path'):
            evidence_file_path = config.get('evidence_file', 'path')
            if not evidence_file_path:
                evidence_file_path = os.path.dirname(os.path.abspath(__file__))
        else:
            print 'Configuration section:  evidence_file.  path option is missing.'
            good_config = False
    else:
        print 'Configuration file is missing evidence_file section.'
        good_config = False

    if config.has_section('os_exclusions'):
        if config.has_option('os_exclusions', 'evidence'):
            evidence_exclusions = config.get('os_exclusions', 'evidence').split(',')
        else:
            print 'Configuration section:  os_exclusions.  evidence option is missing.'
            good_config = False
        if config.has_option('os_exclusions', 'count'):
            count_exclusions = config.get('os_exclusions', 'count').split(',')
        else:
            print 'Configuration section:  os_exclusions.  count option is missing.'
    else:
        print 'Configuration file is missing os_exclusions section.'
        good_config = False
    if config.has_section('mail'):
        if config.has_option('mail', 'company_name'):
            company_name = config.get('mail', 'company_name')
        else:
            print 'Configuration section:  mail.  company_name is missing.'
            good_config = False
        if config.has_option('mail', 'server'):
            mail_server = config.get('mail', 'server')
        else:
            print 'Configuration section:  mail.  server option is missing.'
            good_config = False
        if config.has_option('mail', 'from'):
            from_address = config.get('mail', 'from')
        else:
            print 'Configuration section:  mail.  from option is missing.'
            good_config = False
        if config.has_option('mail', 'to'):
            to_address_list = config.get('mail', 'to').split(',')
        else:
            print 'Configuration section:  mail.  to option is missing'
            good_config = False
    else:
        print 'Configuration file is missing mail section.'
        good_config = False
else:
    print 'Configuration File Missing.'

if not good_config:
    sys.exit(1)

# print satellite_list
# print username
# print password
# print evidence_file_path
# print mail_server
# print from_address
# print to_address_list


def get_certificate(satellite):
    if not os.path.isfile(os.path.dirname(os.path.abspath(__file__)) + '/' + satellite + '.crt'):
        # Performs a GET using the passed URL location
        try:
            r = requests.get('http://' + satellite + '/pub/katello-server-ca.crt', auth=(username, password))
        except:
            print 'Certificate pull error.'
            sys.exit(1)
        if r and r.text:
            with open(os.path.dirname(os.path.abspath(__file__)) + '/' + satellite + '.crt', 'w') as certificate_file:
                certificate_file.write(r.text)
        else:
            print 'Certificate pull error.'
            sys.exit(1)

def get_json(url):
    # Performs a GET using the passed URL location
    try:
        r = requests.get(url, auth=(username, password), verify=os.path.dirname(os.path.abspath(__file__)) + '/' + url.split('/')[2] + '.crt')
    except:
        print 'API connection Error.'
        sys.exit(1)
    if r and r.json():
        if  'error' in r.json() and r.json()['error']:
            print 'Error:  ' + r.json()['error']['message']
            return []
        else:
            return r.json()
    else:
        return []

def get_api_version(satellite):
    api_status_url = 'https://' + satellite + '/api/status'
    api_status = get_json(api_status_url)
    if api_status and 'api_version' in api_status and (api_status['api_version'] == 1 or api_status['api_version'] == 2):
        return api_status['api_version']
    else:
        print 'Invalid API version.'
        sys.exit(2)

def get_results(url):
    per_page = 100
    results_list = []
    results_list_page = []
    page = 0
    while page == 0 or (int(results_list_page['per_page']) == len(results_list_page['results'])):
        page += 1
        # print url + '?per_page=' + str(per_page) + '&page=' + str(page)
        results_list_page = get_json(url + '?per_page=' + str(per_page) + '&page=' + str(page))
        if results_list_page and 'results' in results_list_page:
            results_list += results_list_page['results']
        # print 'Page ' + str(page) + ' completed.'
        if not 'per_page' in results_list_page or not results_list_page['per_page']:
            break
    return results_list

def categorize_hosts(master_list, second_list):
    # print 'second_list: ' + str(len(second_list))
    uniq_list = []
    dup_list = []
    for second_host in second_list:
        duplicate = False
        for master_host in master_list:
            if second_host['name'] == master_host['name']:
                duplicate = True
                break
        if duplicate:
            dup_list.append(second_host)
        else:
            uniq_list.append(second_host)
    # print 'unique_list:     ' + str(len(uniq_list))
    # print 'duplicate_list:  ' + str(len(dup_list))
    return ( uniq_list, dup_list )

def get_evidence(api_version, satellite, count_dict, master_list, extra_list):

    katello_system_details_url = 'https://' + satellite + '/katello/api/v2/systems/'
    foreman_host_details_url = 'https://' + satellite + '/api/v2/hosts/'
    katello_packages_url = 'https://' + satellite + '/katello/api/systems/'
    katello_system_details_option = '?fields=full'
    packages_option = '/packages'

    output_list = []
    regex = re.compile('[0-9,.]')

    if master_list:
        for host in master_list:
            output_dict = {}
            release = ''
            extra_call = False
            if extra_list:
                for extra_host in extra_list:
                    if host['name'] == extra_host['name']:
                        extra_call = True
            
            full_sys = []
            if api_version == 1 and 'uuid' in host and host['uuid']:
                full_sys = get_json(katello_system_details_url + host['uuid'] + katello_system_details_option)

            full_host = []
            if ( api_version == 1 and extra_call ) or api_version == 2:
                full_host = get_json(foreman_host_details_url + str(host['name']))

            output_dict['System_Name'] = host['name']

            Build_Status = 'COMPLETE'
            if full_host and 'build' in full_host and full_host['build'] and full_host['build'] != 'false':
                    Build_Status = 'INCOMPLETE'
            
            Entitlement = 'NONE'
            if api_version == 1 and 'entitlementStatus' in host and host['entitlementStatus']:
                if host['entitlementStatus'] == 'valid':
                    Entitlement = 'Fully entitled'
                else:
                    Entitlement = host['entitlementStatus']
            elif api_version == 2 and 'subscription_status_label' in host and host['subscription_status_label']:
                Entitlement = host['subscription_status_label']
            if ',' in Entitlement:
                Entitlement = '"' + Entitlement + '"'

            Katello_Agent = 'NO_KATELLO'
            if api_version == 1 and 'katello_agent_installed' in host and host['katello_agent_installed'] != '':
                Katello_Agent = str(host['katello_agent_installed'])
            elif api_version == 2 and 'content_facet_attributes' in full_host and 'katello_agent_installed' in full_host['content_facet_attributes'] and full_host['content_facet_attributes']['katello_agent_installed'] != '':
                    Katello_Agent = str(full_host['content_facet_attributes']['katello_agent_installed'])

            output_dict['Operating_System'] = 'NONE'
            if api_version == 1:
                if 'distribution' in host and host['distribution']:
                    output_dict['Operating_System'] = host['distribution']
                elif 'operatingsystem_name' in host and host['operatingsystem_name']:
                    output_dict['Operating_System'] = host['operatingsystem_name']
            elif api_version == 2 and 'operatingsystem_name' in full_host and full_host['operatingsystem_name']:
                    output_dict['Operating_System'] = full_host['operatingsystem_name']
            elif api_version == 2 and 'facts' in full_host and 'distribution::name' in full_host['facts'] and full_host['facts']['distribution::name'] and 'distribution::version' in full_host['facts'] and full_host['facts']['distribution::version']:
                    output_dict['Operating_System'] = full_host['facts']['distribution::name'] + ' ' + full_host['facts']['distribution::version']
            if output_dict['Operating_System'] == ' ':
                output_dict['Operating_System'] = 'NONE'
            if not output_dict['Operating_System'] == 'NONE':
                release = output_dict['Operating_System'].split(' ')[-2:]
                if regex.match(release[1]):
                    release = release[1]
                elif release[1].startswith('SP'):
                    release = release[0] + '.' + release[1].strip('SP')
                else:
                    release = ''
                if output_dict['Operating_System'].split(' ')[0] in ['Red', 'RedHat', 'RHEL']:
                    output_dict['Operating_System'] = 'RedHat'
                elif output_dict['Operating_System'].split(' ')[0] == 'CentOS':
                    output_dict['Operating_System'] = 'CentOS'
                if release:
                    output_dict['Operating_System'] = output_dict['Operating_System'] + ' ' + release
                # print output_dict['Operating_System'] + release

            output_dict['Satellite'] = satellite

            output_dict['Server_Type'] = 'UNKNOWN'
            output_dict['Azure_Agent_Installed'] = 'UNKNOWN'
            if api_version == 1 and full_sys and 'facts' in full_sys and 'virt.is_guest' in full_sys['facts'] and full_sys['facts']['virt.is_guest'] != '':
                if full_sys['facts']['virt.is_guest'] == 'true':
                    if 'lscpu.hypervisor_vendor' in full_sys['facts']:
                        output_dict['Server_Type'] = full_sys['facts']['lscpu.hypervisor_vendor'].upper()
                    else:
                        output_dict['Server_Type'] = 'VIRTUAL'
                    if 'uuid' in host and host['uuid']:
                        packages = get_results(katello_packages_url + host['uuid'] + packages_option)
                        if packages:
                            output_dict['Azure_Agent_Installed'] = 'NO'
                            for package in packages:
                                if package['name'] == 'WALinuxAgent':
                                    output_dict['Azure_Agent_Installed'] = 'YES'
                                    break
                elif full_sys['facts']['virt.is_guest'] == 'false':
                    output_dict['Server_Type'] = 'PHYSICAL'
                    output_dict['Azure_Agent_Installed'] = 'NO'
            elif api_version == 2 and 'facts' in full_host and 'virt::is_guest' in full_host['facts'] and full_host['facts']['virt::is_guest'] != '':
                if full_host['facts']['virt::is_guest'] == 'true':
                    if 'virt::host_type' in full_host['facts']:
                        output_dict['Server_Type'] = full_host['facts']['virt::host_type'].upper()
                    else:
                        output_dict['Server_Type'] = 'VIRTUAL'
                    packages = get_results(foreman_host_details_url + str(full_host['id']) + packages_option)
                    if packages:
                        output_dict['Azure_Agent_Installed'] = 'NO'
                        for package in packages:
                            if package['name'] == 'WALinuxAgent':
                                output_dict['Azure_Agent_Installed'] = 'YES'
                                break
                elif full_host['facts']['virt::is_guest'] == 'false':
                    output_dict['Server_Type'] = 'PHYSICAL'
                    output_dict['Azure_Agent_Installed'] = 'NO'

            if not output_dict['Operating_System'].split(' ')[0] in evidence_exclusions and output_dict['Server_Type'] != 'UNKNOWN':
                output_list.append(output_dict)

            if not output_dict['Operating_System'].split(' ')[0] in count_exclusions:
                if Build_Status == 'COMPLETE':
                    if output_dict['Operating_System'].split(' ')[0] == 'RedHat':
                        if output_dict['Azure_Agent_Installed'] == 'YES':
                            if count_dict.has_key('RedHat Azure'):
                                count_dict['RedHat Azure'] = count_dict['RedHat Azure'] + 1
                            else:
                                count_dict['RedHat Azure'] = 1
                        elif output_dict['Server_Type'] == 'PHYSICAL':
                            if count_dict.has_key('RedHat Physical'):
                                count_dict['RedHat Physical'] = count_dict['RedHat Physical'] + 1
                            else:
                                count_dict['RedHat Physical'] = 1
                        elif output_dict['Server_Type'] == 'UNKNOWN':
                            if count_dict.has_key('RedHat Unmanaged'):
                                count_dict['RedHat Unmanaged'] = count_dict['RedHat Unmanaged'] + 1
                            else:
                                count_dict['RedHat Unmanaged'] = 1
                        else:
                            if count_dict.has_key('RedHat Virtual'):
                                count_dict['RedHat Virtual'] = count_dict['RedHat Virtual'] + 1
                            else:
                                count_dict['RedHat Virtual'] = 1
                    else:
                        if count_dict.has_key(output_dict['Operating_System'].split(' ')[0]):
                            count_dict[output_dict['Operating_System'].split(' ')[0]] = count_dict[output_dict['Operating_System'].split(' ')[0]] + 1
                        else:
                            count_dict[output_dict['Operating_System'].split(' ')[0]] = 1


    return output_list

def main():
    evidence_list = []
    count_dict = {}
    for satellite in satellite_list:
        katello_system_list_url = 'https://' + satellite + '/katello/api/v2/systems'
        foreman_host_list_url = 'https://' + satellite + '/api/v2/hosts'

        get_certificate(satellite)
        api_version = get_api_version(satellite)
        # print 'API Version:  :  ' + str(api_version)
        # print
        primary_list = []
        secondary_list = []

        if api_version == 1:
            primary_list = get_results(katello_system_list_url)
            secondary_list = get_results(foreman_host_list_url)
        else:
            primary_list = get_results(foreman_host_list_url)
            secondary_list = get_results(katello_system_list_url)
        ( unique_list, duplicate_list ) = categorize_hosts(primary_list, secondary_list)
        if api_version == 1:
            evidence_list += get_evidence(api_version, satellite, count_dict, primary_list, duplicate_list)
            evidence_list += get_evidence(2, satellite, count_dict, unique_list, [])
        else:
            evidence_list += get_evidence(api_version, satellite, count_dict, primary_list, [])
            evidence_list += get_evidence(1, satellite, count_dict, unique_list, [])

    count_summary = ''
    for count in count_dict.keys():
        count_summary = count_summary + count + ' Systems:  ' + str(count_dict[count]) + '\n'
    if not count_dict.has_key('RedHat Azure'):
        count_dict['RedHat Azure'] = 0
    if not count_dict.has_key('RedHat Physical'):
        count_dict['RedHat Physical'] = 0
    if not count_dict.has_key('RedHat Virtual'):
        count_dict['RedHat Virtual'] = 0
    if not count_dict.has_key('RedHat Unmanaged'):
        count_dict['RedHat Unmanaged'] = 0
    redhat_virtual_systems_total = count_dict['RedHat Virtual'] + count_dict['RedHat Azure']
    redhat_virtual_subscriptions_total = int(round(float(redhat_virtual_systems_total) / 2))
    count_summary = count_summary + 'Total RHEL Virtual Systems (On-premises + Azure):  ' + str(redhat_virtual_systems_total) + '\n\n'
    count_summary = count_summary + 'Total RHEL Subscriptions consumed by Virtual Systems:  ' + str(redhat_virtual_subscriptions_total) + '\n'
    count_summary = count_summary + 'Total RHEL Subscriptions consumed by Physical Systems:  ' + str(count_dict['RedHat Physical']) + '\n\n'
    count_summary = count_summary + 'Total RHEL Subscriptions consumed:  ' + str(redhat_virtual_subscriptions_total + count_dict['RedHat Physical']) + '\n\n\n'

    evidence_file_name = evidence_file_path + '/subscription_report_' + today + '.csv'

    with open(evidence_file_name, 'w') as evidence_file:
        evidence_file.write(count_summary)            
        fieldnames = ['System_Name', 'Operating_System', 'Satellite', 'Server_Type', 'Azure_Agent_Installed']
        writer = csv.DictWriter(evidence_file, fieldnames)
        writer.writerow({'System_Name': 'System_Name', 'Operating_System': 'Operating_System', 'Satellite': 'Satellite', 'Server_Type': 'Server_Type', 'Azure_Agent_Installed': 'Azure_Agent_Installed'})
        writer.writerows(evidence_list)

    msg_body = """This is the latest subscription count for """ + company_name + """.

"""
    msg_body = msg_body + count_summary
    msg_body = msg_body + 'This script runs from ' + socket.getfqdn() + ':' + os.path.abspath(__file__)

    msg_container = MIMEMultipart()
    msg_container['Subject'] = company_name + ' Subscription Report'
    msg_container['From'] = from_address
    msg_container['To'] = ', '.join(to_address_list)
    msg_container.preamble = company_name + ' Subscription Report\n'

    attach_file = open(evidence_file_name, 'rb')
    attachment = MIMEBase('application', 'octect-stream')
    attachment.set_payload(attach_file.read())
    attach_file.close()
    encoders.encode_quopri(attachment)

    attachment.add_header('Content-Disposition', 'attachment', filename=evidence_file_name)

    msg_container.attach(attachment)
    msg_container.attach(MIMEText(msg_body, 'plain'))

    mailer = smtplib.SMTP(mail_server)
    mailer.sendmail(from_address, to_address_list, msg_container.as_string())

if __name__ == "__main__":
    main()

# vim: set ts=4 sw=4 sts=4 et :
# syntax=off :
