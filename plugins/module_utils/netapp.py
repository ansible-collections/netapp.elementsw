# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c) 2017, Sumit Kumar <sumit4@netapp.com>
# Copyright (c) 2017, Michael Price <michael.price@netapp.com>
# Copyright: (c) 2018, NetApp Ansible Team <ng-ansibleteam@netapp.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import os
import random
import mimetypes

from ansible.module_utils import six

try:
    from ansible.module_utils.ansible_release import __version__ as ansible_version
except ImportError:
    ansible_version = 'unknown'

try:
    from netapp_lib.api.zapi import zapi
    HAS_NETAPP_LIB = True
except ImportError:
    HAS_NETAPP_LIB = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

import ssl
try:
    from urlparse import urlparse, urlunparse
except ImportError:
    from urllib.parse import urlparse, urlunparse


HAS_SF_SDK = False
SF_BYTE_MAP = dict(
    # Management GUI displays 1024 ** 3 as 1.1 GB, thus use 1000.
    bytes=1,
    b=1,
    kb=1000,
    mb=1000 ** 2,
    gb=1000 ** 3,
    tb=1000 ** 4,
    pb=1000 ** 5,
    eb=1000 ** 6,
    zb=1000 ** 7,
    yb=1000 ** 8
)

POW2_BYTE_MAP = dict(
    # Here, 1 kb = 1024
    bytes=1,
    b=1,
    kb=1024,
    mb=1024 ** 2,
    gb=1024 ** 3,
    tb=1024 ** 4,
    pb=1024 ** 5,
    eb=1024 ** 6,
    zb=1024 ** 7,
    yb=1024 ** 8
)

try:
    from solidfire.factory import ElementFactory
    from solidfire.custom.models import TimeIntervalFrequency
    from solidfire.models import Schedule, ScheduleInfo

    HAS_SF_SDK = True
except Exception:
    HAS_SF_SDK = False


def has_netapp_lib():
    return HAS_NETAPP_LIB


def has_sf_sdk():
    return HAS_SF_SDK


def na_ontap_host_argument_spec():

    return dict(
        hostname=dict(required=True, type='str'),
        username=dict(required=True, type='str', aliases=['user']),
        password=dict(required=True, type='str', aliases=['pass'], no_log=True),
        https=dict(required=False, type='bool', default=False),
        validate_certs=dict(required=False, type='bool', default=True),
        http_port=dict(required=False, type='int'),
        ontapi=dict(required=False, type='int'),
        use_rest=dict(required=False, type='str', default='Auto', choices=['Never', 'Always', 'Auto'])
    )


def ontap_sf_host_argument_spec():

    return dict(
        hostname=dict(required=True, type='str'),
        username=dict(required=True, type='str', aliases=['user']),
        password=dict(required=True, type='str', aliases=['pass'], no_log=True)
    )


def create_sf_connection(module, port=None):
    hostname = module.params['hostname']
    username = module.params['username']
    password = module.params['password']

    if HAS_SF_SDK and hostname and username and password:
        try:
            return_val = ElementFactory.create(hostname, username, password, port=port)
            return return_val
        except Exception:
            raise Exception("Unable to create SF connection")
    else:
        module.fail_json(msg="the python SolidFire SDK module is required")


def setup_na_ontap_zapi(module, vserver=None):
    hostname = module.params['hostname']
    username = module.params['username']
    password = module.params['password']
    https = module.params['https']
    validate_certs = module.params['validate_certs']
    port = module.params['http_port']
    version = module.params['ontapi']

    if HAS_NETAPP_LIB:
        # set up zapi
        server = zapi.NaServer(hostname)
        server.set_username(username)
        server.set_password(password)
        if vserver:
            server.set_vserver(vserver)
        if version:
            minor = version
        else:
            minor = 110
        server.set_api_version(major=1, minor=minor)
        # default is HTTP
        if https:
            if port is None:
                port = 443
            transport_type = 'HTTPS'
            # HACK to bypass certificate verification
            if validate_certs is False:
                if not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):
                    ssl._create_default_https_context = ssl._create_unverified_context
        else:
            if port is None:
                port = 80
            transport_type = 'HTTP'
        server.set_transport_type(transport_type)
        server.set_port(port)
        server.set_server_type('FILER')
        return server
    else:
        module.fail_json(msg="the python NetApp-Lib module is required")


def setup_ontap_zapi(module, vserver=None):
    hostname = module.params['hostname']
    username = module.params['username']
    password = module.params['password']

    if HAS_NETAPP_LIB:
        # set up zapi
        server = zapi.NaServer(hostname)
        server.set_username(username)
        server.set_password(password)
        if vserver:
            server.set_vserver(vserver)
        # Todo : Replace hard-coded values with configurable parameters.
        server.set_api_version(major=1, minor=110)
        server.set_port(80)
        server.set_server_type('FILER')
        server.set_transport_type('HTTP')
        return server
    else:
        module.fail_json(msg="the python NetApp-Lib module is required")


def create_multipart_formdata(files, fields=None, send_8kb=False):
    """Create the data for a multipart/form request.

    :param list(list) files: list of lists each containing (name, filename, path).
    :param list(list) fields: list of lists each containing (key, value).
    :param bool send_8kb: only sends the first 8kb of the files (default: False).
    """
    boundary = "---------------------------" + "".join([str(random.randint(0, 9)) for x in range(27)])
    data_parts = list()
    data = None

    if six.PY2:  # Generate payload for Python 2
        newline = "\r\n"
        if fields is not None:
            for key, value in fields:
                data_parts.extend(["--%s" % boundary,
                                   'Content-Disposition: form-data; name="%s"' % key,
                                   "",
                                   value])

        for name, filename, path in files:
            with open(path, "rb") as fh:
                value = fh.read(8192) if send_8kb else fh.read()

                data_parts.extend(["--%s" % boundary,
                                   'Content-Disposition: form-data; name="%s"; filename="%s"' % (name, filename),
                                   "Content-Type: %s" % (mimetypes.guess_type(path)[0] or "application/octet-stream"),
                                   "",
                                   value])
        data_parts.extend(["--%s--" % boundary, ""])
        data = newline.join(data_parts)

    else:
        newline = six.b("\r\n")
        if fields is not None:
            for key, value in fields:
                data_parts.extend([six.b("--%s" % boundary),
                                   six.b('Content-Disposition: form-data; name="%s"' % key),
                                   six.b(""),
                                   six.b(value)])

        for name, filename, path in files:
            with open(path, "rb") as fh:
                value = fh.read(8192) if send_8kb else fh.read()

                data_parts.extend([six.b("--%s" % boundary),
                                   six.b('Content-Disposition: form-data; name="%s"; filename="%s"' % (name, filename)),
                                   six.b("Content-Type: %s" % (mimetypes.guess_type(path)[0] or "application/octet-stream")),
                                   six.b(""),
                                   value])
        data_parts.extend([six.b("--%s--" % boundary), b""])
        data = newline.join(data_parts)

    headers = {
        "Content-Type": "multipart/form-data; boundary=%s" % boundary,
        "Content-Length": str(len(data))}

    return headers, data


def ems_log_event(source, server, name="Ansible", id="12345", version=ansible_version,
                  category="Information", event="setup", autosupport="false"):
    ems_log = zapi.NaElement('ems-autosupport-log')
    # Host name invoking the API.
    ems_log.add_new_child("computer-name", name)
    # ID of event. A user defined event-id, range [0..2^32-2].
    ems_log.add_new_child("event-id", id)
    # Name of the application invoking the API.
    ems_log.add_new_child("event-source", source)
    # Version of application invoking the API.
    ems_log.add_new_child("app-version", version)
    # Application defined category of the event.
    ems_log.add_new_child("category", category)
    # Description of event to log. An application defined message to log.
    ems_log.add_new_child("event-description", event)
    ems_log.add_new_child("log-level", "6")
    ems_log.add_new_child("auto-support", autosupport)
    server.invoke_successfully(ems_log, True)


def get_cserver_zapi(server):
    vserver_info = zapi.NaElement('vserver-get-iter')
    query_details = zapi.NaElement.create_node_with_children('vserver-info', **{'vserver-type': 'admin'})
    query = zapi.NaElement('query')
    query.add_child_elem(query_details)
    vserver_info.add_child_elem(query)
    result = server.invoke_successfully(vserver_info,
                                        enable_tunneling=False)
    attribute_list = result.get_child_by_name('attributes-list')
    vserver_list = attribute_list.get_child_by_name('vserver-info')
    return vserver_list.get_child_content('vserver-name')


def get_cserver(connection, is_rest=False):
    if not is_rest:
        return get_cserver_zapi(connection)

    params = {'fields': 'type'}
    api = "private/cli/vserver"
    json, error = connection.get(api, params)
    if json is None or error is not None:
        # exit if there is an error or no data
        return None
    vservers = json.get('records')
    if vservers is not None:
        for vserver in vservers:
            if vserver['type'] == 'admin':     # cluster admin
                return vserver['vserver']
        if len(vservers) == 1:                  # assume vserver admin
            return vservers[0]['vserver']

    return None
