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


def main(conn):
    
    ###########################################################################
    #
    # get image, flavor, network for instance creation
    #
    ###########################################################################

    images = conn.list_images()
    image = ''
    for img in images:
        if img.name == ubuntu_image_name:
            image = img

    flavors = conn.list_sizes()
    flavor = ''
    for flav in flavors:
        if flav.name == flavor_name:
            flavor = conn.ex_get_size(flav.id)

    networks = conn.ex_list_networks()
    network = ''
    for net in networks:
        if net.name == project_network:
            network = net


    ###########################################################################
    #
    # clean up resources from previous demos
    #
    ###########################################################################

    # destroy running demo instances
    for instance in conn.list_nodes():
        # if instance.name in ['all-in-one', 'app-worker-1', 'app-worker-2', 'app-worker-3', 'app-controller',
                             # 'app-services', 'app-api-1', 'app-api-2','app-server']:
            print('Destroying Instance: %s' % instance.name)
            conn.destroy_node(instance)

    # wait until all nodes are destroyed to be able to remove depended security groups
    nodes_still_running = True
    while nodes_still_running:
        nodes_still_running = False
        time.sleep(5)
        instances = conn.list_nodes()
        for instance in instances:
            # if we see any demo instances still running continue to wait for them to stop
            if instance.name in ['all-in-one', 'app-worker-1', 'app-worker-2', 'app-controller']:
                nodes_still_running = True
        print('There are still instances running, waiting for them to be destroyed...')

    # delete security groups
    for group in conn.ex_list_security_groups():
        if group.name in ['control', 'worker', 'api', 'services']:
            print('Deleting security group: %s' % group.name)
            conn.ex_delete_security_group(group)

    
