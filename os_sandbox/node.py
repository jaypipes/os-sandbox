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
import shutil
import uuid
import yaml

import libvirt
import slugify

from os_sandbox import helpers
from os_sandbox import image
from os_sandbox import template

_libvirt_domain_state_code_map = {
    libvirt.VIR_DOMAIN_NOSTATE: 'No state',
    libvirt.VIR_DOMAIN_RUNNING: 'Running',
    libvirt.VIR_DOMAIN_BLOCKED: 'Blocked',
    libvirt.VIR_DOMAIN_PAUSED: 'Paused',
    libvirt.VIR_DOMAIN_SHUTDOWN: 'Shutdown',
    libvirt.VIR_DOMAIN_SHUTOFF: 'Shut off',
    libvirt.VIR_DOMAIN_CRASHED: 'Crashed',
    libvirt.VIR_DOMAIN_PMSUSPENDED: 'Suspended',
}

def libvirt_callback(ignore, err):
    if err[3] != libvirt.VIR_ERR_ERROR:
          # Don't log libvirt errors: global error handler will do that
          logging.warn("Non-error from libvirt: '%s'" % err[2])
libvirt.registerErrorHandler(f=libvirt_callback, ctx=None)


class Node(object):

    STATUS_UNDEFINED = 'Undefined'
    STATUS_RUNNING = 'Running'
    STATUS_ERROR = 'Error'

    def __init__(self, sandbox, name):
        self.sandbox = sandbox
        self.parsed_args = sandbox.parsed_args
        self.name = name
        self.node_dir = os.path.join(sandbox.nodes_dir,
                                     self.name)
        self.conf_path = os.path.join(self.node_dir,
                                      'config.yaml')

        if os.path.exists(self.conf_path):
            self._fill()

    def _fill(self):
        conf = yaml.load(open(self.conf_path, 'rb'))
        self.uuid = conf['uuid']
        self.resources = conf['resources']
        self.image = image.Image(self.parsed_args, conf['image'])

    def _get_conn(self, readonly=True):
        if readonly:
            conn = libvirt.openReadOnly(None)
        else:
            conn = libvirt.open(None)
        if conn == None:
            msg = "Failed to connect to QEMU."
            raise RuntimeError(msg)
        return conn

    def _get_domain(self, readonly=True):
        conn = self._get_conn(readonly)
        return conn.lookupByName(self.name)

    def exists(self):
        return os.path.exists(self.conf_path)

    def started(self):
        try:
            dom = self._get_domain()
            return dom.info()[0] == libvirt.VIR_DOMAIN_RUNNING
        except:
            return False

    def get_info(self):
        return {
            'uuid': self.uuid,
            'name': self.name,
            'image': self.image.name,
            'resources': self.resources,
        }

    def create(self, node_conf):
        """Define the virtual machine if it isn't already defined using
        the node configuration block from a template definition."""
        if self.exists():
            msg = "The node with name {0} is already defined."
            msg = msg.format(self.name)
            raise RuntimeError(msg)

        os.mkdir(self.node_dir, 0755)

        self.resources = node_conf['resources']
        self.image = image.Image(self.parsed_args,
                                 node_conf['image'])
        self.uuid = uuid.uuid4().hex

        with open(self.conf_path, 'wb') as conf_file:
            conf_file.write(yaml.dump(self.get_info(),
                                      default_flow_style=False))

    def _get_xml(self):
        net_xml_texts = []
        for net in self.sandbox.networks:
            net_xml_texts.append("""
<interface type='network'>
    <source network='{0}'/>
    <model type='e1000'/>
</interface>
""".format(net.slug))
        net_xml_text = "\n".join(net_xml_texts)
        conf = {
            'name': self.name,
            'uuid': self.uuid,
            'image_path': self.image.image_path,
            'vcpus': self.resources['vcpu'],
            'memory_bytes': self.resources['ram_mb'] * 1024,
            'net_xml': net_xml_text,
        }
        xml_text = """
<domain type='kvm'>
    <uuid>{uuid}</uuid>
    <name>{name}</name>
    <vcpu>{vcpus}</vcpu>
    <memory>{memory_bytes}</memory>
    <os>
        <type arch="i686">hvm</type>
    </os>
    <devices>
        <disk type='file' device='disk'>
            <source file='{image_path}'/>
            <target dev='hda'/>
        </disk>
        {net_xml}
        <serial type='pty'>
            <target port='0'/>
        </serial>
        <console type='pty'>
            <target type='serial' port='0'/>
        </console>
    </devices>
</domain>
""".format(**conf)
        return xml_text

    @property
    def status(self):
        """Queries libvirt to return the status of the environment's VMs"""
        if not self.exists():
            return Node.STATUS_UNDEFINED
        try:
            dom = self._get_domain()
            return _libvirt_domain_state_code_map[dom.info()[0]]
        except:
            return Node.STATUS_ERROR

    def start(self):
        if not self.exists():
            msg = "A node with name {0} does not exist."
            msg = msg.format(self.name)
            raise RuntimeError(msg)

        if self.started():
            return

        conn = self._get_conn(readonly=False)
        dom = conn.createXML(self._get_xml(), 0)
        if dom == None:
            msg = "Failed to start guest {0}"
            msg = msg.format(self.name)
            raise RuntimeError(msg)
        conn.close()

    def stop(self):
        if not self.exists():
            msg = "A node with name {0} does not exist."
            msg = msg.format(self.name)
            raise RuntimeError(msg)

        if not self.started():
            return

        dom = self._get_domain(readonly=False)
        if dom == None:
            msg = "Failed to stop guest {0}"
            msg = msg.format(self.name)
            raise RuntimeError(msg)
        dom.destroy()
