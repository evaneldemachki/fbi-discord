def initialize(conn, c):
    c.execute('''
    create table if not exists trump (quote text null)
    ''')
    c.execute('''
    create table if not exists members (
        guild_id bigint null,
        user_id bigint null,
        infractions int null,
        xp bigint null,
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

class Routes:
    def __init__(self, conn, cursor):
        self.conn = conn
        self.c = cursor

        initialize(conn, cursor)
    
    def insert_new_user(self, member):
        query = """
            INSERT INTO members (guild_id, user_id, xp, infractions)
            VALUES({0}, {1}, {2}, {3})
            ON CONFLICT DO NOTHING
        """.format(member.guild.id, member.id, 0, 0)

        self.c.execute(query)
        self.conn.commit()
    
    def insert_new_channel(self, channel):
        query = """
            INSERT INTO channels (guild_id, channel_id, owner_id)
            VALUES({0}, {1}, NULL)
            ON CONFLICT DO NOTHING
        """.format(channel.guild.id, channel.id)

        self.c.execute(query)
        self.conn.commit()

    def members(self, guild):
        query = """
            SELECT * FROM members WHERE guild_id = {0}
        """.format(guild.id)

        self.c.execute(query)
        members = self.c.fetchall()

        return members    
    
    def member_ids(self, guild):
        query = """
            SELECT user_id FROM members WHERE guild_id = {0}
        """.format(guild.id)

        self.c.execute(query)
        member_ids = self.c.fetchall()
        member_ids = [mid[0] for mid in member_ids]
        print(member_ids)
        return member_ids
    
    def channel_ids(self, guild):
        query = """
            SELECT channel_id FROM channels WHERE guild_id = {0}
        """.format(guild.id)    

        self.c.execute(query)
        channel_ids = self.c.fetchall()
        channel_ids = [cid[0] for cid in channel_ids]
        print(channel_ids)
        return channel_ids    

    def get_member(self, member):
        query = """SELECT * from MEMBERS where (USER_ID = {0} and GUILD_ID = {1})"""
        query = query.format(member.id, member.guild.id)

        self.c.execute(query)
        member_data = self.c.fetchone()

        return member_data
    
    def get_channel(self, channel):
        query = """SELECT * from CHANNELS where (CHANNEL_ID = {0} and GUILD_ID = {1})"""
        query = query.format(channel.id, channel.guild.id)

        self.c.execute(query)
        channel_data = self.c.fetchone()
        print(channel_data)
        return channel_data      
    
    def member_channels(self, member):
        query = """SELECT channel_id from CHANNELS where (OWNER_ID = {0} and GUILD_ID = {1})"""
        query = query.format(member.id, member.guild.id)

        self.c.execute(query)
        member_channels = self.c.fetchall()
        member_channels = [mc[0] for mc in member_channels]
        
        return member_channels
    
    def remove_channel(self, guild, channel_id):
        query = "DELETE FROM channels WHERE (CHANNEL_ID = {1} and GUILD_ID = {1})"
        query = query.format(channel_id, guild.id)     

        self.c.execute(query)
        self.conn.commit()
    
    def set_channel_owner(self, channel, member):
        query = """
            UPDATE channels SET owner_id = {0} WHERE (guild_id = {1} and channel_id = {2})"""
        
        query = query.format(member.id, channel.guild.id, channel.id)

        self.c.execute(query)
        self.conn.commit()

    def remove_channel_owner(self, channel):
        query = """
            UPDATE channels SET owner_id = NULL WHERE (guild_id = {0} and channel_id = {1})"""
        
        query = query.format(channel.guild.id, channel.id)

        self.c.execute(query)
        self.conn.commit()