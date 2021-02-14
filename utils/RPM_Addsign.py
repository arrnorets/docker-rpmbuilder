#!/usr/bin/env python3

# /* 
# A very simple script for signing RPM packages
# */

from configparser import ConfigParser

import os
import pexpect
import sys
import time

# /* Gets passphrase for RPM signing */

def get_Passphrase():
    try:
        # instantiate
        config = ConfigParser()

        # parse existing file
        config.read('/etc/rpmbuilder.ini')

        # read values from a section
        pph = config.get('gpg', 'passphrase')

        return pph
    except:
        print("Unable to get passphrase for GPG key")
        sys.exit(3)

# /* END BLOCK */

# /* Sign packages */

def sign_Package(pkg, p):
    child = pexpect.spawn (F"rpm --addsign {pkg}", encoding='utf-8')
    i = child.expect ("Enter pass phrase:", timeout=5)
    if ( i == 0):
        child.sendline(p)
        time.sleep(5)
        child.close()
    else:
        print( F"Could not sign package {pkg}" )
# /* END BLOCK */

if( len( sys.argv ) != 2 ):
    print( "Please specify path to the directory with RPM packages that have to be signed." ) 
    sys.exit(0)

os.chdir(sys.argv[1])
p = get_Passphrase()

files = [f for f in os.listdir('.') if os.path.isfile(f)]
for f in files:
    sign_Package(f, p)

