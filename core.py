import os
import random
import discord
from discord import Embed
from discord.ext.commands import Bot
import sqlite3
import re
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

conn = sqlite3.connect('core.db')
c = conn.cursor()
# Create table
c.execute('''CREATE TABLE IF NOT EXISTS trump
             (quote text)''')

conn.commit()

MODS = ["WarrenYC#3813", "chaostheory#9357"]

client = discord.Client()

async def unmute(channel, member, role):
    await asyncio.sleep(60)
    await member.remove_roles(role)
    await channel.send("{0} is no longer choi'd".format(member.mention))

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.split(' ')[0] == "!mute":
        if str(message.author) not in MODS:
            response = "**Think-You're-Clever Error**: Who the bloody hell do you think you are?"
            await message.channel.send(response)
            return
        
        if len(message.mentions) == 0:
            response = "**Dumb-As-Rocks Error**: Oy! You thick in the skull, kid?"

        role = None
        for entry in message.guild.roles:
            if entry.name == "Muted":
                role = entry
                break

        members = []
        for member in message.mentions:
            if str(member) not in MODS and member != client.user:
                await member.add_roles(role)
                members.append(member)
        
        if len(members) == 0:
            return
        
        members = [mem.mention for mem in members]
        response = "Right, then. I muted the following assholes: {0}"
        response = response.format(", ".join(members))
        await message.channel.send(response)

    if message.content.split(' ')[0] == "!unmute":
        if str(message.author) not in MODS:
            response = "**Think-You're-Clever Error**: Who the bloody hell do you think you are?"
            await message.channel.send(response)
            return
        
        if len(message.mentions) == 0:
            response = "**Dumb-As-Rocks Error**: Oy! You thick in the skull, kid?"

        role = None
        for entry in message.guild.roles:
            if entry.name == "Muted":
                role = entry
                break

        members = []
        for member in message.mentions:
            if str(member) not in MODS and member != client.user and member in role.members:
                await member.remove_roles(role)
                members.append(member)
        
        if len(members) == 0:
            return
        
        members = [mem.mention for mem in members]
        response = "Yeah alright mate, whatever. Unmuted: {0}"
        response = response.format(", ".join(members))
        await message.channel.send(response)
    
    if message.content.rstrip() == "!muted":
        role = None
        for entry in message.guild.roles:
            if entry.name == "Muted":
                role = entry
                break
        
        members = [mem.mention for mem in role.members]
        if len(members) == 0:
            return
        
        members = ", ".join(members)
        response = "Dickheads: {0}".format(members)
        await message.channel.send(response)
    
    if message.content.rstrip() == "!choi":
        if str(message.author) not in MODS:
            response = "**Think-You're-Clever Error**: Who the bloody hell do you think you are?"
            await message.channel.send(response)
            return

        members = []
        async for member in message.guild.fetch_members():
            if member != client.user and str(member) not in MODS and not member.bot:
                members.append(member)

        role = None
        for entry in message.guild.roles:
            if entry.name == "Muted":
                role = entry
                break

        member = random.choice(members)
        await member.add_roles(role)

        response = member.mention + " has been choi'd!"
        await message.channel.send(response)

        await unmute(message.channel, member, role)
        
    if re.search(r"\b" + 'trump' + r"\b", message.content.lower()):
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
