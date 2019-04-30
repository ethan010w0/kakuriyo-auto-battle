# -*- coding: utf-8 -*-

import sys

from battle_handlers import config
from battle_handlers import enemy_pop
from battle_handlers import enter_area
from battle_handlers import exchange
from battle_handlers import get_battle
from battle_handlers import get_exchange_info
from battle_handlers import get_move
from battle_handlers import get_status
from battle_handlers import move_channel
from battle_handlers import post_action
from battle_handlers import run_battle
from battle_handlers import run_move
from battle_handlers import whistle


exchange_npc_id = config.getint('Sublimation Battle', 'ExchangeNpcId')
exchange_code = config.getint('Sublimation Battle', 'ExchangeCode')
area_code = config.getint('Sublimation Battle', 'AreaCode')
field_code = config.getint('Sublimation Battle', 'FieldCode')
round_enemy_code = config.getint('Sublimation Battle', 'RoundEnemyCode')
point_enemy_code = config.getint('Sublimation Battle', 'PointEnemyCode')

point_enemy_position = (config.getint('Sublimation Battle', 'PointEnemyPositionX'),
                        config.getint('Sublimation Battle', 'PointEnemyPositionY'))
round_enemy_position = (config.getint('Sublimation Battle', 'RoundEnemyPositionX'),
                        config.getint('Sublimation Battle', 'RoundEnemyPositionY'))

channel = 1
# 點的印章
point_seal_id = 1913344
# 圓的印章
round_seal_id = 1913340


def _get_seal_num():
    response = get_status(
        'http://s1sky.gs.funmily.com/api/inventories/load_minimum_info.json')
    important_items = response.get('response').get(
        'body').get('important_items')

    point_seal_num = 0
    round_seal_num = 0
    for important_item in important_items:
        if important_item.get('id') == point_seal_id:
            point_seal_num = important_item.get('num')
        elif important_item.get('id') == round_seal_id:
            round_seal_num = important_item.get('num')

    return point_seal_num, round_seal_num


def sublimation_battle():
    # get_exchange_info
    exchange_limit, require_count, has_num = get_exchange_info(
        exchange_npc_id, exchange_code)
    if exchange_limit == 0:
        return

    # enter_area
    enter_area(area_code)

    # move_channel
    move_channel(channel)

    while exchange_limit > 0:
        if require_count < has_num:
            # exchange
            exchange(exchange_npc_id, exchange_code)
            # get_exchange_info
            exchange_limit, require_count, has_num = get_exchange_info(
                exchange_npc_id, exchange_code)
            continue

        # _get_item_num
        point_seal_num, round_seal_num = _get_seal_num()

        if round_seal_num or point_seal_num:
            point_map = (
                point_seal_num, point_enemy_code, point_enemy_position)
            round_map = (
                round_seal_num, round_enemy_code, round_enemy_position)
            for seal_num, enemy_code, enemy_position in (point_map, round_map):
                if not seal_num:
                    continue

                # move
                move_info = get_move()
                run_move(move_info, channel, field_code, enemy_position)

                # enemy_pop
                battle_info = enemy_pop(enemy_code)
                if not battle_info:
                    enter_area(area_code)
                    move_channel(channel)
                    continue

                # battle
                battle_client_id = get_battle(battle_info)
                run_battle(battle_info, battle_client_id)

                # finish
                post_action(
                    'http://s1sky.gs.funmily.com/api/battles/finish.json')
        else:
            # whistle
            battle_info = whistle()
            if not battle_info:
                enter_area(area_code)
                move_channel(channel)
                continue

            # battle
            battle_client_id = get_battle(battle_info)
            run_battle(battle_info, battle_client_id)

            # finish
            post_action('http://s1sky.gs.funmily.com/api/battles/finish.json')

        # get_exchange_info
        exchange_limit, require_count, has_num = get_exchange_info(
            exchange_npc_id, exchange_code)
