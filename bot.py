import nextcord
import chat_exporter
from nextcord.ext import commands
import typing
import io
import re
from types import SimpleNamespace
import time
import datetime
from html_to_bbcode import html_to_bbcode
import os
from dotenv import load_dotenv
import json
from nextcord.ext import tasks
import threading
import quick_copy_server
import uuid

load_dotenv()

intents = nextcord.Intents.default()
intents.members = True
intents.messages = False
intents.message_content = True

bot = commands.Bot(
    intents=intents, shard_count=1, shard_id=0,
    chunk_guilds_at_startup=False,
    max_messages=None)

userids_whitelist=set()

async def load_user_whitelist():
    try:
      (chId,mId)=map(int,str(CONFIGURATION_MESSAGE).split("/"))
    except:
      raise Exception("cannot parse CONFIGURATION_MESSAGE=" + str(CONFIGURATION_MESSAGE))
    
    ch = await bot.fetch_channel(chId)
    m = await ch.fetch_message(mId)  # type: ignore
    config=json.loads(str(m.content))
    userids_whitelist = set(config["USER_WHITELIST"])
    

async def check_permissions(interaction: nextcord.Interaction):
    if interaction.user is None:
        await interaction.response.send_message("permission err: user not found")
        return False
    if interaction.user.id in userids_whitelist:
        await interaction.response.send_message("permission err: user not in whitelist")
        return False
    return True

lastInteractionUpdated = threading.Event()
lastInteraction:float=time.time() #seconds
@tasks.loop(minutes=5)
async def bot_inactivity_check():
    now = time.time()
    diff = now - lastInteraction
    if diff > 60*10:
        await bot.close()

#runs in another thread
def wakeupbot():
    lastInteraction = time.time()
    lastInteractionUpdated.set()


@bot.slash_command(description="Save transcript bounded by two messages, inclusive.")
async def save(interaction: nextcord.Interaction, 
               msglink1:str = nextcord.SlashOption(required=True),
               msglink2:str = nextcord.SlashOption(required=True)):
    if not hasattr(interaction, "send"):
        await interaction.response.send_message("err: unknown channel type")
        return
    
    if not await check_permissions(interaction):
        return
    
    lastInteraction = time.time()
    
    msgBody = "Starting transcription."
    msg = await interaction.send(msgBody)
    async def msgAppend(s:str):
        nonlocal msgBody
        msgBody += "\n" + s
        await msg.edit(msgBody)
    try:

        channel = typing.cast(nextcord.TextChannel, interaction.channel)

        #Get range
        links=[]
        for discordUrl in [msglink1,msglink2]:
            m = re.match(r"^https:\/\/discord\.com\/channels\/(?P<guildId>\d{17,21})\/(?P<channelId>\d{17,21})\/(?P<msgId>\d{17,21})$",
                     discordUrl)
            if m is None:
                await msgAppend("err: can't parse msgLink.")
                return
            link = SimpleNamespace()
            link.guildId = int(m.group("guildId"))
            link.channelId = int(m.group("channelId"))
            link.msgId = int(m.group("msgId"))
            links.append(link)

        if links[0].channelId != links[1].channelId \
          or links[0].guildId != links[1].guildId:
            await msgAppend("err: links must be in the same channel.")
            return

        tChannel = bot.get_channel(links[0].channelId)
        if tChannel is None:
            try:
              tChannel=await bot.fetch_channel(links[0].channelId)
            except:
                await msgAppend("err: can't find the channel.")
                return

        if not hasattr(tChannel,"fetch_message"):
            await msgAppend("err: unknown channel type.")
            return
        tChannel = typing.cast(nextcord.PartialMessageable,tChannel)

        rangeDates:list[datetime.datetime] = []
        for link in links:
            try:
              rmsg=await tChannel.fetch_message(int(link.msgId))
            except nextcord.NotFound:
                await msgAppend("err: no such message.")
                return
            except nextcord.Forbidden:
                await msgAppend("err: bot doesn't have the right to access message.")
                return
            rangeDates.append(rmsg.created_at)

        before = max(rangeDates)
        after = min(rangeDates) - datetime.timedelta(milliseconds=10)

        await msgAppend("Message range determined, downloading messages.")
        transcript = await chat_exporter.export(
            tChannel,
            limit=None,
            tz_info="UTC",
            military_time=False,
            before=before,
            after=after,
            bot=bot
        )

        if transcript is None:
            await msgAppend("err: message download failed")
            return
        await msgAppend("Messages downloaded, converting to bbcode.")

        bbcode = html_to_bbcode(transcript)

        await msgAppend("Converted to bbcode.")

        transcript_file = nextcord.File(
            io.BytesIO(bbcode.encode()),
            filename=f"transcript-{channel.name}.txt",
        )
        await msg.edit(msgBody,file=transcript_file)
        id = str(uuid.uuid4())
        quick_copy_server.add_to_quick_copy(id,bbcode)
        await msgAppend("Quick copy link: [copy]("+HOST+"/copy/"+id+")")
        #await channel.send(file=transcript_file)
    except Exception as e:
        await msgAppend("err: " + str(e))
        raise
        

@bot.slash_command(description="load_user_whitelist()")
async def reload_whitelist(interaction: nextcord.Interaction):
    lastInteraction = time.time()

    msg = await interaction.response.send_message("Reloading")
    try:
        await load_user_whitelist()
    except Exception as e:
        await msg.edit(content=str(e))
        raise
    

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CONFIGURATION_MESSAGE = os.getenv("CONFIGURATION_MESSAGE")
HOST = os.getenv("HOST") or os.getenv("RENDER_EXTERNAL_URL") or "None"

if BOT_TOKEN is None:
    print("BOT_TOKEN cannot be empty")
elif CONFIGURATION_MESSAGE is None:
    print("CONFIGURATION_MESSAGE cannot be empty")
else:
  quick_copy_server.onbotwakeup=wakeupbot
  quick_copy_server.start_web_server_thread()
  while True:
    bot.run(BOT_TOKEN)
    if lastInteractionUpdated.is_set():
      lastInteractionUpdated.clear()
    lastInteractionUpdated.wait()
    lastInteractionUpdated.clear()