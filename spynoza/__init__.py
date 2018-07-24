__version__ = '0.0.1b'

import os.path as op

from . import denoising
from . import conversion
from . import filtering
from . import glm
from . import ica_fix
from . import masking
from . import registration
from . import uniformization
from . import unwarping

root_dir = op.dirname(op.abspath(__file__))
test_data_path = op.join(root_dir, 'data', 'test_data')

__all__ = ['unwarping', 'uniformization', 'registration',
           'retroicor', 'masking', 'ica_fix', 'glm', 'conversion'
           'filtering', 'test_data_path', 'root_dir']