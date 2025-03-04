#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy
import re
import yaml

HAS_SDK = True

try:
    import ionoscloud
    from ionoscloud import __version__ as sdk_version
    from ionoscloud.models import ApplicationLoadBalancer, ApplicationLoadBalancerProperties
    from ionoscloud.rest import ApiException
    from ionoscloud import ApiClient
except ImportError as e:
    HAS_SDK = False

from ansible import __version__
from ansible.module_utils.basic import AnsibleModule, env_fallback
from ansible.module_utils._text import to_native

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community',
}
USER_AGENT = 'ansible-module/%s_ionos-cloud-sdk-python/%s' % ( __version__, sdk_version)
DOC_DIRECTORY = 'applicationloadbalancer'
STATES = ['present', 'absent', 'update']
OBJECT_NAME = 'Application Loadbalancer'

OPTIONS = {
    'name': {
        'description': ['The name of the Application Load Balancer.'],
        'available': STATES,
        'required': ['present', 'update'],
        'type': 'str',
    },
    'listener_lan': {
        'description': ['ID of the listening LAN (inbound).'],
        'available': ['present', 'update'],
        'required': ['present', 'update'],
        'type': 'str',
    },
    'ips': {
        'description': [
            'Collection of the Application Load Balancer IP addresses. (Inbound and outbound) '
            'IPs of the listenerLan must be customer-reserved IPs for public Load Balancers, and private IPs for private Load Balancers.',
        ],
        'available': ['present', 'update'],
        'type': 'list',
    },
    'target_lan': {
        'description': ['ID of the balanced private target LAN (outbound).'],
        'available': ['present', 'update'],
        'required': ['present', 'update'],
        'type': 'str',
    },
    'lb_private_ips': {
        'description': [
            'Collection of private IP addresses with subnet mask of the Application Load Balancer. '
            'IPs must contain a valid subnet mask. If no IP is provided, the system will generate an IP with /24 subnet.',
        ],
        'available': ['present', 'update'],
        'type': 'list',
    },
    'datacenter_id': {
        'description': ['The ID of the datacenter.'],
        'available': STATES,
        'required': STATES,
        'type': 'str',
    },
    'application_load_balancer_id': {
        'description': ['The ID of the Application Loadbalancer.'],
        'available': ['update', 'absent'],
        'type': 'str',
    },
    'api_url': {
        'description': ['The Ionos API base URL.'],
        'version_added': '2.4',
        'env_fallback': 'IONOS_API_URL',
        'available': STATES,
        'type': 'str',
    },
    'certificate_fingerprint': {
        'description': ['The Ionos API certificate fingerprint.'],
        'env_fallback': 'IONOS_CERTIFICATE_FINGERPRINT',
        'available': STATES,
        'type': 'str',
    },
    'username': {
        # Required if no token, checked manually
        'description': ['The Ionos username. Overrides the IONOS_USERNAME environment variable.'],
        'aliases': ['subscription_user'],
        'env_fallback': 'IONOS_USERNAME',
        'available': STATES,
        'type': 'str',
    },
    'password': {
        # Required if no token, checked manually
        'description': ['The Ionos password. Overrides the IONOS_PASSWORD environment variable.'],
        'aliases': ['subscription_password'],
        'available': STATES,
        'no_log': True,
        'env_fallback': 'IONOS_PASSWORD',
        'type': 'str',
    },
    'token': {
        # If provided, then username and password no longer required
        'description': ['The Ionos token. Overrides the IONOS_TOKEN environment variable.'],
        'available': STATES,
        'no_log': True,
        'env_fallback': 'IONOS_TOKEN',
        'type': 'str',
    },
    'wait': {
        'description': ['Wait for the resource to be created before returning.'],
        'default': True,
        'available': STATES,
        'choices': [True, False],
        'type': 'bool',
    },
    'wait_timeout': {
        'description': ['How long before wait gives up, in seconds.'],
        'default': 600,
        'available': STATES,
        'type': 'int',
    },
    'state': {
        'description': ['Indicate desired state of the resource.'],
        'default': 'present',
        'choices': STATES,
        'available': STATES,
        'type': 'str',
    },
}

def transform_for_documentation(val):
    val['required'] = len(val.get('required', [])) == len(STATES) 
    del val['available']
    del val['type']
    return val

DOCUMENTATION = '''
---
module: application_load_balancer
short_description: Create or destroy a Ionos Cloud Application Loadbalancer.
description:
     - This is a simple module that supports creating or removing Application Loadbalancers.
version_added: "2.0"
options:
''' + '  ' + yaml.dump(yaml.safe_load(str({k: transform_for_documentation(v) for k, v in copy.deepcopy(OPTIONS).items()})), default_flow_style=False).replace('\n', '\n  ') + '''
requirements:
    - "python >= 2.6"
    - "ionoscloud >= 6.0.0"
author:
    - "IONOS Cloud SDK Team <sdk-tooling@ionos.com>"
'''

EXAMPLE_PER_STATE = {
  'present' : '''
  - name: Create Application Load Balancer
    application_load_balancer:
      datacenter_id: "{{ datacenter_response.datacenter.id }}"
      name: "{{ name }}"
      ips:
        - "10.12.118.224"
      listener_lan: "{{ listener_lan.lan.id }}"
      target_lan: "{{ target_lan.lan.id }}"
      wait: true
    register: alb_response
  ''',
  'update' : '''
  - name: Update Application Load Balancer
    application_load_balancer:
      datacenter_id: "{{ datacenter_response.datacenter.id }}"
      application_load_balancer_id: "{{ alb_response.application_load_balancer.id }}"
      name: "{{ name }} - UPDATE"
      listener_lan: "{{ listener_lan.lan.id }}"
      target_lan: "{{ target_lan.lan.id }}"
      wait: true
      state: update
    register: alb_response_update
  ''',
  'absent' : '''
  - name: Remove Application Load Balancer
    application_load_balancer:
      application_load_balancer_id: "{{ alb_response.application_load_balancer.id }}"
      datacenter_id: "{{ datacenter_response.datacenter.id }}"
      wait: true
      state: absent
  ''',
}

EXAMPLES = '\n'.join(EXAMPLE_PER_STATE.values())

uuid_match = re.compile('[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}', re.I)


def _get_matched_resources(resource_list, identity, identity_paths=None):
    """
    Fetch and return a resource based on an identity supplied for it, if none or more than one matches 
    are found an error is printed and None is returned.
    """

    if identity_paths is None:
      identity_paths = [['id'], ['properties', 'name']]

    def check_identity_method(resource):
      resource_identity = []

      for identity_path in identity_paths:
        current = resource
        for el in identity_path:
          current = getattr(current, el)
        resource_identity.append(current)

      return identity in resource_identity

    return list(filter(check_identity_method, resource_list.items))


def get_resource(module, resource_list, identity, identity_paths=None):
    matched_resources = _get_matched_resources(resource_list, identity, identity_paths)

    if len(matched_resources) == 1:
        return matched_resources[0]
    elif len(matched_resources) > 1:
        module.fail_json(msg="found more resources of type {} for '{}'".format(resource_list.id, identity))
    else:
        return None


def get_resource_id(module, resource_list, identity, identity_paths=None):
    resource = get_resource(module, resource_list, identity, identity_paths)
    return resource.id if resource is not None else None


def _update_alb(module, client, alb_server, datacenter_id, application_load_balancer_id, alb_properties):
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')
    response = alb_server.datacenters_applicationloadbalancers_patch_with_http_info(datacenter_id, application_load_balancer_id,
                                                                                alb_properties)
    (alb_response, _, headers) = response

    if wait:
        request_id = _get_request_id(headers['Location'])
        client.wait_for_completion(request_id=request_id, timeout=wait_timeout)

    return alb_response


def _get_request_id(headers):
    match = re.search('/requests/([-A-Fa-f0-9]+)/', headers)
    if match:
        return match.group(1)
    else:
        raise Exception("Failed to extract request ID from response "
                        "header 'location': '{location}'".format(location=headers['location']))


def create_alb(module, client):
    """
    Creates a Application Load Balancer

    This will create a new Application Load Balancer in the specified Datacenter.

    module : AnsibleModule object
    client: authenticated ionoscloud object.

    Returns:
        The Application Load Balancer ID if a new Application Load Balancer was created.
    """
    datacenter_id = module.params.get('datacenter_id')
    name = module.params.get('name')
    ips = module.params.get('ips')
    listener_lan = module.params.get('listener_lan')
    target_lan = module.params.get('target_lan')
    lb_private_ips = module.params.get('lb_private_ips')

    wait = module.params.get('wait')
    wait_timeout = int(module.params.get('wait_timeout'))

    alb_server = ionoscloud.ApplicationLoadBalancersApi(client)
    alb_list = alb_server.datacenters_applicationloadbalancers_get(datacenter_id=datacenter_id, depth=2)
    alb_response = None

    existing_alb = get_resource(module, alb_list, name)

    if existing_alb:
        return {
            'changed': False,
            'failed': False,
            'action': 'create',
            'application_load_balancer': existing_alb.to_dict()
        }

    alb_properties = ApplicationLoadBalancerProperties(name=name, listener_lan=listener_lan, ips=ips, target_lan=target_lan,
                                                   lb_private_ips=lb_private_ips)
    application_load_balancer = ApplicationLoadBalancer(properties=alb_properties)

    try:
        response = alb_server.datacenters_applicationloadbalancers_post_with_http_info(datacenter_id, application_load_balancer)
        (alb_response, _, headers) = response

        if wait:
            client.wait_for_completion(request_id=_get_request_id(headers['Location']), timeout=wait_timeout)

    except ApiException as e:
        module.fail_json(msg="failed to create the new Application Load Balancer: %s" % to_native(e))

    return {
        'changed': True,
        'failed': False,
        'action': 'create',
        'application_load_balancer': alb_response.to_dict()
    }


def update_alb(module, client):
    """
    Updates a Application Load Balancer.

    This will update a Application Load Balancer.

    module : AnsibleModule object
    client: authenticated ionoscloud object.

    Returns:
        True if the Application Load Balancer was updated, false otherwise
    """
    datacenter_id = module.params.get('datacenter_id')
    name = module.params.get('name')
    ips = module.params.get('ips')
    listener_lan = module.params.get('listener_lan')
    target_lan = module.params.get('target_lan')
    lb_private_ips = module.params.get('lb_private_ips')
    application_load_balancer_id = module.params.get('application_load_balancer_id')

    alb_server = ionoscloud.ApplicationLoadBalancersApi(client)
    alb_response = None

    alb_list = alb_server.datacenters_applicationloadbalancers_get(datacenter_id=datacenter_id, depth=2)
    existing_alb_id_by_name = get_resource_id(module, alb_list, name)

    if application_load_balancer_id is not None and existing_alb_id_by_name is not None and existing_alb_id_by_name != application_load_balancer_id:
            module.fail_json(msg='failed to update the {}: Another resource with the desired name ({}) exists'.format(OBJECT_NAME, name))

    alb_properties = ApplicationLoadBalancerProperties(
        name=name, listener_lan=listener_lan, ips=ips,
        target_lan=target_lan,
        lb_private_ips=lb_private_ips,
    )

    application_load_balancer_id = application_load_balancer_id if application_load_balancer_id else existing_alb_id_by_name

    if application_load_balancer_id:
        alb_response = _update_alb(module, client, alb_server, datacenter_id, application_load_balancer_id, alb_properties)
    else:
        module.fail_json(msg="failed to update the Application Load Balancer: The resource does not exist")

    return {
        'changed': True,
        'action': 'update',
        'failed': False,
        'application_load_balancer': alb_response.to_dict()
    }


def remove_alb(module, client):
    """
    Removes a Application Load Balancer.

    This will remove a Application Load Balancer.

    module : AnsibleModule object
    client: authenticated ionoscloud object.

    Returns:
        True if the Application Load Balancer was deleted, false otherwise
    """
    name = module.params.get('name')
    datacenter_id = module.params.get('datacenter_id')
    application_load_balancer_id = module.params.get('application_load_balancer_id')

    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    alb_server = ionoscloud.ApplicationLoadBalancersApi(client)


    alb_list = alb_server.datacenters_applicationloadbalancers_get(datacenter_id=datacenter_id, depth=2)
    existing_alb_id_by_name = get_resource_id(module, alb_list, name)

    application_load_balancer_id = application_load_balancer_id if application_load_balancer_id else existing_alb_id_by_name
    try:

        _, _, headers = alb_server.datacenters_applicationloadbalancers_delete_with_http_info(datacenter_id, application_load_balancer_id)

        if wait:
            client.wait_for_completion(request_id=_get_request_id(headers['Location']), timeout=wait_timeout)

    except Exception as e:
        module.fail_json(
            msg="failed to delete the Application Load Balancer: %s" % to_native(e))

    return {
        'action': 'delete',
        'changed': True,
        'id': application_load_balancer_id
    }


def get_module_arguments():
    arguments = {}

    for option_name, option in OPTIONS.items():
      arguments[option_name] = {
        'type': option['type'],
      }
      for key in ['choices', 'default', 'aliases', 'no_log', 'elements']:
        if option.get(key) is not None:
          arguments[option_name][key] = option.get(key)

      if option.get('env_fallback'):
        arguments[option_name]['fallback'] = (env_fallback, [option['env_fallback']])

      if len(option.get('required', [])) == len(STATES):
        arguments[option_name]['required'] = True

    return arguments


def get_sdk_config(module, sdk):
    username = module.params.get('username')
    password = module.params.get('password')
    token = module.params.get('token')
    api_url = module.params.get('api_url')
    certificate_fingerprint = module.params.get('certificate_fingerprint')

    if token is not None:
        # use the token instead of username & password
        conf = {
            'token': token
        }
    else:
        # use the username & password
        conf = {
            'username': username,
            'password': password,
        }

    if api_url is not None:
        conf['host'] = api_url
        conf['server_index'] = None

    if certificate_fingerprint is not None:
        conf['fingerprint'] = certificate_fingerprint

    return sdk.Configuration(**conf)


def check_required_arguments(module, state, object_name):
    # manually checking if token or username & password provided
    if (
        not module.params.get("token")
        and not (module.params.get("username") and module.params.get("password"))
    ):
        module.fail_json(
            msg='Token or username & password are required for {object_name} state {state}'.format(
                object_name=object_name,
                state=state,
            ),
        )

    for option_name, option in OPTIONS.items():
        if state in option.get('required', []) and not module.params.get(option_name):
            module.fail_json(
                msg='{option_name} parameter is required for {object_name} state {state}'.format(
                    option_name=option_name,
                    object_name=object_name,
                    state=state,
                ),
            )


def main():
    module = AnsibleModule(argument_spec=get_module_arguments(), supports_check_mode=True)

    if not HAS_SDK:
        module.fail_json(msg='ionoscloud is required for this module, run `pip install ionoscloud`')

    state = module.params.get('state')
    with ApiClient(get_sdk_config(module, ionoscloud)) as api_client:
        api_client.user_agent = USER_AGENT
        check_required_arguments(module, state, OBJECT_NAME)

        if state == 'absent' and not module.params.get('name') and not module.params.get('application_load_balancer_id'):
            module.fail_json(msg='either name or application_load_balancer_id parameter is required for {object_name} state present'.format(object_name=OBJECT_NAME))

        try:
            if state == 'absent':
                module.exit_json(**remove_alb(module, api_client))
            elif state == 'present':
                module.exit_json(**create_alb(module, api_client))
            elif state == 'update':
                module.exit_json(**update_alb(module, api_client))
        except Exception as e:
            module.fail_json(msg='failed to set {object_name} state {state}: {error}'.format(object_name=OBJECT_NAME, error=to_native(e), state=state))

if __name__ == '__main__':
    main()
