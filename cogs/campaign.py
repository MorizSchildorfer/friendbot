import pytz
import time
import requests
import re
import shlex
import decimal
import random
import discord
import asyncio
from cogs.guild import pin_control
from discord.utils import get        
from discord.ext import commands
from math import ceil, floor
from itertools import product      
from datetime import datetime, timezone, timedelta
from bfunc import gameCategory, commandPrefix, roleArray, timezoneVar, currentTimers, db, traceBack, settingsRecord, alphaEmojis, roleArray, cp_bound_array, settingsRecord
from cogs.util import callAPI, paginate, timeConversion
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError


def campaign_channel_check(channel):
    return "campaign" in str(channel.category.name).lower()

class Campaign(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
       

    @commands.group(aliases=['c'], case_insensitive=True, invoke_without_command=True)
    async def campaign(self, ctx):
        usersCollection = db.users
        userRecords = usersCollection.find_one({"User ID": str(ctx.author.id)})	
        contents = []
        campaignString = ""
        if "Campaigns" in userRecords:
            for u, v in userRecords['Campaigns'].items():
                hidden = ("Hidden" in v and v["Hidden"])
                campaignString += f"• {(not v['Active'])*'~~'}{'*'*hidden}{u}{'*'*hidden}{(not v['Active'])*'~~'}: {v['Sessions']} sessions, {timeConversion(v['Time'],hmformat=True)}\n"

        contents.append((f"Campaigns", campaignString, False))
        await paginate(ctx, self.bot, "" , contents, separator="\n", author = ctx.author)
   
    
    def is_log_channel():
        async def predicate(ctx):
            return (ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Mod Rooms"])
        return commands.check(predicate)
    async def cog_command_error(self, ctx, error):
        msg = None
        if isinstance(error, commands.CommandNotFound):
            await ctx.channel.send(f'Sorry, the command `{commandPrefix}campaign {ctx.invoked_with}` requires an additional keyword to the command or is invalid, please try again!')
            return
        if isinstance(error, commands.CommandOnCooldown):
            msg = f"The command is on cooldown." 
        elif isinstance(error, discord.NotFound):
            msg = "The session log could not be found."
        elif isinstance(error, commands.MissingAnyRole):
            await ctx.channel.send("You do not have the required permissions for this command.")
            return
        elif isinstance(error, commands.BadArgument):
            await ctx.channel.send("One of your parameters was of an incorrect type.")
            return
        else:
            if isinstance(error, commands.MissingRequiredArgument):
                print(error.param.name)
                if error.param.name == "roleName":
                    msg = "You're missing the @role for the campaign you want to create"
                elif error.param.name == "channelName":
                    msg = "You're missing the #channel for the campaign you want to create."
                elif error.param.name == 'userList':
                    msg = "You can't prepare a timer without any players! \n"
                else:
                    msg = "Your command is missing an argument!"
            elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
              msg = "There seems to be an unexpected or a missing closing quote mark somewhere, please check your format and retry the command."

            if msg:
                if ctx.command.name == "prep":
                    msg += f'Please follow this format:\n```yaml\n{commandPrefix}campaign timer prep "@player1, @player2, [...]" "session name"```'
        if msg:
            if ctx.command.name == "create":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}campaign create @rolename #channel-name```"

            ctx.command.reset_cooldown(ctx)
            await ctx.channel.send(msg)
        else:
            if ctx.channel.mention in currentTimers and "State" in currentTimers[ctx.channel.mention]:
                currentTimers[ctx.channel.mention]["State"] = "Crashed"
                await ctx.channel.send(f"This timer has crashed. The DM can use `{commandPrefix}campaign timer resume` to continue the timer.")
            ctx.command.reset_cooldown(ctx)
            await traceBack(ctx,error)
    
    
    @campaign.command()
    async def show(self, ctx, campaign_name):
        await self.hideKernel(ctx,campaign_name, False)
    
    
    @campaign.command()
    async def hide(self, ctx, campaign_name):
        await self.hideKernel(ctx,campaign_name, True)
    
    async def hideKernel(self, ctx, campaign_name, target_value):
        usersCollection = db.users
        userRecords = usersCollection.find_one({"User ID": str(ctx.author.id)})
        campaignFind = False        
        campaignChannels = ctx.message.channel_mentions
        if len(campaignChannels) > 1 or campaignChannels == list():
            for key in userRecords["Campaigns"].keys():
                if campaign_name.lower() in key.lower(): 
                    campaignFind = True
                    campaignKey = key
                    break
            error_name = campaign_name
        else:
            for key in userRecords["Campaigns"].keys():
                if key.lower().replace(",", "") == (campaignChannels[0].name.replace('-', ' ')):
                    campaignFind = True
                    campaignKey = key
                    break
            error_name = campaignChannels[0].mention
        if not campaignFind:
            msg = f"I could not find {error_name} in your records!"
        else:
            usersCollection.update_one({'_id': userRecords['_id']}, {"$set": {f"Campaigns.{campaignKey}.Hidden": target_value}})
            msg = f"You have {'un'*(not target_value)}hidden {campaignKey} in your profile"
        await ctx.channel.send(msg)
            
    @campaign.command()
    async def info(self, ctx, channel="", full=""):
        campaignChannel = ctx.message.channel_mentions

        channel = ctx.channel
        if not (campaignChannel == list()):
            channel = campaignChannel[0] 
        
        campaignRecords = db.campaigns.find_one({"Channel ID": str(channel.id)})
        if not campaignRecords:
            await channel.send(f"No campaign could be found for this channel.")
            return 
        playerRecords = list(db.users.find({"Campaigns."+campaignRecords["Name"]: {"$exists": True}}))
        if full:
            playerRecords.sort(key=lambda x:not  x["Campaigns"][campaignRecords["Name"]]["Active"])
        else:
            playerRecords = filter(lambda x:  x["Campaigns"][campaignRecords["Name"]]["Active"], playerRecords)
        infoEmbed = discord.Embed()
        infoEmbedmsg = None
        master = None
        master_text = ""
        infoEmbed.title = f"Campaign Info: {campaignRecords['Name']}"
        description_string = f"**Sessions**: {campaignRecords['Sessions']}\n**Created On**: " +datetime.fromtimestamp(campaignRecords['Creation Date']).strftime("%b-%d-%y %I:%M %p")
        for player in playerRecords:
            if player['User ID'] == campaignRecords["Campaign Master ID"]:
                master = player
            else:
                info_string= ""
                member = ctx.guild.get_member(int(player['User ID']))
                member_name = "Left the Server"
                if member:
                    member_name = member.display_name
                info_string += f"• Total Time: {timeConversion(player['Campaigns'][campaignRecords['Name']]['Time'])}\n"
                info_string += f"• Sessions: {player['Campaigns'][campaignRecords['Name']]['Sessions']}\n"
                if full:
                    active_string = 'Active'
                    if (not player['Campaigns'][campaignRecords['Name']]['Active']):
                        active_string = 'Inactive'
                    info_string += f"• {active_string}"
                infoEmbed.add_field(name=f"**{member_name}**:", value = info_string, inline = False)
        infoEmbed.description = description_string
        
        member = ctx.guild.get_member(int(master['User ID']))
        member_name = "Left the Server"
        if member:
            member_name = member.display_name
        master_text += f"• Total Time: {timeConversion(master['Campaigns'][campaignRecords['Name']]['Time'])}\n"  
        master_text += f"• Sessions: {master['Campaigns'][campaignRecords['Name']]['Sessions']}\n"
        infoEmbed.insert_field_at(0, name=f"**{member_name}** (Campaign Master):", value = master_text, inline = False)
        await ctx.channel.send(embed=infoEmbed)
    
    #@commands.cooldown(1, 5, type=commands.BucketType.member)
    @campaign.command()
    async def create(self,ctx, roleName, channelName):
        channel = ctx.channel
        author = ctx.author
        campaignEmbed = discord.Embed()
        campaignEmbedmsg = None
        campaignCog = self.bot.get_cog('Campaign')

        campaignRole = ctx.message.role_mentions
        campaignChannel = ctx.message.channel_mentions

        roles = [r.name for r in ctx.author.roles]
        
        if 'Campaign Master' not in roles:
            await channel.send(f"You do not have the Campaign Master role to use this command.")
            return  

        if campaignRole == list() or campaignChannel == list():
            await channel.send(f"A campaign role and campaign channel must be supplied.")
            return 
        campaignName = campaignRole[0].name
        
        roleStr = (campaignRole[0].name.lower().replace(',', '').replace('.', '').replace(' ', '').replace('-', ''))
        
        campaignNameStr = (campaignChannel[0].name.replace('-', ''))
        if campaignNameStr != roleStr:
            await channel.send(f"The campaign name: ***{campaignName}*** does not match the campaign channel ***{campaignChannel[0].name}***. Please try the command again with the correct channel.")
            return 
        campaignCollection = db.campaigns
        campaignRecords = campaignCollection.find_one({"Name": {"$regex": campaignName, '$options': 'i' }})
        if campaignRecords:
            await channel.send(f"Another campaign by this name has already been created.")
            return 

        usersCollection = db.users
        userRecords = usersCollection.find_one({"User ID": str(author.id)})

        if userRecords: 
            if 'Campaigns' not in userRecords:
                userRecords['Campaigns'] = {}
            userRecords['Campaigns'][campaignRole[0].name] = {"Time" : 0, "Sessions" : 0, "Active" : True}
            campaignDict = {'Name': campaignName, 
                            'Campaign Master ID': str(author.id), 
                            'Role ID': str(campaignRole[0].id), 
                            'Channel ID': str(campaignChannel[0].id),
                            'Sessions':0,
                            'Creation Date' : time.time()}
            await author.add_roles(campaignRole[0], reason=f"Added campaign {campaignName}")

            try:
                campaignCollection.insert_one(campaignDict)
                usersCollection.update_one({'_id': userRecords['_id']}, {"$set": {"Campaigns": userRecords['Campaigns']}}, upsert=True)
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                campaignEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your campaign again.")
            else:
                campaignEmbed.title = f"Campaign Creation: {campaignName}"
                campaignEmbed.description = f"{author.name} has created **{campaignName}**!\nRole: {campaignRole[0].mention}\nChannel: {campaignChannel[0].mention}"
                if campaignEmbedmsg:
                    await campaignEmbedmsg.clear_reactions()
                    await campaignEmbedmsg.edit(embed=campaignEmbed)
                else: 
                    campaignEmbedmsg = await channel.send(embed=campaignEmbed)
        else:
            await channel.send("You need a user profile to create a campaign. Use the `$user` command in one of the log channels.")
        return

    #@commands.cooldown(1, 5, type=commands.BucketType.member)
    @campaign.command()
    async def add(self,ctx, user, campaignName):
        channel = ctx.channel
        author = ctx.author
        campaignEmbed = discord.Embed()
        campaignEmbedmsg = None
        campaignCog = self.bot.get_cog('Campaign')
        guild = ctx.message.guild
        campaignName = ctx.message.channel_mentions
        user = ctx.message.mentions

        roles = [r.name for r in ctx.author.roles]

        if 'Campaign Master' not in roles:
            await channel.send(f"You do not have the Campaign Master role and cannot use this command.")
            return  

        if user == list() or len(user) > 1:
            await channel.send(f"I could not find the user you were trying to add to the campaign. Please try again.")
            return  
        if campaignName == list() or len(campaignName) > 1:
            await channel.send(f"I couldn't find the campaign you were trying add to. Please try again.")
            return
        
        campaignName = campaignName[0]  
        campaignCollection = db.campaigns
        campaignRecords = campaignCollection.find_one({"Channel ID": {"$regex": f"{campaignName.id}", '$options': 'i' }})

        if not campaignRecords:
            await channel.send(f"**{campaignName.mention}** doesn\'t exist! Check to see if it is a valid campaign and check your spelling.")
            return

        if campaignRecords['Campaign Master ID'] != str(author.id):
            await channel.send(f"You cannot add users to this campaign because you are not the Campaign Master of **{campaignRecords['Name']}**.")
            return
        
        roles = [r.name for r in user[0].roles]
        if "D&D Friend" not in roles:
            await channel.send(f"***{user[0].display_name}*** needs to apply for membership to the server before they can be added to a campaign! Please have them apply for membership and then use this command again. See section :two: of #how-to-play for more information on applying for membership.")
            return
            
            
        usersCollection = db.users
        userRecords = usersCollection.find_one({"User ID": str(user[0].id)})  
        if not userRecords:
            await channel.send(f"***{user[0].display_name}*** needs to establish a user profile before they can be added to a campaign! Please have them use the `$user` command in a log channel and then use this command again.")
            return
        if 'Campaigns' not in userRecords:
            userRecords['Campaigns'] = {campaignRecords['Name'] : {"Time" : 0, "Sessions" : 0} }
        else:
            if campaignRecords['Name'] not in userRecords['Campaigns']:
                userRecords['Campaigns'][campaignRecords['Name']] = {"Time" : 0, "Sessions" : 0}
        userRecords['Campaigns'][campaignRecords['Name']]["Active"] = True

        await user[0].add_roles(guild.get_role(int(campaignRecords['Role ID'])), reason=f"{author.name} add campaign member to {campaignRecords['Name']}")
        if not any([role in roles for role in ["Junior Friend", "Journeyfriend", "Elite Friend", "True Friend", "Ascended Friend"]]):
            await user[0].add_roles(get(guild.roles, name = "Junior Friend"), reason=f"{author.name} added campaign member to {campaignRecords['Name']}")

        try:
            usersCollection.update_one({'_id': userRecords['_id']}, {"$set": {"Campaigns": userRecords['Campaigns']}}, upsert=True)
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            campaignEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try adding to your campaign again.")
        else:
            campaignEmbed.title = f"Campaign: {campaignRecords['Name']}"
            campaignEmbed.description = f"{author.name} has added {user[0].mention} to **{campaignRecords['Name']}**!"
            if campaignEmbedmsg:
                await campaignEmbedmsg.clear_reactions()
                await campaignEmbedmsg.edit(embed=campaignEmbed)
            else: 
                campaignEmbedmsg = await channel.send(embed=campaignEmbed)

        return

    #@commands.cooldown(1, 5, type=commands.BucketType.member)
    @campaign.command()
    async def remove(self,ctx, user, campaignName):
        channel = ctx.channel
        author = ctx.author
        campaignEmbed = discord.Embed()
        campaignEmbedmsg = None
        campaignCog = self.bot.get_cog('Campaign')
        guild = ctx.message.guild

        campaignName = ctx.message.channel_mentions
        user = ctx.message.mentions

        usersCollection = db.users

        roles = [r.name for r in ctx.author.roles]

        if 'Campaign Master' not in roles:
            await channel.send(f"You do not have the Campaign Master role to use this command.")
            return  

        if user == list() or len(user) > 1:
            await channel.send(f"I could not find the user you were trying to remove from the campaign. Please try again.")
            return  

        if campaignName == list() or len(campaignName) > 1:
            await channel.send(f"`I couldn't find the campaign you were trying remove from. Please try again")
            return
        campaignName = campaignName[0]
        campaignCollection = db.campaigns
        campaignRecords = campaignCollection.find_one({"Channel ID": {"$regex": str(campaignName.id), '$options': 'i' }})

        if not campaignRecords:
            await channel.send(f"`{campaignName}` doesn\'t exist! Check to see if it is a valid campaign and check your spelling.")
            return
        
        if campaignRecords['Campaign Master ID'] != str(author.id):
            await channel.send(f"You cannot remove users from this campaign because you are not the Campaign Master of **{campaignRecords['Name']}**.")
            return
        user_roles = [r.name for r in user[0].roles]
        if campaignRecords["Name"] not in user_roles:
            await channel.send(f"The user does not have the campaign role to remove.")
            return  
        user_entry = usersCollection.find_one({'User ID': str(user[0].id), f"Campaigns.{campaignRecords['Name']}" : {"$exists" : True}})
        if not user_entry:
            await channel.send(f"`{user[0].display_name}` could not be found as part of the campaign.")
            return
        try:
            usersCollection.update_one({'User ID': str(user[0].id)}, {"$set": {f"Campaigns.{campaignRecords['Name']}.Active": False}}, upsert=True)
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            campaignEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try removing from your campaign again.")
        else:
            await user[0].remove_roles(guild.get_role(int(campaignRecords['Role ID'])), reason=f"{author.name} remove campaign member from {campaignRecords['Name']}")
            campaignEmbed.title = f"Campaign: {campaignRecords['Name']}"
            campaignEmbed.description = f"{author.name} has removed {user[0].mention} from **{campaignRecords['Name']}**!"
            campaignEmbedmsg = await channel.send(embed=campaignEmbed)
        return
        
    @campaign.command()
    @commands.has_any_role("Mod Friend", "Bot Friend", "A d m i n")
    async def end(self,ctx, campaignName):
        channel = ctx.channel
        campaignEmbed = discord.Embed()
        campaignEmbedmsg = None
        if ctx.message.channel_mentions != list():
            campaignName = ctx.message.channel_mentions

            if len(campaignName) > 1:
                await channel.send(f"I couldn't find the campaign you were trying add to. Please try again.")
                return
            
            campaignName = campaignName[0]  
            campaignRecords = db.campaigns.find_one({"Channel ID": {"$regex": f"{campaignName.id}", '$options': 'i' }})
        else:
            campaignRecords = db.campaigns.find_one({"Name": campaignName})
        if not campaignRecords:
            await channel.send(f"**{campaignName}** doesn\'t exist! Check to see if it is a valid campaign and check your spelling.")
            return

        try:
            db.users.update_many({f'Campaigns.{campaignRecords["Name"]}': {"$exists": True}}, {"$set": {f'Campaigns.{campaignRecords["Name"]}.Active': False}})
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            campaignEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try ending the campaign again.")
        else:
            campaignEmbed.title = f"Campaign: {campaignRecords['Name']}"
            campaignEmbed.description = f"All players have been removed from the campaign!"
            campaignEmbedmsg = await channel.send(embed=campaignEmbed)
        return

    async def campaign_check(self, ctx):
        channel = ctx.channel
        author = ctx.author
        if not campaign_channel_check(channel):
            #inform the user of the correct location to use the command and how to use it
            await channel.send('Try this command in a campaign channel! ')
            return False
        campaignRecords = db.campaigns.find_one({"Channel ID": str(channel.id)}) #finds the campaign that has the same Channel ID as the channel the command was typed.
        if not campaignRecords:
            return False
        if str(author.id) != campaignRecords['Campaign Master ID']:
            await channel.send(f"You are not the campaign owner!")
            return False
        return True

    @campaign.command()
    @commands.has_any_role('Campaign Master')
    async def pin(self,ctx):
        if not await self.campaign_check(ctx):
            return
        
        async with ctx.channel.typing():
            
            await pin_control(self, ctx, "pin")
            async for message in ctx.channel.history(after=ctx.message): #searches for and deletes any non-default messages in the channel to delete, including the message saying that something was pinned.
                if message.type != ctx.message.type:
                    await message.delete()

        
    @campaign.command()
    @commands.has_any_role('Campaign Master')
    async def unpin(self,ctx):
        
        if not await self.campaign_check(ctx):
            return
        
        async with ctx.channel.typing():
            await pin_control(self, ctx, "unpin")
    
    @campaign.command()
    @commands.has_any_role('Campaign Master')
    async def topic(self, ctx, *, messageTopic = ""): # channelName=""
        
        if not await self.campaign_check(ctx):
            return
        
        await ctx.channel.edit(topic=messageTopic)
        await ctx.message.delete()

        resultMessage = await ctx.channel.send(f"You have successfully updated the topic for your campaign! This message will self-destruct in 10 seconds.")
        await asyncio.sleep(10) 
        await resultMessage.delete()
        
async def setup(bot):
    await bot.add_cog(Campaign(bot))
