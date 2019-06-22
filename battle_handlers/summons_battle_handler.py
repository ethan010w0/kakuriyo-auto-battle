# -*- coding: utf-8 -*-

import csv
import logging
import time

from battle_handlers import config
from battle_handlers import enemy_pop
from battle_handlers import enter_area
from battle_handlers import exchange
from battle_handlers import get_battle
from battle_handlers import get_exchange_info
from battle_handlers import get_move
from battle_handlers import get_player_id
from battle_handlers import get_status
from battle_handlers import go_home
from battle_handlers import move_channel
from battle_handlers import post_action
from battle_handlers import run_battle
from battle_handlers import run_move


logger = logging.getLogger(__name__)

summons_sources = config.get('Summons Battle', 'SummonsSources')
exchange_npc_id = config.getint('Summons Battle', 'ExchangeNpcId')
units_preset = config.getint('Summons Battle', 'UnitsPreset')

player_id = get_player_id()
channel = 1


def _get_challenge_statuses():
    response = get_status('http://s1sky.gs.funmily.com/api/challenges.json')
    challenge_statuses = {}
    for challenge in response.get('response').get('body'):
        challenge_statuses[challenge.get('code')] = challenge.get('status')
    return challenge_statuses


def _do(field_code, enemy_code, enemy_position):
    # move
    move_info = get_move()
    run_move(move_info, player_id, channel, field_code, enemy_position)

    # enemy_pop
    battle_info = enemy_pop(enemy_code)
    if not battle_info:
        # clear bag
        post_action(
            'http://s1sky.gs.funmily.com/api/inventories/put_all_item_to_celler.json')
        return False

        # battle
    battle_client_id = get_battle(battle_info)
    run_battle(battle_info, battle_client_id)

    # finish
    post_action('http://s1sky.gs.funmily.com/api/battles/finish.json')

    return True


def summons_battle():
    # _get_challenge_statuses
    challenge_statuses = _get_challenge_statuses()

    area_battles = {}
    reader = csv.reader(summons_sources.splitlines())
    for (challenge_code, exchange_code,
         area_code, field_code,
         enemy_code, enemy_position_x, enemy_position_y) in reader:
        if challenge_statuses.get(int(challenge_code)) != 1:
            continue

        battles = area_battles.setdefault(area_code, [])
        battles.append((
            field_code,
            enemy_code,
            # enemy_position
            (enemy_position_x, enemy_position_y),
            int(exchange_code)
        ))

    if not area_battles:
        logger.info('no pending battles')
        return

    for area_code, battles in area_battles.items():
        # enter_area
        enter_area(area_code, units_preset)

        # move_channel
        move_channel(channel)

        # challenge first
        for field_code, enemy_code, enemy_position, _ in battles:
            logger.info('challenge battle with {}'.format(enemy_code))

            # _do
            done = _do(field_code, enemy_code, enemy_position)
            if not done:
                logger.info('battle falied')
                continue

        # exchange next
        for field_code, enemy_code, enemy_position, exchange_code in battles:
            if exchange_code == -1:
                continue
            logger.info('exchange battle with {}'.format(enemy_code))

            # get_exchange_info
            exchange_limit, require_count, has_num = get_exchange_info(
                exchange_npc_id, exchange_code)

            while exchange_limit > 0:
                if require_count < has_num:
                    # exchange
                    exchange(exchange_npc_id, exchange_code)
                    # get_exchange_info
                    exchange_limit, require_count, has_num = get_exchange_info(
                        exchange_npc_id, exchange_code)
                    continue

                # _do
                _do(field_code, enemy_code, enemy_position)
                if not done:
                    logger.info('battle falied')
                    break

                # get_exchange_info
                exchange_limit, require_count, has_num = get_exchange_info(
                    exchange_npc_id, exchange_code)

        # go_home
        go_home()
