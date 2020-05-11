# import getpass
# import os
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


# web service endpoint of the private cloud infrastructure
auth_url = 'https://private-cloud.informatik.hs-fulda.de:5000'
# your username in OpenStack
auth_username = 'CloudComp' + str(group_number)
# your project in OpenStack
project_name = 'CloudComp' + str(group_number)
# A network in the project the started instance will be attached to
project_network = 'CloudComp' + str(group_number) + '-net'

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
    # clean up resources from previous demos
    #
    ###########################################################################

    # destroy running demo instances
    for instance in conn.list_nodes():
        if instance.name in ['all-in-one', 'app-worker-1', 'app-worker-2', 'app-worker-3', 'app-controller',
                             'app-services', 'app-api-1', 'app-api-2']:
            print('Destroying Instance: %s' % instance.name)
            conn.destroy_node(instance)

    # wait until all nodes are destroyed to be able to remove depended security groups
    nodes_still_running = True
    while nodes_still_running:
        nodes_still_running = False
        time.sleep(3)
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
                return worker_security_group
        return False

    if not get_security_group(conn, "api"):
        api_security_group = conn.ex_create_security_group('api', 'for API services only')
        conn.ex_create_security_group_rule(api_security_group, 'TCP', 80, 80)
        conn.ex_create_security_group_rule(api_security_group, 'TCP', 22, 22)
    else:
        api_security_group = get_security_group(conn, "api")

    if not get_security_group(conn, "worker"):
        worker_security_group = conn.ex_create_security_group('worker', 'for services that run on a worker node')
        conn.ex_create_security_group_rule(worker_security_group, 'TCP', 22, 22)
    else:
        worker_security_group = get_security_group(conn, "worker")

    if not get_security_group(conn, "control"):
        controller_security_group = conn.ex_create_security_group('control', 'for services that run on a control node')
        conn.ex_create_security_group_rule(controller_security_group, 'TCP', 22, 22)
        conn.ex_create_security_group_rule(controller_security_group, 'TCP', 80, 80)
        conn.ex_create_security_group_rule(controller_security_group, 'TCP', 5672, 5672,
                                           source_security_group=worker_security_group)

    if not get_security_group(conn, "services"):
        services_security_group = conn.ex_create_security_group('services', 'for DB and AMQP services only')
        conn.ex_create_security_group_rule(services_security_group, 'TCP', 22, 22)
        conn.ex_create_security_group_rule(services_security_group, 'TCP', 3306, 3306,
                                           source_security_group=api_security_group)
        conn.ex_create_security_group_rule(services_security_group, 'TCP', 5672, 5672,
                                           source_security_group=worker_security_group)
        conn.ex_create_security_group_rule(services_security_group, 'TCP', 5672, 5672,
                                           source_security_group=api_security_group)
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

    ###########################################################################
    #
    # create app-services instance (database & messaging)
    #
    ###########################################################################

    # https://git.openstack.org/cgit/openstack/faafo/plain/contrib/install.sh
    # is currently broken, hence the "rabbitctl" lines were added in the example
    # below, see also https://bugs.launchpad.net/faafo/+bug/1679710
    #
    # Thanks to Stefan Friedmann for finding this fix ;)

    userdata_service = '''#!/usr/bin/env bash
    curl -L -s https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/faafo/contrib/install.sh | bash -s -- \
        -i database -i messaging
    rabbitmqctl add_user faafo guest
    rabbitmqctl set_user_tags faafo administrator
    rabbitmqctl set_permissions -p / faafo ".*" ".*" ".*"
    '''

    print('Starting new app-services instance and wait until it is running...')
    instance_services = conn.create_node(name='app-services',
                                         image=image,
                                         size=flavor,
                                         networks=[network],
                                         ex_keyname=keypair_name,
                                         ex_userdata=userdata_service,
                                         ex_security_groups=[services_security_group])
    instance_services = conn.wait_until_running(nodes=[instance_services], timeout=120,
                                                ssh_interface='private_ips')[0][0]
    services_ip = instance_services.private_ips[0]

    ###########################################################################
    #
    # create app-api instances
    #
    ###########################################################################

    userdata_api = '''#!/usr/bin/env bash
    curl -L -s https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/faafo/contrib/install.sh | bash -s -- \
        -i faafo -r api -m 'amqp://faafo:guest@%(services_ip)s:5672/' \
        -d 'mysql+pymysql://faafo:password@%(services_ip)s:3306/faafo'
    ''' % {'services_ip': services_ip}

    print('Starting new app-api-1 instance and wait until it is running...')
    instance_api_1 = conn.create_node(name='app-api-1',
                                      image=image,
                                      size=flavor,
                                      networks=[network],
                                      ex_keyname=keypair_name,
                                      ex_userdata=userdata_api,
                                      ex_security_groups=[api_security_group])

    print('Starting new app-api-2 instance and wait until it is running...')
    instance_api_2 = conn.create_node(name='app-api-2',
                                      image=image,
                                      size=flavor,
                                      networks=[network],
                                      ex_keyname=keypair_name,
                                      ex_userdata=userdata_api,
                                      ex_security_groups=[api_security_group])

    instance_api_1 = conn.wait_until_running(nodes=[instance_api_1], timeout=120,
                                             ssh_interface='private_ips')[0][0]
    api_1_ip = instance_api_1.private_ips[0]
    instance_api_2 = conn.wait_until_running(nodes=[instance_api_2], timeout=120,
                                             ssh_interface='private_ips')[0][0]
    # api_2_ip = instance_api_2.private_ips[0]

    #Create the load balancer

    #associate a floating IP to it
    
     
    for instance in [instance_api_1, instance_api_2]:
        floating_ip = get_floating_ip(conn)
        conn.ex_attach_floating_ip_to_node(instance, floating_ip)
        print('allocated %(ip)s to %(host)s' % {'ip': floating_ip.ip_address, 'host': instance.name})

    ###########################################################################
    #
    # create worker instances
    #
    ###########################################################################

    userdata_worker = '''#!/usr/bin/env bash
    curl -L -s https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/faafo/contrib/install.sh | bash -s -- \
        -i faafo -r worker -e 'http://%(api_1_ip)s' -m 'amqp://faafo:guest@%(services_ip)s:5672/'
    ''' % {'api_1_ip': api_1_ip, 'services_ip': services_ip}

    # userdata_api-api-2 = '''#!/usr/bin/env bash
    # curl -L -s https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/faafo/contrib/install.sh | bash -s -- \
    #     -i faafo -r worker -e 'http://%(api_2_ip)s' -m 'amqp://faafo:guest@%(services_ip)s:5672/'
    # ''' % {'api_2_ip': api_2_ip, 'services_ip': services_ip}

    print('Starting new app-worker-1 instance and wait until it is running...')
    instance_worker_1 = conn.create_node(name='app-worker-1',
                                         image=image, size=flavor,
                                         networks=[network],
                                         ex_keyname=keypair_name,
                                         ex_userdata=userdata_worker,
                                         ex_security_groups=[worker_security_group])

    print('Starting new app-worker-2 instance and wait until it is running...')
    instance_worker_2 = conn.create_node(name='app-worker-2',
                                         image=image, size=flavor,
                                         networks=[network],
                                         ex_keyname=keypair_name,
                                         ex_userdata=userdata_worker,
                                         ex_security_groups=[worker_security_group])

    # do not start worker 3 initially, can be started using scale-out-add-worker.py demo
    
    print('Starting new app-worker-3 instance and wait until it is running...')
    instance_worker_3 = conn.create_node(name='app-worker-3',
                                        image=image, size=flavor,
                                        networks=[network],
                                        ex_keyname=keypair_name,
                                        ex_userdata=userdata_worker,
                                        ex_security_groups=[worker_security_group])

    print(instance_worker_1)
    print(instance_worker_2)
    print(instance_worker_3)


if __name__ == '__main__':
    main()
