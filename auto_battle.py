# -*- coding: utf-8 -*-

import getopt
import logging
import sys

from battle_handlers.area_battle_handler import area_battle
from battle_handlers.sublimation_battle_handler import sublimation_battle

logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    try:
        _, args = getopt.getopt(sys.argv[1:], '')
    except getopt.GetoptError as err:
        sys.exit()

    if args[0] == 'area':
        area_battle()
    elif args[0] == 'sublimation':
        sublimation_battle()
