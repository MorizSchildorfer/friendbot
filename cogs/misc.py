import discord
import random
import asyncio
import re
from cogs.view import AlphaView
from cogs.util import admin_or_owner, uwuize
from discord.utils import get
from discord.ext import commands
from bfunc import settingsRecord, settingsRecord, alphaEmojis, commandPrefix, db, left,right,back

def split_text(input_text, limit, separator):
    # get everything to the limit
    limit_text = input_text[:limit]
    # ensure that we do not separate mid sentence by splitting at the separator
    left_text = limit_text.rsplit(separator, 1)[0]
    right_text = input_text[len(left_text):]
    return left_text, right_text

class Misc(commands.Cog):
    def __init__ (self, bot):
    
        self.bot = bot
        self.current_message= None
        #0: No message search so far, 1: Message searched, but no new message made so far, 2: New message made
        self.past_message_check= 0

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @commands.command()
    async def uwu(self,ctx, *, text=""):
        channel = ctx.channel
        async with channel.typing():
            uwuMessage = uwuize(text)
            await channel.send(content="UwU\n" +  uwuMessage)
        
    #this function is passed in with the channel which has been created/moved
    #relies on there being a message to use
    async def printCampaigns(self,chan):
        
        ch =self.bot.get_channel(382027251618938880) #382027251618938880 728476108940640297
        #find the message in the Campaign Board
        
        message = await discord.utils.get(ch.history(), author__id = self.bot.user.id)
        #Go through all categories with Campaign in the name and Grab all channels in the Campaign category and their ids
        campaign_channels = []
        for cat in chan.guild.categories:
            if("campaigns" in cat.name.lower()):
                campaign_channels+=cat.text_channels
        excluded = [787161189767577640, 382027251618938880, 1003501229588107386] 
        text = "Number of currently-running campaigns: "
        filtered = []
        #filter the list of channels to be just viewable and not in the specific excluded list
        for channel in campaign_channels:
            if(channel.permissions_for(chan.guild.me).view_channel and channel.id not in excluded):
                filtered.append(channel)
        #sort alphebetical ignoring the 'the'
        def sortChannel(elem):
            name = elem.name
            if(name.startswith("the-")):
                name = name.split("-", 1)[1]
            return name
        #generate the string
        filtered.sort(key = sortChannel)
        text += "**"+str(len(filtered))+"**!\n\n"
        text += (" | ").join(map(lambda c: c.name.replace("-", " ").title(), filtered))
        if(not message):
            message = await ch.send(content=text)
            return
        await message.edit(content=text)
                
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if("campaigns" in channel.category.name.lower()):   
            await self.printCampaigns(channel)
            
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if("campaigns" in channel.category.name.lower()):   
            await self.printCampaigns(channel)
            
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if("campaigns" in before.category.name.lower()   and  before.category.name != after.category.name):   
            await self.printCampaigns(before)
    #searches for the last message sent by the bot in case a restart was made
    #Allows it to use it to remove the last post
    async def find_message(self, channel_id):
        #block any check but the first one
        if(not self.past_message_check):
            self.past_message_check= 1
            self.current_message = await discord.utils.get(self.bot.get_channel(channel_id).history(), author__id = self.bot.user.id)
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self,payload):
        await self.role_management_kernel(payload)
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self,payload):
        await self.role_management_kernel(payload)
    
    async def role_management_kernel(self, payload):
        if not str(payload.channel_id) in settingsRecord["Role Channel List"].keys(): 
            return
        guild_id = settingsRecord["Role Channel List"][str(payload.channel_id)]
        guild = self.bot.get_guild(int(guild_id))

        if (str(payload.message_id) in settingsRecord[guild_id]["Messages"].keys()
            and payload.emoji.name in settingsRecord[guild_id]["Messages"][str(payload.message_id)].keys()):
            
            name = settingsRecord[guild_id]["Messages"][str(payload.message_id)][payload.emoji.name]
            role = get(guild.roles, name = name)
            if role is not None:
                member = guild.get_member(payload.user_id)
                if member is not None:
                    has_role = role in member.roles
                    if has_role:
                        action = "remove_roles"
                        extra_text = "You will no longer be pinged for quests of this tier. React with the same emoji if you would like to be pinged for quests of this tier again!"
                        if "Campaign" in role.name:
                            extra_text = "You will no longer be pinged for campaigns on the `#campaign-board` channel. React to the same emoji if you want to be pinged for campaigns!"
                    
                        text = f":tada: ***{member.display_name}***, I have removed the ***{name}*** role from you! {extra_text}"
                    else:
                        action = "add_roles"
                        extra_text = "You will be pinged for quests of this tier. React to the same emoji if you no longer want to be pinged for quests of this tier!"
                        if "Campaign" in role.name:
                            extra_text = "You will be pinged for campaigns on the `#campaign-board` channel. React to the same emoji if you no longer want to be pinged for campaigns!"
                    
                        text = f":tada: ***{member.display_name}***, I have given you the ***{name}*** role! {extra_text}"
                        
                    await getattr(member, action)(role, atomic=True)
                    successMsg = await getattr(member, "send")(text)
                else:
                    print('member not found')
            else:
                print('role not found')

    #A function that grabs all messages in the quest board and compiles a list of availablities
    async def generateMessageText(self, channel_id):
        channel= self.bot.get_channel(channel_id)
        #get all game channel ids
        game_channel_category = self.bot.get_channel(settingsRecord[str(channel.guild.id)]["Game Rooms"])
        game_channel_ids = set(map(lambda c: c.id, game_channel_category.text_channels))
        build_message = "**It is Double DM Rewards Weekend (DDMRW)!**\nGet out there and host some one-shots!\n"*settingsRecord['ddmrw']#+ "The current status of the game channels is:\n"
        #create a dictonary to store the room/user pairs
        tierMap = {"Tier 0" : "T0", "Tier 1" : "T1", "Tier 2" : "T2", "Tier 3" : "T3", "Tier 4" : "T4", "Tier 5" : "T5"}
        emoteMap = settingsRecord[str(channel.guild.id)]["Emotes"]
        channel_dm_dic = {}
        for c in game_channel_category.text_channels:
            channel_dm_dic[c.mention]= ["✅ "+c.mention+": Clear", []]
        #get all posts in the channel
        all_posts = [post async for post in channel.history(oldest_first=True)]
        for elem in all_posts:
            content = elem.content
            #ignore self and Ghost example post
            if(elem.author.id==self.bot.user.id 
                or elem.id == 800644241189503026
                or not isinstance(elem.author, discord.Member)):
                continue
            #loop in order to avoid guild channels blocking the check
            for mention in elem.channel_mentions:
                if mention.id in game_channel_ids:
                    username = elem.author.display_name
                    channel_dm_dic[mention.mention][0] = "❌ "+mention.mention+": "+username
                    tier_list = []
                    system = "5E"
                    systems = re.findall("SYSTEM.*?:.*? (.*?)\n", content, re.IGNORECASE)
                    if len(systems) > 0:
                        system = systems[0]
                    for tierMention in elem.role_mentions:
                        name_split = tierMention.name.split(" ",1)
                        if len(name_split) > 1 and name_split[0] in emoteMap:
                            description_text = name_split[1]
                            if name_split[1] in tierMap:
                                description_text = tierMap[name_split[1]]
                            tier_list.append(emoteMap[name_split[0]]+" "+system+" "+description_text)
                            
                    time_text = ""
                    hammer_times = re.findall("<t:(\\d+)(?::.)?>", content)
                    if hammer_times:
                        time_text = f" - <t:{hammer_times[0]}> [⮥]({elem.jump_url})"
                    else:
                        timing = re.findall("When.*?:.*? (.*?)\n", content)
                        if timing:
                            time_text = (f" - [{timing[0]}⮥]({elem.jump_url})")
                    if tier_list or time_text:
                        channel_dm_dic[mention.mention][1].append("/".join(sorted(tier_list))+ time_text)
        #build the message using the pairs built above
        for c in game_channel_category.text_channels:
            if(c.permissions_for(channel.guild.me).view_channel and c.id != 820394366278697020): 
                tierAddendum = ""
                if(len(channel_dm_dic[c.mention][1])> 0):
                    tierAddendum = "\n       "+"\n       ".join(channel_dm_dic[c.mention][1])
                build_message+=""+channel_dm_dic[c.mention][0]+tierAddendum+"\n"
        build_message = build_message
        post_embed = discord.Embed()
        post_embed.description = build_message
        if len(build_message) > 4000:
            main_text, secondary_text = split_text(build_message, 4000, "❌")
            # then update the text to everything past what we took for the section text
            
            post_embed.description = main_text
            if len(secondary_text) > 1000:
                secondary_text, tertiary_text = split_text(secondary_text, 1000, "❌")
                post_embed.add_field(name="** **", value = secondary_text, inline=False)
                post_embed.add_field(name="** **", value = tertiary_text, inline=False)
            else:
                post_embed.add_field(name="** **", value = secondary_text, inline=False)
            
        return post_embed
    
        
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        #if in the correct channel and the message deleted was not the last QBAP
        if(str(payload.channel_id) in settingsRecord["QB List"].keys() and (not self.current_message or payload.message_id != self.current_message.id)):
            await self.find_message(payload.channel_id)
            #Since we dont know whose post was deleted we need to cover all the posts to find availablities
            #Also protects against people misposting
            postEmbed = await self.generateMessageText(payload.channel_id)
            #if we created the last message during current runtime we can just edit
            if(self.current_message and self.past_message_check != 1):
                await self.current_message.edit(embed=postEmbed)
            else:
                #otherwise delete latest message if possible and resend to get back to the bottom
                if(self.current_message):
                    await self.current_message.delete()
                self.past_message_check = 2
                self.current_message = await self.bot.get_channel(payload.channel_id).send(embed=postEmbed)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if(str(payload.channel_id) in settingsRecord["QB List"].keys() and (not self.current_message or payload.message_id != self.current_message.id)):
            await self.find_message(payload.channel_id)
            
            postEmbed = await self.generateMessageText(payload.channel_id)
            if(self.current_message and self.past_message_check != 1):
                #in case a message is posted without a game channel which is then edited in we need to this extra check
                msgAfter = False
                async for message in self.bot.get_channel(payload.channel_id).history(after=self.current_message, limit=1):
                    msgAfter = True
                if( not msgAfter):
                    await self.current_message.edit(embed=postEmbed)
                else:
                    await self.current_message.delete()
                    self.current_message = await self.current_message.channel.send(embed=postEmbed)
            else:
                self.past_message_check = 2
                if(self.current_message):                
                    msgAfter = False
                    async for message in self.bot.get_channel(payload.channel_id).history(after=self.current_message, limit=1):
                        msgAfter = True
                    if(not msgAfter):
                        await self.current_message.edit(embed=postEmbed)
                        return
                    else:
                        await self.current_message.delete()
                self.current_message = await self.bot.get_channel(payload.channel_id).send(embed=postEmbed)

    @commands.Cog.listener()
    async def on_message(self,msg):
        if msg.guild == None or msg.author.id == self.bot.user.id: 
            return
        tChannel = settingsRecord[str(msg.guild.id)]["QB"]
        if any(word in msg.content.lower() for word in ['uwu', 'owo']):
            await msg.add_reaction('<a:owoo:633820509053648908>')
            await msg.add_reaction('<a:owow:633820509540188176>')
            await msg.add_reaction('<a:owooo:634494313040183316>')
        if any(word in msg.content.lower() for word in ['thank', 'thx', 'gracias', 'danke', 'arigato', 'xie xie', 'merci']) and 'bot' in msg.content.lower():
            await msg.add_reaction('❤️')
            await msg.channel.send("You're welcome friend!")
        elif msg.channel.id == tChannel:
            await self.find_message(msg.channel.id)
            server = msg.guild
            channel = msg.channel
            game_channel_category = server.get_channel(settingsRecord[str(server.id)]["Game Rooms"])
            cMentionArray = msg.channel_mentions
            game_channel_ids = list(map(lambda c: c.id, game_channel_category.text_channels))
            for mention in cMentionArray:
                if mention.id in game_channel_ids:
                    postEmbed = await self.generateMessageText(msg.channel.id)
                    if(self.past_message_check == 2):
                        await self.current_message.delete()
                        self.current_message = await msg.channel.send(embed=postEmbed)
                        return
                    #if there is an old message our record could be out of date so we need to regather info and go to the bottom
                    elif(self.past_message_check == 1 and self.current_message):
                        await self.current_message.delete()
                    self.past_message_check = 2
                    self.current_message = await msg.channel.send(embed=postEmbed)
                    return
            return
async def setup(bot):
    await bot.add_cog(Misc(bot))