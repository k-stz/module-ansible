#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re
import yaml
import copy

HAS_SDK = True

try:
    import ionoscloud
    from ionoscloud import __version__ as sdk_version
    from ionoscloud.models import FlowLog, FlowLogProperties, FlowLogPut
    from ionoscloud.rest import ApiException
    from ionoscloud import ApiClient
except ImportError:
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
OBJECT_NAME = 'Flowlog'

OPTIONS = {
    'name': {
        'description': ['The name of the flowlog.'],
        'available': STATES,
        'required': ['present'],
        'type': 'str',
    },
    'action': {
        'description': ['Specifies the traffic action pattern.'],
        'available': ['present', 'update'],
        'required': ['present'],
        'type': 'str',
    },
    'direction': {
        'description': ['Specifies the traffic direction pattern.'],
        'available': ['present', 'update'],
        'required': ['present'],
        'type': 'str',
    },
    'bucket': {
        'description': ['S3 bucket name of an existing IONOS Cloud S3 bucket.'],
        'available': ['present', 'update'],
        'required': ['present'],
        'type': 'str',
    },
    'datacenter_id': {
        'description': ['The ID of the datacenter.'],
        'available': STATES,
        'required': STATES,
        'type': 'str',
    },
    'application_load_balancer_id': {
        'description': ['The ID of the Application Loadbalancer.'],
        'available': STATES,
        'required': STATES,
        'type': 'str',
    },
    'flowlog_id': {
        'description': ['The ID of the Flowlog.'],
        'available': STATES,
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
module: application_balancer_flowlog
short_description: Create or destroy a Ionos Cloud Application Loadbalancer Flowlog.
description:
     - This is a simple module that supports creating or removing Application Loadbalancer Flowlogs.
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
  - name: Create Application Load Balancer Flowlog
    application_load_balancer_flowlog:
      name: "{{ name }}"
      action: "ACCEPTED"
      direction: "INGRESS"
      bucket: "sdktest"
      datacenter_id: "{{ datacenter_response.datacenter.id }}"
      application_load_balancer_id: "{{ alb_response.application_load_balancer.id }}"
      wait: true
    register: alb_flowlog_response
  ''',
  'update' : '''
  - name: Update Application Load Balancer Flowlog
    application_load_balancer_flowlog:
      datacenter_id: "{{ datacenter_response.datacenter.id }}"
      application_load_balancer_id: "{{ alb_response.application_load_balancer.id }}"
      flowlog_id: "{{ alb_flowlog_response.flowlog.id }}"
      name: "{{ name }}"
      action: "ALL"
      direction: "INGRESS"
      bucket: "sdktest"
      wait: true
      state: update
    register: alb_flowlog_update_response
  ''',
  'absent' : '''
  - name: Delete Application Load Balancer Flowlog
    application_load_balancer_flowlog:
      datacenter_id: "{{ datacenter_response.datacenter.id }}"
      application_load_balancer_id: "{{ alb_response.application_load_balancer.id }}"
      flowlog_id: "{{ alb_flowlog_response.flowlog.id }}"
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


def _update_alb_flowlog(module, client, alb_server, datacenter_id, application_load_balancer_id, flowlog_id,
                        flowlog_properties):
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')
    response = alb_server.datacenters_applicationloadbalancers_flowlogs_patch_with_http_info(datacenter_id,
                                                                                         application_load_balancer_id,
                                                                                         flowlog_id,
                                                                                         flowlog_properties)
    (flowlog_response, _, headers) = response

    if wait:
        request_id = _get_request_id(headers['Location'])
        client.wait_for_completion(request_id=request_id, timeout=wait_timeout)

    return flowlog_response


def _get_request_id(headers):
    match = re.search('/requests/([-A-Fa-f0-9]+)/', headers)
    if match:
        return match.group(1)
    else:
        raise Exception("Failed to extract request ID from response "
                        "header 'location': '{location}'".format(location=headers['location']))


def create_alb_flowlog(module, client):
    """
    Creates a Application Load Balancer Flowlog

    This will create a new Application Load Balancer Flowlog in the specified Datacenter.

    module : AnsibleModule object
    client: authenticated ionoscloud object.

    Returns:
        The Application Load Balancer Flowlog ID if a new Application Load Balancer Flowlog was created.
    """
    name = module.params.get('name')
    action = module.params.get('action')
    direction = module.params.get('direction')
    bucket = module.params.get('bucket')
    datacenter_id = module.params.get('datacenter_id')
    application_load_balancer_id = module.params.get('application_load_balancer_id')

    wait = module.params.get('wait')
    wait_timeout = int(module.params.get('wait_timeout'))

    alb_server = ionoscloud.ApplicationLoadBalancersApi(client)
    alb_flowlogs = alb_server.datacenters_applicationloadbalancers_flowlogs_get(
        datacenter_id=datacenter_id,
        application_load_balancer_id=application_load_balancer_id,
        depth=2,
    )
    alb_flowlog_response = None

    existing_flowlog = get_resource(module, alb_flowlogs, name)

    if existing_flowlog:
        return {
            'changed': False,
            'failed': False,
            'action': 'create',
            'flowlog': existing_flowlog.to_dict()
        }

    alb_flowlog_properties = FlowLogProperties(name=name, action=action, direction=direction, bucket=bucket)
    alb_flowlog = FlowLog(properties=alb_flowlog_properties)

    try:
        response = alb_server.datacenters_applicationloadbalancers_flowlogs_post_with_http_info(
            datacenter_id, application_load_balancer_id, alb_flowlog,
        )
        (alb_flowlog_response, _, headers) = response

        if wait:
            client.wait_for_completion(request_id=_get_request_id(headers['Location']), timeout=wait_timeout)

    except ApiException as e:
        module.fail_json(msg="failed to create the new Application Load Balancer Flowlog: %s" % to_native(e))

    return {
        'changed': True,
        'failed': False,
        'action': 'create',
        'flowlog': alb_flowlog_response.to_dict()
    }


def update_alb_flowlog(module, client):
    """
    Updates a Application Load Balancer Flowlog.

    This will update a Application Load Balancer Flowlog.

    module : AnsibleModule object
    client: authenticated ionoscloud object.

    Returns:
        True if the Application Load Balancer Flowlog was updated, false otherwise
    """
    name = module.params.get('name')
    action = module.params.get('action')
    direction = module.params.get('direction')
    bucket = module.params.get('bucket')
    datacenter_id = module.params.get('datacenter_id')
    application_load_balancer_id = module.params.get('application_load_balancer_id')
    flowlog_id = module.params.get('flowlog_id')

    alb_server = ionoscloud.ApplicationLoadBalancersApi(client)
    flowlog_response = None

    flowlog_properties = FlowLogProperties(name=name, action=action, direction=direction, bucket=bucket)

    flowlogs = alb_server.datacenters_applicationloadbalancers_flowlogs_get(
        datacenter_id=datacenter_id,
        application_load_balancer_id=application_load_balancer_id,
        depth=2,
    )
    
    existing_flowlog_id_by_name = get_resource_id(module, flowlogs, name)

    if flowlog_id is not None and existing_flowlog_id_by_name is not None and existing_flowlog_id_by_name != flowlog_id:
        module.fail_json(msg='failed to update the {}: Another resource with the desired name ({}) exists'.format(OBJECT_NAME, name))

    flowlog_id = flowlog_id if flowlog_id else existing_flowlog_id_by_name
    
    if flowlog_id:
        flowlog_response = _update_alb_flowlog(
            module, client, alb_server, datacenter_id,
            application_load_balancer_id, flowlog_id,
            flowlog_properties,
        )
    else:
        module.fail_json(msg="failed to update the Application Load Balancer Flowlog: The resource does not exist")

    return {
        'changed': True,
        'action': 'update',
        'failed': False,
        'flowlog': flowlog_response.to_dict()
    }


def remove_alb_flowlog(module, client):
    """
    Removes a Application Load Balancer Flowlog.

    This will remove a Application Load Balancer Flowlog.

    module : AnsibleModule object
    client: authenticated ionoscloud object.

    Returns:
        True if the Application Load Balancer Flowlog was deleted, false otherwise
    """
    name = module.params.get('name')
    datacenter_id = module.params.get('datacenter_id')
    application_load_balancer_id = module.params.get('application_load_balancer_id')
    flowlog_id = module.params.get('flowlog_id')

    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    alb_server = ionoscloud.ApplicationLoadBalancersApi(client)

    flowlogs = alb_server.datacenters_applicationloadbalancers_flowlogs_get(
        datacenter_id=datacenter_id,
        application_load_balancer_id=application_load_balancer_id,
        depth=2,
    )
    
    existing_flowlog_id_by_name = get_resource_id(module, flowlogs, name)
    flowlog_id = flowlog_id if flowlog_id else existing_flowlog_id_by_name

    try:
        _, _, headers = alb_server.datacenters_applicationloadbalancers_flowlogs_delete_with_http_info(
            datacenter_id, application_load_balancer_id, flowlog_id,
        )
        if wait:
            client.wait_for_completion(request_id=_get_request_id(headers['Location']), timeout=wait_timeout)
    except Exception as e:
        module.fail_json(msg="failed to delete the Application Load Balancer Flowlog: %s" % to_native(e))

    return {
        'action': 'delete',
        'changed': True,
        'id': flowlog_id
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

        if state in ['absent', 'update'] and not module.params.get('name') and not module.params.get('flowlog_id'):
            module.fail_json(msg='either name or flowlog_id parameter is required for {object_name} state {state}'.format(
                object_name=OBJECT_NAME, state=state,
            ))

        try:
            if state == 'absent':
                module.exit_json(**remove_alb_flowlog(module, api_client))
            elif state == 'present':
                module.exit_json(**create_alb_flowlog(module, api_client))
            elif state == 'update':
                module.exit_json(**update_alb_flowlog(module, api_client))
        except Exception as e:
            module.fail_json(msg='failed to set {object_name} state {state}: {error}'.format(object_name=OBJECT_NAME, error=to_native(e), state=state))


if __name__ == '__main__':
    main()
