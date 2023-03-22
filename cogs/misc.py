import discord
import random
import asyncio
import re
from cogs.view import AlphaView
from cogs.util import admin_or_owner
from discord.utils import get
from discord.ext import commands
from bfunc import settingsRecord, settingsRecord, alphaEmojis, commandPrefix, db, left,right,back

class Misc(commands.Cog):
    def __init__ (self, bot):
    
        self.bot = bot
        self.current_message= None
        #0: No message search so far, 1: Message searched, but no new message made so far, 2: New message made
        self.past_message_check= 0

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @admin_or_owner()
    @commands.command()
    async def uwu(self,ctx):
        channel = ctx.channel
        vowels = ['a','e','i','o','u']
        faces = ['rawr XD', 'OwO', 'owo', 'UwU', 'uwu']
        async with channel.typing():
            async for message in channel.history(before=ctx.message, limit=1, oldest_first=False):
                uwuMessage = message.content.replace('r', 'w')
                uwuMessage = uwuMessage.replace('l', 'w')
                uwuMessage = uwuMessage.replace('ove', 'uv')
                uwuMessage = uwuMessage.replace('.', '!')
                uwuMessage = uwuMessage.replace(' th', ' d')
                uwuMessage = uwuMessage.replace('th', 'f')
                uwuMessage = uwuMessage.replace('mom', 'yeshh')

                for v in vowels:
                  uwuMessage = uwuMessage.replace('n'+ v, 'ny'+v)

        i = 0
        while i < len(uwuMessage):
            if uwuMessage[i] == '!':
                randomFace = random.choice(faces)
                if i == len(uwuMessage):
                    uwuMessage = uwuMessage + ' ' + randomFace
                    break
                else:
                  uwuList = list(uwuMessage)
                  uwuList.insert(i+1, " " + randomFace)
                  uwuMessage = ''.join(uwuList)
                  i += len(randomFace)
            i += 1
            

        await channel.send(content=message.author.display_name + ":\n" +  uwuMessage)
        await ctx.message.delete()
        
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
        text += (" | ").join(map(lambda c: c.mention, filtered))
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
        tChannel = channel_id
        channel= self.bot.get_channel(tChannel)
        #get all game channel ids
        game_channel_category =self.bot.get_channel(settingsRecord[str(channel.guild.id)]["Game Rooms"])
        game_channel_ids = set(map(lambda c: c.id, game_channel_category.text_channels))
        build_message = "**It is Double DM Rewards Weekend (DDMRW)!** Get out there and host some one-shots!\n"*settingsRecord['ddmrw']#+ "The current status of the game channels is:\n"
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
                    username = elem.author.name
                    if(elem.author.nick):
                        username = elem.author.nick
                    channel_dm_dic[mention.mention][0] = "❌ "+mention.mention+": "+username
                    tier_list = []
                    for tierMention in elem.role_mentions:
                        name_split = tierMention.name.split(" ",1)
                        if tierMention.name.split(" ",1)[1] in tierMap:
                            tier_list.append(emoteMap[tierMention.name.split(" ",1)[0]]+" "+tierMap[tierMention.name.split(" ",1)[1]])
                    time_text = ""
                    hammer_times = re.findall("<t:(\\d+)(?::.)?>", content)
                    if hammer_times:
                        time_text = f" - <t:{hammer_times[0]}>"
                    else:
                        timing = re.findall("When.*?:.*? (.*?)\n", content)
                        if timing:
                            time_text = f" - {timing[0]}"
                    if tier_list or time_text:
                        channel_dm_dic[mention.mention][1].append("/".join(sorted(tier_list))+ time_text)
        #build the message using the pairs built above
        for c in game_channel_category.text_channels:
            if(c.permissions_for(channel.guild.me).view_channel and c.id != 820394366278697020): 
                tierAddendum = ""
                if(len(channel_dm_dic[c.mention][1])> 0):
                    tierAddendum = "\n       "+"\n       ".join(channel_dm_dic[c.mention][1])
                build_message+=""+channel_dm_dic[c.mention][0]+tierAddendum+"\n"
        return build_message
    
        
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        #if in the correct channel and the message deleted was not the last QBAP
        if(str(payload.channel_id) in settingsRecord["QB List"].keys() and (not self.current_message or payload.message_id != self.current_message.id)):
            await self.find_message(payload.channel_id)
            #Since we dont know whose post was deleted we need to cover all the posts to find availablities
            #Also protects against people misposting
            new_text = await self.generateMessageText(payload.channel_id)
            #if we created the last message during current runtime we can just edit
            if(self.current_message and self.past_message_check != 1):
                await self.current_message.edit(content=new_text)
            else:
                #otherwise delete latest message if possible and resend to get back to the bottom
                if(self.current_message):
                    await self.current_message.delete()
                self.past_message_check = 2
                self.current_message = await self.bot.get_channel(payload.channel_id).send(content=new_text)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
    
        if(str(payload.channel_id) in settingsRecord["QB List"].keys() and (not self.current_message or payload.message_id != self.current_message.id)):
            await self.find_message(payload.channel_id)
            new_text = await self.generateMessageText(payload.channel_id)
            if(self.current_message and self.past_message_check != 1):
                #in case a message is posted without a game channel which is then edited in we need to this extra check
                msgAfter = False
                async for message in self.bot.get_channel(payload.channel_id).history(after=self.current_message, limit=1):
                    msgAfter = True
                if( not msgAfter):
                    await self.current_message.edit(content=new_text)
                else:
                    await self.current_message.delete()
                    self.current_message = await self.current_message.channel.send(content=new_text)
            else:
                self.past_message_check = 2
                if(self.current_message):                
                    msgAfter = False
                    async for message in self.bot.get_channel(payload.channel_id).history(after=self.current_message, limit=1):
                        msgAfter = True
                    if(not msgAfter):
                        await self.current_message.edit(content=new_text)
                        return
                    else:
                        await self.current_message.delete()
                self.current_message = await self.bot.get_channel(payload.channel_id).send(content=new_text)

    @commands.Cog.listener()
    async def on_message(self,msg):
        if msg.guild == None: 
            return
        tChannel = settingsRecord[str(msg.guild.id)]["QB"]
        if any(word in msg.content.lower() for word in ['thank', 'thanks', 'thank you', 'thx', 'gracias', 'danke', 'arigato', 'xie xie', 'merci']) and 'bot' in msg.content.lower():
            await msg.add_reaction('❤️')
            await msg.channel.send("You're welcome friend!")
        elif msg.channel.id == tChannel and msg.author.id != self.bot.user.id:

            await self.find_message(msg.channel.id)
            server = msg.guild
            channel = msg.channel
            game_channel_category = server.get_channel(settingsRecord[str(server.id)]["Game Rooms"])
            cMentionArray = msg.channel_mentions
            game_channel_ids = list(map(lambda c: c.id, game_channel_category.text_channels))
            for mention in cMentionArray:
                if mention.id in game_channel_ids:
                    new_text = await self.generateMessageText(channel.id)
                    if(self.past_message_check == 2):
                        await self.current_message.delete()
                        self.current_message = await msg.channel.send(content=new_text)
                        return
                    #if there is an old message our record could be out of date so we need to regather info and go to the bottom
                    elif(self.past_message_check == 1 and self.current_message):
                        await self.current_message.delete()
                    self.past_message_check = 2
                    self.current_message = await msg.channel.send(content=new_text)
                    return
            return
async def setup(bot):
    await bot.add_cog(Misc(bot))