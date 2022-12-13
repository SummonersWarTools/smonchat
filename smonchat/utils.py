from . import packet, types

async def GlobalChatSend(conn, chat_message, nickname = None):
    await packet.UserChatReq(conn, types.CHAT_GLOBAL, { "chat_message": chat_message }, nickname)

async def RequestSecretDungeon(conn, instance_iid, owner_id, nickname = None):
    await packet.UserChatReq(conn, types.CHAT_ACCESS_DUNGEON, { "chat_item_type": 13, "chat_item_id": instance_iid, "chat_owner_wizard_uid": owner_id }, nickname)

async def ShareSecretDungeon(conn, instance_iid, instance_end_time, nickname = None):
    await packet.UserChatReq(conn, types.CHAT_SHARE_DUNGEON, { "instance_iid": instance_iid, "instance_end_time": instance_end_time }, nickname)

async def WhisperChatSend(conn, chat_message, target_hub_uid, target_wizard_uid, target_level, target_nickname, nickname = None):
    await packet.UserWhisperReq(conn, types.CHAT_USER_WHISPER, { "chat_message": chat_message }, { "hub_uid": target_hub_uid, "wizard_uid": target_wizard_uid, "wizard_level": target_level, "wizard_name": target_nickname }, nickname)