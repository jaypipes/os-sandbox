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

from cliff import command
from cliff import lister

from os_sandbox import conf
from os_sandbox import helpers
from os_sandbox import image


class ImageList(lister.Lister):
    """Show a list of templates available on the sandbox host."""

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(ImageList, self).get_parser(prog_name)
        conf.add_common_args(parser)
        return parser

    def take_action(self, parsed_args):
        images = []
        state_dir = helpers.ensure_state_dir(parsed_args)
        images_dir = os.path.join(state_dir, 'images')
        for entry in os.listdir(images_dir):
            img_path = os.path.join(images_dir, entry)
            if os.path.isfile(img_path):
                images.append(image.Image(parsed_args, entry))
        return (
            ('Image', 'Type', 'Virtual Size', 'Disk Size'),
            ((
                img.name,
                img.file_format,
                helpers.human_bytes(img.virtual_size_bytes),
                helpers.human_bytes(img.disk_size_bytes),
              )
             for img in images)
        )
