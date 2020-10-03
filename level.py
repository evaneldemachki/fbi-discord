import asyncio

rank_index = {
    
}

# TODO: make into class

def register_message(conn, c, message):
    member = message.author
    guild = message.guild

    query = "UPDATE members SET xp = xp + 1 WHERE user_id = {0} and guild_id = {1}"
    query = query.format(member.id, guild.id)

    c.execute(query)
    conn.commit()

    query = "SELECT xp FROM "


# TODO: count all messages from history to create rank_index