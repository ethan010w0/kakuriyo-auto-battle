# -*- coding: utf-8 -*-

import configparser
import json
import logging
import re
import requests
import time
import websocket

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

config = configparser.ConfigParser()
config.read('auto_battle.ini')

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

data = {
    'authenticity_token': config.get('Certification', 'AuthenticityToken'),
    'client_id': config.get('Certification', 'ClientId')
}

area_code = config.get('Auto Battle', 'AreaCode')
area_duration = config.getfloat('Auto Battle', 'AreaDuration')
round_times = config.get('Auto Battle', 'RoundTimes')


def get_status(url):
    request = requests.get(url, headers=headers, cookies=cookies)
    match = re.search(r'/(?P<status>[^/]*?).json', url)
    logger.info('{} {}'.format(match.group('status'), request.status_code))
    logger.debug(request.text)
    return request.json()


def post_action(url, data):
    request = requests.post(url, headers=headers,
                            cookies=cookies, data=data)
    match = re.search(r'/(?P<action>[^/]*?).json', url)
    logger.info('{} {}'.format(match.group('action'), request.status_code))
    logger.debug(request.text)
    return request.json()


def enter_area():
    response = get_status('http://s1sky.gs.funmily.com/api/players.json')
    at_town = response.get('response').get('body').get('at_town')
    if not at_town:
        logger.info('at_town {}'.format(at_town))
        return

    enter_area_data = {'area_code': area_code}
    enter_area_data.update(data)
    post_action(
        'http://s1sky.gs.funmily.com/api/fields/enter_area.json', enter_area_data)
    time.sleep(10)


def whistle():
    response = post_action(
        'http://s1sky.gs.funmily.com/api/items/whistle.json', data)

    head = response.get('response').get('head')
    if head.get('status') == 1:
        if head.get('message') == u'不在郊外':
            enter_area()
            return whistle()
        else:
            # fix repeat whistle
            post_action(
                'http://s1sky.gs.funmily.com/api/battles/finish.json', data)
        return
    body = response.get('response').get('body')
    # whistle named enemy
    if body.get('named'):
        time.sleep(60)
        return whistle()

    info = body.get('info')
    battle = info.get('battle')
    battle_id = str(battle.get('id'))
    battle_host = battle.get('battle_host')
    player_info = info.get('player_info')
    player_id = player_info.get('player_id')
    player_character = player_info.get('player').get('player_battle_ch')

    return {
        'battle_id': battle_id,
        'battle_host': battle_host,
        'player_id': player_id,
        'player_character': player_character
    }


def get_battle(whistle_info):
    params = {
        'message': '[{"channel":"/meta/handshake","version":"1.0","supportedConnectionTypes":["websocket","eventsource","long-polling","cross-origin-long-polling","callback-polling"],"id":"1"}]',
        'jsonp': '__jsonp6__'
    }
    request = requests.get(whistle_info.get('battle_host'), params=params)
    logger.info('{} {}'.format('get_battle', request.status_code))
    logger.debug(request.text)

    match = re.search('"clientId":"(?P<client_id>.*?)"', request.text)
    return match.group('client_id')


def run_battle(whistle_info, battle_client_id):
    client_id = data.get('client_id')
    battle_id = whistle_info.get('battle_id')
    player_id = whistle_info.get('player_id')
    player_character = whistle_info.get('player_character')
    ws_battle_host = whistle_info.get('battle_host').replace('http', 'ws')
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

    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(ws_battle_host,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()


if __name__ == "__main__":
    round_time = 0
    while round_time < round_times:
        round_time += 1

        # enter_area
        enter_area()

        timeout = time.time() + area_duration
        while time.time() < timeout:
            # whistle
            whistle_info = whistle()
            if not whistle_info:
                continue

            # battel
            battle_client_id = get_battle(whistle_info)
            run_battle(whistle_info, battle_client_id)

            # finish
            post_action(
                'http://s1sky.gs.funmily.com/api/battles/finish.json', data)

        # go_town
        post_action('http://s1sky.gs.funmily.com/api/fields/go_town.json', data)
        time.sleep(10)
