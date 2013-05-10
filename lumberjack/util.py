# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
""" Utility functions """
from __future__ import absolute_import

import json
import datetime

from tornado.escape import url_escape, url_unescape

def slug(url):
    """Not at all like django"""

    return url_escape(url)


def deslug(url):
    return url_unescape(url)


def now():
    return datetime.datetime.now()


def _default_serializer(obj):
    if hasattr(obj, '_serialize'):
        return obj._serialize()
    else:
        return TypeError(repr(obj)+" is not serializable")


def serialize(obj):
    return json.dumps(obj, default=_default_serializer)


def deserialize(obj):
    return json.loads(obj)


def import_config_file(f, globs, locs):
    code = compile(f.read(), '<string>', 'exec')
    exec(code, globs, locs)

