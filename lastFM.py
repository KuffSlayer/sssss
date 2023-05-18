import sqlite3
import discord
import json
import typing
import handlers.userhandler as userhandler
import traceback
from discord.ext import commands, tasks
from tools.utils import EmbedBuilder
from handlers.lastfmhandler import Handler


def sort_key(lis):
    return lis[1]





async def lf_add_reactions(ctx: commands.Context, message: typing.Union[discord.Message, None]): 
    if message is None:
        return 
    conn = sqlite3.connect('Tough.db')
    c = conn.cursor()
    check = c.execute("SELECT * FROM lfreactions WHERE user_id = ?", (ctx.author.id,)).fetchone() 
    if not check: 
        for i in ["🔥", "🗑️"]:
            await message.add_reaction(i)
        conn.close()
        return 
    reactions = json.loads(check[1])
    if reactions[0] == "none": 
        conn.close()
        return
    for r in reactions: 
        await message.add_reaction(r)
    conn.close()
    return

async def lastfm_message(ctx: commands.Context, content: str) -> discord.Message:
    return await ctx.reply(embed=discord.Embed(color=0xff0000, description=f"> <:lastfm:1103725112458489957> {ctx.author.mention}: {content}"))

@tasks.loop(hours=1)
async def clear_caches(bot: commands.AutoShardedBot):
    lol = LastFM(bot)
    lol.globalwhoknows_cache = []
    lol.lastfm_crowns = []


class LastFM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("Toughs.db")
        self.cursor = self.db.cursor()

        self.lastfmhandler = Handler("43693facbb24d1ac893a7d33846b15cc")
        self.lastfm_crowns = {}
        self.globalwhoknows_cache = {}

    async def lastfm_replacement(self, user: str, params: str) -> str:
        a = await self.lastfmhandler.get_tracks_recent(user, 1)
        userinfo = await self.lastfmhandler.get_user_info(user)
        userpfp = userinfo["user"]["image"][2]["#text"]
        artist = a['recenttracks']['track'][0]['artist']['#text']
        albumplays = await self.lastfmhandler.get_album_playcount(user, a['recenttracks']['track'][0]) or "N/A"
        artistplays = await self.lastfmhandler.get_artist_playcount(user, artist)
        trackplays = await self.lastfmhandler.get_track_playcount(user, a['recenttracks']['track'][0]) or "N/A"
        album = a["recenttracks"]['track'][0]['album']['#text'].replace(" ", "+") or "N/A"
        params = params.replace('{track}', a['recenttracks']['track'][0]['name']).replace('{trackurl}', a['recenttracks']['track'][0]['url']).replace('{artist}', a['recenttracks']['track'][0]['artist']['#text']).replace('{artisturl}', f"https://last.fm/music/{artist.replace(' ', '+')}").replace('{trackimage}', str((a['recenttracks']['track'][0])['image'][3]['#text']).replace('{https', "https")).replace('{artistplays}', str(artistplays)).replace('{albumplays}', str(albumplays)).replace('{trackplays}', str(trackplays)).replace('{album}', a['recenttracks']['track'][0]['album']['#text'] or "N/A").replace('{albumurl}', f"https://www.last.fm/music/{artist.replace(' ', '+')}/{album.replace(' ', '+')}" or "https://none.none").replace('{username}', user).replace('{scrobbles}', a['recenttracks']['@attr']['total']).replace('{useravatar}', userpfp)
        return params

    @commands.Cog.listener()
    async def on_ready(self):
        clear_caches.start(self.bot)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        if message.author.bot:
            return

        conn = sqlite3.connect('Toughs.db')
        c = conn.cursor()

        check = c.execute("SELECT * FROM lastfmcc WHERE command = ? AND user_id = ?",
                        (message.clean_content, message.author.id)).fetchone()

        conn.close()

        if check:
            context = await self.bot.get_context(message)
            await context.invoke(self.bot.get_command("nowplaying"))



    @commands.group(invoke_without_command=True, aliases=["lf"])
    async def lastfm(self, ctx: commands.Context):
        await ctx.create_pages()

    @lastfm.command(
        name="set",
        help="lastfm",
        description="register your lastfm account",
        usage="[name]",
    )
    async def lf_set(self, ctx: commands.Context, *, ref: str):
        if not await userhandler.lastfm_user_exists(ref):
            return await lastfm_message(ctx, "**Invalid** Last.Fm username")

        check =  self.cursor.execute("SELECT * FROM lastfm WHERE user_id = ?", (ctx.author.id,))
        check =  check.fetchone()

        if not check:
            self.cursor.execute("INSERT INTO lastfm VALUES (?,?)", (ctx.author.id, ref))
        else:
            self.cursor.execute("UPDATE lastfm SET username = ? WHERE user_id = ?", (ref, ctx.author.id))

        self.db.commit()
        return await lastfm_message(ctx, f"Your **Last.fm** username has been set to **{ref}**")
    


    @lastfm.command(name="customcommand", help="lastfm", description="set a custom command for nowplaying", usage="[command]", aliases=["cc"])
    async def lf_customcommand(self, ctx: commands.Context, *, cmd: str):
        try:
            self.cursor.execute("SELECT * FROM lastfmcc WHERE user_id = ?", (ctx.author.id,))
            check = self.cursor.fetchone()
            if cmd == "none":
                if check is None:
                    return await lastfm_message(ctx, f"You don't have a **last.fm** custom command")
                self.cursor.execute("DELETE FROM lastfmcc WHERE user_id = ?", (ctx.author.id,))
                return await lastfm_message(ctx, "Your **Last.fm** custom command got succesfully deleted")
            if check is None:
                self.cursor.execute("INSERT INTO lastfmcc VALUES (?, ?)", (ctx.author.id, cmd))
            else:
                self.cursor.execute("UPDATE lastfmcc SET command = ? WHERE user_id = ?", (cmd, ctx.author.id))
            self.db.commit()
            return await lastfm_message(ctx, f"Your **Last.fm** custom command is **{cmd}**")
        except Exception as e:
            print(f"An error occurred: {e}")
            await lastfm_message(ctx, "An error occurred while executing the command.") 


    
    
    @lastfm.command(name="toptracks", aliases=['tt'], description="check a member's top 10 tracks", help="lastfm", usage="<member>")
    async def lf_toptracks(self, ctx: commands.Context, *, member: discord.Member=None):
        if member is None:
            member = ctx.author
        try:
            check = self.cursor.execute("SELECT * FROM lastfm WHERE user_id = ?", (member.id,))
            check = check.fetchone()
            if check:
                user = check[1]
                if user != "error":
                    jsonData = await self.lastfmhandler.get_top_tracks(user, 10)
                    embed = discord.Embed(description='\n'.join(f"`{i+1}` **[{jsonData['toptracks']['track'][i]['name']}]({jsonData['toptracks']['track'][i]['url']})** {jsonData['toptracks']['track'][i]['playcount']} plays" for i in range(10)),
                                        color=self.bot.color)
                    embed.set_thumbnail(url=member.avatar.url)
                    embed.set_author(name=f"{user}'s overall top tracks", icon_url=member.avatar.url)
                    return await ctx.reply(embed=embed)
            else:
                return await lastfm_message(ctx, "There is no **last.fm** account linked for this member")
        except Exception as e:
            print(e)

    @lastfm.command(name="topalbums", aliases=['tal'], description="check a member's top 10 albums", help="lastfm", usage="<member>")
    async def lf_topalbums(self, ctx: commands.Context, *, member: discord.Member = None):
        if member is None:
            member = ctx.author
        try:
            cursor = self.db.cursor()
            check = cursor.execute("SELECT * FROM lastfm WHERE user_id = ?", (member.id,)).fetchone()
            if check:
                user = check[1]
                if user != "error":
                    jsonData = await self.lastfmhandler.get_top_albums(user, 10)
                    embed = discord.Embed(description='\n'.join(f"`{i+1}` **[{jsonData['topalbums']['album'][i]['name']}]({jsonData['topalbums']['album'][i]['url']})** {jsonData['topalbums']['album'][i]['playcount']} plays" for i in range(10)),
                                        color=self.bot.color)
                    embed.set_thumbnail(url=ctx.message.author.avatar)
                    embed.set_author(name=f"{user}'s overall top albums", icon_url=ctx.message.author.avatar)
                    return await ctx.reply(embed=embed)
            else:
                return await lastfm_message(ctx, "There is no **last.fm** account linked for this member")
        except Exception as e:
            print(e)
        finally:
            cursor.close()

    @lastfm.command(name="reactions", help="lastfm", description="add custom reactions to your lastfm embed", usage="[emojis | none]\nnone -> no reactions for np command\nno emoji -> default emojis will be used")
    async def lf_reactions(self, ctx: commands.Context, *emojis: str):
        conn = sqlite3.connect("tets.db")
        cursor = conn.cursor()

        check_query = "SELECT * FROM lfreactions WHERE user_id = ?"
        check_params = (ctx.author.id,)
        check = cursor.execute(check_query, check_params).fetchone()

        if len(emojis) == 0:
            if not check:
                conn.close()
                return await lastfm_message(ctx, "You don't have any **last.fm** custom reaction to remove")

            delete_query = "DELETE FROM lfreactions WHERE user_id = ?"
            delete_params = (ctx.author.id,)
            cursor.execute(delete_query, delete_params)
            conn.commit()
            conn.close()
            return await lastfm_message(ctx, "Deleted your **last.fm** custom reactions")

        sql_as_text = json.dumps(emojis)
        if check:
            update_query = "UPDATE lfreactions SET reactions = ? WHERE user_id = ?"
            update_params = (sql_as_text, ctx.author.id)
            cursor.execute(update_query, update_params)
        else:
            insert_query = "INSERT INTO lfreactions VALUES (?,?)"
            insert_params = (ctx.author.id, sql_as_text)
            cursor.execute(insert_query, insert_params)

        conn.commit()
        conn.close()
        return await lastfm_message(ctx, f"Your **last.fm** reactions are {''.join([e for e in emojis])}")




    @commands.command(aliases=['np', 'fm'], help="lastfm", description="check what song is playing right now", usage="<user>")
    async def nowplaying(self, ctx: commands.Context, *, member: discord.User=None):
        if member is None: member = ctx.author
        cursor = self.db.cursor()
        try:
            await ctx.typing()             
            cursor.execute("SELECT * FROM lastfm WHERE user_id = ?", (member.id,))
            check =cursor.fetchone()          
            if check:   
                cursor.execute("SELECT mode FROM lfmode WHERE user_id = ?", (member.id,))
                starData =cursor.fetchone()
                if starData is None:  
                    user = check[1]
                    if user != "error":      
                        a = await self.lastfmhandler.get_tracks_recent(user, 1)
                        artist = a['recenttracks']['track'][0]['artist']['#text'].replace(" ", "+")
                        album = a['recenttracks']['track'][0]['album']['#text'] or "N/A"
                        embed = discord.Embed(colour=self.bot.color)
                        embed.add_field(name="**Track:**", value = f"""[{"" + a['recenttracks']['track'][0]['name']}]({"" + a['recenttracks']['track'][0]['url']})""", inline = False)
                        embed.add_field(name="**Artist:**", value = f"""[{a['recenttracks']['track'][0]['artist']['#text']}](https://last.fm/music/{artist})""", inline = False)
                        embed.set_author(name = user, icon_url = member.display_avatar, url = f"https://last.fm/user/{user}")                               
                        embed.set_thumbnail(url=(a['recenttracks']['track'][0])['image'][3]['#text'])
                        embed.set_footer(text = f"Track Playcount: {await self.lastfmhandler.get_track_playcount(user, a['recenttracks']['track'][0])} ・Album: {album}", icon_url = (a['recenttracks']['track'][0])['image'][3]['#text'])
                        message = await ctx.reply(embed=embed)
                        return await lf_add_reactions(ctx, message)
                else:
                    user = check['username']
                    try: 
                        x = await EmbedBuilder.to_object(EmbedBuilder.embed_replacement(member, await self.lastfm_replacement(user, starData[0])))
                        message = await ctx.send(content=x[0], embed=x[1], view=x[2])
                    except: message = await ctx.send(await self.lastfm_replacement(user, starData[0]))
                    await lf_add_reactions(ctx, message)
            elif check is None: return await lastfm_message(ctx, f"**{member}** doesn't have a **Last.fm account** linked. Use `{ctx.clean_prefix}lf set <username>` to link your **account**.")
        except Exception: 
            print(traceback.format_exc())
            await lastfm_message(ctx, f"unable to get **{member.name}'s** recent track".capitalize())
        finally:
          cursor.close()


    @lastfm.command(name="howto", help="lastfm", description="tutorial for using lastfm", aliases=["tutorial"])
    async def lf_howto(self, ctx: commands.Context): 
        await ctx.reply(f"1) create an account at https://last.fm\n2) link your **spotify** account to your **last.fm** account\n3) use the command `{ctx.clean_prefix}lf set [your lastfm username]`\n4) while you listen to your songs, you can use the `{ctx.clean_prefix}nowplaying` command")


    @lastfm.command(name="cover", help="lastfm", description="get the cover image of your lastfm song", usage="<member>")
    async def lf_cover(self, ctx: commands.Context, *, member: discord.Member=commands.Author): 
        conn = sqlite3.connect('tets.db')
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM lastfm WHERE user_id = ?", (member.id,))
        check = cursor.fetchone()
        conn.close()
        
        if check is None: 
            return await lastfm_message(ctx, "You don't have a **last.fm** account connected")
        
        user = check[0]
        a = await self.lastfmhandler.get_tracks_recent(user, 1)
        file = discord.File(await self.bot.getbyte((a['recenttracks']['track'][0])['image'][3]['#text']), filename="cover.png")
        return await ctx.reply(f"**{a['recenttracks']['track'][0]['name']}**", file=file)


    @lastfm.command(name="whoknows", aliases=['wk'], help="lastfm", description="see who knows a certain artist in the server", usage="[artist]")
    async def lf_whoknows(self, ctx: commands.Context, *, artist: str=None):
        await ctx.typing()

        # Retrieve the last.fm username of the user from the database
        cursor = self.db.cursor()
        cursor.execute("SELECT username FROM lastfm WHERE user_id = ?", (ctx.author.id,))
        row = cursor.fetchone()
        if row is None:
            return await lastfm_message(ctx, "You don't have a **last.fm** account connected")
        fmuser = row[0]

        if not artist:
            # Retrieve the most recent track played by the user
            resp = await self.lastfmhandler.get_tracks_recent(fmuser, 1)
            artist = resp["recenttracks"]["track"][0]["artist"]["#text"]

        tuples = []
        rows = []

        # Retrieve the last.fm usernames of all users in the server from the database
        cursor.execute("SELECT user_id, username FROM lastfm WHERE user_id IN (SELECT user_id FROM lastfm WHERE guild_id = ?)", (ctx.guild.id,))
        results = cursor.fetchall()
        if len(results) == 0:
            return await lastfm_message(ctx, "No one has a **last.fm** account linked")

        # Iterate over the results and retrieve the play count for the specified artist
        for user_id, fmuser2 in results:
            us = ctx.guild.get_member(user_id)
            z = await self.lastfmhandler.get_artist_playcount(fmuser2, artist)
            tuples.append((str(us), int(z), f"https://last.fm/user/{fmuser2}", us.id))

        # Sort the results and format them into rows for display
        num = 0
        for x in sorted(tuples, key=lambda n: n[1])[::-1][:10]:
            if x[1] != 0:
                num += 1
                rows.append(f"{'<a:crown:1021829752782323762>' if num == 1 else f'`{num}`'} [**{x[0]}**]({x[2]}) has **{x[1]}** plays")

        # Construct the final message and send it
        if rows:
            em = discord.Embed(
                title=f"Who knows **{artist}**?",
                description="\n".join(rows),
                color=discord.Color.green()
            )
            await ctx.send(embed=em)
        else:
            await lastfm_message(ctx, "No one has scrobbled **{artist}**") 
            # Send the results to the user
            await lastfm_message(ctx, "\n".join(rows))



    @lastfm.command(name="chart", aliases=["c"], help="lastfm", description="Generates an album image chart.", usage="[size] [period]\nsizes available: 3x3 (default), 2x2, 4x5, 20x4\nperiods available: alltime (default), yearly, monthly")
    async def lf_chart(self, ctx: commands.Context, size: str="3x3", period: str="alltime"): 
        await ctx.typing()
        
        conn = sqlite3.connect('tets.db')
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM lastfm WHERE user_id = ?", (ctx.author.id,))
        check = cursor.fetchone()
        conn.close()
        
        if check is None: 
            return await lastfm_message(ctx, "You don't have a **last.fm** account connected")
        
        fmuser = check[0]
        if not size in ["3x3", "2x2", "4x5", "20x4"] or not period in ["alltime", "yearly", "monthly"]: 
            raise commands.MissingRequiredArgument("lf chart")
        perio = period.replace('yearly', '12month').replace('monthly', '1month')
        ec = size.replace('x', "*").split('*')      
        limit = int(int(ec[0])*int(ec[1]))
        file = await self.bot.rival.lastfm_chart(username=fmuser, chart_size=size, timeperiod=perio, limit=limit, filename="chart.png")
        
        embed = discord.Embed(title=f"{ctx.author.name}'s {period} album {size} chart")
        embed.set_image(url=f"attachment://chart.png")
        await ctx.reply(embed=embed, file=file)
















    






async def setup(bot):
    await bot.add_cog(LastFM(bot))