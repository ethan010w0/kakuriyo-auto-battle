# -*- coding: utf-8 -*-

import logging
import sys
import time


from battle_handlers import config
from battle_handlers import enemy_pop
from battle_handlers import enter_area
from battle_handlers import get_battle
from battle_handlers import get_move
from battle_handlers import get_status
from battle_handlers import move_channel
from battle_handlers import post_action
from battle_handlers import run_battle
from battle_handlers import run_move
from battle_handlers import whistle

logger = logging.getLogger(__name__)

area_code = config.get('Sublimation Battle', 'AreaCode')
field_code = config.get('Sublimation Battle', 'FieldCode')
round_enemy_code = config.get('Sublimation Battle', 'RoundEnemyCode')
point_enemy_code = config.get('Sublimation Battle', 'PointEnemyCode')

point_enemy_position = (config.get('Sublimation Battle', 'PointEnemyPositionX'),
                        config.get('Sublimation Battle', 'PointEnemyPositionY'))
round_enemy_position = (config.get('Sublimation Battle', 'RoundEnemyPositionX'),
                        config.get('Sublimation Battle', 'RoundEnemyPositionY'))

channel = 1

exchange_npc_id = 543
exchange_code = 22101

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


def _get_exchange_info():
    payload = {'npc_id': exchange_npc_id}
    response = get_status(
        'http://s1sky.gs.funmily.com/api/item_exchanges/item_exchange_list.json', payload=payload)
    items = response.get('response').get('body').get('items')

    exchange_limit = 0
    require_count = 0
    has_num = 0
    for item in items:
        if item.get('code') == exchange_code:
            exchange_limit = item.get('exchange_limit')
            require_count = item.get('require_count')
            has_num = item.get('has_require_item_num')

    logger.info('exchange_limit {}, require_count {}, has_num {}'.format(
        exchange_limit, require_count, has_num))
    return exchange_limit, require_count, has_num


def sublimation_battle():
    exchange_limit, require_count, has_num = _get_exchange_info()
    if exchange_limit == 0:
        return

    # enter_area
    enter_area(area_code)

    # move_channel
    move_channel(channel)

    while exchange_limit > 0:
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

        if require_count < has_num:
            # exchange
            payload = {
                'code': exchange_code,
                'npc_id': exchange_npc_id,
                'count': 1
            }
            get_status(
                'http://s1sky.gs.funmily.com/api/item_exchanges/exchange_item.json?', payload=payload)

        # _get_exchange_info
        exchange_limit, require_count, has_num = _get_exchange_info()
