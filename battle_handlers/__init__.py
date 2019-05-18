# -*- coding: utf-8 -*-

import configparser
import json
import logging
import random
import re
import requests
import time
import websocket

from websocket import create_connection

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('auto_battle.ini', encoding='utf_8')

client_id = config.get('Certification', 'ClientId')

headers = {
    'accept': '*/*',
    'accept-encoding': 'gzip, deflate',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'connection': 'keep-alive',
    'host': 's1sky.gs.funmily.com',
    'origin': 'http://a0sky.gs.funmily.com',
    'pragma': 'no-cache',
    'referer': 'http://a0sky.gs.funmily.com/swf/kagura_main.swf?v=20190320062003',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36',
    'x-requested-with': 'ShockwaveFlash/32.0.0.156'
}

cookies = {
    '_kakuriyo_session': config.get('Certification', 'Session')
}

cert_payload = {
    'authenticity_token': config.get('Certification', 'AuthenticityToken'),
    'client_id': client_id
}


def get_status(url, payload=None):
    request = requests.get(url, headers=headers,
                           cookies=cookies, params=payload)
    match = re.search(r'/(?P<status>[^/]*?).json', url)
    logger.info('{} {}'.format(match.group('status'), request.status_code))
    logger.debug(request.text)
    return request.json()


def post_action(url, payload=None):
    if payload:
        payload.update(cert_payload)
    else:
        payload = cert_payload

    request = requests.post(url, headers=headers,
                            cookies=cookies, json=payload)
    match = re.search(r'/(?P<action>[^/]*?).json', url)
    logger.info('{} {}'.format(match.group('action'), request.status_code))
    logger.debug(request.text)
    return request.json()


def set_client_id():
    response = post_action('http://s1sky.gs.funmily.com/api/games/init.json')
    client_id = response.get('response').get('body').get('client_id')
    cert_payload['client_id'] = client_id
    time.sleep(10)


def get_player_id():
    response = get_status('http://s1sky.gs.funmily.com/api/players.json')
    return response.get('response').get('body').get('id')


def is_at_town():
    response = get_status('http://s1sky.gs.funmily.com/api/players.json')
    body = response.get('response').get('body')
    at_home = body.get('at_home')
    at_town = body.get('at_town')
    logger.info('at_home {}, at_town {}'.format(at_home, at_town))
    return at_home, at_town


def enter_area(area_code, units_preset=None):
    at_home, at_town = is_at_town()
    if not at_town:
        return
    if at_home:
        # clear bag
        post_action(
            'http://s1sky.gs.funmily.com/api/inventories/put_all_item_to_celler.json')

    payload = {'area_code': area_code}
    if units_preset and units_preset > 0:
        payload['preset_num'] = units_preset
    post_action(
        'http://s1sky.gs.funmily.com/api/fields/enter_area.json', payload)
    time.sleep(10)


def go_home():
    post_action('http://s1sky.gs.funmily.com/api/fields/go_home.json')
    time.sleep(10)

    # clear bag
    post_action(
        'http://s1sky.gs.funmily.com/api/inventories/put_all_item_to_celler.json')


def move_channel(channel):
    payload = {'channel': 1}
    post_action(
        'http://s1sky.gs.funmily.com/api/fields/move_channel.json', payload)
    time.sleep(10)


def get_move():
    port = 9500 + random.randint(1, 29)
    url = 'http://f1-2sky.gs.funmily.com:{}/battle'.format(port)
    params = {
        'message': '[{"channel":"/meta/handshake","version":"1.0","supportedConnectionTypes":["websocket","eventsource","long-polling","cross-origin-long-polling","callback-polling"],"id":"1"}]',
        'jsonp': '__jsonp1__'
    }
    request = requests.get(url, params=params)
    logger.info('{} {}'.format('get_move', request.status_code))
    logger.debug(request.text)

    match = re.search('"clientId":"(?P<client_id>.*?)"', request.text)
    return {
        'move_host': url,
        'move_client_id': match.group('client_id')
    }


def run_move(move_info, player_id, channel, field_code, position):
    move_client_id = move_info.get('move_client_id')
    x, y = position
    move_host = move_info.get('move_host').replace('http', 'ws')
    ws = create_connection(move_host)

    logger.info('make_move {}, {}'.format(x, y))
    ws.send('{{"channel":"/meta/connect","clientId":"{}","connectionType":"websocket","id":"2"}}'.format(move_client_id))
    ws.send('{{"channel":"/field/{}-{}/command","data":{{"command_type":"move","cid":"{}","pid":{},"info":{{"d8":{},"md":{},"cp":{{"x":{},"y":{}}}}}}},"clientId":"{}","id":"3"}}'.format(
        field_code, channel, client_id, player_id, x, y, x, y, move_client_id))
    result = ws.recv()
    logger.debug(result)
    ws.close()


def get_exchange_info(exchange_npc_id, exchange_code):
    payload = {'npc_id': exchange_npc_id}
    response = get_status(
        'http://s1sky.gs.funmily.com/api/item_exchanges/item_exchange_list.json', payload=payload)
    body = response.get('response').get('body')
    meta = body.get('meta')
    if meta.get('npc_exchange_limit') == meta.get('npc_exchange_count'):
        logger.info('npc_exchange_limit reached')
        return 0, None, None

    exchange_limit = None
    require_count = None
    has_num = None
    for item in body.get('items'):
        if item.get('code') == exchange_code:
            exchange_limit = item.get('exchange_limit')
            require_count = item.get('require_count')
            has_num = item.get('has_require_item_num')

    logger.info('exchange_limit {}, require_count {}, has_num {}'.format(
        exchange_limit, require_count, has_num))
    return exchange_limit, require_count, has_num


def exchange(exchange_npc_id, exchange_code, count=1):
    payload = {
        'code': exchange_code,
        'npc_id': exchange_npc_id,
        'count': count
    }
    get_status(
        'http://s1sky.gs.funmily.com/api/item_exchanges/exchange_item.json?', payload=payload)


def whistle():
    response = post_action(
        'http://s1sky.gs.funmily.com/api/items/whistle.json')

    head = response.get('response').get('head')
    if head.get('status') == 1 and head.get('message') == u'不在郊外':
        return
    if head.get('status') == 99:
        # fix repeat whistle
        post_action(
            'http://s1sky.gs.funmily.com/api/battles/finish.json')
        return
    body = response.get('response').get('body')
    # whistle named enemy
    if body.get('named'):
        logger.info('wait for named enemy')
        time.sleep(60)
        return whistle()

    info = body.get('info')
    battle = info.get('battle')
    player_info = info.get('player_info')

    return {
        'battle_id': str(battle.get('id')),
        'battle_host':  battle.get('battle_host'),
        'player_id':  player_info.get('player_id'),
        'player_character':  player_info.get('player').get('player_battle_ch')
    }


def enemy_pop(enemy_code):
    payload = {'code': enemy_code, 'matching_id': 0}
    response = post_action(
        'http://s1sky.gs.funmily.com/api/battles/enemy_pop.json', payload)

    head = response.get('response').get('head')
    if head.get('status') == 1:
        return
    if head.get('status') == 99:
        # fix repeat enemy_pop
        post_action(
            'http://s1sky.gs.funmily.com/api/battles/finish.json')
        return

    body = response.get('response').get('body')
    battle = body.get('battle')
    player_info = body.get('player_info')

    return {
        'battle_id':  str(battle.get('id')),
        'battle_host': battle.get('battle_host'),
        'player_id': player_info.get('player_id'),
        'player_character': player_info.get('player').get('player_battle_ch')
    }


def get_battle(battle_info):
    params = {
        'message': '[{"channel":"/meta/handshake","version":"1.0","supportedConnectionTypes":["websocket","eventsource","long-polling","cross-origin-long-polling","callback-polling"],"id":"1"}]',
        'jsonp': '__jsonp6__'
    }
    request = requests.get(battle_info.get('battle_host'), params=params)
    logger.info('{} {}'.format('get_battle', request.status_code))
    logger.debug(request.text)

    match = re.search('"clientId":"(?P<client_id>.*?)"', request.text)
    return match.group('client_id')


def run_battle(battle_info, battle_client_id):
    battle_id = battle_info.get('battle_id')
    player_id = battle_info.get('player_id')
    player_character = battle_info.get('player_character')
    ws_battle_host = battle_info.get('battle_host').replace('http', 'ws')
    subscribe = {}

    def on_message(ws, message):
        logger.debug(message)

        content = json.loads(message)[0]
        channel = content.get('channel')

        if channel == '/meta/subscribe':
            subscribe[content.get('id')] = content.get('successful')
            if subscribe.get('3') and subscribe.get('4'):
                publish_timer = str(int(time.time()))[-1:-8:-1][::-1]
                ws.send('{{"channel":"/battle/{}/command","data":{{"publish_timer":{},"command_type":"sync_all","client_id":"{}","player_id":{}}},"clientId":"{}","id":"5"}}'.format(
                    battle_id, publish_timer, client_id, player_id, battle_client_id))
                ws.send('{{"channel":"/battle/{}/command","data":{{"publish_timer":{},"command_type":"start","client_id":"{}","player_id":{}}},"clientId":"{}","id":"6"}}'.format(
                    battle_id, publish_timer, client_id, player_id, battle_client_id))
                ws.send('{{"channel":"/battle/{}/command","data":{{"command_type":"player_ids","client_id":"{}}}","player_id":{}}},"clientId":"{}","id":"7"}}'.format(
                    battle_id, client_id, player_id, battle_client_id))
        elif channel == player_character and content.get('data').get('info_type') == 'battle_finished':
            ws.send('{{"channel":"/meta/disconnect","clientId":"{}","id":"8"}}'.format(
                battle_client_id))
            ws.send('{{"channel":"/meta/unsubscribe","clientId":"{}","subscription":"/battle/{}/info","id":"9"}}'.format(
                battle_client_id, battle_id))

    def on_error(ws, error):
        logger.error(error)

    def on_close(ws):
        logger.info('close_battle')

    def on_open(ws):
        logger.info('make_battle')
        ws.send('')
        ws.send(
            '{{"channel":"/meta/connect","clientId":"{}","connectionType":"websocket","id":"2"}}'.format(battle_client_id))
        ws.send('{{"channel":"/meta/subscribe","clientId":"{}","subscription":"{}","id":"3"}}'.format(
            battle_client_id, player_character))
        ws.send('{{"channel":"/meta/subscribe","clientId":"{}","subscription":"/battle/{}/info","id":"4"}}'.format(
            battle_client_id, battle_id))

    ws = websocket.WebSocketApp(ws_battle_host,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()
