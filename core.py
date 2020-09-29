import os
import random
import discord
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
    
    if message.content.rstrip() == "!choi":
        if str(message.author) != "WarrenYC#3813" and str(message.author) != "chaostheory#9357":
            response = "Error: Access Denied"
            await message.channel.send(response)
            return

        members = []
        async for member in message.guild.fetch_members():
            if member != client.user and str(member) != "WarrenYC#3813" and not member.bot:
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
            await message.channel.send(response)
            return


client.run(TOKEN)
