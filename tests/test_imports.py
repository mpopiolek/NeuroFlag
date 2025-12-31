import numpy as np
import scipy
import pandas as pd
import mne
import sklearn


def test_imports_and_basic_behavior():
    # Versions exist
    assert isinstance(np.__version__, str) and np.__version__
    assert isinstance(scipy.__version__, str) and scipy.__version__
    assert isinstance(pd.__version__, str) and pd.__version__
    assert isinstance(mne.__version__, str) and mne.__version__
    assert isinstance(sklearn.__version__, str) and sklearn.__version__

    # Basic functionality checks
    a = np.array([1, 2, 3])
    assert a.sum() == 6
    df = pd.DataFrame({"x": [1, 2]})
    assert df.x.sum() == 3
