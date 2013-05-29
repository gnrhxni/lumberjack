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
from setuptools import setup, find_packages

setup(
    name='lumberjack',
    version='0.3.0',
    description='Real time file streaming over HTTP',
    packages=find_packages(exclude=['ez_setup', 'tests', 'tests.*']),
    zip_safe=False,
    install_requires=[
        'tornado>=3.0'
    ],
    classifiers=[
        "Development Status :: 3 - Alpha"
    ],
    entry_points= {
        'console_scripts': [
            'lumberjack = lumberjack:main',
            'sluice = lumberjack.sluice:main',
        ],
    }
)
