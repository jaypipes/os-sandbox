# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import os

import libvirt
import netaddr
import slugify

from os_sandbox import helpers


class Network(object):

    LOG = logging.getLogger(__name__)

    STATUS_UP = 'UP'
    STATUS_DOWN = 'DOWN'
    STATUS_ERROR = 'ERROR'

    def __init__(self, sandbox, name, cidr):
        self.sandbox = sandbox
        self.name = name
        self.slug = slugify.slugify(helpers.utf8_bytes(self.name))
        self.cidr = cidr
        self.error = None
        self.ip_net = netaddr.IPNetwork(cidr)
        self.gateway_ip_address = str(self.ip_net.ip)
        self.dhcp_ip_address_start = str(self.ip_net[1])
        self.dhcp_ip_address_end = str(self.ip_net[-2])  # [-1] is broadcast

    def _get_conn(self, readonly=True):
        if readonly:
            conn = libvirt.openReadOnly(None)
        else:
            conn = libvirt.open(None)
        if conn == None:
            msg = "Failed to connect to QEMU."
            raise RuntimeError(msg)
        return conn

    def _get_libvirt_net(self, readonly=True):
        conn = self._get_conn(readonly)
        return conn.networkLookupByName(self.name)

    def _get_xml(self):
        conf = {
            'name': self.name,
            'gateway_ip_address': self.gateway_ip_address,
            'dhcp_ip_address_start': self.dhcp_ip_address_start,
            'dhcp_ip_address_end': self.dhcp_ip_address_end,
        }
        xml_text = """
<network>
    <name>{name}</name>
    <forward mode='nat'/>
    <ip address='{gateway_ip_address}' netmask='255.255.255.0'>
        <dhcp>
            <range start='{dhcp_ip_address_start}'
                   end='{dhcp_ip_address_end}'/>
        </dhcp>
    </ip>
</network>
""".format(**conf)
        return xml_text

    @property
    def status(self):
        if self.error is not None:
            return Network.STATUS_ERROR
        try:
            net = self._get_libvirt_net()
            if net.isActive() :
                return Network.STATUS_UP
            else:
                return Network.STATUS_DOWN
        except libvirt.libvirtError as err:
            err_code = err.get_error_code()
            if err_code == libvirt.VIR_ERR_NO_NETWORK:
                # The networks for sandboxes are temporal, so there's
                # no real mapping of "no network found" other than the
                # network should be considered not "up".
                return Network.STATUS_DOWN
            self.error = err
            return Network.STATUS_ERROR

    def start(self):
        if self.status == Network.STATUS_UP:
            return

        conn = self._get_conn(readonly=False)
        net = conn.networkCreateXML(self._get_xml())
        if net == None:
            msg = "Failed to start network {0}"
            msg = msg.format(self.name)
            self.error = msg
            raise RuntimeError(msg)
        conn.close()

    def stop(self):
        conn = self._get_conn(False)
        try:
            net = conn.networkLookupByName(self.name)
        except libvirt.libvirtError as err:
            if err.get_error_code() == libvirt.VIR_ERR_NO_NETWORK:
                return
            self.error = err
        if net == None:
            msg = "Failed to stop network {0}"
            msg = msg.format(self.name)
            raise RuntimeError(msg)
        net.destroy()
