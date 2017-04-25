__version__ = '0.0.1'

import os.path as op
from . import unwarping
from . import uniformization
from . import retroicor
from . import masking
from . import ica_fix
from . import glm
from . import filtering
from . import registration

root_dir = op.dirname(op.abspath(__file__))
test_data_path = op.join(root_dir, 'data', 'test_data')

__all__ = ['unwarping', 'uniformization', 'registration',
           'retroicor', 'masking', 'ica_fix', 'glm',
           'filtering', 'test_data_path', 'root_dir']