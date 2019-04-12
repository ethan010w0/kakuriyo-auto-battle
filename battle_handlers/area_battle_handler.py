# -*- coding: utf-8 -*-

import time

from battle_handlers import config
from battle_handlers import enter_area
from battle_handlers import get_battle
from battle_handlers import go_home
from battle_handlers import is_at_town
from battle_handlers import post_action
from battle_handlers import run_battle
from battle_handlers import whistle


area_code = config.get('Area Battle', 'AreaCode')
area_duration = config.getfloat('Area Battle', 'AreaDuration')
round_times = config.get('Area Battle', 'RoundTimes')


def area_battle():
    round_time = 0
    while round_time < round_times:
        round_time += 1

        # enter_area
        enter_area(area_code)

        timeout = time.time() + area_duration
        while time.time() < timeout:
            # whistle
            battle_info = whistle()
            if not battle_info:
                at_home, _ = is_at_town()
                if at_home:
                    # clear bag
                    post_action(
                        'http://s1sky.gs.funmily.com/api/inventories/put_all_item_to_celler.json')
                    time.sleep(10)
                    enter_area(area_code)
                continue

            # battle
            battle_client_id = get_battle(battle_info)
            run_battle(battle_info, battle_client_id)

            # finish
            post_action('http://s1sky.gs.funmily.com/api/battles/finish.json')

        # go_home
        go_home()
