import os
import random
import json
import discord
from discord import Embed
from discord.ext.commands import Bot
import sqlite3
import re
import asyncio
from dotenv import load_dotenv
import datetime as dt
import pprint

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

conn = sqlite3.connect('core.db')
c = conn.cursor()
# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS trump
             (quote text)''')
c.execute('''CREATE TABLE IF NOT EXISTS members
             (username TEXT UNIQUE, channels TEXT, infractions INTEGER)''')

conn.commit()

GUILDS = {}
COLORS = {
    "mod-negative": 15746887, # red
    "mod-positive": 4437377,  # green
    "mod-neutral": 7506394,   # blue
    "profile-card": 15105570  # orange
}
IGNORE = ["@everyone", "Muted"]

client = discord.Client()

async def unmute(channel, member, role):
    await asyncio.sleep(60)
    await member.remove_roles(role)
    await channel.send("{0} is no longer choi'd".format(member.mention))

def is_moderator(guild, member):
    mod_role = GUILDS[guild]["roles"]["moderator"]
    if member.top_role >= mod_role or member == client.user:
        return True
    
    return False

def is_muted(guild, member):
    muted_role = GUILDS[guild]["roles"]["muted"]
    if muted_role in member.roles:
        return True
    
    return False
    

@client.event
async def on_ready():
    global GUILDS

    for guild in client.guilds:
        mod_role = muted_role = None

        for role in await guild.fetch_roles():
            if str(role) == "Moderator":
                mod_role = role
            elif str(role) == "Muted":
                muted_role = role
            else:
                continue

            if mod_role is not None and muted_role is not None:
                break

        if mod_role is None or muted_role is None:
            raise KeyError("Guild '{0}' not configured".format(str(guild)))

        GUILDS[guild] = {
            "roles": {
                "moderator": mod_role,
                "muted": muted_role
            }
        }

        async for member in guild.fetch_members():
            # change to execute_many with ? syntax
            c.execute("""
                INSERT OR IGNORE INTO members(username, channels, infractions)
                VALUES('{0}', '{1}', {2})
            """.format(str(member), "[]", 0))
        
        conn.commit()
            
    print(f'{client.user} has connected to Discord!')
    print(GUILDS)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.split(' ')[0] == "!mute":
        if not is_moderator(message.guild, message.author):
            response = "**Error**: permission denied.".format(member.mention)
            return await message.channel.send(response)

        members = []
        for member in message.mentions:
            if is_moderator(message.guild, member):
                response = "**Error: cannot perform action 'unmute' on user {0}.**".format(member.mention)
                return await message.channel.send(response)
                members.append(member)
            else:
                if is_muted(message.guild, member):
                    response = "**Error: user '{0}' is already muted.**".format(member.mention)
                    return await message.channel.send(response)

                members.append(member)
        
        if len(members) == 0:
            response = "**Error: no users specified.**"
            return await message.channel.send(response)
        
        muted_role = GUILDS[message.guild]["roles"]["muted"]
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
            if is_moderator(message.guild, member):
                response = "**Error: cannot perform action 'unmute' on user {0}.**".format(member.mention)
                return await message.channel.send(response)
            else:
                if not is_muted(message.guild, member):
                    response = "**Error: user {0} is not muted.**".format(member.mention)
                    return await message.channel.send(response)

                members.append(member)
        
        if len(members) == 0:
            response = "**Error: no users specified.**"
            return await message.channel.send(response)
        
        muted_role = GUILDS[message.guild]["roles"]["muted"]
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
        
        embed = Embed(
            title=member.nick,
            color=COLORS["profile-card"], timestamp=dt.datetime.now()
        ).set_thumbnail(url=member.avatar_url).set_author(name=member)

        embed.add_field(name="Joined", value=member.joined_at)

        c.execute("SELECT * FROM members WHERE username='{0}'".format(str(member)))
        # TODO: handle not exists
        member_data = c.fetchone()

        channels = []
        channel_ids = json.loads(member_data[1])
        for ch in channel_ids:
            channels.append("  -  {0}".format(message.guild.get_channel(ch).mention))

        if len(channels) != 0:
            channels = "\n".join(channels)
        else:
            channels = "*No channels yet*"
        
        embed.add_field(name="Channels", value=channels)

        infractions = member_data[2]

        roles = []
        for role in member.roles:
            if str(role) not in IGNORE:
                roles.append("  -  {0}".format(role.mention))

        roles = "\n".join(reversed(roles))
        embed.add_field(name="Roles", value=roles)

        return await message.channel.send(embed=embed)
        
                     

    if message.content.split(' ')[0] == "!choi":
        if not message.content.rstrip() == "!choi":
            response = "**Error: !choi does not take arguments**"
            return await message.channel.send(response)

        if not is_moderator(message.guild, message.author):
            response = "**Error: permission denied.**".format(member.mention)
            return await message.channel.send(response)

        members = []
        async for member in message.guild.fetch_members():
            if not is_moderator(message.guild, member):
                members.append(member)

        role = GUILDS[message.guild]["roles"]["muted"]
        member = random.choice(members)
        await member.add_roles(role)

        response = member.mention + " has been choi'd!"
        await message.channel.send(response)

        await unmute(message.channel, member, role)
        
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
