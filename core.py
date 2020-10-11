import os
import json
import random
import asyncio
import discord
from discord import Embed
from discord.ext import commands
from dotenv import load_dotenv
import datetime as dt

from db import Connection
from routing import Routes
from level import Leveler
from errors import ConfigurationError

import requests
from movies import search as movie_search
from movies import load as movie_load
from wiki import find_page, get_summary

import pprint

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

CONFIG = [
    {
        "id": 759623723170136085,
        "colors": {
            "mod-negative": 15746887, # red
            "mod-positive": 4437377,  # green
            "mod-neutral": 7506394,   # blue
            "profile-card": 15105570  # orange
        },
        "roles": {
            "Administrators": [760869449451831357],
            "Moderators": [761313582348238848],
            "Muted": 760598156156338208,
            "Bot": 761377588424998932
        },
        "ranks": [
            {"id": 761855274645454888, "level": 1, "role": None},
            {"id": 761858285145555015, "level": 5, "role": None},
            {"id": 761858810737459211, "level": 10, "role": None},
            {"id": 761861671970013195, "level": 15, "role": None},
            {"id": 761861676831342613, "level": 20, "role": None}
        ],
        "channels": {
            "feed": 762952918848503859,
            "debug": 764641152682033172
        }
    }
]

CACHE = {}
LEVELER = None
FROZEN_USERS = []
IGNORE_ROLES = ["@everyone", "Muted"]

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

conn = Connection()
c = conn.cursor

routes = Routes(conn, c)

def is_moderator(ctx):
    mod_roles = CACHE[ctx.guild.id]["roles"]["Moderators"]
    admin_roles = CACHE[ctx.guild.id]["roles"]["Administrators"]
    valid_roles = mod_roles + admin_roles
    if any(r in ctx.author.roles for r in valid_roles):
        return True
    
    return False

@bot.event
async def on_ready():
    global CACHE
    global LEVELER

    for guild in bot.guilds:
        guild_id = guild.id
        
        guild_config = None
        for entry in CONFIG:
            if entry["id"] == guild_id:
                guild_config = entry
                break

        if guild_config is None: 
            raise ConfigurationError("guild {0} has not been configured".format(str(guild)))

        CACHE[guild_id] = {
            "roles": {
                "Administrators": [],
                "Moderators": [],
                "Muted": None,
                "Bot": None
            },
            "ranks": [],
            "channels": {
                "feed": None,
                "debug": None
            },
            "frozen": [],
            "colors": guild_config["colors"]
        }
        # cache administrator and moderator roles
        for key in ["Administrators", "Moderators"]:
            for role_id in guild_config["roles"][key]:
                role = guild.get_role(role_id)
                if role is None:
                    raise ConfigurationError("{0} role {1} does not exist".format(key[:-1], role_id))
                
                CACHE[guild_id]["roles"][key].append(role)
        # cache muted and bot role
        for key in ["Muted", "Bot"]:
            role_id = guild_config["roles"][key]
            role = guild.get_role(role_id)
            if role is None:
                raise ConfigurationError("{0} role {1} does not exist".format(key, role_id))

            CACHE[guild_id]["roles"][key] = role
        # cache rank hierarchy
        for entry in guild_config["ranks"]:
            role_id = entry["id"]
            role = guild.get_role(role_id)
            if role is None:
                raise ConfigurationError("ranked role {0} does not exist".format(role_id))

            CACHE[guild_id]["ranks"].append({
                "role": role,
                "level": entry["level"]
            })
        # cache bot channels
        for key in guild_config["channels"]:
            channel_id = guild_config["channels"][key]
            channel = guild.get_channel(channel_id)
            if channel is None:
                raise ConfigurationError("channel {0} does not exist".format(channel_id))

            CACHE[guild_id]["channels"][key] = channel
        
        debug = CACHE[guild_id]["channels"]["debug"]
        member_ids = routes.member_ids(guild)
        async for member in guild.fetch_members():
            if not member.bot:
                if member.id not in member_ids:
                    routes.insert_new_user(member)
                    await debug.send("LOG: new member {0} detected -> updated database".format(str(member)))
        
        channel_ids = routes.channel_ids(guild)
        for channel in await guild.fetch_channels():
            if isinstance(channel, discord.TextChannel):
                if channel.id not in channel_ids:
                    routes.insert_new_channel(channel)
                    await debug.send("LOG: new channel {0} detected -> updated database".format(str(channel)))

    LEVELER = Leveler(conn, c, CACHE)

    for key in CACHE:
        debug = CACHE[key]["channels"]["debug"]
        await debug.send(
            """```json
            {0}```""".format(pprint.pformat(CACHE[key]))
        )
        await debug.send("```{0} has successfully connected to {1}```".format(bot.user, bot.get_guild(key)))

    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_member_join(member):
    if member.bot:
        return
    
    routes.insert_new_user(member)

    print("new member detected -> updated database")
    return await member.add_roles(GUILDS[member.guild]["ranks"]["Foreigner"]["role"])

@bot.listen('on_message')
async def add_xp(message):
    if message.author.bot:
        return
    if message.author.id in CACHE[message.guild.id]["frozen"]:
        return
    
    await LEVELER.register_message(message)
    
@bot.command()
async def kick(ctx, member: discord.Member, reason: str = None):
    if not is_moderator(ctx):
        response = "**Error: permission denied.**"
        return await ctx.send(response)
    
    if ctx.author.top_role <= member.top_role:
        response = "**Error: target rank is equal to or above your own.**"
        return await ctx.send(response)

    if reason is None:
        reason = "*No reason specified*"
        await ctx.guild.kick(member)
    else:
        await ctx.guild.kick(member, reason=reason)

    embed = Embed(
        title="Kicked user {0}".format(str(member)), 
        description=reason, 
        color=CACHE[ctx.guild.id]["colors"]["mod-negative"], 
        timestamp=dt.datetime.now()
    )
    embed.set_author(name=ctx.author, icon_url=str(ctx.author.avatar_url))

    return await ctx.send(embed=embed)

@kick.error
async def kick_error(ctx, error):
    return await ctx.send(str(error))
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("**Member not found**")
    else:
        await ctx.send("**Invalid usage of command !kick**")


@bot.command()
async def freeze(ctx, member: discord.Member, reason: str = None):
    if not is_moderator(ctx):
        response = "**Error: permission denied.**"
        return await ctx.send(response)
    
    if ctx.author.top_role <= member.top_role:
        response = "**Error: target rank is equal to or above your own.**"
        return await ctx.send(response)

    if member.id in CACHE[ctx.guild.id]["frozen"]:
        response = "**{0} is already frozen**".format(member.mention)
        return await ctx.send(response)
    
    CACHE[ctx.guild.id]["frozen"].append(member.id)

    if reason is None:
        reason = "*No reason specified*"

    description = "XP gain for {0} is now frozen.\nReason: {1}".format(member.mention, reason)
    embed = Embed(
        title="Freeze", 
        description=description, 
        color=CACHE[ctx.guild.id]["colors"]["mod-negative"], 
        timestamp=dt.datetime.now()
    )
    embed.set_author(name=ctx.author, icon_url=str(ctx.author.avatar_url))

    return await ctx.send(embed=embed)

@freeze.error
async def freeze_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("**Member not found**")
    else:
        await ctx.send("**Invalid usage of command !freeze**")

@bot.command()
async def thaw(ctx, member: discord.Member, reason: str = None):
    if not is_moderator(ctx):
        response = "**Error: permission denied.**"
        return await ctx.send(response)
    
    if ctx.author.top_role <= member.top_role:
        response = "**Error: target rank is equal to or above your own.**"
        return await ctx.send(response)

    if member.id not in CACHE[ctx.guild.id]["frozen"]:
        response = "**{0} is not frozen**".format(member.mention)
        return await ctx.send(response)
    
    CACHE[ctx.guild.id]["frozen"].pop(
        CACHE[ctx.guild.id]["frozen"].index(member.id))

    if reason is None:
        reason = "*No reason specified*"

    description = "XP gain for {0} has resumed.\nReason: {1}".format(member.mention, reason)
    embed = Embed(
        title="Thaw", 
        description=description, 
        color=CACHE[ctx.guild.id]["colors"]["mod-positive"], 
        timestamp=dt.datetime.now()
    )
    embed.set_author(name=ctx.author, icon_url=str(ctx.author.avatar_url))

    return await ctx.send(embed=embed)

@thaw.error
async def thaw_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("**Member not found**")
    else:
        await ctx.send("**Invalid usage of command !thaw**")

@bot.command()
async def mute(ctx, member: discord.Member, reason: str = None):
    if not is_moderator(ctx):
        response = "**Error: permission denied.**"
        return await ctx.send(response)
    
    if ctx.author.top_role <= member.top_role:
        response = "**Error: target rank is equal to or above your own.**"
        return await ctx.send(response)

    muted_role = CACHE[ctx.guild.id]["roles"]["Muted"]
    if muted_role in member.roles:
        response = "**Error: member {0} is already muted.**".format(member.mention)
        return await ctx.send(response)

    await member.add_roles(muted_role)

    if reason is None:
        reason = "*No reason specified*"

    description = "Muted member {0}.\nReason: {1}".format(member.mention, reason)
    embed = Embed(
        title="Mute", 
        description=description, 
        color=CACHE[ctx.guild.id]["colors"]["mod-negative"], 
        timestamp=dt.datetime.now()
    )
    embed.set_author(name=ctx.author, icon_url=str(ctx.author.avatar_url))

    return await ctx.send(embed=embed)

@mute.error
async def mute_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("**Member not found**")
    else:
        await ctx.send("**Invalid usage of command !thaw**")

@bot.command()
async def unmute(ctx, member: discord.Member, reason: str = None):
    if not is_moderator(ctx):
        response = "**Error: permission denied.**"
        return await ctx.send(response)
    
    if ctx.author.top_role <= member.top_role:
        response = "**Error: target rank is equal to or above your own.**"
        return await ctx.send(response)

    muted_role = CACHE[ctx.guild.id]["roles"]["Muted"]
    if muted_role not in member.roles:
        response = "**Error: member {0} is not muted.**".format(member.mention)
        return await ctx.send(response)

    await member.remove_roles(muted_role)

    if reason is None:
        reason = "*No reason specified*"

    description = "Unmuted member {0}.\nReason: {1}".format(member.mention, reason)
    embed = Embed(
        title="Unmute", 
        description=description, 
        color=CACHE[ctx.guild.id]["colors"]["mod-positive"], 
        timestamp=dt.datetime.now()
    )
    embed.set_author(name=ctx.author, icon_url=str(ctx.author.avatar_url))

    return await ctx.send(embed=embed)

@unmute.error
async def unmute_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("**Member not found**")
    else:
        await ctx.send("**Invalid usage of command !unmute**")

@bot.command()
async def muted(ctx):
    members = []
    muted_role = CACHE[ctx.guild.id]["roles"]["Muted"]
    async for member in ctx.guild.fetch_members():
        if muted_role in member.roles:
            members.append(member)

    if len(members) == 0:
        response = "**Nobody is currently muted**"
        return await ctx.send(response)

    description = []
    for member in members:
        description.append("  -  {0} ({1})".format(member.mention, str(member)))
    
    description = "\n".join(description)

    embed = Embed(
        title="Currently Muted", 
        description=description, 
        color=CACHE[ctx.guild.id]["colors"]["mod-neutral"], 
        timestamp=dt.datetime.now()
    )

    return await ctx.send(embed=embed)

@muted.error
async def muted_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("**Member not found**")
    else:
        await ctx.send("**Invalid usage of command !muted**")

@bot.command()
async def profile(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    if member.bot:
        return

    if member.id == 353697138854854658:
        avatar_url = "https://i.ibb.co/GHzrGJ0/aladeen.gif"
    else:
        avatar_url = member.avatar_url

    embed = Embed(
        title=member.nick,
        color=member.top_role.color
    ).set_thumbnail(url=avatar_url).set_author(name=member)

    embed.set_footer(
        text="Joined: {0}".format(str(member.joined_at).split(' ')[0]))

    xp, next_xp = LEVELER.get_xp_range(ctx.guild, member)
    level_title = "Level" + " " + str(LEVELER.get_level(ctx.guild, member))
    level_str = "XP: ({0}/{1})".format(xp, next_xp)

    embed.add_field(name=level_title, value=level_str)

    member_data = routes.get_member(member)
    member_channels = routes.member_channels(member)

    channels = []
    removals = []
    for ch in member_channels:
        channel = ctx.guild.get_channel(ch)
        if channel is None:
            removals.append(ch)
        else:
            channels.append("  -  {0}".format(channel.mention))

    if len(removals) != 0:
        debug = CACHE[ctx.guild.id]["channels"]["debug"]
        # remove deleted channels
        for ch in removals:
            routes.remove_channel(ctx.guild, ch)
            debug.send(
                """```LOG: detected deleted channel {0} -> updated database```""".format(ch))
        
    if len(channels) != 0:
        channels = "\n".join(channels)
    else:
        channels = "*No channels yet*"        

    embed.add_field(name="Channels", value=channels, inline=False)
    roles = []
    for role in member.roles:
        if str(role) not in IGNORE_ROLES:
            roles.append("  -  {0}".format(role.mention))
    
    roles = "\n".join(reversed(roles))

    embed.add_field(name="Roles", value=roles, inline=True)

    return await ctx.send(embed=embed)

@profile.error
async def profile_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("**Member not found**")
    else:
        await ctx.send("**Invalid usage of command !profile**")

@bot.command(name='set-owner')
async def set_owner(ctx, channel: discord.TextChannel, member: discord.Member):
    if not is_moderator(ctx):
        response = "**Error: permission denied.**"
        return await ctx.send(response)    

    channel_data = routes.get_channel(channel)
    if channel_data is None:
        response = "**Error: channel not found.**"
        return await ctx.send(response) 

    if channel_data[2] == member.id:
        response = "**Error: channel is already owned by member {0}.**".format(channel.mention)
        return await ctx.send(response)
    
    routes.set_channel_owner(channel, member)

    await channel.set_permissions(
        member, 
        manage_channel=True,
        manage_permissions=True,
        manage_webhooks=True,
        manage_messages=True
    )

    description = "Channel {0} is now owned by {1}".format(channel.mention, member.mention)
    embed = Embed(
        title="Set Channel Owner", 
        description=description, 
        color=CACHE[ctx.guild.id]["colors"]["mod-positive"], 
        timestamp=dt.datetime.now()
    ).set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))

    return await ctx.send(embed=embed)

@set_owner.error
async def set_owner_error(ctx, error):
    return await ctx.send("""```{0}```""".format(str(error)))
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("**Member not found**")
    else:
        await ctx.send("**Invalid usage of command !set-owner**")

@bot.command(name='remove-owner')
async def remove_owner(ctx, channel: discord.TextChannel):
    if not is_moderator(ctx):
        response = "**Error: permission denied.**"
        return await ctx.send(response)
    
    channel_data = routes.get_channel(channel)
    if channel_data is None:
        response = "**Error: channel not found.**"
        return await ctx.send(response)

    if channel_data[2] is not None:
        routes.remove_channel_owner(channel)
    else:
        response = "**Error: channel is currently unowned.**"
        return await ctx.send(response)
    
    await channel.edit(sync_permissions=True)

    description = "Channel {0} is now unowned.".format(channel.mention)
    embed = Embed(
        title="Removed Channel Owner", 
        description=description, 
        color=CACHE[ctx.guild.id]["colors"]["mod-negative"], 
        timestamp=dt.datetime.now()
    ).set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))

    return await ctx.send(embed=embed)    
    
@remove_owner.error
async def remove_owner_error(ctx, error):
    return await ctx.send("""```{0}```""".format(str(error)))
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("**Member not found**")
    else:
        await ctx.send("**Invalid usage of command !remove-owner**")

@bot.command()
async def wiki(ctx, search_str: str):
    page = find_page(search_str)
    if page is None:
        response = "**Page not found**"
        return await ctx.send(response)

    title = page["title"]
    summary = get_summary(page)
    
    icon_url = "https://i.ibb.co/ZWqwGZx/wiki.png"

    embed = Embed(
        title=title, description=summary["extract"], 
        color=CACHE[ctx.guild.id]["colors"]["mod-neutral"], 
        timestamp=dt.datetime.now()
    ).set_author(name="wikipedia.com", url=summary["url"], icon_url=icon_url)

    if summary["thumbnail"] is not None:
        embed.set_thumbnail(url=summary["thumbnail"])
    
    return await ctx.send(embed=embed)

@wiki.error
async def wiki_error(ctx, error):
    return await ctx.send("**Invalid usage of command !wiki**")

@bot.command()
async def movies(ctx, search_str: str, index: int = None):
    if index is None:
        embed = movie_search(search_str)
        if embed is None:
            response = "**Sorry, no titles found by that name**"
            return await ctx.send(response)

        return await ctx.send(embed=embed)
    else:
        try:
            embed = movie_load(search_str, index)
        except IndexError:
            response = "**Error: invalid index**"
            return await ctx.send(response)
        except KeyError:
            response = "**Error: invalid title**"
            return await ctx.send(response)

        return await ctx.send(embed=embed)


@movies.error
async def movies_error(ctx, error):
    return await ctx.send("**Invalid usage of command !movies**")

@bot.command()
async def joke(ctx):
    url = "https://sv443.net/jokeapi/v2/joke/Dark?type=twopart"
    content = json.loads(requests.get(url).content)

    setup = content["setup"]
    delivery = content["delivery"]

    await ctx.send(setup)
    await asyncio.sleep(5)
    await ctx.send(delivery)
    return    

@joke.error
async def joke_error(ctx, error):
    return await ctx.send("**Invalid usage of command !movies**")

@bot.command()
async def trump(ctx):
    return await ctx.send("**Trump quotes are temporarily disabled, sorry!**")
    # response = random.choice(
    #     c.execute('SELECT * FROM trump').fetchall())[0]
    
    # if '—' in response:
    #     response = response.split('—')[0] + '\n— ' + response.split('—')[1]
    # else:
    #     response += '\n— Donald J. Trump'

    # embed = Embed(
    #     description=response
    # )

    # embed.set_thumbnail(
    #     url="https://i.insider.com/5ea18a43a2fd914dad7b2073?width=1100&format=jpeg&auto=webp"
    # )

    # await ctx.send(embed=embed)
    # return

@trump.error
async def trump_error(ctx, error):
    return await ctx.send("**Trump quotes are temporarily disabled, sorry!**")

bot.run(TOKEN)