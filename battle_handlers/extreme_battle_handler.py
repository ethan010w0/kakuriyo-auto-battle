# -*- coding: utf-8 -*-

import time

from battle_handlers import config
from battle_handlers import enemy_pop
from battle_handlers import enter_area
from battle_handlers import exchange
from battle_handlers import get_battle
from battle_handlers import get_exchange_info
from battle_handlers import get_move
from battle_handlers import get_player_id
from battle_handlers import move_channel
from battle_handlers import post_action
from battle_handlers import run_battle
from battle_handlers import run_move


area_code = config.getint('Extreme Battle', 'AreaCode')
field_code = config.getint('Extreme Battle', 'FieldCode')
enemy_code = config.getint('Extreme Battle', 'EnemyCode')
enemy_position = (config.getint('Extreme Battle', 'EnemyPositionX'),
                  config.getint('Extreme Battle', 'EnemyPositionY'))
trump_id = config.getint('Extreme Battle', 'TrumpId')
key_exchange_npc_id = config.getint('Extreme Battle', 'KeyExchangeNpcId')
key_exchange_code = config.getint('Extreme Battle', 'KeyExchangeCode')
exp_exchange_npc_id = config.getint('Extreme Battle', 'ExpExchangeNpcId')
exp_exchange_code = config.getint('Extreme Battle', 'ExpExchangeCode')

player_id = get_player_id()
channel = 1


def extreme_battle():
    # enter_area
    enter_area(area_code)

    # move_channel
    move_channel(channel)

    while True:
        key_exchange_info = (key_exchange_npc_id, key_exchange_code)
        exp_exchange_info = (exp_exchange_npc_id, exp_exchange_code)
        for exchange_npc_id, exchange_code in (key_exchange_info, exp_exchange_info):
            # get_exchange_info
            exchange_limit, require_count, has_num = get_exchange_info(
                exchange_npc_id, exchange_code)

            while exchange_limit != 0 and require_count < has_num:
                # exchange
                exchange(exchange_npc_id, exchange_code)
                # get_exchange_info
                exchange_limit, require_count, has_num = get_exchange_info(
                    exchange_npc_id, exchange_code)

        # move
        move_info = get_move()
        run_move(move_info, player_id, channel, field_code, enemy_position)

        # enemy_pop
        battle_info = enemy_pop(enemy_code)
        if not battle_info:
            # enter_area
            enter_area(area_code)
            # move_channel
            move_channel(channel)
            continue

        # battle
        battle_client_id = get_battle(battle_info)
        run_battle(battle_info, battle_client_id, trump_id)

        # finish
        post_action('http://s1sky.gs.funmily.com/api/battles/finish.json')
