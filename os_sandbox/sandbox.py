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

import os
import shutil
import yaml

import slugify

from os_sandbox import helpers
from os_sandbox import template
from os_sandbox import network
from os_sandbox import node


class Sandbox(object):

    STATUS_NO_NODES = 'No nodes defined'
    STATUS_NOT_STARTED = 'Not started'
    STATUS_ERROR = 'Error'
    STATUS_STARTED = 'Started'

    def __init__(self, parsed_args, name):
        self.parsed_args = parsed_args
        self.name = name
        self.slug = slugify.slugify(helpers.utf8_bytes(name))
        self.sandbox_dir = os.path.join(parsed_args.state_dir,
                                        'sandboxes',
                                        self.slug)
        self.nodes_dir = os.path.join(self.sandbox_dir, 'nodes')
        self.conf_path = os.path.join(self.sandbox_dir, 'config.yaml')
        # networks contains a list of network.Network objects that contain CIDR
        # information and are start()ed when the Sandbox is started. Networks,
        # like nodes, not persistent. They are torn down when the sandbox is
        # torn down or when the sandbox host is restarted.
        self.networks = []
        # nodes contains a list of node.Node objects that contain configuration
        # information and are start()ed when the Sandbox is started. Nodes are
        # not persistent; their libvirt XML content is created on-demand when
        # the sandbox is started.
        if os.path.exists(self.conf_path):
            self._fill()

    def _fill(self):
        self.conf = yaml.load(open(self.conf_path, 'rb').read())
        self.full_name = self.conf['full_name']
        self.nodes = [
            node.Node(self, node_info['name'])
            for node_info in self.conf['nodes']
        ]
        self.networks = [
            network.Network(self, net_name, net_info['cidr'])
            for net_name, net_info in self.conf['networks'].items()
        ]
        self.template = template.Template(self.parsed_args,
                                          self.conf['template'])

    def exists(self):
        return os.path.exists(self.sandbox_dir)

    def create(self):
        """Creates the sandbox if it doesn't exist."""
        if self.exists():
            msg = "A sandbox with name {0} already exists.".format(self.name)
            raise RuntimeError(msg)

        tpl_name = self.parsed_args.template
        tpl = template.Template(self.parsed_args, tpl_name)
        if not tpl.exists():
            msg = "No template with name {0} found.".format(tpl_name)
            raise RuntimeError(msg)

        os.mkdir(self.sandbox_dir, 0755)
        os.mkdir(self.nodes_dir, 0755)

        networks = tpl.networks
        nodes = self._create_nodes(tpl)
        config = {
            'full_name': self.name,
            'template': tpl_name,
            'networks': networks,
            'nodes': nodes,
        }

        with open(self.conf_path, 'wb') as conf_file:
            conf_file.write(yaml.dump(config, default_flow_style=False))
        self._fill()

    def _create_nodes(self, tpl):
        """Given a template instance, create the libvirt XML file definition of
        each node in the template.
        """
        nodes = []
        for node_info in tpl.nodes:
            node_name = node_info['name']
            n = node.Node(self, node_name)
            n.create(node_info)
            nodes.append(n.get_info())
        return nodes

    @property
    def status(self):
        """Queries libvirt to return the status of the environment's VMs"""
        if len(self.nodes) == 0:
            return Sandbox.STATUS_NO_NODES_DEFINED
        else:
            status = Sandbox.STATUS_NOT_STARTED
            
            guest_states = [n.status for n in self.nodes]
            if all(node.Node.STATUS_RUNNING == s for s in guest_states):
                status = Sandbox.STATUS_STARTED
            elif node.Node.STATUS_ERROR in guest_states:
                status = Sandbox.STATUS_ERROR
        return status

    def start(self):
        for net in self.networks:
            net.start()
        for n in self.nodes:
            n.start()

    def stop(self):
        for net in self.networks:
            net.stop()
        for n in self.nodes:
            n.stop()

    def delete(self):
        self.stop()
        shutil.rmtree(self.sandbox_dir)
