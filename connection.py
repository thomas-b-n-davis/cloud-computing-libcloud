# import getpass
import os
import subprocess
# import libcloud.security

import time
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider

# reqs:
#   services: nova, glance, neutron
#   resources: 2 instances (m1.small), 2 floating ips (1 keypair, 2 security groups)

# Please use 1-29 for X in the following variable to specify your group number. (will be used for the username,
# project etc., as coordinated in the lab sessions)

group_number = 12
number_of_api_instances=2


# web service endpoint of the private cloud infrastructure
auth_url = 'https://private-cloud.informatik.hs-fulda.de:5000'
# your username in OpenStack
auth_username = 'CloudComp' + str(group_number)
# your project in OpenStack
project_name = 'CloudComp' + str(group_number)
# A network in the project the started instance will be attached to
project_network = 'CloudComp' + str(group_number) + '-net'
project_subnet = 'CloudComp' + str(group_number) + '-subnet'

# The image to look for and use for the started instance
ubuntu_image_name = "Ubuntu 18.04 - Bionic Beaver - 64-bit - Cloud Based Image"

# The public key to be used for SSH connection, please make sure, that you have the corresponding private key
#
# id_rsa.pub should look like this (standard sshd pubkey format):
# ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAw+J...F3w2mleybgT1w== user@HOSTNAME

keypair_name = 'srieger-pub'
pub_key_file = '~/.ssh/id_rsa.pub'

flavor_name = 'm1.small'


# default region
region_name = 'RegionOne'
# domain to use, "default" for local accounts, "hsfulda" for RZ LDAP, e.g., using fdaiXXXX as auth_username
domain_name = "default"


def main():
    ###########################################################################
    #
    # get credentials
    #
    ###########################################################################

    # if "OS_PASSWORD" in os.environ:
    #     auth_password = os.environ["OS_PASSWORD"]
    # else:
    #     auth_password = getpass.getpass("Enter your OpenStack password:")
    auth_password = "cloudGP12"

    ###########################################################################
    #
    # create connection
    #
    ###########################################################################

    # libcloud.security.VERIFY_SSL_CERT = False

    provider = get_driver(Provider.OPENSTACK)
    conn = provider(auth_username,
                    auth_password,
                    ex_force_auth_url=auth_url,
                    ex_force_auth_version='3.x_password',
                    ex_tenant_name=project_name,
                    ex_force_service_region=region_name,
                    ex_domain_name=domain_name)
    return conn

if __name__ == '__main__':
    main()
