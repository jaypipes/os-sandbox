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
import yaml

import slugify
import netaddr

from os_sandbox import helpers
from os_sandbox import template
from os_sandbox import network
from os_sandbox import node


class Sandbox(object):

    LOG = logging.getLogger(__name__)

    STATUS_NO_NODES = 'NO_NODES'
    STATUS_ERROR = 'ERROR'
    STATUS_DOWN = 'DOWN'
    STATUS_UP = 'UP'

    def __init__(self, parsed_args, name):
        self.parsed_args = parsed_args
        self.name = name
        self.slug = slugify.slugify(helpers.utf8_bytes(name))
        self.sandbox_dir = os.path.join(parsed_args.state_dir,
                                        'sandboxes',
                                        self.slug)
        self.nodes_dir = os.path.join(self.sandbox_dir, 'nodes')
        self.conf_path = os.path.join(self.sandbox_dir, 'config.yaml')
        self.error = None
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
            try:
                self._fill()
            except Exception as err:
                self.error = err
                raise

    def _fill(self):
        self.conf = yaml.load(open(self.conf_path, 'rb').read())
        self.full_name = self.conf['full_name']
        self.nodes = [
            node.Node(self, node_info['name'])
            for node_info in self.conf['nodes']
        ]
        self.networks = [
            network.Network(self, net_name, cidr)
            for net_name, cidr in self.conf['networks'].items()
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

        sandboxes = Sandboxes(self.parsed_args)
        network_cidrs = sandboxes.get_next_available_network_cidrs()

        os.mkdir(self.sandbox_dir, 0755)
        os.mkdir(self.nodes_dir, 0755)

        nodes = self._create_nodes(tpl)
        config = {
            'full_name': self.name,
            'template': tpl_name,
            'networks': network_cidrs,
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
        if self.error is not None:
            return Sandbox.STATUS_ERROR
        if len(self.nodes) == 0:
            return Sandbox.STATUS_NO_NODES
        else:
            status = Sandbox.STATUS_DOWN
            
            guest_states = [n.status for n in self.nodes]
            if all(node.Node.STATUS_UP == s for s in guest_states):
                status = Sandbox.STATUS_UP
            elif node.Node.STATUS_ERROR in guest_states:
                node_errors = [n.error for n in self.nodes
                               if n.status == node.Node.STATUS_ERROR]
                self.error = "\n".join(node_errors)
                status = Sandbox.STATUS_ERROR
        return status

    def start(self):
        if self.error is not None:
            msg = ("Cannot start sandbox {0}. Sandbox is in error state.\n"
                   "Current error: {1}").format(self.name, self.error)
            self.LOG.warning(msg)
            return

        #for net in self.networks:
        #    net.start()
        for n in self.nodes:
            n.start()

    def stop(self):
        #for net in self.networks:
        #    net.stop()
        for n in self.nodes:
            n.stop()

    def delete(self):
        self.stop()
        shutil.rmtree(self.sandbox_dir)


class Sandboxes(object):
    """Operations on all sandboxes on the sandbox host."""

    MGMT_SUBNETS = [
        n for n in netaddr.IPNetwork('10.10.0.0/16').subnet(28)
    ]
    PRIVATE_SUBNETS = [
        n for n in netaddr.IPNetwork('10.20.0.0/16').subnet(28)
    ]
    PUBLIC_SUBNETS = [
        n for n in netaddr.IPNetwork('10.30.0.0/16').subnet(28)
    ]

    def __init__(self, parsed_args):
        self.sandboxes_dir = os.path.join(parsed_args.state_dir,
                                          'sandboxes')
        sandboxes = []
        for entry in os.listdir(self.sandboxes_dir):
            sb_entry = os.path.join(self.sandboxes_dir, entry)
            if os.path.isdir(sb_entry):
                sandboxes.append(Sandbox(parsed_args, entry))
        
        self.sandboxes = sandboxes

    def __iter__(self):
        for sb in self.sandboxes:
            yield sb

    def __len__(self):
        return len(self.sandboxes)

    def get_next_available_network_cidrs(self):
        """Returns a dict of CIDR network addresses for various networks, keyed
        by the name of the network. At present, we return a management, private
        and public network.
        """
        # The management network CIDRs are /28 subnets in a 10.10.0.0/16
        # The private network CIDRs are /28 subnets in a 10.20.0.0/16
        # The public network CIDRs are /28 subnets in a 10.30.0.0/16
        if len(self.sandboxes) == 0:
            return {
                'mgmt': '10.10.0.0/28',
                'private': '10.20.0.0/28',
                'public': '10.30.0.0/28',
            }

        # We determine next available CIDR addresses by simply iterating the
        # existing sandboxes, and removing the sandbox's mgmt CIDR from the set
        # of /28 subnets in the mgmt /8 supernet CIDR and the first element in
        # the remaining set of /28 subnets is used.
        sb_cidrs = netaddr.IPSet([sb.networks['mgmt'].ip_net
                                  for sb in self.sandboxes])
        for cidr_idx, subnet in enumerate(Sandboxes.MGMT_SUBNETS):
            if subnet not in sb_cidrs:
                break

        next_mgmt = str(Sandboxes.MGMT_SUBNETS[cidr_idx].cidr)
        next_private = str(Sandboxes.PRIVATE_SUBNETS[cidr_idx].cidr)
        next_public = str(Sandboxes.PUBLIC_SUBNETS[cidr_idx].cidr)
        return {
            'mgmt': next_mgmt,
            'private': next_private,
            'public': next_public,
        }
