import copy
import yaml

from ansible import __version__
from ansible.module_utils.basic import AnsibleModule, env_fallback
from ansible.module_utils._text import to_native

HAS_SDK = True
try:
    import ionoscloud_dataplatform
except ImportError:
    HAS_SDK = False

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community',
}
DATAPLATFORM_USER_AGENT = 'ansible-module/%s_ionos-cloud-sdk-python/%s' % (
__version__, ionoscloud_dataplatform.__version__)
DOC_DIRECTORY = 'dataplatform'
STATES = ['info']
OBJECT_NAME = 'DataPlatform Clusters'

OPTIONS = {
    'filters': {
            'description': [
                'Filter that can be used to list only objects which have a certain set of propeties. Filters '
                'should be a dict with a key containing keys and value pair in the following format:'
                "'properties.name': 'server_name'"
            ],
            'available': STATES,
            'type': 'dict',
    },
    'api_url': {
        'description': ['The Ionos API base URL.'],
        'version_added': '2.4',
        'env_fallback': 'IONOS_API_URL',
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
}


def transform_for_documentation(val):
    val['required'] = len(val.get('required', [])) == len(STATES)
    del val['available']
    del val['type']
    return val


DOCUMENTATION = '''
---
module: dataplatform_cluster_info
short_description: List DataPlatform Clusters
description:
     - This is a simple module that supports listing existing DataPlatform Clusters
     - ⚠️ **Note:** Data Platform is currently in the Early Access (EA) phase. We recommend keeping usage and testing to non-production critical applications. Please contact your sales representative or support for more information.
version_added: "2.0"
options:
''' + '  ' + yaml.dump(
    yaml.safe_load(str({k: transform_for_documentation(v) for k, v in copy.deepcopy(OPTIONS).items()})),
    default_flow_style=False).replace('\n', '\n  ') + '''
requirements:
    - "python >= 2.6"
    - "ionoscloud-dataplatform >= 1.0.0"
author:
    - "IONOS Cloud SDK Team <sdk-tooling@ionos.com>"
'''

EXAMPLES = '''
    - name: List DataPlatform Clusters
        dataplatform_cluster_info:
        register: dataplatform_clusters_response


    - name: Show DataPlatform Clusters
        debug:
            var: dataplatform_clusters_response.result
'''


def get_method_from_filter(filter):
    '''
    Returns the method which check a filter for one object. Such a method would work in the following way:
    for filter = ('properties.name', 'server_name') the resulting method would be
    def method(item):
        return item.properties.name == 'server_name'
    Parameters:
            filter (touple): Key, value pair representing the filter.
    Returns:
            the wanted method
    '''
    key, value = filter
    def method(item):
        current = item
        for key_part in key.split('.'):
            current = getattr(current, key_part)
        return current == value
    return method


def get_method_to_apply_filters_to_item(filter_list):
    '''
    Returns the method which applies a list of filtering methods obtained using get_method_from_filter to
    one object and returns true if all the filters return true
    Parameters:
            filter_list (list): List of filtering methods
    Returns:
            the wanted method
    '''
    def f(item):
        return all([f(item) for f in filter_list])
    return f


def apply_filters(module, item_list):
    '''
    Creates a list of filtering methods from the filters module parameter, filters item_list to keep only the
    items for which every filter matches using get_method_to_apply_filters_to_item to make that check and returns
    those items
    Parameters:
            module: The current Ansible module
            item_list (list): List of items to be filtered
    Returns:
            List of items which match the filters
    '''
    filters = module.params.get('filters')
    if not filters:
        return item_list
    filter_methods = list(map(get_method_from_filter, filters.items()))

    return filter(get_method_to_apply_filters_to_item(filter_methods), item_list)


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

    return sdk.Configuration(**conf)


def check_required_arguments(module, object_name):
    # manually checking if token or username & password provided
    if (
            not module.params.get("token")
            and not (module.params.get("username") and module.params.get("password"))
    ):
        module.fail_json(
            msg='Token or username & password are required for {object_name}'.format(
                object_name=object_name,
            ),
        )

    for option_name, option in OPTIONS.items():
        if 'info' in option.get('required', []) and not module.params.get(option_name):
            module.fail_json(
                msg='{option_name} parameter is required for retrieving {object_name}'.format(
                    option_name=option_name,
                    object_name=object_name,
                ),
            )


def main():
    module = AnsibleModule(argument_spec=get_module_arguments(), supports_check_mode=True)

    if not HAS_SDK:
        module.fail_json(
            msg='ionoscloud_dataplatform is required for this module, run `pip install ionoscloud_dataplatform`')

    dataplatform_api_client = ionoscloud_dataplatform.ApiClient(get_sdk_config(module, ionoscloud_dataplatform))
    dataplatform_api_client.user_agent = DATAPLATFORM_USER_AGENT

    check_required_arguments(module, OBJECT_NAME)
    try:
        clusters = ionoscloud_dataplatform.DataPlatformClusterApi(dataplatform_api_client).get_clusters()
        results = list(map(lambda x: x.to_dict(), apply_filters(module, clusters.items)))
        module.exit_json(result=results)
    except Exception as e:
        module.fail_json(
            msg='failed to retrieve {object_name}: {error}'.format(object_name=OBJECT_NAME, error=to_native(e)))


if __name__ == '__main__':
    main()
