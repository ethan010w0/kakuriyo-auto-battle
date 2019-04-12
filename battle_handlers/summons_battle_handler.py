# -*- coding: utf-8 -*-

import csv

from battle_handlers import config
from battle_handlers import enemy_pop
from battle_handlers import enter_area
from battle_handlers import get_battle
from battle_handlers import get_exchange_info
from battle_handlers import get_move
from battle_handlers import get_status
from battle_handlers import go_home
from battle_handlers import move_channel
from battle_handlers import post_action
from battle_handlers import run_battle
from battle_handlers import run_move


summons_sources = config.get('Summons Battle', 'SummonsSources')

channel = 1
exchange_npc_id = 35


def _get_challenge_statuses():
    response = get_status('http://s1sky.gs.funmily.com/api/challenges.json')
    challenge_statuses = {}
    for challenge in response.get('response').get('body'):
        challenge_statuses[challenge.get('code')] = challenge.get('status')
    return challenge_statuses


def _do(field_code, enemy_code, enemy_position):
    # move
    move_info = get_move()
    run_move(move_info, channel, field_code, enemy_position)

    # enemy_pop
    battle_info = enemy_pop(enemy_code)

    # battle
    battle_client_id = get_battle(battle_info)
    run_battle(battle_info, battle_client_id)

    # finish
    post_action('http://s1sky.gs.funmily.com/api/battles/finish.json')


def summons_battle():
    # _get_challenge_statuses
    challenge_statuses = _get_challenge_statuses()

    area_battles = {}
    reader = csv.reader(summons_sources.splitlines())
    for challenge_code, exchange_code, area_code, field_code, enemy_code, enemy_position_x, enemy_position_y in reader:
        if challenge_statuses.get(int(challenge_code)) != 1:
            continue

        battles = area_battles.setdefault(area_code, [])
        battles.append({
            'field_code': int(field_code),
            'enemy_code': int(enemy_code),
            'enemy_position': (int(enemy_position_x), int(enemy_position_y)),
            'exchange_code': int(exchange_code)
        })

    for area_code, battles in area_battles:
        # enter_area
        enter_area(area_code)

        # move_channel
        move_channel(channel)

        # challenge first
        for field_code, enemy_code, enemy_position, _ in battles:
            # _do
            _do(field_code, enemy_code, enemy_position)

        # exchange next
        for field_code, enemy_code, enemy_position, exchange_code in battles:
            exchange_limit, require_count, has_num = get_exchange_info(
                exchange_npc_id, exchange_code)

            while exchange_limit > 0:
                # _do
                _do(field_code, enemy_code, enemy_position)

                if require_count < has_num:
                    # exchange
                    payload = {
                        'code': exchange_code,
                        'npc_id': exchange_npc_id,
                        'count': 1
                    }
                    get_status(
                        'http://s1sky.gs.funmily.com/api/item_exchanges/exchange_item.json?', payload=payload)

                exchange_limit, require_count, has_num = get_exchange_info(
                    exchange_npc_id, exchange_code)

        # go_home
        go_home()
