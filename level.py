import asyncio
import datetime as dt
from discord import Embed

def rank_gen(factor):
    x = [0]
    c = 10
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

class Leveler:
    def __init__(self, conn, c, GUILDS):
        self.conn = conn
        self.c = c
        self.GUILDS = GUILDS
    
    def get_level(self, guild, member):
        query = "SELECT xp FROM members WHERE user_id = {0} and guild_id = {1}"
        query = query.format(member.id, guild.id)

        xp = self.c.execute(query).fetchone()[0]
        level = level_pos(xp) + 1

        return level
    
    #TODO: combine these functions
    def get_xp_range(self, guild, member):
        query = "SELECT xp FROM members WHERE user_id = {0} and guild_id = {1}"
        query = query.format(member.id, guild.id)

        xp = self.c.execute(query).fetchone()[0]
        pos = level_pos(xp+10) + 1
        next_xp = RANKS[pos]

        return xp, next_xp

    async def register_message(self, message):
        member = message.author
        guild = message.guild

        query = "SELECT xp FROM members WHERE user_id = {0} and guild_id = {1}"
        query = query.format(member.id, guild.id)

        xp = self.c.execute(query).fetchone()[0]
        pos = level_pos(xp)
        promotion = None
        pos_plus = level_pos(xp+10)
        if pos_plus > pos:
            promotion = pos_plus + 1
        
        query = "UPDATE members SET xp = xp + 10 WHERE user_id = {0} and guild_id = {1}"
        query = query.format(member.id, guild.id)

        self.c.execute(query)
        self.conn.commit()

        if promotion is not None:
            description = "**{0} has reached level {1}!**"
            description = description.format(member.mention, pos_plus)
            embed = Embed(
                title="Level Up!", 
                description=description, color=15105570, 
                timestamp=dt.datetime.now()
            )
            embed.set_author(name=member, icon_url=str(member.avatar_url))

            channel = self.GUILDS[guild]["channels"]["general"]
            await channel.send(embed=embed)

            rank_up = None
            current_ranks = []
            rank_keys = list(self.GUILDS[guild]["ranks"].keys())
            for i in range(len(rank_keys)):
                rank = self.GUILDS[guild]["ranks"][rank_keys[i]]
                if promotion >= rank["level"]:
                    rank_up = rank
                    current_ranks.append(self.GUILDS[guild]["ranks"][rank_keys[i-1]]["role"])
            
            if rank_up is None:
                return

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

            channel = self.GUILDS[guild]["channels"]["general"]
            return await channel.send(embed=embed)


# TODO: count all messages from history to create rank_index