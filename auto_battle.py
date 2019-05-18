# -*- coding: utf-8 -*-

import argparse
import logging
import sys

from battle_handlers import set_client_id
from battle_handlers.area_battle_handler import area_battle
from battle_handlers.extreme_battle_handler import extreme_battle
from battle_handlers.sublimation_battle_handler import sublimation_battle
from battle_handlers.summons_battle_handler import summons_battle


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='An auto battle script for game kakuriyo-no-mon.')
    parser.add_argument('command',
                        choices=['area', 'extreme', 'sublimation', 'summons'],
                        help='battle type: { area, extreme, sublimation, summons }',
                        metavar='command')
    parser.add_argument('-s', '--set-client-id',
                        action='store_true',
                        help='set a new client id')
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='increase output verbosity')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.set_client_id:
        set_client_id()

    if args.command == 'area':
        area_battle()
    elif args.command == 'extreme':
        extreme_battle()
    elif args.command == 'sublimation':
        sublimation_battle()
    elif args.command == 'summons':
        summons_battle()
