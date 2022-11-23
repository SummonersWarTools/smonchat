from hive.auth import HiveUser, HiveGuestUser
from swgateway import regions
from swgateway.wizard import WizardGuest
from swgateway.api.gateway import GetChatServerInfo

from . import packet

import requests
import json
import math
import time
import asyncio
import binascii
import logging
from base64 import b64encode, b64decode

def connect(guest, region = regions.GLOBAL):
    if not isinstance(guest, HiveUser): raise Exception("connect() should be called with a HiveUser")
    if not isinstance(guest, HiveGuestUser): raise Exception("smonchat does not yet support HiveUser types other than HiveGuestUser")

    # ensure guest user has authenticated
    if guest.HIVE_UID == None or guest.PEPPERMINT_TOKEN == None: raise hive.HiveAuthException("HiveUser is not authenticated with Hive, ensure you call authenticate() on the user before calling connect()")

    # create a wizard and authenticate via GuestLogin
    wizard = WizardGuest(guest)
    wizard.set_region(region)
    wizard.authenticate()

    # return the wizard object
    return wizard

async def join(wizard, channel=1123, nickname=None):
    logging.info(f"Joining channel {channel} with user ID {wizard.WIZARD_ID}")
    # fetch chat server info
    chat_data = GetChatServerInfo(wizard)
    if chat_data['status'] != 200 or chat_data['data']['ret_code'] != 0: raise Exception(f"failed to fetch chat server info from API, status={chat_data['status']}, return={chat_data['data']['ret_code']}")
    # create chat connection
    conn = ChatConnection(wizard, chat_data['data']['chat_server']['ip'], chat_data['data']['chat_server']['port'], chat_data['data']['chat_server']['game_server_id'], chat_data['data']['chat_server']['login_key'])
    logging.info(f"Chat connection is {conn.CHAT_SERVER_IP}:{conn.CHAT_SERVER_PORT}")
    # prep a LOGIN_REQ_V2 packet for send
    await packet.LoginV2Req(conn)

    # open connection to the chat server
    reader, writer = await asyncio.open_connection(conn.CHAT_SERVER_IP, conn.CHAT_SERVER_PORT)
    logging.debug(f"Successful connection to chat server")

    # initialize consumer/producer/timer threads
    conn.consumer = asyncio.create_task(_consumer(conn, reader))
    conn.producer = asyncio.create_task(_producer(conn, writer))
    conn.timer    = asyncio.create_task(_timer(conn))

    await packet.GroupChangeReq(conn, channel)

    return conn

# receive a packet from the connection's RECV_QUEUE and processes it to the appropriate packet type as a dictionary
async def receive(conn):
    # read packet from the receive queue
    packet_data = await conn.RECV_QUEUE.get()
    packet_type = int.from_bytes(packet_data[:2], byteorder='big')
    # return the appropriate packet processing based on the response code
    # (this will fall back to just returning type + raw data for an unrecognized packet)
    if   packet_type == codes.LOGIN_V2_RES:       return packet.LoginV2Res(packet_data)
    elif packet_type == codes.GROUP_CHANGE_RES:   return packet.GroupChangeRes(packet_data)
    elif packet_type == codes.PING_RES:           return packet.PingRes(packet_data)
    elif packet_type == codes.USER_CHAT_NOTIFY:   return packet.UserChatNotify(packet_data)
    elif packet_type == codes.SERVER_CHAT_NOTIFY: return packet.ServerChatNotify(packet_data)
    else: return { "type": packet_type, "raw": packet_data, "unhandled": True }

# consumes packets from the TCP connection and writes them to the RECEIVE_QUEUE.
async def _consumer(conn, reader):
    logging.debug("Initialized consumer task")
    # loop to process packets
    while True:
        # read packet length first (always 2 bytes)
        packet_len = await reader.read(2)
        packet_len = int.from_bytes(packet_len, byteorder='big')
        logging.info(f"Consumer read packet length as {packet_len}")
        # read remainder of packet based on length
        packet_data = await reader.read(packet_len - 2)
        logging.info(f"Consumer read packet data as {binascii.hexlify(packet_data)}")
        # stash the CHAT_LOGIN_ID if this is a login response
        if int.from_bytes(packet_data[:2], byteorder='big') == codes.LOGIN_V2_RES: conn.CHAT_LOGIN_ID = int.from_bytes(packet_data[6:10], byteorder='big')
        # push the packet onto the receive queue
        await conn.RECV_QUEUE.put(packet_data)

# reads the SEND_QUEUE and writes to the TCP connection.
async def _producer(conn, writer):
    logging.debug("Initialized producer task")
    # loop to process queue
    while True:
        packet_data = await conn.SEND_QUEUE.get()
        writer.write(packet_data)
        logging.info(f"Producer sent packet data as {binascii.hexlify(packet_data)}")

# loops and sends a PING_REQ packet every 10s to maintain connectivity to the server.
async def _timer(conn):
    await conn.wait_for_login()
    logging.debug("Initialized ping timer task")
    # loop to send ping requests
    while True:
        await packet.PingReq(conn)
        await asyncio.sleep(10)

class ChatConnection:
    WIZARD = None
    CHAT_SERVER_IP = None
    CHAT_SERVER_PORT = None
    CHAT_GAME_SERVER_ID = None
    CHAT_LOGIN_KEY = None
    CHAT_LOGIN_ID = None

    SEND_QUEUE = asyncio.Queue(maxsize=64)
    RECV_QUEUE = asyncio.Queue(maxsize=64)

    consumer = None
    producer = None
    timer = None

    def __init__(self, wizard, ip, port, server_id, login_key):
        self.WIZARD = wizard
        self.CHAT_SERVER_IP = ip
        self.CHAT_SERVER_PORT = port
        self.CHAT_GAME_SERVER_ID = server_id
        self.CHAT_LOGIN_KEY = login_key

    async def send(self, packet):
        await self.SEND_QUEUE.put(packet)

    async def receive(self, packet):
        await self.RECV_QUEUE.put(packet)

    async def wait_for_login(self):
        # wait for the chat login ID to become available from login response
        while self.CHAT_LOGIN_ID == None: await asyncio.sleep(1)
