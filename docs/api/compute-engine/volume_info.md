# volume_info

This is a simple module that supports listing volumes.

## Example Syntax


```yaml

    - name: Get all volumes for given datacenter
      volume_info:
        datacenter: "{{ datacenter }}"
      register: volume_list_response
      
    - name: Get all volumes for given server
      volume_info:
        datacenter: "{{ datacenter }}"
        server: "{{ server }}"
      register: volume_list_server_response

    - name: Show all volumes for the datacenter
      debug:
        var: volume_list_response

```
### Available parameters:
&nbsp;

| Name | Required | Type | Default | Description |
| :--- | :---: | :--- | :--- | :--- |
| datacenter | True | str |  | The ID or name of the datacenter. |
| server | False | str |  | The ID or name of the server. |
| filters | False | dict |  | Filter that can be used to list only objects which have a certain set of propeties. Filters should be a dict with a key containing keys and value pair in the following format:'properties.name': 'server_name' |
| depth | False | int | 1 | The depth used when retrieving the items. |
| api_url | False | str |  | The Ionos API base URL. |
| certificate_fingerprint | False | str |  | The Ionos API certificate fingerprint. |
| username | False | str |  | The Ionos username. Overrides the IONOS_USERNAME environment variable. |
| password | False | str |  | The Ionos password. Overrides the IONOS_PASSWORD environment variable. |
| token | False | str |  | The Ionos token. Overrides the IONOS_TOKEN environment variable. |
