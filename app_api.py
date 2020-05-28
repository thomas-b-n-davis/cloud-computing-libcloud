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
    # create keypair dependency
    #
    ###########################################################################

    print('Checking for existing SSH key pair...')
    keypair_exists = False
    for keypair in conn.list_key_pairs():
        if keypair.name == keypair_name:
            keypair_exists = True

    if keypair_exists:
        print('Keypair ' + keypair_name + ' already exists. Skipping import.')
    else:
        print('adding keypair...')
        conn.import_key_pair_from_file(keypair_name, pub_key_file)

    for keypair in conn.list_key_pairs():
        print(keypair)

    
    ###########################################################################
    #
    # create security group dependency
    #
    ###########################################################################

    def get_security_group(connection, security_group_name):
        """A helper function to check if security group already exists"""
        print('Checking for existing ' + security_group_name + ' security group...')
        for security_grp in connection.ex_list_security_groups():
            if security_grp.name == security_group_name:
                print('Security Group ' + security_group_name + ' already exists. Skipping creation.')
                return security_grp
        return False

    if not get_security_group(conn, "api"):
        api_security_group = conn.ex_create_security_group('api', 'for API services only')
        conn.ex_create_security_group_rule(api_security_group, 'TCP', 80, 80)
        conn.ex_create_security_group_rule(api_security_group, 'TCP', 22, 22)
        conn.ex_create_security_group_rule(api_security_group, 'TCP', 1337, 1337)
    else:
        api_security_group = get_security_group(conn, "api")

    if not get_security_group(conn, "services"):
        services_security_group = conn.ex_create_security_group('services', 'for services that run on a worker node')
        conn.ex_create_security_group_rule(services_security_group, 'TCP', 22, 22)
        conn.ex_create_security_group_rule(services_security_group, 'TCP', 80, 80)
    else:
        services_security_group = get_security_group(conn, "services")


    for security_group in conn.ex_list_security_groups():
        print(security_group)

    ###########################################################################
    #
    # get floating ip helper function
    #
    ###########################################################################

    def get_floating_ip(connection):
        """A helper function to re-use available Floating IPs"""
        unused_floating_ip = None
        for float_ip in connection.ex_list_floating_ips():
            if not float_ip.node_id:
                unused_floating_ip = float_ip
                break
        if not unused_floating_ip:
            pool = connection.ex_list_floating_ip_pools()[0]
            unused_floating_ip = pool.create_floating_ip()
        return unused_floating_ip

    # https://git.openstack.org/cgit/openstack/faafo/plain/contrib/install.sh
    # is currently broken, hence the "rabbitctl" lines were added in the example
    # below, see also https://bugs.launchpad.net/faafo/+bug/1679710
    #

    ###########################################################################
    #
    # create app-api instances
    #
    ###########################################################################
    userdata_api = '''#!/usr/bin/env bash
    apt-get update
    apt-get -y install apache2
    rm /var/www/html/index.html
    apt-get install curl
    curl -sL https://deb.nodesource.com/setup_14.x | sudo bash -
    sudo apt-get install -y nodejs
    apt-get install git
    nodejs --version
    npm –version
    git config --global user.name 'Thomas Davis'
    git config --global user.email 'thomas.b.n.davis@outlook.com'
    cd /var/www/
    sudo chmod 777 /var/www/html/
    cd /var/www/html/
    git clone https://thomas-b-n-davis:th*mas024@github.com/NadzeyaD/dogsapi.git
    sudo chmod 777 dogsapi
    cd /var/www/html/dogsapi/
    sudo npm install
    npm install pm2 -g
    pm2 start app.js
    '''

    instance_number=len(conn.list_nodes())+1
    print("Creating api instance" + str(instance_number))
    instance_api = conn.create_node(name='app-api',
                                          image=image,
                                          size=flavor,
                                          networks=[network],
                                          ex_keyname=keypair_name,
                                          ex_userdata=userdata_api,
                                          ex_security_groups=[api_security_group])
    instance_api = conn.wait_until_running(nodes=[instance_api], timeout=360,
                                                 ssh_interface='private_ips')[0][0]
    

