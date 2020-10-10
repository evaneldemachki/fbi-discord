import os
import random
import json
import discord
from discord import Embed
import re
import asyncio
from dotenv import load_dotenv
import datetime as dt
import pprint
from level import Leveler
from db import Connection
import requests
import movies

from collections import OrderedDict

from wiki import find_page, get_summary

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

conn = Connection()
c = conn.cursor

# Create tables
c.execute('''
create table if not exists trump (quote text null)
''')
c.execute('''
create table if not exists members (
    user_id bigint null,
    channels text null,
    infractions int null,
    xp bigint null,
    guild_id bigint null,
    unique (
        user_id,
        guild_id
    )
)
''')
c.execute('''
create table if not exists channels (
    guild_id bigint null,
    channel_id bigint null,
    owner_id bigint null,
    unique (
        guild_id,
        channel_id
    )
)
''')

conn.commit()

GUILDS = {}
COLORS = {
    "mod-negative": 15746887, # red
    "mod-positive": 4437377,  # green
    "mod-neutral": 7506394,   # blue
    "profile-card": 15105570  # orange
}
IGNORE_ROLES = ["@everyone", "Muted"]
IGNORE_CHANNELS = []
FROZEN = []
LEVELER = None

async def unmute(channel, member, role):
    await asyncio.sleep(60)
    await member.remove_roles(role)
    await channel.send("{0} is no longer choi'd".format(member.mention))

def is_moderator(guild, member):
    mod_role = GUILDS[guild]["roles"]["Fascist"]
    admin_role = GUILDS[guild]["roles"]["Dictator"]
    if mod_role in member.roles or admin_role in member.roles or member == client.user:
        return True
    
    return False

def is_muted(guild, member):
    muted_role = GUILDS[guild]["roles"]["Muted"]
    if muted_role in member.roles:
        return True
    
    return False

@client.event
async def on_member_join(member):
    if member.bot:
        return

    query = """
    INSERT INTO members (guild_id, member_id, channels, xp, infractions)
    VALUES({0}, {1}, '{2}', {3}, {4})
    ON CONFLICT DO NOTHING
    """.format(member.guild.id, member.id, "[]", 0, 0)

    c.execute(query)
    conn.commit()

    return await member.add_roles(GUILDS[member.guild]["ranks"]["Foreigner"]["role"])  
    
@client.event
async def on_ready():
    global GUILDS
    global LEVELER

    for guild in client.guilds:
        guild_id = guild.id
        
        roles = {
            "Dictator": None,
            "Fascist": None,
            "Muted": None,
            "Bot": None
        }
        ranks = OrderedDict([
            ("Foreigner", {"level": 1, "role": None}),
            ("Citizen", {"level": 5, "role": None}),
            ("Elite", {"level": 10, "role": None}),
            ("Elder", {"level": 15, "role": None}),
            ("Legend", {"level": 20, "role": None})
        ])
        channels = {
            "feed": None
        }

        valid = False
        for role in await guild.fetch_roles():
            if str(role) in roles:
                roles[str(role)] = role
            if str(role) in list(ranks.keys()):
                ranks[str(role)]["role"] = role
            else:
                continue

            roles_valid = all([roles[key] is not None for key in roles])
            ranks_valid = all([ranks[key]["role"] is not None for key in ranks])
            if roles_valid and ranks_valid:
                valid = True
                break

        if not valid:
            raise KeyError("Guild '{0}' not properly configured".format(str(guild)))

        for channel in await guild.fetch_channels():
            if channel.id == 762952918848503859:
                channels["feed"] = channel
                break
        
        if channels["feed"] is None:
            raise KeyError("Guild '{0}' not properly configured".format(str(guild)))
        
        GUILDS[guild] = {
            "roles": roles,
            "ranks": ranks,
            "channels": channels
        }
    
        #bot_role = GUILDS[guild]["roles"]["Bot"]
        async for member in guild.fetch_members():
            if not member.bot:
                # change to execute_many with ? syntax
                query = """
                INSERT INTO members (user_id, guild_id, channels, xp, infractions)
                VALUES({0}, {1}, '{2}', {3}, {4})
                ON CONFLICT DO NOTHING
                """.format(member.id, guild.id, "[]", 0, 0)
                c.execute(query)
        
        conn.commit()

    LEVELER = Leveler(conn, c, GUILDS)

    for guild in GUILDS:
        await GUILDS[guild]["channels"]["feed"].send(f'{client.user} has connected to {str(guild)}')

    print(f'{client.user} has connected to Discord!')
    print(GUILDS)

@client.event
async def on_message(message):
    global FROZEN_USERS
    if message.author == client.user:
        return

    #bot_role = GUILDS[message.guild]["roles"]["Bot"]
    if not message.author.bot:
        if not message.author.id in FROZEN:
            await LEVELER.register_message(message)

    if message.content.split(' ')[0] == "!kick": 
        if not is_moderator(message.guild, message.author):
            response = "**Error: permission denied.**"
            return await message.channel.send(response)      

        if len(message.mentions) != 1:
            response = "**Error: invalid usage of !kick.**"
            return await message.channel.send(response)
        
        msg_split = message.content.split(' ')[1:]
        if msg_split[0][0].strip() != "<" or msg_split[0][-1].strip() != ">":
            response = "**Error: invalid usage of !kick.**"
            return await message.channel.send(response)

        member = message.mentions[0]
        msg_split = msg_split[1:]

        if message.author.top_role <= member.top_role:
            response = "**Error: target rank is equal to or above your own.**"
            return await message.channel.send(response)  

        if len(msg_split) == 0:
            reason = "*No reason specified*"
            await message.guild.kick(member)
        else:
            reason = ' '.join(msg_split)
            await message.guild.kick(member, reason=reason)

        embed = Embed(
            title="Kicked user {0}".format(str(member)), 
            description=reason, color=COLORS["mod-negative"], 
            timestamp=dt.datetime.now()
        )
        embed.set_author(name=message.author, icon_url=str(message.author.avatar_url))

        return await message.channel.send(embed=embed)

    if message.content.split(' ')[0] == "!freeze": 
        if not is_moderator(message.guild, message.author):
            response = "**Error: permission denied.**"
            return await message.channel.send(response)      

        msg_split = message.content.split(' ')
        if len(msg_split) != 2 or len(message.mentions) != 1:
            response = "**Error: invalid usage of !freeze.**"
            return await message.channel.send(response)

        member = message.mentions[0]
        if message.author.top_role <= member.top_role:
            response = "**Error: target rank is equal to or above your own.**"
            return await message.channel.send(response)                      
        
        if member.id in FROZEN:
           response = "**{0} is already frozen**".format(member.mention)
           return await message.channel.send(response)    

        FROZEN.append(member.id)

        description = "XP gain for {0} is now frozen".format(member.mention)
        embed = Embed(
            title="Freeze", 
            description=description, color=COLORS["mod-negative"], 
            timestamp=dt.datetime.now()
        )
        embed.set_author(name=message.author, icon_url=str(message.author.avatar_url))

        return await message.channel.send(embed=embed)
    
    if message.content.split(' ')[0] == "!thaw":
        if not is_moderator(message.guild, message.author):
            response = "**Error: permission denied.**"
            return await message.channel.send(response)

        msg_split = message.content.split(' ')
        if len(msg_split) != 2 or len(message.mentions) != 1:
            response = "**Error: invalid usage of !freeze.**"
            return await message.channel.send(response)

        member = message.mentions[0]
        if message.author.top_role <= member.top_role:
            response = "**Error: target rank is equal to or above your own.**"
            return await message.channel.send(response)

        if not member.id in FROZEN:
           response = "**{0} is not frozen**".format(member.mention)
           return await message.channel.send(response)

        FROZEN.pop(FROZEN.index(member.id))

        description = "XP gain for {0} has resumed".format(member.mention)
        embed = Embed(
            title="Thaw", 
            description=description, color=COLORS["mod-positive"], 
            timestamp=dt.datetime.now()
        )
        embed.set_author(name=message.author, icon_url=str(message.author.avatar_url))

        return await message.channel.send(embed=embed)            

    if message.content.split(' ')[0] == "!mute":
        if not is_moderator(message.guild, message.author):
            response = "**Error**: permission denied."
            return await message.channel.send(response)

        members = []
        for member in message.mentions:
            if message.author.top_role <= member.top_role:
                response = "**Error: target rank is equal to or above your own.**"
                return await message.channel.send(response)
            else:
                if is_muted(message.guild, member):
                    response = "**Error: user '{0}' is already muted.**".format(member.mention)
                    return await message.channel.send(response)

                members.append(member)
        
        if len(members) == 0:
            response = "**Error: no users specified.**"
            return await message.channel.send(response)
        
        muted_role = GUILDS[message.guild]["roles"]["Muted"]
        for member in members:
            await member.add_roles(muted_role)

        description = []
        for member in members:
            description.append("  -  {0} ({1})".format(member.mention, str(member)))
        
        description = "\n".join(description)

        embed = Embed(
            title="Muted ({0}) Members".format(len(members)), 
            description=description, color=COLORS["mod-negative"], 
            timestamp=dt.datetime.now()
        )
        embed.set_author(name=message.author, icon_url=str(message.author.avatar_url))

        return await message.channel.send(embed=embed)

    if message.content.split(' ')[0] == "!unmute":
        if not is_moderator(message.guild, message.author):
            response = "**Error: permission denied.**".format(member.mention)
            return await message.channel.send(response)

        members = []
        for member in message.mentions:
            if message.author.top_role <= member.top_role:
                response = "**Error: target rank is equal to or above your own.**"
                return await message.channel.send(response)
            else:
                if not is_muted(message.guild, member):
                    response = "**Error: user {0} is not muted.**".format(member.mention)
                    return await message.channel.send(response)

                members.append(member)
        
        if len(members) == 0:
            response = "**Error: no users specified.**"
            return await message.channel.send(response)
        
        muted_role = GUILDS[message.guild]["roles"]["Muted"]
        for member in members:
            await member.remove_roles(muted_role)

        description = []
        for member in members:
            description.append("  -  {0} ({1})".format(member.mention, str(member)))
        
        description = "\n".join(description)

        embed = Embed(
            title="Unmuted ({0}) Members".format(len(members)), 
            description=description, color=COLORS["mod-positive"], 
            timestamp=dt.datetime.now()
        )
        embed.set_author(name=message.author, icon_url=str(message.author.avatar_url))

        return await message.channel.send(embed=embed)
    
    if message.content.split(' ')[0] == "!muted":
        if not message.content.rstrip() == "!muted":
            response = "**Error: !muted does not take arguments.**"
            return await message.channel.send(response)

        members = []
        async for member in message.guild.fetch_members():
            if is_muted(message.guild, member):
                members.append(member)

        if len(members) == 0:
            response = "**Nobody is currently muted**"
            return await message.channel.send(response)

        description = []
        for member in members:
            description.append("  -  {0} ({1})".format(member.mention, str(member)))
        
        description = "\n".join(description)

        embed = Embed(
            title="Currently Muted", 
            description=description, color=COLORS["mod-neutral"], 
            timestamp=dt.datetime.now()
        )

        return await message.channel.send(embed=embed)
    
    if message.content.split(' ')[0] == "!profile":
        if message.content.rstrip() == "!profile":
            member = message.author
        else:
            msg_split = message.content.split(' ')
            if len(msg_split) > 2 or not (msg_split[1][0] == "<" and msg_split[1][-1] == ">"):
                response = "**Error: invalid usage of !profile.**"
                return await message.channel.send(response)
            if len(message.mentions) == 0:
                response = "**Error: invalid usage of !profile.**"
                return await message.channel.send(response)

            member = message.mentions[0]
        
        if member.bot:
            return
            
        embed = Embed(
            title=member.nick,
            color=COLORS["profile-card"]
        ).set_thumbnail(url=member.avatar_url).set_author(name=member)

        embed.set_footer(text="Joined: {0}".format(str(member.joined_at).split(' ')[0]))

        xp, next_xp = LEVELER.get_xp_range(message.guild, member)
        level_title = "Level" + " " + str(LEVELER.get_level(message.guild, member))
        level_str = "XP: ({0}/{1})".format(xp, next_xp)
        embed.add_field(name=level_title, value=level_str)

        query = """select * from MEMBERS where (USER_ID = {0} and GUILD_ID = {1})"""
        query = query.format(member.id, message.guild.id)
        c.execute(query)
        # TODO: handle not exists
        member_data = c.fetchone()

        channels = []

        channel_ids = json.loads(member_data[1])
        removals = []
        for ch in channel_ids:
            channel = message.guild.get_channel(ch)
            if channel is None: # channel no longer exists
                # queue channel removal
                removals.append(ch)
            else:
                channels.append("  -  {0}".format(channel.mention))
        
        if len(removals) != 0:
            # remove deleted channels
            for ch in removals:
                channel_ids.pop(channel_ids.index(ch))
            # re-insert into database
            query = "UPDATE members SET channels='{1}' WHERE (USER_ID = {1} and GUILD_ID = {2})"
            query = query.format(json.dumps(channel_ids), member.id, message.guild.id)
            c.execute(query)
            conn.commit()
            # log database update
            print("Channel(s) [{0}] no longer exist(s) -> updated database".format(removals))
           
        if len(channels) != 0:
            channels = "\n".join(channels)
        else:
            channels = "*No channels yet*"
        
        embed.add_field(name="Channels", value=channels, inline=False)

        infractions = member_data[2]

        roles = []
        for role in member.roles:
            if str(role) not in IGNORE_ROLES:
                roles.append("  -  {0}".format(role.mention))

        roles = "\n".join(reversed(roles))

        embed.add_field(name="Roles", value=roles, inline=True)

        return await message.channel.send(embed=embed)

    if message.content.split(' ')[0] == "!set-owner":
        if not is_moderator(message.guild, message.author):
            response = "**Error: permission denied.**".format(member.mention)
            return await message.channel.send(response)

        msg_split = message.content.split(' ')
        if len(msg_split) != 3:
            ".."
            response = "**Error: invalid usage of !set-owner.**"
            return await message.channel.send(response)
        if not (len(message.mentions) == len(message.channel_mentions) == 1):
            response = "**Error: invalid usage of !set-owner.**"
            return await message.channel.send(response)
        
        channel = message.channel_mentions[0]
        member = message.mentions[0]

        query = """select * from MEMBERS where GUILD_ID = {0}"""
        query = query.format(message.guild.id)
        c.execute(query)
        # TODO: handle not exists
        data = list(c.fetchall())

        for i in range(len(data)):
            data[i] = list(data[i])
            data[i][1] = json.loads(data[i][1])
        
        for entry in data:
            if channel.id in entry[1]:
                if entry[0] == member.id:
                    response = "**Error: user {0} already owns channel {1}.**".format(member.mention, channel.mention)
                    return await message.channel.send(response)
                else:
                    insertion = entry[1]
                    insertion.pop(insertion.index(channel.id))
                    insertion = json.dumps(insertion)

                    query = "UPDATE members SET channels='{1}' WHERE user_id='{0}'"
                    query = query.format(entry[0], insertion)
                    c.execute(query)

                    break
        
        record = None
        for entry in data:
            if entry[0] == member.id:
                record = entry
        
        record[1].append(channel.id)
        insertion = json.dumps(record[1])

        query = """
        update MEMBERS set CHANNELS = '{0}' where 
        (USER_ID = {1} and GUILD_ID = {2})"""
        query = query.format(insertion, record[0], message.guild.id)
        c.execute(query)

        conn.commit()

        description = "Channel {0} is now owned by {1}".format(channel.mention, member.mention)

        embed = Embed(
            title="Set Channel Owner", 
            description=description, color=COLORS["mod-positive"], 
            timestamp=dt.datetime.now()
        ).set_author(name=str(message.author), icon_url=str(message.author.avatar_url))

        return await message.channel.send(embed=embed)

    if message.content.split(' ')[0] == "!remove-owner":
        if not is_moderator(message.guild, message.author):
            response = "**Error: permission denied.**".format(member.mention)
            return await message.channel.send(response)

        msg_split = message.content.split(' ')
        if len(msg_split) != 2:
            response = "**Error: invalid usage of !set-owner.**"
            return await message.channel.send(response)
        if len(message.channel_mentions) != 1:
            response = "**Error: invalid usage of !set-owner.**"
            return await message.channel.send(response)
        
        channel = message.channel_mentions[0]

        query = """select * from MEMBERS where GUILD_ID = {0}"""
        query = query.format(message.guild.id)
        c.execute(query)
        # TODO: handle not exists
        data = c.fetchall()

        record = None
        for entry in data:
            channel_ids = json.loads(entry[1])
            if channel.id in channel_ids:
                record = list(entry)
                record[1] = channel_ids
                break
        
        if record is None:
            response = "**Error: channel {0} does not have an owner.**".format(channel.id)
            return await message.channel.send(response)

        record[1].pop(record[1].index(channel.id))
        record[1] = json.dumps(record[1])
        
        query = """update MEMBERS set CHANNELS = '{0}'
        where (USER_ID = {1} and GUILD_ID = {2})"""
        query = query.format(record[1], record[0], message.guild.id)
        c.execute(query)

        conn.commit()

        member = await message.guild.fetch_member(record[0])
        description = "Channel {0} is no longer owned by {1}".format(channel.mention, member.mention)

        embed = Embed(
            title="Removed Channel Owner", 
            description=description, color=COLORS["mod-negative"], 
            timestamp=dt.datetime.now()
        ).set_author(name=str(message.author), icon_url=str(message.author.avatar_url))

        return await message.channel.send(embed=embed)

    if message.content.split(' ')[0] == "!wiki":
        search_str = message.content.split(' ')[1:]
        search_str = " ".join(search_str)

        page = find_page(search_str)
        if page is None:
            response = "**Page not found**"
            return await message.channel.send(response)

        title = page["title"]
        summary = get_summary(page)
        
        icon_url = "https://i.ibb.co/ZWqwGZx/wiki.png"

        embed = Embed(
            title=title, description=summary["extract"], 
            color=COLORS["mod-neutral"], timestamp=dt.datetime.now()
        ).set_author(name="wikipedia.com", url=summary["url"], icon_url=icon_url)

        if summary["thumbnail"] is not None:
            embed.set_thumbnail(url=summary["thumbnail"])
        
        return await message.channel.send(embed=embed)
    
    if message.content.split(' ')[0] == "!movies":
        msg_split = message.content.split(' ')[1:]
        msg = " ".join(msg_split).strip()

        if msg[0] != '"':
            response = "**Error: invalid usage of !movies**"
            return await message.channel.send(response)
        
        msg = msg[1:]
        index = None
        for i in range(len(msg)):
            char = msg[i]
            if char == '"':
                if index is None:
                    index = i
                    break
                else:
                    response = "**Error: invalid usage of !movies**"
                    return await message.channel.send(response) 
        
        if index is None:
            response = "**Error: invalid usage of !movies**"
            return await message.channel.send(response)

        title = msg[:index].strip()
        index = msg[index+1:].strip()

        if len(index) == 0:
            embed = movies.search(title)
            if embed is None:
                response = "**Sorry, no titles found by that name**"
                return await message.channel.send(response)

            return await message.channel.send(embed=embed)
        else:
            try:
                index = int(index)
            except:
                response = "**Error: invalid usage of !movies**"
                return await message.channel.send(response)

            try:
                embed = movies.load(title, index)
            except IndexError:
                response = "**Error: invalid index**"
                return await message.channel.send(response)
            except KeyError:
                response = "**Error: invalid title**"
                return await message.channel.send(response)

            return await message.channel.send(embed=embed)                                   
          
    if message.content.split(' ')[0] == "!choi":
        if not message.content.rstrip() == "!choi":
            response = "**Error: !choi does not take arguments**"
            return await message.channel.send(response)

        if not is_moderator(message.guild, message.author):
            response = "**Error: permission denied.**".format(message.author.mention)
            return await message.channel.send(response)

        members = []
        async for member in message.guild.fetch_members():
            if not is_moderator(message.guild, member):
                members.append(member)

        role = GUILDS[message.guild]["roles"]["Muted"]
        member = random.choice(members)
        await member.add_roles(role)

        response = member.mention + " has been choi'd!"
        await message.channel.send(response)

        await unmute(message.channel, member, role)
    
    if message.content.split(' ')[0] == "!joke":
        if not message.content.rstrip() == "!joke":
            response = "**Error: !joke does not take arguments**"
            return await message.channel.send(response)

        url = "https://sv443.net/jokeapi/v2/joke/Dark?type=twopart"
        content = json.loads(requests.get(url).content)

        setup = content["setup"]
        delivery = content["delivery"]

        await message.channel.send(setup)
        await asyncio.sleep(5)
        await message.channel.send(delivery)
        return

    if message.content.split(' ')[0] == "!trump":
        if not message.content.rstrip() == "!trump":
            response = "**Error: !trump does not take arguments**"
            return await message.channel.send(response)

        response = random.choice(
            c.execute('SELECT * FROM trump').fetchall())[0]
        
        if '—' in response:
            response = response.split('—')[0] + '\n— ' + response.split('—')[1]
        else:
            response += '\n— Donald J. Trump'

        embed = Embed(
            description=response
        )

        embed.set_thumbnail(
            url="https://i.insider.com/5ea18a43a2fd914dad7b2073?width=1100&format=jpeg&auto=webp"
        )

        await message.channel.send(embed=embed)
        return


client.run(TOKEN)
