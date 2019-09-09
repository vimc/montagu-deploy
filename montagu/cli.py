"""Usage:
  montagu start
"""

import docopt

import montagu


def main(argv=None):
    target, args = parse_args(argv)
    target(*args)


def parse_args(argv):
    args = docopt.docopt(__doc__, argv)
    if args["start"]:
        args = ()
        target = montagu.start
    return target, args
