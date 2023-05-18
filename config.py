import json
import traceback
import datetime
import sqlite3
from discord import TextChannel, ChannelType, Embed, Role, Member,  Message, User, SelectOption, Interaction, PartialEmoji, PermissionOverwrite
import discord
from discord.ext.commands import Cog, Context, group, hybrid_command, hybrid_group, command, AutoShardedBot as AB
from discord.ui import Select, View, Button
from typing import Union
from tools.checks import Perms as utils, Boosts
from tools.utils import EmbedBuilder, InvokeClass
from tools.utils import EmbedScript
from discord.ext import commands
from discord.utils import find

class config(Cog):
    def __init__(self, bot: AB):
        self.bot = bot
        self.db = sqlite3.connect("mediaonly.db")
        self.db.execute(
            'CREATE TABLE IF NOT EXISTS mediaonly (guild_id INTEGER, channel_id INTEGER)')
        self.conn = sqlite3.connect('fake_permissions.db')
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS fake_permissions 
                    (guild_id INTEGER, role_id INTEGER, permissions TEXT, PRIMARY KEY (guild_id, role_id))''')
        self.conn.commit()

        


    async def is_mediaonly(self, channel_id, guild_id):
        check = self.db.execute(
            "SELECT * FROM mediaonly WHERE guild_id = ? AND channel_id = ?", (guild_id, channel_id)).fetchone()
        return check is not None

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if isinstance(message.author, User):
            return
        if message.author.guild_permissions.manage_guild:
            return
        if message.author.bot:
            return
        if message.attachments:
            return
        if await self.is_mediaonly(message.channel.id, message.guild.id):
            try:
                await message.delete()
            except:
                pass

    @group(invoke_without_command=True)
    async def mediaonly(self, ctx: Context):
        await ctx.create_pages()

    @mediaonly.command(name="add", description="delete messages that are not images", help="config", usage="[channel]", brief="manage_guild")
    @utils.get_perms("manage_guild")
    async def mediaonly_add(self, ctx: Context, *, channel: TextChannel):
        check = await self.db.fetchrow("SELECT * FROM mediaonly WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if check is not None:
            return await ctx.send(f"{channel.mention} is already added")
        elif check is None:
            await self.db.execute("INSERT INTO mediaonly VALUES ($1,$2)", ctx.guild.id, channel.id)
            return await ctx.send(f"added {channel.mention} as a mediaonly channel")

    @mediaonly.command(name="remove", description="unset media only", help="config", usage="[channel]", brief="manage_guild")
    @utils.get_perms("manage_guild")
    async def mediaonly_remove(self, ctx: Context, *, channel: TextChannel = None):
        if channel is not None:
            check = await self.db.fetchrow("SELECT * FROM mediaonly WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
            if check is None:
                return await ctx.send(f"{channel.mention} is not added")
            await self.db.execute("DELETE FROM mediaonly WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
            return await ctx.send(f"{channel.mention} isn't a **mediaonly** channel anymore")

        res = await self.db.fetch("SELECT * FROM mediaonly WHERE guild_id = $1", ctx.guild.id)
        if res is None:
            return await ctx.send("There is no **mediaonly** channel in this server")
        await self.db.execute("DELETE FROM mediaonly WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send("Removed all channels")

    @mediaonly.command(name="list", description="return a list of mediaonly channels", help="config")
    async def mediaonly_list(self, ctx: Context):
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        results = await self.db.execute("SELECT * FROM mediaonly WHERE guild_id = ?", (ctx.guild.id,))
        rows = results.fetchall()
        if len(rows) == 0:
            return await ctx.reply("there are no mediaonly channels")
        for result in rows:
            mes = f"{mes}`{k}` <#{result[1]}> ({result[1]})\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(Embed(
                    color=self.bot.color, title=f"mediaonly channels ({len(rows)})", description=messages[i]))
                i += 1
                mes = ""
                l = 0
        messages.append(mes)
        number.append(Embed(color=self.bot.color,
                      title=f"mediaonly channels ({len(rows)})", description=messages[i]))
        if len(number) > 1:
            return await ctx.paginator(number)
        return await ctx.send(embed=number[0])
    
    @group(invoke_without_command=True)
    async def prefix(self, ctx: Context):
        await ctx.create_pages()

    @hybrid_command(description="changes the guild prefix", usage="[prefix]", help="config", brief="manage guild")
    async def prefix(self, ctx: Context, prefix: str):
        if len(prefix) > 3:
            return await ctx.send("Uh oh! The prefix is too long")

        conn = sqlite3.connect('prefixes.db')
        c = conn.cursor()

        check = c.execute(
            "SELECT * FROM prefixes WHERE guild_id = ?", (ctx.guild.id,)).fetchone()
        if check is not None:
            c.execute("UPDATE prefixes SET prefix = ? WHERE guild_id = ?",
                      (prefix, ctx.guild.id))
        else:
            c.execute("INSERT INTO prefixes VALUES (?, ?)",
                      (ctx.guild.id, prefix))
        conn.commit()
        conn.close()

        return await ctx.send(f"guild prefix changed to `{prefix}`".capitalize())
    
    @group(invoke_without_command=True)
    async def selfprefix(self, ctx: Context):
        await ctx.create_pages()

    @hybrid_command(description="set your own prefix", usage="[prefix]", help="config")
    async def selfprefix(self, ctx: Context, prefix: str):
        if len(prefix) > 3 and prefix.lower() != "none":
            return await ctx.send("Uh oh! The prefix is too long")

        conn = sqlite3.connect('prefixes.db')
        c = conn.cursor()

        if prefix.lower() == "none":
            check = c.execute(
                "SELECT * FROM selfprefix WHERE user_id = ?", (ctx.author.id,)).fetchone()
            if check is not None:
                c.execute("DELETE FROM selfprefix WHERE user_id = ?",
                          (ctx.author.id,))
                conn.commit()
                conn.close()
                return await ctx.send("Removed your self prefix")
            elif check is None:
                conn.close()
                return await ctx.send("you don't have a self prefix".capitalize())
        else:
            result = c.execute(
                "SELECT * FROM selfprefix WHERE user_id = ?", (ctx.author.id,)).fetchone()
            if result is not None:
                c.execute(
                    "UPDATE selfprefix SET prefix = ? WHERE user_id = ?", (prefix, ctx.author.id))
            elif result is None:
                c.execute("INSERT INTO selfprefix VALUES (?, ?)",
                          (ctx.author.id, prefix))
            conn.commit()
            conn.close()
            return await ctx.send(f"self prefix changed to `{prefix}`".capitalize())
        
    @commands.group(invoke_without_command=True, aliases=["fakeperms"])
    async def fakepermissions(self, ctx):
        await ctx.create_pages()

    @fakepermissions.command(description="edit fake permissions for a role", help="config", usage="[role]", brief="server owner")
    @utils.server_owner()
    async def edit(self, ctx: Context, *, role: Union[Role, str]=None):
        if isinstance(role, str):
            role = find(lambda r: r.name.lower() == role.lower(), ctx.guild.roles)
            if role is None:
                return await ctx.send("This is not a valid role")

        perms = ["administrator", "manage_guild", "manage_roles", "manage_channels", "manage_messages", "manage_nicknames", "manage_emojis", "ban_members", "kick_members", "moderate_members"]
        options = [SelectOption(label=perm.replace("_", " "), value=perm) for perm in perms]
        embed = Embed(color=self.bot.color, description="🔍 Which permissions would you like to add to {}?".format(role.mention))
        select = Select(placeholder="select permissions", max_values=10, options=options)

        async def select_callback(interaction: Interaction):
            if ctx.author != interaction.user:
                return await self.bot.ext.send(interaction, "This is not your embed", ephemeral=True)
            data = json.dumps(select.values)
            check = self.conn.execute("SELECT permissions FROM fake_permissions WHERE guild_id = ? AND role_id = ?", (interaction.guild.id, role.id)).fetchone()
            if not check:
                self.conn.execute("INSERT INTO fake_permissions VALUES (?,?,?)", (interaction.guild.id, role.id, data))
            else:
                self.conn.execute("UPDATE fake_permissions SET permissions = ? WHERE guild_id = ? AND role_id = ?", (data, interaction.guild.id, role.id))
            self.conn.commit()
            await interaction.response.edit_message(embed=Embed(color=self.bot.color, description=f"{self.bot.yes} {interaction.user.mention}: Added **{len(select.values)}** permission{'s' if len(select.values) > 1 else ''} to {role.mention}"), view=None)

        select.callback = select_callback
        view = View()
        view.add_item(select)
        await ctx.reply(embed=embed, view=view)

    @fakepermissions.command(name="list", description="list the permissions of a specific role", help="config", usage="[role]")
    async def fakeperms_list(self, ctx: Context, *, role: Union[Role, str]): 
        if isinstance(role, str): 
            role = ctx.find_role(role)
            if role is None: return await ctx.send("This is not a valid role") 
        
        async with self.conn.execute("SELECT permissions FROM fake_permissions WHERE guild_id = ? AND role_id = ?", (ctx.guild.id, role.id)) as cursor:
            check = await cursor.fetchone()
        if check is None: return await ctx.send("This role has no fake permissions")
        permissions = json.loads(check['permissions'])
        embed = Embed(color=self.bot.color, title=f"@{role.name}'s fake permissions", description="\n".join([f"`{permissions.index(perm)+1}` {perm}" for perm in permissions]))
        embed.set_thumbnail(url=role.display_icon)
        return await ctx.reply(embed=embed)
    
    @commands.group(invoke_without_command=True) 
    async def autopfp(self, ctx):
       await ctx.create_pages()


    @autopfp.command(name="clear", description="clear the whole autopfp module", help="config", brief="manage server")
    async def autopfp_clear(self, ctx: Context): 
        conn = sqlite3.connect('Toughs.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM autopfp WHERE guild_id = ?", (ctx.guild.id,))
        check = cursor.fetchone()
        if not check:
            await ctx.send("Autopfp module is **not** configured")
            conn.close()
            return
        embed = Embed(color=self.bot.color, description="Are you sure you want to clear the autopfps module?")
        yes = Button(emoji=self.bot.yes)
        no = Button(emoji=self.bot.no)

        async def yes_callback(interaction: Interaction): 
            if interaction.user.id != ctx.author.id:
                await self.bot.ext.send(interaction, "You are not the **author** of this embed", ephemeral=True)                                      
                conn.close()
                return
            cursor.execute("DELETE FROM autopfp WHERE guild_id = ?", (ctx.guild.id,))
            conn.commit()
            conn.close()
            await interaction.response.edit_message(embed=Embed(color=self.bot.color, description="Autopfp module cleared"), view=None)

    
    @autopfp.command(name="add", description="add the autopfp module", help="config", usage="[channel] [genre] [type]\nexample: autopfp add #boys male pfp", brief="manage guild")
    async def autopfp_add(self, ctx: Context, channel: TextChannel, genre: str, typ: str="none"):
        self.conn = sqlite3.connect('Toughs.db')
        self.cursor = self.conn.cursor()
        try:
            if genre in ["female", "male", "anime"]:
                if typ in ["pfp", "gif"]:
                    check = self.cursor.execute("SELECT * FROM autopfp WHERE guild_id = ? AND genre = ? AND type = ?", (ctx.guild.id, genre, typ)).fetchone()
                    if check is not None:
                        return await ctx.send(f"A channel is already **configured** for {genre} {typ}s")
                    self.cursor.execute("INSERT INTO autopfp (guild_id, channel_id, genre, type) VALUES (?, ?, ?, ?)", (ctx.guild.id, channel.id, genre, typ))
                    self.conn.commit()
                    return await ctx.send(f"Configured {channel.mention} as {genre} {typ}s")
                else:
                    return await ctx.send("The **type** passed wasn't one of the following: pfp, gif")
            elif genre in ["random", "banner"]:
                check = self.cursor.execute("SELECT * FROM autopfp WHERE channel_id = ? AND guild_id = ? AND genre = ?", (channel.id, ctx.guild.id, genre)).fetchone()
                if check is not None:
                    return await ctx.send(f"A channel is already **configured** for {genre}")
                self.cursor.execute("INSERT INTO autopfp (guild_id, channel_id, genre, type) VALUES (?, ?, ?, ?)", (ctx.guild.id, channel.id, genre, typ))
                self.conn.commit()
                return await ctx.send(f"Configured {channel.mention} as {genre} pictures")
            else:
                return await ctx.send("The **genre** passed wasn't one of the following: male, female, anime, banner, random")
        except:
            traceback.print_exc()
    

    @autopfp.command(name="remove", description="remove the autopfp module", help="config", usage="[genre] [type]\nexample: autopfp remove male gif", brief="manage guild")
    async def autopfp_remove(self, ctx: Context, genre: str, typ: str="none"):
        conn = sqlite3.connect('Toughs.db')
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM autopfp WHERE guild_id = ? AND genre = ? AND type = ?", (ctx.guild.id, genre, typ))
            check = cursor.fetchone()
            if check is None:
                return await ctx.send(f"No autopfp channel found for **{genre} {typ if typ != 'none' else ''}**")
            cursor.execute("DELETE FROM autopfp WHERE guild_id = ? AND genre = ? AND type = ?", (ctx.guild.id, genre, typ))
            conn.commit()
            await ctx.send(f"Removed **{genre} {typ if typ != 'none' else ''}** posting")
        except:
            traceback.print_exc()

    @commands.group(invoke_without_command=True)
    async def embed(self, ctx): 
        await ctx.create_pages() 
  
    @embed.command(help="config", description="shows variables for the embed")
    async def variables(self, ctx: Context): 
     embed1 = Embed(color=self.bot.color, title="user related variables")
     embed1.description = """
    >>> {user} - returns user full name
{user.name} - returns user's username
{user.mention} - mentions user
{user.avatar} - return user's avatar
{user.joined_at} returns the relative date the user joined the server
{user.created_at} returns the relative time the user created the account
{user.discriminator} - returns the user's discriminator
    """

     embed2 = Embed(color=self.bot.color, title="guild related variables")
     embed2.description = """
    >>> {guild.name} - returns the server's name
 {guild.count} - returns the server's member count
 {guild.count.format} - returns the server's member count in ordinal format
 {guild.icon} - returns the server's icon
 {guild.id} - returns the server's id
 {guild.vanity} - returns the server's vanity, if any 
 {guild.created_at} - returns the relative time the server was created
 {guild.boost_count} - returns the number of server's boosts
 {guild.booster_count} - returns the number of boosters
 {guild.boost_count.format} - returns the number of boosts in ordinal format
 {guild.booster_count.format} - returns the number of boosters in ordinal format
 {guild.boost_tier} - returns the server's boost level
   """
    
     embed3 = Embed(color=self.bot.color, title="invoke command only variables")
     embed3.description = """
    >>> {member} - returns member's name and discriminator
    {member.name} - returns member's name
    {member.mention} - returns member mention
    {member.discriminator} - returns member's discriminator
    {member.id} - return member's id
    {member.avatar} - returns member's avatar
    {reason} - returns action reason, if any
    """
     
     embed4 = Embed(color=self.bot.color, title="last.fm variables")
     embed4.description = """
    >>> {scrobbles} - returns all song play count
    {trackplays} - returns the track total plays
    {artistplays} - returns the artist total plays
    {albumplays} - returns the album total plays
    {track} - returns the track name
    {trackurl} - returns the track url
    {trackimage} - returns the track image
    {artist} - returns the artist name
    {artisturl} - returns the artist profile url
    {album} - returns the album name 
    {albumurl} - returns the album url
    {username} - returns your username
    {useravatar} - returns user's profile picture"""
     
     embed6 = Embed(color=self.bot.color, title="vanity variables")
     embed6.description = """
     >>> {vanityrole.name} - returns the vanity role name\n{vanityrole.mention} - returns the mention of the vanity role\n{vanityrole.id} - returns the id of the vanity role\n{vanityrole.members} - returns the number of members who have the vanity role\n{vanityrole.members.format} - returns the number of members who have the vanity role in ordinal"""

     embed5 = Embed(color=self.bot.color, title="other variables")
     embed5.description = """
    >>> {invisible} - returns the invisible embed color
    {delete} - delete the trigger (for autoresponder)"""

     await ctx.paginator([embed1, embed2, embed3, embed4, embed6, embed5])
    





async def setup(bot):
    await bot.add_cog(config(bot))
