import discord
import re
import asyncio
from discord.ext import commands
from bfunc import db, roleArray, commandPrefix, tier_reward_dictionary, alphaEmojis, traceback
from cogs.util import checkForChar, calculateTreasure, timeConversion
from random import *

async def randomReward(self,ctx, tier, rewardType, block=[], amount=None, start=None):
        channel = ctx.channel
        author = ctx.author
        rewardCollection = db.rit


        if not block:
            rewardTable = list(rewardCollection.find({"Tier": int(tier), "Minor/Major": rewardType}))
        else:
            rewardTable = list(rewardCollection.find({"Tier": tier, "Minor/Major": rewardType, "Name": {"$nin": block}, "Grouped": {"$nin": block}}))

        if int(amount) > 0:
            if len(rewardTable) < int(amount): # size restriction check if used from rewardtable, which varies based on tier.
                await channel.send(f'Error: You requested more {rewardType} reward items than the Tier {tier} table has available!')
                return None
        else:
            await channel.send(f'Error: You requested an invalid amount of {rewardType} reward items.')
            return None


        randomItem = sample(rewardTable, int(amount)) # Makes a list of all the randomly chosen items. Includes their entire entry, which is needed for special cases of spell scrolls and ammunition
        rewardString = []

        def spellEmbedCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((r.emoji in alphaEmojis[:len(spellClasses)]) or (str(r.emoji) == '❌')) and u == author

        #Puts all rewards into an array
        for i in range(0,int(amount)):
            if not isinstance(randomItem[i]['Name'], str): #If one of the items has subchoices, such as ammunition, only the category will be added instead of an array of all the choices
                temp = sample(randomItem[i]['Name'], 1)[0]
                tempstr = str(temp)
                rewardString.append(tempstr)
            elif 'Spell Scroll' in randomItem[i]['Name']:
                spell = re.findall(r"\d+", randomItem[i]['Name'])

                # create an embed object for user communication
                #extract spell level:
                if len(spell)>0:
                    spellLevel = int(spell[0])
                else:
                    spellLevel = 0
                charEmbed = discord.Embed()
                charEmbed.title = f"{randomItem[i]['Name']}"
                charEmbed.description = f"What class list would you like the spell scroll to be from?"

                #Determine if the scroll level is available to half-casters
                if spellLevel < 1: #all caster list
                    spellClasses = ["Artificer", "Bard", "Cleric", "Druid", "Sorcerer", "Warlock", "Wizard"]
                    charEmbed.add_field(name="Please pick the spell list you want the scroll to be from:", value=f"{alphaEmojis[0]}: Artificer\n{alphaEmojis[1]}: Bard\n{alphaEmojis[2]}: Cleric\n{alphaEmojis[3]}: Druid\n{alphaEmojis[4]}: Sorcerer\n{alphaEmojis[5]}: Warlock\n{alphaEmojis[6]}: Wizard\n", inline=False)
                elif spellLevel < 6: #all caster list
                    spellClasses = ["Artificer", "Bard", "Cleric", "Druid", "Paladin", "Ranger", "Sorcerer", "Warlock", "Wizard"]
                    charEmbed.add_field(name="Please pick the spell list you want the scroll to be from:", value=f"{alphaEmojis[0]}: Artificer\n{alphaEmojis[1]}: Bard\n{alphaEmojis[2]}: Cleric\n{alphaEmojis[3]}: Druid\n{alphaEmojis[4]}: Paladin\n{alphaEmojis[5]}: Ranger\n{alphaEmojis[6]}: Sorcerer\n{alphaEmojis[7]}: Warlock\n{alphaEmojis[8]}: Wizard\n", inline=False)
                else: #full caster list
                    spellClasses = ["Bard", "Cleric", "Druid", "Sorcerer", "Warlock", "Wizard"]
                    charEmbed.add_field(name="Please pick the spell list you want the scroll to be from:", value=f"{alphaEmojis[0]}: Bard\n{alphaEmojis[1]}: Cleric\n{alphaEmojis[2]}: Druid\n{alphaEmojis[3]}: Sorcerer\n{alphaEmojis[4]}: Warlock\n{alphaEmojis[5]}: Wizard\n", inline=False)
                charEmbedmsg = await channel.send(embed=charEmbed)
                await charEmbedmsg.add_reaction('❌')

                try:
                    await charEmbedmsg.edit(embed=charEmbed)
                    await charEmbedmsg.add_reaction('❌')
                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=spellEmbedCheck, timeout=60)
                except asyncio.TimeoutError:
                    await charEmbedmsg.delete()
                    await channel.send(f'Spell list selection timed out! Try again using the same command:\n')
                    #self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                    return None
                else:
                    if tReaction.emoji == '❌':
                        await charEmbedmsg.edit(embed=None, content=f"Spell list selection cancelled.\n")
                        await charEmbedmsg.clear_reactions()
                        #self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx) #error
                        return None
                await charEmbedmsg.clear_reactions()
                classList = spellClasses[alphaEmojis.index(tReaction.emoji)]

                spellCollection = db.spells

                output = list(spellCollection.find({"$and": [{"Classes": {"$regex": classList, '$options': 'i' }, "Level": spellLevel}]}))
                spellReward = sample(output, 1)[0] # results in the entire spell's entry
                spellRewardStr = []  
                spellRewardStr.append(f"Spell Scroll ({spellReward['Name']})")
                await charEmbedmsg.delete()
                rewardString.append(spellRewardStr[0])
            else:
                rewardString.append(randomItem[i]['Name'])

        return rewardString
class Reward(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
    async def cog_command_error(self, ctx, error):
        msg = None
        if isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
             msg = "Your \" placement seems to be messed up.\n"
        elif isinstance(error, commands.BadArgument):
            msg = "A parameter needed to be a number! \n"
        else:
            if isinstance(error, commands.MissingRequiredArgument):
                if error.param.name == 'rewardType':
                    msg = "You are missing the reward type! \n"
                elif error.param.name == 'tier':
                    msg = "You are missing the tier! \n"
                else:
                    msg = "Your command was missing an argument! "
        if msg:
            if ctx.command.name == "prep":
                msg +=  f'Please follow this format:\n```yaml\n{commandPrefix}timer prep "@player1 @player2 [...]" "quest name" #guild-channel-1 #guild-channel-2```'
            
            ctx.command.reset_cooldown(ctx)
            await ctx.channel.send(content=msg)
        else:
            ctx.command.reset_cooldown(ctx)
            await traceBack(ctx,error)
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @commands.command()

    async def reward(self,ctx, timeString=None, tier=None):
        rewardCommand = f"\nPlease follow this format:\n```yaml\n{commandPrefix}reward \"#h#m\" \"tier or character name\"```\n"

        def convert_to_seconds(s):
            return int(s[:-1]) * seconds_per_unit[s[-1]]

        channel = ctx.channel
        author = ctx.author
        charEmbed = discord.Embed()
        charEmbedmsg = None
        char = tier #this is mainly for my sanity
        
        if timeString is None:
            await channel.send(content="Woops, you're forgetting the time duration for the command." + rewardCommand)
            return

        if tier is None:
            await channel.send(content="Woops, you're forgetting the tier or character name for the command. Please try again with 1, 2, 3, or 4 or Junior, Journey, Elite, or True as the tier, or use a character name and" + rewardCommand)
            return

        seconds_per_unit = { "m": 60, "h": 3600 }
        lowerTimeString = timeString.lower()
        
        
        # Converts the time given to data
        l = list((re.findall('.*?[hm]', lowerTimeString)))
        totalTime = 0
        
        # protect from incorrect inputs like #h#m
        try:
            for timeItem in l:
                    totalTime += convert_to_seconds(timeItem)
        except Exception as e:
            totalTime = 0

        if totalTime == 0:
            charEmbed.description = "You may have formatted the time incorrectly or calculated for 0. Try again with the correct format." + rewardCommand
            await channel.send(embed=charEmbed)
            return
        
        characterPresent = False    #base case: No character is given
        
        
        # Checks to see if a tier was given. If there wasn't, it then checks to see if a valid character was given. If not, error.
        if tier not in ('0', '1','2','3','4', '5') and tier.lower() not in [r.lower() for r in roleArray]:
            charDict, charEmbedmsg = await checkForChar(ctx, char, charEmbed)
            if charDict == None:
                charEmbed.description = f"**{tier}** is not a valid tier or character name. Please try again with **New** or **0**, **Junior** or **1**, **Journey** or **2**, **Elite** or **3**, **True** or **4**, or **Ascended** or **5**, or input a valid character name."
                charEmbed.clear_fields()
                
                # reuse the message created by checkForChar
                if charEmbedmsg:
                    await charEmbedmsg.edit(embed=charEmbed)
                else:
                    await channel.send(embed=charEmbed)
                return
            else:
                characterPresent = True
        
        

        # Calculates rewards and output if a tier was given instead of a character
        if not characterPresent:
            tierName = ""
            if tier.isdigit():
                tierName = roleArray[int(tier)]
                tier = tierName
            else:
                tierName = tier.capitalize()

            cp = ((totalTime) // 1800) / 2
            tier = tier.lower()
            tierNum = 0
            if tier == 'junior':
              tierNum = 0
            elif tier == "journey":
              tierNum = 1
            elif tier == "elite":
              tierNum = 2
            elif tier == "true":
              tierNum = 3
            elif tier == "ascended":
              tierNum = 4
            
            gp = cp* tier_reward_dictionary[tierNum][0]
            tp = cp* tier_reward_dictionary[tierNum][1]

            treasureArray = [cp, tp, gp]
            durationString = timeConversion(totalTime)
            treasureString = f"{treasureArray[0]} CP, {treasureArray[1]} TP, and {treasureArray[2]} GP"
            
            charEmbed.description = f"A {durationString} game would give a **{tierName}** Friend:\n{treasureString}"
            charEmbed.clear_fields()
            if charEmbedmsg:
                await charEmbedmsg.edit(embed=charEmbed)
            else:
                await channel.send(embed=charEmbed)
            return
        else:  # Calculates rewards and output if a character was given.
                        

            if charDict["Level"] < 5:
                tierNum = 0
            elif charDict["Level"] < 11:
                tierNum = 1
            elif charDict["Level"] < 17:
                tierNum = 2
            elif charDict["Level"] < 20:
                tierNum = 3
            else:
                tierNum = 4
            
            # Uses calculateTreasure to determine the rewards from the quest based on the character
            treasureArray  = calculateTreasure(charDict["Level"], charDict["CP"] , totalTime)
            durationString = timeConversion(totalTime)
            treasureString = f"{treasureArray[0]} CP, {sum(treasureArray[1].values())} TP, {treasureArray[2]} GP"
            resultLevel = charDict["Level"]
            resultCP = charDict["CP"] + treasureArray[0]
            
            # CP and level calculations
            if resultLevel < 5:
                maxCP = 4
            else:
                maxCP = 10
                
            while(resultCP >= maxCP and resultLevel <20):
                resultCP -= maxCP
                resultLevel += 1
                if resultLevel > 4:
                    maxCP = 10
            
            # A list comprehension that joins together the TP values with their names into one string.
            tpString = ", ".join([f"{value} {key}" for key, value in treasureArray[1].items()])+", "
            
            totalGold = charDict["GP"] + treasureArray[2]
            
            # Final output plugs in the duration string, treasure string, tp string, and other variables to make a coherent output
            charEmbed.description = f"A {durationString} game would give **{charDict['Name']}** \n{treasureString}\n**{charDict['Name']}** will be level {resultLevel} with {resultCP} CP with an additional {tpString}and {totalGold} gold total!"
            charEmbed.clear_fields()
            if charEmbedmsg:
                await charEmbedmsg.edit(embed=charEmbed)
            else:
                await channel.send(embed=charEmbed)
            return
            
    @commands.command()
    async def random(self,ctx, tier, rewardType, size=1):
        rewardCommand = f"\nPlease follow this format:\n```yaml\n{commandPrefix}random tier major/minor #```\n"

        channel = ctx.channel
        author = ctx.author

        if tier not in ('0', '1','2','3','4', '5') and tier.lower() not in [r.lower() for r in roleArray]:
            errorMessage = f"**{tier}** is not a valid tier. Please try again with **New** or **0**, **Junior** or **1**, **Journey** or **2**, **Elite** or **3**, **True** or **4**, or **Ascended** or **5**."
            await channel.send(errorMessage)
            return

        if rewardType.lower() == "major":
            rewardType = "Major"
        elif rewardType.lower() == "minor":
            rewardType = "Minor"
        else:
            await channel.send(content="The reward type must be Major or Minor." + rewardCommand)
            return

        tierNum = 1
        if tier == 'new':
            tierNum = 1
        elif tier == 'junior':
            tierNum = 1
        elif tier == "journey":
            tierNum = 2
        elif tier == "elite":
            tierNum = 3
        elif tier == "true":
            tierNum = 4
        elif tier == "ascended":
            tierNum = 5
        else:
            tierNum = int(tier)
        tierNum = max(tierNum, 1)
        reward = await randomReward(self, ctx, tier=int(tierNum), rewardType=rewardType, amount=size)
        if reward == None:
            return

        outputString = f"{rewardType.capitalize()}s: "+", ".join(reward[i] for i in range(0, len(reward)))

        await channel.send(outputString)
            
async def setup(bot):
    await bot.add_cog(Reward(bot))