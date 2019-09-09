import io
from contextlib import redirect_stdout

import montagu
import montagu.cli


def test_cli_basic_usage():
    f = io.StringIO()
    with redirect_stdout(f):
        montagu.cli.main(["start"])
    out = f.getvalue()
    assert out.strip() == "Hello montagu world"
