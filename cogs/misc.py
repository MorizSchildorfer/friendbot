import discord
import random
import asyncio
from discord.utils import get
from discord.ext import commands
from bfunc import settingsRecord

def admin_or_owner():
    async def predicate(ctx):
        
        role = get(ctx.message.guild.roles, name = "A d m i n")
        output = (role in ctx.message.author.roles) or ctx.message.author.id in [220742049631174656, 203948352973438995]
        return  output
    return commands.check(predicate)

class Misc(commands.Cog):
    def __init__ (self, bot):
    
        self.tMessages = [776980963325771777, 776980983232331788]
        self.system_dict = {776980963325771777: "", 776980983232331788: "F "}
        self.bot = bot
        self.current_message= None
        #0: No message search so far, 1: Message searched, but no new message made so far, 2: New message made
        self.past_message_check= 0
        self.quest_board_channel_id = 728476108940640297 #382027190633627649 728476108940640297
        self.category_channel_id = 728456686024523810 #382027737189056544  728456686024523810

    @commands.cooldown(1, 60, type=commands.BucketType.member)
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
    
        #searches for the last message sent by the bot in case a restart was made
    #Allows it to use it to remove the last post
    async def find_message(self):
        #block any check but the first one
        if(not self.past_message_check):
            self.past_message_check= 1
            self.current_message = await self.bot.get_channel(self.quest_board_channel_id).history().get(author__id = self.bot.user.id)
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self,payload):
        #[758144721423433728, 776980983232331788] 
        #[650482015342166036]
        guild = self.bot.get_guild(payload.guild_id)

        if payload.message_id in self.tMessages:
            if payload.emoji.name == "1️⃣":
                name = 'Tier 1' 
            elif payload.emoji.name == "2️⃣":
                name = 'Tier 2' 
            elif payload.emoji.name == "3️⃣":
                name = 'Tier 3' 
            elif payload.emoji.name == "4️⃣":
                name = 'Tier 4' 
            elif payload.emoji.name == "5️⃣" :
                name = 'Tier 5' 
            elif payload.emoji.name == "0️⃣":
                name = 'Tier 0' 
            else:
                return
            
            name = self.system_dict[payload.message_id]+name     
            role = get(guild.roles, name = name)
            if role is not None:
                member = guild.get_member(payload.user_id)
                if member is not None:
                    await member.remove_roles(role)
                    successMsg = await member.send(f":tada: ***{member.display_name}***, I have removed the ***{name}*** role from you! You will no longer be pinged for quests of this tier. React to the same emoji if you would like to be pinged for quests of this tier again!")
                else:
                    print('member not found')
            else:
                print('role not found')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self,payload):
        guild = self.bot.get_guild(payload.guild_id)
        if payload.message_id in self.tMessages:
            if payload.emoji.name == "1️⃣":
                name = 'Tier 1' 
            elif payload.emoji.name == "2️⃣":
                name = 'Tier 2' 
            elif payload.emoji.name == "3️⃣":
                name = 'Tier 3' 
            elif payload.emoji.name == "4️⃣":
                name = 'Tier 4' 
            elif payload.emoji.name == "5️⃣" :
                name = 'Tier 5' 
            elif payload.emoji.name == "0️⃣":
                name = 'Tier 0' 
            else:
                return
            
            name = self.system_dict[payload.message_id]+name    
            print(name)
            role = get(guild.roles, name = name)    

            if role is not None:
                member = guild.get_member(payload.user_id)

                if member is not None:
                    await member.add_roles(role)
                    successMsg = await member.send(f":tada: ***{member.display_name}***, I have given you the ***{name}*** role! You will be pinged for quests of this tier. React to the same emoji if you would not like to be pinged for quests of this tier!")

                        
                else:
                    print('member not found')
            else:
                print('role not found')
    
    #A function that grabs all messages in the quest board and compiles a list of availablities
    async def generateMessageText(self):
        tChannel = self.quest_board_channel_id
        channel= self.bot.get_channel(tChannel)
        #get all game channel ids
        game_channel_category =self.bot.get_channel(self.category_channel_id)
        game_channel_ids = set(map(lambda c: c.id, game_channel_category.text_channels))
        build_message = "**It is DDMRW** get out there and play some games!\n"*settingsRecord['ddmrw']+ "The current status of the game channels is:\n"
        #create a dictonary to store the room/user pairs
        tierMap = {"Tier 0" : "T0", "Tier 1" : "T1", "Tier 2" : "T2", "Tier 3" : "T3", "Tier 4" : "T4", "Tier 5" : "T5"}
        emoteMap = {"Roll20" : "<:adorabat:733763021008273588>", "Foundry" : ":dagger:"}
        channel_dm_dic = {}
        for c in game_channel_category.text_channels:
            channel_dm_dic[c.mention]= ["✅ "+c.mention+": Clear", set([])]
        #get all posts in the channel
        all_posts = await channel.history(oldest_first=True).flatten()
        for elem in all_posts:
            #ignore self and Ghost example post
            if(elem.author.id==self.bot.user.id or elem.id == 540049894598246420):
                continue
            #loop in order to avoid guild channels blocking the check
            for mention in elem.channel_mentions:
                if mention.id in game_channel_ids:
                    username = elem.author.name
                    if(elem.author.nick):
                        username = elem.author.nick
                    channel_dm_dic[mention.mention][0] = "❌ "+mention.mention+": "+username
                    for tierMention in elem.role_mentions:
                        name_split = tierMention.name.split(" ",1)
                        print(tierMention)
                        print("Split",)
                        if tierMention.name.split(" ",1)[1] in tierMap:
                            channel_dm_dic[mention.mention][1].add(emoteMap[tierMention.name.split(" ",1)[0]]+" "+tierMap[tierMention.name.split(" ",1)[1]])
        #build the message using the pairs built above
        for c in game_channel_category.text_channels:
            print(c, c.permissions_for(channel.guild.me).view_channel)
            if(c.permissions_for(channel.guild.me).view_channel):
                tierAddendum = ""
                if(len(channel_dm_dic[c.mention][1])> 0):
                    tierAddendum = " - "+"/".join(sorted(channel_dm_dic[c.mention][1]))
                build_message+=channel_dm_dic[c.mention][0]+tierAddendum+"\n"
        return build_message
    
        
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        tChannel = self.quest_board_channel_id

        #if in the correct channel and the message deleted was not the last QBAP
        if(payload.channel_id==tChannel and (not self.current_message or payload.message_id != self.current_message.id)):
            await self.find_message()
            #Since we dont know whose post was deleted we need to cover all the posts to find availablities
            #Also protects against people misposting
            new_text = await (self.generateMessageText)()
            #if we created the last message during current runtime we can just edit
            if(self.current_message and self.past_message_check != 1):
                await self.current_message.edit(content=new_text)
            else:
                #otherwise delete latest message if possible and resend to get back to the bottom
                if(self.current_message):
                    await self.current_message.delete()
                self.past_message_check = 2
                self.current_message = await self.bot.get_channel(self.quest_board_channel_id).send(content=new_text)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
    
        tChannel = self.quest_board_channel_id
        if(int(payload.data["channel_id"])==tChannel and (not self.current_message or payload.message_id != self.current_message.id)):
            await self.find_message()
            new_text = await (self.generateMessageText)()
            if(self.current_message and self.past_message_check != 1):
                #in case a message is posted without a game channel which is then edited in we need to this extra check
                msgAfter = False
                async for message in self.bot.get_channel(self.quest_board_channel_id).history(after=self.current_message, limit=1):
                    msgAfter = True
                if( not msgAfter):
                    await self.current_message.edit(content=new_text)
                else:
                    await self.current_message.delete()
                    self.current_message = await self.current_message.send(content=new_text)
            else:
                self.past_message_check = 2
                if(self.current_message):                
                    msgAfter = False
                    async for message in self.bot.get_channel(self.quest_board_channel_id).history(after=self.current_message, limit=1):
                        msgAfter = True
                    if(not msgAfter):
                        await self.current_message.edit(content=new_text)
                        return
                    else:
                        await self.current_message.delete()
                self.current_message = await self.bot.get_channel(self.quest_board_channel_id).send(content=new_text)

    @commands.Cog.listener()
    async def on_message(self,msg):
        tChannel = self.quest_board_channel_id
        if(msg.type.value == 7):
            await msg.add_reaction('👋')
        #check if any tier boost was done and react
        elif(7 < msg.type.value and msg.type.value < 12):
            await msg.add_reaction('<:boost:585637770970660876>')
        elif any(word in msg.content.lower() for word in ['thank', 'thanks', 'thank you', 'thx', 'gracias', 'danke', 'arigato', 'xie xie', 'merci']) and 'bot friend' in msg.content.lower():
            await msg.add_reaction('❤️')
            await msg.channel.send("You're welcome friend!")
        elif msg.channel.id == tChannel and msg.author.id != self.bot.user.id:

            await self.find_message()
            server = msg.guild
            channel = msg.channel
            game_channel_category = server.get_channel(self.category_channel_id)
            cMentionArray = msg.channel_mentions
            game_channel_ids = list(map(lambda c: c.id, game_channel_category.text_channels))
            for mention in cMentionArray:
                if mention.id in game_channel_ids:
                    new_text = await (self.generateMessageText)()
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

        
def setup(bot):
    bot.add_cog(Misc(bot))
