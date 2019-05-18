# -*- coding: utf-8 -*-

import csv
import logging
import time

from battle_handlers import config
from battle_handlers import get_status
from battle_handlers import post_action


logger = logging.getLogger(__name__)

exhibit_sources = config.get('Trade Battle', 'ExhibitSources')
exhibit_player_id = config.get('Trade Battle', 'ExhibitPlayerId')

exhibit_price = 1
exhibit_num = 50


def _exhibit_item(exhibit_code):
    payload = {
        'item_code': exhibit_code,
        'num': exhibit_num,
        'in_bag': False,
        'price': exhibit_price
    }
    return post_action('http://s1sky.gs.funmily.com/api/trades/exhibit_item.json', payload)


def _exhibit_equip(exhibit_id, exhibit_type):
    payload = {
        'id': exhibit_id,
        'type': exhibit_type,
        'in_bag': False,
        'price': exhibit_price
    }
    return post_action('http://s1sky.gs.funmily.com/api/trades/exhibit_equip.json', payload)


def _buy(trade_id):
    payload = {
        'trade_id': trade_id,
        'price': exhibit_price
    }
    post_action('http://s1sky.gs.funmily.com/api/trades/buy.json', payload)


def exhibit_battle():
    category_exhibit_codes = {}
    reader = csv.reader(exhibit_sources.splitlines())
    for (category, exhibit_code) in reader:
        exhibit_codes = category_exhibit_codes.setdefault(category, [])
        exhibit_codes.append(int(exhibit_code))

    # get items
    response = get_status(
        'http://s1sky.gs.funmily.com/api/inventories/load_minimum_info.json')
    cellar = response.get('response').get('body').get('cellar')

    exhibit_items = []
    for category, exhibit_codes in category_exhibit_codes.items():
        items = cellar.get(category)
        for item in items:
            item_code = item.get('code')
            if item_code not in exhibit_codes:
                continue

            item_num = item.get('num')
            if item_num:
                batches = item.get('num')/exhibit_num
                for _ in range(batches):
                    exhibit_item = (True, (item_code,))
                    exhibit_items.append(exhibit_item)
            else:
                exhibit_item = (False, (item.get('id'), item.get('type')))
                exhibit_items.append(exhibit_item)

    index = 0
    while index < len(exhibit_items):
        item_has_num, item_info = exhibit_items[index]
        if item_has_num:
            exhibit_code, = item_info
            # _exhibit_item
            response = _exhibit_item(exhibit_code)
        else:
            exhibit_id, exhibit_type = item_info
            # _exhibit_equip
            response = _exhibit_equip(exhibit_id, exhibit_type)

        if response.get('response').get('head').get('status') == 1:
            logger.info('exhibit limit reached')
            time.sleep(10)
            continue

        index += 1


def buy_battle():
    while True:
        # get trades
        payload = {'id': exhibit_player_id}
        response = get_status(
            'http://s1sky.gs.funmily.com/api/trades.json?id=29438', payload)

        trades = response.get('response').get('body')
        if not trades:
            logger.info('no trades')
            time.sleep(10)
            continue

        for trade in trades:
            # buys
            _buy(trade.get('id'))
