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
import yaml

import slugify

from os_sandbox import helpers


class Template(object):

    def __init__(self, parsed_args, name):
        self.name = name
        self.slug = slugify.slugify(helpers.utf8_bytes(name))
        self.template_dir = os.path.join(parsed_args.state_dir,
                                         'templates',
                                         self.slug)
        self.conf_path = os.path.join(self.template_dir, 'config.yaml')

        if os.path.exists(self.conf_path):
            self._fill()

    def _fill(self):
        self.conf = yaml.load(open(self.conf_path, 'rb').read())
        self.full_name = self.conf['full_name']
        self.description = self.conf['description']
        self.networks = self.conf['networks']
        self.nodes = self.conf['nodes']

    def exists(self):
        """Returns True if the named template exists, False otherwise."""
        return os.path.exists(self.conf_path)

    def create(self, full_name=None, description=None, networks=None,
               nodes=None):
        """Creates a new template."""
        if self.exists():
            msg = "A template with name {0} already exists.".format(self.name)
            raise RuntimeError(msg)

        full_name = full_name or self.name
        nodes = nodes or []
        description = description or self.name
        networks = networks or {}
        conf = {
            'full_name': full_name,
            'description': description,
            'networks': networks,
            'nodes': nodes,
        }
        os.mkdir(self.template_dir, 0755)
        with open(self.conf_path, 'wb') as conf_file:
            conf_file.write(yaml.dump(conf, default_flow_style=False))
        self._fill()
