import datetime
import logging

import discord
from helpers import *
from discord.ext import commands

date = f'{datetime.datetime.now().year}-{datetime.datetime.now().month}-{datetime.datetime.now().day}'
logging.basicConfig(
    filename=f'logs/{date}.log',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def is_alive(ctx, target):
    roles = target.roles
    logging.info(f'{ctx.guild.name} | {target.name} alive check')
    alive_role = get_config(ctx)['names']['alive_role']
    for x in roles:
        if x.name == alive_role:
            return True
    return False


def is_voting_channel(ctx):
    config = get_config(ctx)
    if ctx.message.channel.name != config['names']['voting_booth']:
        return False
    else:
        return True


class Player(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cheaters = get_cheaters()

    def cog_unload(self):
        save_cheaters(self.cheaters)

    def get_votes_embed(self, ctx):
        embed = discord.Embed(title='Current Votes', color=0xFF0000)
        vote_targets = {}

        votes = get_votes(ctx)
        for voter in votes:
            target = votes[voter]
            if target in vote_targets.keys():
                vote_targets[target].append(voter)
            else:
                vote_targets[target] = [voter]

        for target in vote_targets:
            votes_against = ''
            for voter in vote_targets[target]:
                votes_against += f'{voter}\n'
            embed.add_field(name=f'Votes for {target} ({len(vote_targets[target])})',
                            value=votes_against, inline=False)

        return embed

    def get_signups_embed(self, ctx):
        embed = discord.Embed(title='Current Signups', color=0xFF0000)
        signups = get_signups(ctx)
        signup_message = ''

        for x in signups:
            signup_message += f'{x}\n'

        embed.add_field(name=f'Players ({len(signups)})', value=signup_message)
        return embed

    async def update_vote_message(self, ctx):
        config = get_config(ctx)
        channel_vb = discord.utils.get(ctx.guild.text_channels, name=config['names']['voting_booth'])
        vmessage = await channel_vb.fetch_message(int(config['ids']['vote_message']))
        if not vmessage:
            await ctx.send('Oh, jeez. I had an accident. Can somebody get me an adult? I can\'t find the vote message.')
            return

        await vmessage.edit(content=config['messages']['vb_day'],
                            embed=self.get_votes_embed(ctx))

    async def update_signup_message(self, ctx):
        config = get_config(ctx)
        channel_signup = self.bot.get_channel(int(config['ids']['signup_channel']))
        logging.info(channel_signup)
        smessage = await channel_signup.fetch_message(int(config['ids']['signup_message']))
        if not smessage:
            await ctx.send('Oh, jeez. I had an accident. Can somebody get me an adult? I can\'t find the vote message.')
            return

        await smessage.edit(content=config['messages']['signups'], embed=self.get_signups_embed(ctx))

    @commands.command(help='\'wolf.vote @target_name\' to cast a vote; voting again auto-retracts old vote')
    async def vote(self, ctx):
        voter = ctx.author
        if not is_voting_channel(ctx):
            if ctx.author.name in self.cheaters.keys():
                self.cheaters[f'{ctx.author.name}'] += 1
                await ctx.send(
                    f'Bruh. We\'ve been over this, {ctx.author.mention}. You cannot vote outside of the public voting '
                    f'booth channel. Does that make sense? If you do not understand, go ask a mod so they can '
                    f'explain it to you.'
                )
                await ctx.message.add_reaction('🖕')
                save_cheaters(self.cheaters)
                return
            else:
                self.cheaters[f'{ctx.author.name}'] = 1
                await ctx.send(
                    f'{ctx.author.mention}, please be aware that it is against the rules to vote outside of the '
                    f'voting booth channel. I understand this might not be explicitly stated somewhere, but votes '
                    f'must be public.')
                await ctx.message.add_reaction('❌')
                save_cheaters(self.cheaters)
                return

        if not is_alive(ctx, voter):
            await ctx.message.add_reaction('❌')
            await ctx.send("Only Alive players can vote.")
            return

        if ctx.message.mentions:
            target = ctx.message.mentions[0]
            if target == ctx.author:
                await ctx.message.add_reaction('❌')
                await ctx.send("You can't vote for yourself, dingus.")
                return
        else:
            await ctx.message.add_reaction('❌')
            await ctx.send('Please @ mention the person you want to hang.')
            return

        if not is_alive(ctx, target):
            await ctx.message.add_reaction('❌')
            await ctx.send(f'{voter.mention}, {target.display_name} is not alive.')
            return

        try:
            votes = get_votes(ctx)
            votes[voter.display_name] = target.display_name
            save_votes(ctx, votes)
            await ctx.message.add_reaction('✅')
            await self.update_vote_message(ctx)
        except Exception as e:
            error = f'**ERROR (vote charlie):** {type(e).__name__} - {e}'
            logging.error(error)

    @commands.command(help='\'wolf.retract @target_name\' to retract a vote')
    async def retract(self, ctx):
        voter = ctx.author

        if not is_voting_channel(ctx):
            if ctx.author.name in self.cheaters.keys():
                self.cheaters[f'{ctx.author.name}'] += 1
                await ctx.send(
                    f'Bruh. We\'ve been over this, {ctx.author.mention}. You cannot vote outside of the public voting '
                    f'booth channel. Does that make sense? If you do not understand, go ask a mod so they can '
                    f'explain it to you.'
                )
                await ctx.message.add_reaction('🖕')
                save_cheaters(self.cheaters)
                return
            else:
                self.cheaters[f'{ctx.author.name}'] = 1
                await ctx.send(
                    f'{ctx.author.mention}, please be aware that it is against the rules to vote outside of the '
                    f'voting booth channel. I understand this might not be explicitly stated somewhere, but votes '
                    f'must be public.')
                await ctx.message.add_reaction('❌')
                save_cheaters(self.cheaters)
                return

        if not is_alive(ctx, voter):
            await ctx.message.add_reaction('❌')
            await ctx.send("Only Alive players can vote.")
            return

        votes = get_votes(ctx)
        if votes[voter.display_name]:
            del votes[voter.display_name]
            save_votes(ctx, votes)
            await ctx.message.add_reaction('✅')
            await self.update_vote_message(ctx)
        else:
            await ctx.send(f'I do not see a vote from you, {ctx.author.mention}')
            await ctx.message.add_reaction('❌')

    @commands.command(name='in', help='\'wolf.in\' to sign up')
    async def player_signup(self, ctx):
        config = get_config(ctx)
        voter = ctx.author
        signups = get_signups(ctx)
        member = ctx.author
        memberid = ctx.author.id
        roles = member.roles
        role_names = [role.name for role in roles]

        if "Suspension" in role_names:
            await ctx.send("Listen, <@" + str(memberid) + "> your account’s suspended, so you’re not getting in right now. It sucks, but that’s the reality. You’ll have to wait until the suspension is lifted, and that’s all there is to it. Don’t expect any shortcuts.")
            await ctx.message.add_reaction('❌')
            modchat = self.bot.get_channel(int(1338701247275991058))
            await modchat.send("Hey, <@" + str(memberid) + ">  is trying to sign up but was suspended")

        else:

            await ctx.author.add_roles(discord.utils.get(ctx.guild.roles, name=config['names']['signedup_role']))
            await ctx.author.remove_roles(discord.utils.get(ctx.guild.roles, name=config['names']['spec_role']))

            if voter.display_name in signups:
                await ctx.send('You\'re already signed up!')
                await ctx.message.add_reaction('✅')
            else:
                signups.append(voter.display_name)
                save_signups(ctx, signups)
                await ctx.message.add_reaction('✅')
                await self.update_signup_message(ctx)
    @commands.command(name='altf4', help='\'wolf.altf4\' to see easter egg')
    async def altf4(self, ctx):
        config = get_config(ctx)
        voter = ctx.author
        signups = get_signups(ctx)

        await ctx.send("heh heh, you found the hidden command because there's too many computer stuff in this game")
        
    @commands.command(name='meme', help='\'wolf.meme\' to see meme')
    async def meme(self, ctx):
        config = get_config(ctx)
        voter = ctx.author
        signups = get_signups(ctx)

        await ctx.send("https://imgix.ranker.com/list_img_v2/19375/339375/original/the-very-best-of-the-courage-wolf-meme-u3")


    @commands.command(name='out', help='\'wolf.out\' to opt out')
    async def player_signup_cancel(self, ctx):
        config = get_config(ctx)
        voter = ctx.author
        signups = get_signups(ctx)

        if is_alive(ctx, voter):
            await ctx.send("The game has started, you cannot simply wolf.out now, please contact a mod")

        else:

            await ctx.send("Are you sure you want to quit? Reply with 'yes' or 'no'.")
            msg = await self.bot.wait_for('message', timeout=30.0, check=lambda message: message.author == ctx.author)
            if msg.content.lower() == "yes":
                await ctx.author.remove_roles(discord.utils.get(ctx.guild.roles, name=config['names']['signedup_role']))
                await ctx.author.add_roles(discord.utils.get(ctx.guild.roles, name=config['names']['spec_role']))

                if voter.display_name in signups:
                    signups.remove(voter.display_name)
                    save_signups(ctx, signups)
                    await ctx.send('Maybe next time.')
                    await ctx.message.add_reaction('✅')
                    await self.update_signup_message(ctx)
                else:
                    await ctx.send('I don\'t see you signed up for this game.')
                    await ctx.message.add_reaction('✅')
            else:
                await ctx.send('wolf.out cancelled...')


async def setup(bot):
    await bot.add_cog(Player(bot))
