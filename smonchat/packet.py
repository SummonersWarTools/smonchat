import struct
from base64 import b64decode
import json

from . import codes
from swgateway.crypto import SWCryptoMgr

async def LoginV2Req(conn):
    request_buffer =  struct.pack(">H", codes.LOGIN_V2_REQ)
    request_buffer += struct.pack(">L", 1)
    request_buffer += struct.pack(">Q", conn.WIZARD.HIVE_USER.HIVE_UID)
    request_buffer += struct.pack(">L", conn.CHAT_GAME_SERVER_ID)
    request_buffer += struct.pack(">L", conn.CHAT_LOGIN_KEY)
    request_buffer += struct.pack(">Q", 0)
    request_buffer += struct.pack(">L", 0)

    buffer_len = len(request_buffer) + 2
    request_buffer = struct.pack(">H", buffer_len) + request_buffer

    await conn.send(request_buffer)

def LoginV2Res(packet):
    return {
        "type": codes.LOGIN_V2_RES,
        "raw": packet,
        "login_id": int.from_bytes(packet[6:10], byteorder='big'),
        "channel": int.from_bytes(packet[10:14], byteorder='big'),
    }

async def GroupChangeReq(conn, channel):
    await conn.wait_for_login()

    request_buffer =  struct.pack(">H", codes.GROUP_CHANGE_REQ)
    request_buffer += struct.pack(">Q", conn.WIZARD.HIVE_USER.HIVE_UID)
    request_buffer += struct.pack(">L", 0)
    request_buffer += struct.pack(">L", conn.CHAT_LOGIN_ID)
    request_buffer += struct.pack(">L", channel)

    buffer_len = len(request_buffer) + 2
    request_buffer = struct.pack(">H", buffer_len) + request_buffer

    await conn.send(request_buffer)

def GroupChangeRes(packet):
    return {
        "type": codes.GROUP_CHANGE_RES,
        "raw": packet,
        "channel": int.from_bytes(packet[6:10], byteorder='big'),
    }

async def PingReq(conn):
    request_buffer =  struct.pack(">H", codes.PING_REQ)
    request_buffer += struct.pack(">Q", conn.WIZARD.HIVE_USER.HIVE_UID)
    request_buffer += struct.pack(">L", 0)
    request_buffer += struct.pack(">L", conn.CHAT_LOGIN_ID)
    request_buffer += struct.pack(">L", 1)

    buffer_len = len(request_buffer) + 2
    request_buffer = struct.pack(">H", buffer_len) + request_buffer

    await conn.send(request_buffer)

def PingRes(packet):
    return {
        "type": codes.PING_RES,
        "raw": packet,
    }

async def UserChatReq(conn, message, nickname):
    data_json = {
        "chat_version": 10001,
        "chat_type": 3,
        "chat_wizard_name": nickname,
        "chat_hub_uid": 0,
        "chat_is_guest": 1,
        "chat_wizard_uid": conn.WIZARD.WIZARD_ID,
        "chat_wizard_level": 1,
        "chat_wizard_rep_id": 0,
        "chat_wizard_rep_rarity": 1,
        "chat_wizard_rating_id": 1001,
        "chat_wizard_mentor_count": 0,
        "chat_wizard_mentee_count": 0,
        "chat_wizard_mentor_volunteer": 0,
        "server_type": 4,
        "chat_message": message 
    }
    data_encrypted = b64encode(SWCryptoMgr.Encrypt(SWCryptoMgr.CHAT, json.dumps(data_json)))
    data_len = len(data_encrypted)
    
    request_buffer =  struct.pack(">H", codes.USER_CHAT_REQ)
    request_buffer += struct.pack(">H", data_len)
    request_buffer += data_encrypted

    buffer_len = len(request_buffer) + 2
    request_buffer = struct.pack(">H", buffer_len) + request_buffer

    await conn.send(request_buffer)

def UserChatNotify(packet):
    data_len = int.from_bytes(packet[2:4], byteorder='big')
    data_b64 = packet[4:]
    data_json = json.loads(SWCryptoMgr.Decrypt(SWCryptoMgr.CHAT, b64decode(data_b64), compression = False))
    data_json.update({
        "type": codes.USER_CHAT_NOTIFY,
        "raw": packet,
    })
    return data_json

def ServerChatNotify(packet):
    data_len = int.from_bytes(packet[2:4], byteorder='big')
    data_b64 = packet[4:]
    data_json = json.loads(SWCryptoMgr.Decrypt(SWCryptoMgr.CHAT, b64decode(data_b64), compression = False))
    data_json.update({
        "type": codes.SERVER_CHAT_NOTIFY,
        "raw": packet,
    })
    return data_json
