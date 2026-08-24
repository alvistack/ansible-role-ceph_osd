#!/usr/bin/python

# Copyright 2020, Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

import datetime
import json
import os
import re

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: ceph_mgr_module
short_description: Manage Ceph MGR module
version_added: "2.8"
description:
    - Manage Ceph MGR module
options:
    name:
        description:
            - name of the ceph MGR module.
        required: true
    cluster:
        description:
            - The ceph cluster name.
        required: false
        default: ceph
    state:
        description:
            - If 'enable' is used, the module enables the MGR module.
            If 'absent' is used, the module disables the MGR module.
        required: false
        choices: ['enable', 'disable']
        default: enable
author:
    - Dimitri Savineau <dsavinea@redhat.com>
'''

EXAMPLES = '''
- name: enable dashboard mgr module
  ceph_mgr_module:
    name: dashboard
    state: enable

- name: disable multiple mgr modules
  ceph_mgr_module:
    name: '{{ item }}'
    state: disable
  loop:
    - 'dashboard'
    - 'prometheus'
'''

RETURN = '''#  '''


def generate_ceph_cmd(sub_cmd, args, user_key=None, cluster='ceph', user='client.admin', container_image=None, interactive=False):  # noqa: E501
    '''
    Generate 'ceph' command line to execute
    '''

    if not user_key:
        user_key = '/etc/ceph/{}.{}.keyring'.format(cluster, user)

    cmd = pre_generate_ceph_cmd(container_image=container_image, interactive=interactive)  # noqa: E501

    base_cmd = [
        '-n',
        user,
        '-k',
        user_key,
        '--cluster',
        cluster
    ]
    base_cmd.extend(sub_cmd)
    cmd.extend(base_cmd + args)

    return cmd


def container_exec(binary, container_image, interactive=False):
    '''
    Build the docker CLI to run a command inside a container
    '''

    container_binary = os.getenv('CEPH_CONTAINER_BINARY', 'podman')
    command_exec = [container_binary, 'run']

    if interactive:
        command_exec.extend(['--interactive'])

    command_exec.extend(['--rm',
                         '--net=host',
                         '-v', '/etc/ceph:/etc/ceph:z',
                         '-v', '/var/lib/ceph/:/var/lib/ceph/:z',
                         '-v', '/var/log/ceph/:/var/log/ceph/:z',
                         '--entrypoint=' + binary, container_image])
    return command_exec


def is_containerized():
    '''
    Check if we are running on a containerized cluster
    '''

    if 'CEPH_CONTAINER_IMAGE' in os.environ:
        container_image = os.getenv('CEPH_CONTAINER_IMAGE')
    else:
        container_image = None

    return container_image


def pre_generate_ceph_cmd(container_image=None, interactive=False):
    '''
    Generate ceph prefix comaand
    '''
    if container_image:
        cmd = container_exec('ceph', container_image, interactive=interactive)
    else:
        cmd = ['ceph']

    return cmd


def exec_command(module, cmd, stdin=None):
    '''
    Execute command(s)
    '''

    binary_data = False
    if stdin:
        binary_data = True
    rc, out, err = module.run_command(cmd, data=stdin, binary_data=binary_data)

    return rc, cmd, out, err


def exit_module(module, out, rc, cmd, err, startd, changed=False, diff=dict(before="", after="")):  # noqa: E501
    endd = datetime.datetime.now()
    delta = endd - startd

    result = dict(
        cmd=cmd,
        start=str(startd),
        end=str(endd),
        delta=str(delta),
        rc=rc,
        stdout=out.rstrip("\r\n"),
        stderr=err.rstrip("\r\n"),
        changed=changed,
        diff=diff
    )
    module.exit_json(**result)


def fatal(message, module):
    '''
    Report a fatal error and exit
    '''

    if module:
        module.fail_json(msg=message, rc=1)
    else:
        raise (Exception(message))


def detect_ceph_version(module, container_image=None):
    '''
    Automatically detect the major version of Ceph running on host/container
    '''
    cmd = pre_generate_ceph_cmd(container_image=container_image)
    cmd.append('--version')
    rc, out, err = module.run_command(cmd)

    if rc == 0 and out:
        match = re.search(r'version\s+(\d+)\.', out)
        if match:
            return int(match.group(1))

    # Fallback to 20 if version query fails
    return 20


def get_enabled_modules(module, cluster='ceph', container_image=None):
    '''
    List currently enabled MGR modules
    '''
    cmd = generate_ceph_cmd(['mgr', 'module'],
                            ['ls'],
                            cluster=cluster,
                            container_image=container_image)
    rc, out, err = module.run_command(cmd)

    enabled_modules = []
    if rc == 0 and out:
        try:
            data = json.loads(out)
            if isinstance(data, dict) and 'enabled_modules' in data:
                enabled_modules = data['enabled_modules']
            elif isinstance(data, list):
                enabled_modules = data
        except ValueError:
            pass

    return enabled_modules


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True),
            cluster=dict(type='str', required=False, default='ceph'),
            state=dict(type='str', required=False, default='enable', choices=['enable', 'disable']),  # noqa: E501
        ),
        supports_check_mode=True,
    )

    name = module.params.get('name')
    cluster = module.params.get('cluster')
    state = module.params.get('state')

    startd = datetime.datetime.now()

    container_image = is_containerized()

    enabled_modules = get_enabled_modules(module, cluster=cluster, container_image=container_image)  # noqa: E501
    is_enabled = name in enabled_modules

    cmd = generate_ceph_cmd(['mgr', 'module'],
                            [state, name],
                            cluster=cluster,
                            container_image=container_image)

    if (state == 'enable' and is_enabled) or (state == 'disable' and not is_enabled):  # noqa: E501
        exit_module(
            module=module,
            out='',
            rc=0,
            cmd=cmd,
            err='',
            startd=startd,
            changed=False
        )

    if module.check_mode:
        exit_module(
            module=module,
            out='',
            rc=0,
            cmd=cmd,
            err='',
            startd=startd,
            changed=True
        )

    rc, out, err = module.run_command(cmd)

    if rc != 0:
        if ('is already enabled' in err or 'is already disabled' in err or
                'is already enabled' in out or 'is already disabled' in out):
            changed = False
            rc = 0
        else:
            module.fail_json(msg='failed to {} MGR module {}: {}'.format(state, name, err), rc=rc)  # noqa: E501
    else:
        changed = True

    exit_module(
        module=module,
        out=out,
        rc=rc,
        cmd=cmd,
        err=err,
        startd=startd,
        changed=changed
    )


if __name__ == '__main__':
    main()
