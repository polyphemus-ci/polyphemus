#!/usr/bin/env python
from __future__ import print_function

import configure

p_logos = ["""                                         
""",
]


def main_body():
    print(p_logos[0])
    configure.setup()


def main():
    success = False
    try:
        main_body()
        success = True
    finally:
        configure.final_message(success)

if __name__ == "__main__":
    main()
