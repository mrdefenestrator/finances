#!/usr/bin/env python3
"""
CLI entrypoint for finances tracker.

Usage:
  python finances.py <data_file> status
  python finances.py <data_file> accounts [ -i TYPE ] [ -x TYPE ]
  python finances.py <data_file> budget [ --kind income|expense ] [ -i TYPE ] [ -x TYPE ] ...
  python finances.py <data_file> assets [ --kind asset|debt ]
  python finances.py <data_file> budget [ --annual ] [ --kind ... ] [ -i TYPE ] [ -x TYPE ] ...

Shared logic (loader, calculations, filters, formatting, tables) lives in the
finances package (finances/). This script delegates to finances.cli.main().
"""

import sys

if __name__ == "__main__":
    from finances.cli import main

    sys.exit(main())
