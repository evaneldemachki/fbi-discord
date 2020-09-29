import os
import discord
from dotenv import load_dotenv
import mongo
import re
import random
import json
from json import JSONEncoder
import datetime as dt


def encode_limits(obj):
    obj2 = {}
    for key in obj:
        obj2[key] = obj[key].isoformat()

    return obj2

# custom Decoder
def DecodeDateTime(empDict):
    for key in empDict:
      empDict[key] = dt.datetime.fromisoformat(empDict[key])

    return empDict

with open("triggers.json", "r") as f:
    triggers = json.load(f)

with open("opinions.json", "r") as f:
    opinions = json.load(f)

with open("limits.json", "r") as f:
    limits = json.load(f, object_hook=DecodeDateTime)

with open("porn.json", "r") as f:
    pornstars = json.load(f)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = discord.Client()
_rate_limit = True

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    global _rate_limit
    print(message.content)
    if message.author == client.user:
        return

    if message.content.rstrip() == '/mongo':
        response = """Available arguments [ /mongo <arg> ]:
            users: prints list of all usernames stored in cloud"""
        await message.channel.send(response)
        return

    if message.content.rstrip() == '/mongo users':
        response = ""
        users = mongo.users()
        for i in range(len(users)):
            username = users[i]
            response += "{0}. {1}\n".format(i, username)

        await message.channel.send(response)
        return

    if message.content.rstrip() == '/butterbot':
        response = """Available arguments [ /butterbot <args> ]:
            purpose: asks ButterBot its purpose to torment it
            opinion: asks Butterbot for a random opinion
            add opinion <opinion>: implant your propaganda in ButterBot's brain
            add trigger <word> | <suggestion>: add trigger words to ButterBot along with an associated suggestion"""

        await message.channel.send(response)
        return

    if message.content.rstrip() == '/butterbot purpose':
        response = "I pass butter..."
        await message.channel.send(response)
        return

    if message.content.rstrip() == '/butterbot opinion':
        response = random.choice(opinions)
        await message.channel.send(response)
        return

    add_op = '/butterbot add opinion'
    if message.content[:len(add_op)] == add_op:
        if str(message.author) in limits.keys() and _rate_limit:
            lim = limits[str(message.author)] - dt.datetime.now()
            if lim.seconds > 0 and lim.days == 0:
                # limit in hours
                lim = lim.seconds / 3600
                hours, minutes = str(lim).split(".")
                hours = int(hours)
                minutes = round(float("0." + minutes) * 60)
                response = "ERROR: Rate limit for user '{0}' ends in {1} hour(s), {2} minute(s)..."
                response = response.format(str(message.author), hours, minutes)
                await message.channel.send(response)
                return

            
        new_opinion =  message.content[len(add_op):].strip()
        if len(new_opinion) < 100:
            opinions.append(new_opinion)
            with open("opinions.json", "w") as f:
                json.dump(opinions, f)
            
            response = "Added opinion: '{0}'".format(new_opinion)
            limits[str(message.author)] = dt.datetime.now() + dt.timedelta(hours=2)

            with open("limits.json", "w") as f:
                json.dump(encode_limits(limits), f)

            await message.channel.send(response)
            return
        else:
            response = "ERROR: opinion too long (must be < 100 characters)"
            await message.channel.send(response)
            return


    add_trig = '/butterbot add trigger'
    if message.content[:len(add_trig)] == add_trig:
        # THIS IS STANDARD: -> modularize
        if str(message.author) in limits.keys() and _rate_limit:
            lim = limits[str(message.author)] - dt.datetime.now()
            if lim.seconds > 0:
                # limit in hours
                lim = lim.seconds / 3600
                hours, minutes = str(lim).split(".")
                hours = int(hours)
                minutes = round(float("0." + minutes) * 60)
                response = "ERROR: Rate limit for user '{0}' ends in {1} hour(s), {2} minute(s)..."
                response = response.format(str(message.author), hours, minutes)
                await message.channel.send(response)
                return

            
        new_trigger =  message.content[len(add_trig):].strip()
        new_trigger, new_suggestion = new_trigger.split('|')
        new_trigger = new_trigger.strip()
        new_suggestion = new_suggestion.strip()
        if len(new_trigger) < 20 and len(new_suggestion) < 50:
            rep = True if new_trigger in triggers else False

            if any(type(val) != str for val in [new_trigger, new_suggestion]):
                response = "ERROR: too many parameters passed"
                await message.channel.send(response)
                return

            triggers[new_trigger] = new_suggestion
            with open("triggers.json", "w") as f:
                json.dump(triggers, f)
            
            if rep:
                response = "Replaced trigger: '{0}'".format(new_trigger)
            else:
                response = "Created new trigger: '{0}'".format(new_trigger)

            limits[str(message.author)] = dt.datetime.now() + dt.timedelta(hours=2)

            with open("limits.json", "w") as f:
                json.dump(encode_limits(limits), f)

            await message.channel.send(response)
            return
        else:
            response = "ERROR: trigger or suggestion too long (must be < 20 & <50 characters)"
            await message.channel.send(response)
            return
    
    if message.content == "/butterbot admin toggle:no-limit":
        if str(message.author).lower() != "chaostheory#9357":
            response = "ERROR: You do not have permission to run this command"
            await message.channel.send(response)
            return
        
        if _rate_limit:
            _rate_limit = False
        else:
            _rate_limit = True
        
        response = "Set no-limit to '{0}'".format(not _rate_limit)
        await message.channel.send(response)
        return        



    for term in triggers.keys():
        if re.search(r"\b" + term.lower() + r"\b", message.content.lower()):
            response = "*{0}*: Did you mean: **{1}**?".format(term, triggers[term])
            await message.channel.send(response)
            return
    
    if re.search(r"\b" + "fuck" + r"\b", message.content.lower()):
        pornstar = random.choice(pornstars)
        response = "***{0}** entered the chat...*".format(pornstar)
        await message.channel.send(response)
        return


client.run(TOKEN)