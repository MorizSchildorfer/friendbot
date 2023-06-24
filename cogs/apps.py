import discord
import asyncio
from datetime import datetime,timedelta
from discord.utils import get        
from discord.ext import commands
from bfunc import db, traceBack

class Apps(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
    async def cog_command_error(self, ctx, error):
        msg = None
        
        
        if isinstance(error, commands.BadArgument):
            # convert string to int failed
            msg = "Your parameter types were off."
        
        elif isinstance(error, commands.CheckFailure):
            msg = ""
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            msg = "You missed a parameter"

        if msg:
            
            await ctx.channel.send(msg)
        # bot.py handles this, so we don't get traceback called.
        elif isinstance(error, commands.CommandOnCooldown):
            return
        elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
             return

        # Whenever there's an error with the parameters that bot cannot deduce
        elif isinstance(error, commands.CommandInvokeError):
            msg = f'The command is not working correctly. Please try again and make sure the format is correct.'
            ctx.command.reset_cooldown(ctx)
            await ctx.channel.send(msg)
            await traceBack(ctx,error, False)
        else:
            ctx.command.reset_cooldown(ctx)
            await traceBack(ctx,error)
            
    @commands.has_any_role('Mod Friend', 'A d m i n')
    @commands.command()
    async def app(self, ctx, response="", message_id :int = 0):	
    
        # appchannel
        #   channelID = 388591318814949376
        # if ctx.channel.id != 388591318814949376:
            # return
            
        channel = ctx.channel
        guild = ctx.guild
        botMsg = await channel.fetch_message(message_id) 
        botEmbed = botMsg.embeds[0]
        member_id = botMsg.raw_mentions[0]
        appMember = guild.get_member(member_id)
        botEmbed.set_footer(text=f"Application Message ID: {botMsg.id}\nMod: {ctx.message.author}")
        response = response.lower()
        if appMember is None:
            await channel.send(content=f"Something went wrong. The application could not find the discord name {member_name} for application {message_id}. Please delete this message once this is resolved.")
            return

        if 'approve' in response or 'sub18' in response:
            # Session Channel
            await botMsg.edit(embed=botEmbed, content=f"{appMember.mention} - **Approved**")
            await botMsg.clear_reactions()
            await ctx.message.delete()

            if 'sub18' in response:
                kidRole = get(guild.roles, name = 'Under-18 Friendling')
                await appMember.add_roles(kidRole, reason="Approved application - the user is under 18.")
            
            if db.players.find_one({"User ID" : str(appMember.id), "Level" : {"$gt" : 1}}):

                juniorRole = get(guild.roles, name = 'Junior Friend')

                await appMember.add_roles(juniorRole, reason=f"Approved application - the user has a level 2 or higher character.")
                
                await appMember.add_roles(juniorRole, reason=f"Approved application - the user has a level 2 or higher character.")
                
            
            newRole = get(guild.roles, name = 'D&D Friend')
            await appMember.add_roles(newRole, reason=f"Approved application - the user has been given the base role.")
            await appMember.add_roles(get(guild.roles, name = 'Roll20 Tier 1'), reason=f"Approved application - the user has been given the base role.")
            await appMember.add_roles(get(guild.roles, name = 'Foundry Tier 1'), reason=f"Approved application - the user has been given the base role.")
            await appMember.add_roles(get(guild.roles, name = 'Roll20 Tier 0'), reason=f"Approved application - the user has been given the base role.")
            await appMember.add_roles(get(guild.roles, name = 'Foundry Tier 0'), reason=f"Approved application - the user has been given the base role.")
            
            await appMember.send(f"Hello, {appMember.name}!\n\nThank you for applying for membership to the **D&D Friends** Discord server! The Mod team has approved your application and you have been assigned the appropriate roles. If you would like to opt-out of the *Tier Roles* in order to no longer be pinged/mentioned for one-shots, navigate to the `#role-management` channel and react to the approrpriate reactions.\n\nIf you have any further questions then please don't hesitate to ask in our `#help-for-players` channel or message a Mod Friend!")
            
        elif 'deny' in response:
            await botMsg.edit(embed=botEmbed, content=f"{appMember.mention} - **Denied** (Generic)")
            await botMsg.clear_reactions()
            await ctx.message.delete()
            await appMember.send(f"Hello, {appMember.name}!\n\nThank you for applying for membership to the **D&D Friends** Discord server! Unfortunately, the Mod team has declined your application since you are not a good fit for the server. Although D&D is for everyone, not every server is for everyone and we hope you find other like-minded people to play D&D with. Good luck!")
        elif 'sub16' in response:
            await botMsg.edit(embed=botEmbed, content=f"{appMember.mention} - **Denied** (Under 16)")
            await botMsg.clear_reactions()
            await ctx.message.delete()
            await appMember.send(f"Hello, {appMember.name}!\n\nThank you for applying for membership to th **D&D Friends** Discord server! Unfortunately, the Mod team has declined your application since you did not meet the cut-off age. Although D&D is for everyone, not every server is for everyone and we hope you find other like-minded people to play D&D with. Good luck!")
    
    def is_private_channel():
        async def predicate(ctx):
            return ctx.channel.type == discord.ChannelType.private
        return commands.check(predicate)
        
    @commands.command()
    @is_private_channel()
    @commands.cooldown(1, 60, type=commands.BucketType.user)
    async def submit(self, ctx, *, response):
        msg = ctx.message
        sMessage = await ctx.channel.send(content=f'Hello, {msg.author.name}!\n\nThank you for submitting your membership application to the **D&D Friends** Discord server! It has been forwarded to the Mod team for review. Please give the Mod team at least 24 hours before you message one of them to inquire about the status of your membership application. Once it has been processed, you will receive another message from me with the status of your application and further instructions!')
                
        # appchannel
        channelID = 388591318814949376
        channel = self.bot.get_channel(channelID)
        files =None
        if msg.attachments:
            files =[]
            for att in msg.attachments:
                files.append(await att.to_file())
        botMsg = await channel.send(f"Incoming Application by {ctx.message.author.mention}", 
                        files= files)
        title = f"D&D Friends: Application - {msg.author.name}#{msg.author.discriminator}"
        footer_text = f"$app approve {botMsg.id}\n"
        footer_text += f"$app sub18 {botMsg.id}\n"
        footer_text += f"$app deny {botMsg.id}\n"
        footer_text += f"$app sub16 {botMsg.id}\n" 
        
        embed = discord.Embed()
        embed.title = title
        embed.description = response
        embed.set_author(name=msg.author, icon_url=msg.author.display_avatar)
        embed.set_footer(text=f"{footer_text}")
        await botMsg.edit(embed=embed)
            
    @commands.command()
    @is_private_channel()
    @commands.cooldown(1, 60, type=commands.BucketType.user)
    async def membership(self, ctx):
        msg = ctx.message
         
            
        text = f"""Hello {msg.author.name}! 

Thank you for applying for membership to the D&D Friends Discord server. Please copy-paste the following template, answer all questions, and reply to me with your filled out template:
```$submit

**What is your age?**
• 

**Tell us about yourself! What brings you to the server? How did you find us? How long have you been playing D&D? Which editions have you played (if any)?**
• 
```

By submitting this membership application, you are consenting to the following:
• You have read through the rules posted in the #dnd-friends-rules channel on the server and will abide by them at all times.
• We are not liable for NSFW content in one-shots on the server and participating in one-shots is done at your own discretion as we can't be held liable if you end up in a situation with which you are uncomfortable. Although the public channels on the server are considered a "safe for work" (SFW) environment, we allow anyone to be a DM and host a one-shot on the server. Therefore, we do not have control over what people put in their quests and some quests may contain explicit or adult content, otherwise known as "not safe for work" (NSFW) content. Explicit or adult content in this context is considered to be: violence, gore, disturbing imagery, or otherwise implied risqué themes. However, we do urge those DMs to put a warning on their quest board post if they will be using such content so all players are fairly warned prior to the one-shot."""
        await ctx.channel.send(content=text)
                
async def setup(bot):
    await bot.add_cog(Apps(bot))