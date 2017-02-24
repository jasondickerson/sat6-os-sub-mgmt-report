#!/usr/bin/python
import getpass
import base64

p = getpass.getpass()
print 'Encoded Password is:', base64.b64encode(p)
