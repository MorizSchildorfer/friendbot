import discord
import asyncio
from datetime import datetime,timedelta
from discord.utils import get        
from discord.ext import commands
from bfunc import roleArray, calculateTreasure, timeConversion, db

class Apps(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
    
    @commands.group(case_insensitive=True)
    async def app(self, ctx):	
        pass
      
    @app.command()
    @commands.has_any_role('Mod Friend', 'A d m i n')
    async def edit(self, ctx, num, *, editString=""):
        # The Bot
        botUser = self.bot.user
        # App Logs channel 
        channel = self.bot.get_channel(388591318814949376) 

        msgFound = False
        async with channel.typing():
            async for message in channel.history(oldest_first=False):
                if int(num) == message.id and message.author == botUser:
                    editMessage = message
                    msgFound = True
                    break 

        if not msgFound:
            delMessage = await ctx.channel.send(content=f"I couldn't find message {num}. Please try again. I will delete your message and this one in 10 seconds.")
            await asyncio.sleep(10) 
            await delMessage.delete()
            await ctx.message.delete() 
            return

        botEmbed = editMessage.embeds[0]
        botEmbed.set_footer(text=f"Application Message ID: {editMessage.id}\nMod: {ctx.author}")

        await editMessage.edit(content=editString, embed=botEmbed)
        delMessage = await ctx.channel.send(content=f"I have edited the message {num}.\n```{editString}```\nPlease double check that the edit is correct. I will now delete your message and this one in 30 seconds.")
        await asyncio.sleep(30) 
        await delMessage.delete()
        await ctx.message.delete() 
        await editMessage.clear_reactions()

    @commands.Cog.listener()
    async def on_message(self,msg):
        def msgCheck(m):
            sameMessage = False
            appDict = botMsg.embeds[0].to_dict()
            appNum = appDict['title'].split('#')[1]
            if appNum in m.content:
                sameMessage = True

            return ('approve #' in m.content.lower() or 'deny #' in m.content.lower() or 'under17 #' in m.content.lower()) and sameMessage

        # appchannel
        channelID = 388591318814949376
        channel = self.bot.get_channel(channelID)
        guild = msg.guild
        if channel and channel.id == channelID and msg.author.name == 'Application Bot Friend':
            botEmbed = msg.embeds[0]
            botMsg = await channel.send(embed=botEmbed)
            await msg.delete()

            mMessage = await self.bot.wait_for("message", check=msgCheck)

            appDict = botMsg.embeds[0].to_dict()
            appNum = appDict['title'].split('#')[1] 
            appDiscord = appDict['fields'][0]['value']
            appHash = appDiscord.split('#')[1]
            appAge = appDict['fields'][1]['value']
            appMember = guild.get_member_named(appDiscord)
            botEmbed.set_footer(text=f"Application Message ID: {botMsg.id}\nMod: {mMessage.author}")

            if appMember is None:
                channel.send(content=f"Something went wrong. The application could not find the discord name {appDiscord} for application {appNum}. Please delete this message once this is resolved.")
                return

            if 'approve' in mMessage.content:
                # Session Channel
                await botMsg.edit(embed=botEmbed, content=f"{appNum}. {appMember.mention} #{appHash} - **Approved**")
                await botMsg.clear_reactions()
                await mMessage.delete()

                if int(appAge) < 18:
                    kidRole = get(guild.roles, name = 'Under-18 Friendling')
                    await appMember.add_roles(kidRole, reason="Approved application - the user is under 18.")
                
                if db.players.find_one({"User ID" : str(appMember.id), "Level" : {"$gt" : 1}}):

                    juniorRole = get(guild.roles, name = 'Junior Friend')

                    await appMember.add_roles(juniorRole, reason=f"Approved application - the user has a level 2 or higher character.")
                    
                
                newRole = get(guild.roles, name = 'D&D Friend')
                await appMember.add_roles(newRole, reason=f"Approved application - the user has been given the base role.")

                await appMember.send(f"Hello, {appMember.name}!\n\nThank you for applying to **D&D Friends**! The Mod team has approved your application and you have been assigned the appropriate role(s). In order to be pinged for one-shots, you must navigate to the `#role-management` channel and opt into the tiers you would like to be pinged for by reacting to the posts.\n\nIf you have any further questions then please don't hesitate to ask in our #help-for-players channel or message a Mod Friend!")

            elif 'deny' in mMessage.content:
                await botMsg.edit(embed=botEmbed, content=f"{appNum}. {guild.get_member_named(appDiscord).mention} #{appHash} - **Denied** (Did not read server rules)")
                await botMsg.clear_reactions()
                await mMessage.delete()
                await appMember.send(f"Hello, {appMember.name}!\n\nThank you for applying to **D&D Friends**! Unfortunately, the Mod team has declined your application since you did not consent to possible NSFW content in one-shots or did not read the server rules and agree to abide by them.\n\nIf you have any questions or inquiries, please direct them to our Reddit or Twitter accounts:\nReddit - <https://www.reddit.com/user/DnDFriends/>\nTwitter - <https://twitter.com/DnD_Friends>\n\nWe hope you find other like-minded people to play D&D with. Good luck!")
             
            elif 'under17' in mMessage.content:
                await botMsg.edit(embed=botEmbed, content=f"{appNum}. {guild.get_member_named(appDiscord).mention} #{appHash} - **Denied** (Under 17)")
                await botMsg.clear_reactions()
                await mMessage.delete()
                await appMember.send(f"Hello, {appMember.name}!\n\nThank you for applying to **D&D Friends**! Unfortunately, the **D&D Friends** Mod team has declined your application since you did not meet the cut-off age.\n\nIf you have any questions or inquiries, please direct them to our Reddit or Twitter accounts:\nReddit - <https://www.reddit.com/user/DnDFriends/>\nTwitter - <https://twitter.com/DnD_Friends>\n\nWe hope you find other like-minded people to play D&D with. Good luck!")

def setup(bot):
    bot.add_cog(Apps(bot))
