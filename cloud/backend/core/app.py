from aiohttp import web
import asyncio
import asyncpg
import json
import logging
import socket
from services.socket.senders import send_read_network_settings_command, send_write_network_settings_command

pg_conn = None

logger = logging.getLogger('core')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch_format = logging.Formatter('%(asctime)s : [%(name)s] : [%(levelname)s] : %(message)s')
ch.setFormatter(ch_format)

logger.addHandler(ch)
logger.setLevel(logging.DEBUG)


async def _connect():
    global pg_conn
    pg_conn = await asyncpg.connect(user='root', password='root',
                                    database='core', host='db')


def format_anchors(anchors: list):
    anchors_ = []

    for anchor in anchors:
        anchor_ = {}
        anchor = dict(anchor)
        for k, v in anchor.items():
            if type(v) is str:
                v = v.strip(' ')
            anchor_[k] = v
        anchors_.append(anchor_)

    return anchors_


async def handle_get_anchors(request):
    anchors = await _get_anchors()

    anchors_ = format_anchors(anchors)

    resp = web.Response(text=json.dumps(anchors_))
    resp.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'

    return resp


async def _get_anchors():
    values = await pg_conn.fetch('''SELECT * FROM anchor ORDER BY id ASC;''')
    return values


async def handle_post_read_network_settings_command(request):
    body = await request.json()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    logger.info(f'Sending read_network_settings command to {body.get("ip")} {body.get("port")}')

    try:
        async with pg_conn.transaction():
            await pg_conn.execute(
                f"""update anchor 
                set is_waiting_for_read_network_settings_command_response = true 
                where ip = \'{body.get("ip")}\' and port = \'{body.get('port')}\';""")
    except Exception as e:
        logger.exception(e)

    try:
        send_read_network_settings_command(sock, (body.get('ip'), body.get('port')), body.get('ip'))
    except Exception as e:
        logger.exception(e)

    resp = web.Response(text=json.dumps(format_anchors(await _get_anchors())))

    resp.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    resp.headers['Content-Type'] = 'application/json'

    return resp


async def handle_post_anchor_deletion(request):
    body = await request.json()

    logger.info(f'Deleting anchor: {body.get("ip")} {body.get("port")}')

    try:
        async with pg_conn.transaction():
            await pg_conn.execute(
                f"""delete from anchor 
                where ip = \'{body.get("ip")}\' and port = \'{body.get('port')}\';""")
    except Exception as e:
        logger.exception(e)
    else:
        logger.info(f'Deleting anchor: {body.get("ip")} {body.get("port")} [Success]')

    resp = web.Response(text=json.dumps(format_anchors(await _get_anchors())))

    resp.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    resp.headers['Content-Type'] = 'application/json'

    return resp


async def handle_post_write_network_settings_command(request):
    body = await request.json()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    logger.info(f"""Sending write_network_settings command to {body.get('ip')} {body.get('port')}
    \t\tPayload: {body.get('payload')}""")

    try:
        async with pg_conn.transaction():
            await pg_conn.execute(
                f"""update anchor
                    set is_waiting_for_write_network_settings_command_response = true
                    where ip = \'{body.get("ip")}\' and port = \'{body.get('port')}\';""")
    except Exception as e:
        logger.exception(e)

    try:
        send_write_network_settings_command(sock,
                                            (body.get('ip'), body.get('port')),
                                            body.get('ip'),
                                            body.get('payload').get('ip'),
                                            body.get('payload').get('server ip'),
                                            body.get('payload').get('server port'),
                                            body.get('payload').get('subnet mask')
                                            )
    except Exception as e:
        logger.exception(e)

    resp = web.Response(text=json.dumps(format_anchors(await _get_anchors())))

    resp.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    resp.headers['Content-Type'] = 'application/json'

    return resp


async def handle_options(request):
    resp = web.Response()

    resp.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers['Access-Control-Allow-Methods'] = 'POST'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    resp.headers['Access-Control-Allow-Max-Age'] = '3600'
    return resp


loop = asyncio.get_event_loop()
loop.run_until_complete(_connect())

app = web.Application()
app.add_routes([web.get('/anchors', handle_get_anchors),
                web.post('/anchors/read_network_settings_command', handle_post_read_network_settings_command),
                web.options('/anchors/read_network_settings_command', handle_options),
                web.post('/anchors/anchor_deletion', handle_post_anchor_deletion),
                web.options('/anchors/anchor_deletion', handle_options),
                web.post('/anchors/write_network_settings_command', handle_post_write_network_settings_command),
                web.options('/anchors/write_network_settings_command', handle_options)
                ])

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=8000)