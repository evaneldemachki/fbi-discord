import asyncio
import datetime as dt
from discord import Embed
from collections import OrderedDict

def rank_gen(factor):
    x = [0]
    c = 50
    for i in range(0, 19):
        x.append(x[i] + c)
        c = c * factor

    x = [round(j) for j in x]
    return x

def level_pos(xp):
    pos = None
    for i in range(len(RANKS)):
        if xp >= RANKS[i]:
            pos = i
    
    return pos

RANKS = rank_gen(1.5)
print("RANKS")
print(RANKS)

class Leveler:
    def __init__(self, conn, c, CACHE):
        self.conn = conn
        self.c = c
        self.CACHE = CACHE
    
    def get_level(self, guild, member):
        query = """SELECT XP from MEMBERS where (USER_ID = {0} and GUILD_ID = {1})"""
        query = query.format(member.id, guild.id)

        self.c.execute(query)
        xp = self.c.fetchone()[0]
        level = level_pos(xp) + 1

        return level
    
    #TODO: combine these functions
    def get_xp_range(self, guild, member):
        query = """select XP from MEMBERS where (USER_ID = {0} and GUILD_ID = {1})"""
        query = query.format(member.id, guild.id)

        self.c.execute(query)
        xp = self.c.fetchone()[0]
        pos = level_pos(xp+10) + 1
        next_xp = RANKS[pos]

        return xp, next_xp

    async def register_message(self, message):
        member = message.author
        guild = message.guild

        query = """select XP from MEMBERS where (USER_ID = {0} and GUILD_ID = {1})"""
        query = query.format(member.id, guild.id)

        self.c.execute(query)
        xp = self.c.fetchone()[0]
        pos = level_pos(xp) + 1

        promotion = None
        pos_plus = level_pos(xp+10) + 1
        if pos_plus > pos:
            promotion = pos_plus
        
        query = """update MEMBERS set XP = (XP + 10)
        where (USER_ID = {0} and GUILD_ID = {1})"""
        query = query.format(member.id, guild.id)

        self.c.execute(query)
        self.conn.commit()

        if promotion is not None:
            description = "**{0} has reached level {1}!**"
            description = description.format(member.mention, promotion)
            embed = Embed(
                title="Level Up!", 
                description=description, color=15105570, 
                timestamp=dt.datetime.now()
            )
            embed.set_author(name=member, icon_url=str(member.avatar_url))

            channel = self.CACHE[guild.id]["channels"]["feed"]
            await channel.send(embed=embed)

            if promotion not in [5, 10, 15, 20]:
                return

            # TODO: fix this mess
            ranks = OrderedDict(self.CACHE[guild.id]["ranks"])
            rank_up = None
            current_ranks = []
            rank_keys = list(ranks.keys())
            for i in range(len(rank_keys)):
                rank = ranks[rank_keys[i]]
                if promotion >= rank["level"]:
                    rank_up = rank
                    current_ranks.append(ranks[rank_keys[i-1]]["role"])

            await member.add_roles(rank_up["role"])
            await member.remove_roles(*current_ranks)

            description = "**{0} has reached rank {1}**"
            description = description.format(member.mention, rank_up["role"].mention)
            embed = Embed(
                title="Rank Up!", 
                description=description, color=15105570, 
                timestamp=dt.datetime.now()
            )
            embed.set_author(name=member, icon_url=str(member.avatar_url))

            channel = self.CACHE[guild.id]["channels"]["feed"]
            return await channel.send(embed=embed)