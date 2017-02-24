# sat6-os-sub-mgmt-report
A Python script with configuration file, to aid Red Hat Satellite 6.x users to properly track the number of Red Hat OS subscriptions needed.  

# What does the script do

The script reports hosts, Operating Systems, Physical or Virtual, if Virtual host the type, and if the host is Azure based or not.  The report stores an evidence csv file in a direcotory for historical reasons, and e-mails the evidence file with a summary report to concerned parties.  The script can be configured to gather the report data from one or more satellites.  

# What versions does it work on

This script has been tested and works on:

* Satellite 6.1
* Satellite 6.2

# Prerequisites

* Python >= 2.4
* A login user to Satellite

# How to run your code

Prepare the configuration file for your environment.  At a minimum the authentication and mail sections must be completely filled out.  

The encode_password.py script is included to translate your passsword to base64 for you.  
Example usage/output:

~~~
$ ./encode_password.py 
Password: 
Encoded Password is: Y2hhbmdlbWU=
$
~~~

Sample Configuration File:

~~~
[authentication]

#csv list of satellites
satellite_list = sat1.example.com,sat2.example.com

#satellite user with access to pull host information from all hosts
username = admin

#base64 encoded password for the satellite user
password_b64 = 'Y2hhbmdlbWU='

[evidence_file]

#directory to store evidence file.  if none specified, current directory is used
path = 

[os_exclusions]

#csv list of Operating System names in satellite to exclude from the evidence file
evidence = CentOS

#csv list of Operating System names in satellite to exclude from the report summary in the e-mail
count =

[mail]

#your company name
company_name = My_Company

#your smtp server to use to send the report e-mail
server = smtp.example.com

#from e-mail address for report e-mail
from = me@example.com

#csv list of email addresses to send report to
to = you@example.com
~~~

Run the script using:

~~~
./subscription_report.py
~~~

# Example Output

The file sends an e-mail with a summary of the report, and the evidence file attached.  

Sample Evidence file:

~~~
RedHat Unmanaged Systems:  1
RedHat Virtual Systems:  4
Total RHEL Virtual Systems (On-premises + Azure):  4

Total RHEL Subscriptions consumed by Virtual Systems:  2
Total RHEL Subscriptions consumed by Physical Systems:  0

Total RHEL Subscriptions consumed:  2


System_Name,Operating_System,Satellite,Server_Type,Azure_Agent_Installed
client105.client.example.com,RedHat 7.2,sat6.example.com,KVM,NO
client106.client.example.com,RedHat 7.2,sat6.example.com,KVM,NO
client107.client.example.com,RedHat 6.8,sat6.example.com,KVM,NO
localhost.localdomain,RedHat 7.2,sat6.example.com,KVM,NO
sat6.example.com,RedHat 7.3,sat6.example.com,UNKNOWN,UNKNOWN

~~~

Sample Report E-mail:

~~~
From: <me@example.com>
Date: 2016-11-16 14:48 GMT-06:00
Subject: My_Company Subscription Report
To: you@example.com


This is the latest subscription count for My_Company.

RedHat Unmanaged Systems:  4
RedHat Physical Systems:  1226
NONE Systems:  999
CentOS Systems:  5
RedHat Virtual Systems:  428
Total RHEL Virtual Systems (On-premises + Azure):  428

Total RHEL Subscriptions consumed by Virtual Systems:  214
Total RHEL Subscriptions consumed by Physical Systems:  1226

Total RHEL Subscriptions consumed:  1440


This script runs from localhost.localdomain:/script_bin/sub_report/subscription_report.py
~~~

# Known issues

* It would be nice to add support to detect AWS hosts, similar to the way we detect Azure hosts.   
