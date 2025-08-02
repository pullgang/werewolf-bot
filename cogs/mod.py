import datetime
import logging
import pytz
import collections
import discord
import asyncio
import os
import time
from helpers import *
from discord.ext import commands

date = f'{datetime.datetime.now().year}-{datetime.datetime.now().month}-{datetime.datetime.now().day}'
logging.basicConfig(
    filename=f'logs/{date}.log',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        if not signups:
            signup_message += 'No signups, yet'
        else:
            for x in signups:
                signup_message += f'{x}\n'

        embed.add_field(name=f'Players ({len(signups)})', value=signup_message)
        return embed

    async def is_mod(self, ctx):
        member = ctx.author
        roles = member.roles
        logging.info(f'{ctx.guild.name} | {member.name} mod check')
        if await self.bot.is_owner(member):
            return True
        else:
            try:
                alive_role = get_config(ctx)['names']['mod_role']
                for x in roles:
                    if x.name == alive_role:
                        return True
                return False
            except Exception as e:
                error = f'**ERROR (is_mod alpha):** {type(e).__name__} - {e}'
                logging.info(error)
                return False

    async def update_vote_message(self, ctx):
        config = get_config(ctx)
        channel_vb = discord.utils.get(ctx.guild.text_channels, name=config['names']['voting_booth'])
        vmessage = await channel_vb.fetch_message(int(config['ids']['vote_message']))
        logging.info(f'vmessage: {vmessage}')
        if not vmessage:
            await ctx.send('Oh, jeez. I had an accident. Can somebody get me an adult? I can\'t find the vote message.')
            return

        await vmessage.edit(content=config['messages']['vb_day'],
                            embed=self.get_votes_embed(ctx))

    async def update_signup_message(self, ctx):
        config = get_config(ctx)
        channel_signup = discord.utils.get(ctx.guild.text_channels, name=config['ids']['signup_channel'])
        smessage = await channel_signup.fetch_message(int(config['ids']['signup_message']))
        if not smessage:
            await ctx.send('Oh, jeez. I had an accident. Can somebody get me an adult? I can\'t find the vote message.')
            return

        await smessage.edit(content=config['messages']['signups'], embed=self.get_signups_embed(ctx))

    @commands.command(help='Mod command to open voting and update channel permissions')
    async def day(self, ctx):
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{get_config(ctx)["messages"]["mod_check"]}')
            return

        logging.info(f'{ctx.guild.name} | Running day steps for {ctx.author.name}')

        config = get_config(ctx)
        role_alive = discord.utils.get(ctx.guild.roles, name=config['names']['alive_role'])

        # Update the voting booth channel
        try:
            channel_vb = discord.utils.get(ctx.guild.text_channels, name=config['names']['voting_booth'])

            await channel_vb.set_permissions(
                role_alive,
                send_messages=config['toggles']['voting_booth'] == 'day-only' or config['toggles']['voting_booth'] == 'always-on',
                read_messages=True
            )
            vmessage = await channel_vb.send(config['messages']['vb_day'])
            config['ids']['vote_message'] = str(vmessage.id)
            save_config(ctx, config)
        except Exception as e:
            error = f'**ERROR (day bravo):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'Yikes. I couldn\'t update {config["names"]["voting_booth"]}')

        # Pin the vote message
        try:
            await vmessage.pin()
        except Exception as e:
            error = f'***ERROR (day delta):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'I was not able to pin the voting booth message.')

        # Update the townsquare channel
        try:
            channel_ts = discord.utils.get(ctx.guild.text_channels, name=config['names']['townsquare'])

            await channel_ts.set_permissions(
                role_alive,
                send_messages=config['toggles']['voting_booth'] == 'day-only' or config['toggles']['townsquare'] == 'always-on',
                read_messages=True
            )
            await channel_ts.send(config['messages']['ts_day'])
        except Exception as e:
            error = f'**ERROR (day charlie):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'Yikes. I couldn\'t update {config["names"]["townsquare"]}')

        # Update the couple chat channel
        try:
            channel_cc = discord.utils.get(ctx.guild.text_channels, name=config['names']['couple_chat'])

            await channel_cc.set_permissions(
                role_alive,
                send_messages=config['toggles']['couple_chat'] == 'day-only' or config['toggles']['couple_chat'] == 'always-on',
                read_messages=False
            )
            await channel_cc.send(config['messages']['cc_day'])
        except Exception as e:
            error = f'**ERROR (day charlie):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'Yikes. I couldn\'t update {config["names"]["couple_chat"]}')

        # Find the mod channel
        try:
            channel_mod = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])
        except Exception as e:
            error = f'**ERROR (day alpha):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'I couldn\'t find the mod-chat channel. '
                           f'Please double check the name listed in settings.')
            return

        # Clear out votes
        save_votes(ctx, {})
        await channel_mod.send(f'Just set day permissions for {ctx.author.name}.')

    @commands.command(help='Mod command to set a delay and update channel permissions')
    async def lock(self, ctx):
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{get_config(ctx)["messages"]["mod_check"]}')
            return

        logging.info(f'{ctx.guild.name} | Running lock steps for {ctx.author.name}')

        config = get_config(ctx)
        role_alive = discord.utils.get(ctx.guild.roles, name=config['names']['alive_role'])


        # Update the townsquare channel
        logging.info(f'{ctx.guild.name} | locking townsquare channel')
        try:
            channel_ts = discord.utils.get(ctx.guild.text_channels, name=config['names']['townsquare'])

            await channel_ts.set_permissions(
                role_alive,
                send_messages=False,
                read_messages=True
            )
            await channel_ts.send("Lockdown set for townsquare, will remove in 5 minutes.")
        except Exception as e:
            error = f'**ERROR (night charlie):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'Yikes. I couldn\'t update {config["names"]["townsquare"]}')

        # Find the mod channel
        logging.info(f'{ctx.guild.name} | Getting mod channel')
        try:
            channel_mod = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])
        except Exception as e:
            error = f'**ERROR (day alpha):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'I couldn\'t find the mod-chat channel. '
                           f'Please double check the name listed in settings.')
            return

        await channel_mod.send(f'Just set locks for {ctx.author.name}.')
        time.sleep(300)
        try:
            channel_ts = discord.utils.get(ctx.guild.text_channels, name=config['names']['townsquare'])

            await channel_ts.set_permissions(
                role_alive,
                send_messages=True,
                read_messages=True
            )
            await channel_ts.send("Lockdown complete.")
        except Exception as e:
            error = f'**ERROR (night charlie):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'Yikes. I couldn\'t update {config["names"]["townsquare"]}')
        await channel_mod.send(f'Lock Complete')

        

    @commands.command(help='Mod command to close voting and update channel permissions')
    async def night(self, ctx):
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{get_config(ctx)["messages"]["mod_check"]}')
            return

        logging.info(f'{ctx.guild.name} | Running night steps for {ctx.author.name}')

        config = get_config(ctx)
        role_alive = discord.utils.get(ctx.guild.roles, name=config['names']['alive_role'])

        # Unpin the vote message
        try:
            channel_vb = discord.utils.get(ctx.guild.text_channels, name=config['names']['voting_booth'])
            vmessage = await channel_vb.fetch_message(int(config['ids']['vote_message']))
            await vmessage.unpin()
        except Exception as e:
            error = f'**ERROR (night echo):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'Ope, I was not able to unpin the last vote message.')

        # Update the voting booth channel
        logging.info(f'{ctx.guild.name} | Starting voting booth channel')
        try:
            channel_vb = discord.utils.get(ctx.guild.text_channels, name=config['names']['voting_booth'])

            await channel_vb.set_permissions(
                role_alive,
                send_messages=config['toggles']['voting_booth'] == 'night-only' or config['toggles']['voting_booth'] == 'always-on',
                read_messages=True
            )
            await channel_vb.send(config['messages']['vb_night'])
            config['ids']['vote_message'] = str(0)
            save_config(ctx, config)
        except Exception as e:
            error = f'**ERROR (night bravo):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'Yikes. I couldn\'t update {config["names"]["voting_booth"]}')

        # Update the townsquare channel
        logging.info(f'{ctx.guild.name} | Starting townsquare channel')
        try:
            channel_ts = discord.utils.get(ctx.guild.text_channels, name=config['names']['townsquare'])

            await channel_ts.set_permissions(
                role_alive,
                send_messages=config['toggles']['voting_booth'] == 'night-only' or config['toggles']['townsquare'] == 'always-on',
                read_messages=True
            )
            await channel_ts.send(config['messages']['ts_night'])
        except Exception as e:
            error = f'**ERROR (night charlie):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'Yikes. I couldn\'t update {config["names"]["townsquare"]}')

        # Update the couple chat channel
        logging.info(f'{ctx.guild.name} | Starting couple chat channel')
        try:
            channel_cc = discord.utils.get(ctx.guild.text_channels, name=config['names']['couple_chat'])

            await channel_cc.set_permissions(
                role_alive,
                send_messages=config['toggles']['couple_chat'] == 'night-only' or config['toggles']['couple_chat'] == 'always-on',
                read_messages=False
            )
            await channel_cc.send(config['messages']['cc_night'])
        except Exception as e:
            error = f'**ERROR (night delta):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'Yikes. I couldn\'t update {config["names"]["couple_chat"]}')

        # Find the mod channel
        logging.info(f'{ctx.guild.name} | Getting mod channel')
        try:
            channel_mod = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])
        except Exception as e:
            error = f'**ERROR (day alpha):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'I couldn\'t find the mod-chat channel. '
                           f'Please double check the name listed in settings.')
            return

        # Clear out votes
        logging.info(f'{ctx.guild.name} | Clearing votes')
        await channel_mod.send(content='Final vote count', embed=self.get_votes_embed(ctx))
        save_votes(ctx, {})
        await channel_mod.send(f'Just set night permissions for {ctx.author.name}.')

    @commands.command(help='Mod command to have current votes posted in mod-chat')
    async def votelist(self, ctx):
        config = get_config(ctx)
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return

        mod_chat = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])
        await mod_chat.send(content=None, embed=self.get_votes_embed(ctx))

    @commands.command(help='Mod command to clear all votes')
    async def clearvotes(self, ctx):
        config = get_config(ctx)
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return

        channel_mod = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])
        await channel_mod.send(content='Votes prior to clearing:', embed=self.get_votes_embed(ctx))
        save_votes(ctx, {})
        await channel_mod.send(f'Just reset the votes')
        await self.update_vote_message(ctx)
    @commands.command(help='So, you broke the settings again')
    async def ibrokeit(self, ctx):
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return
        await ctx.send("https://i.pinimg.com/originals/a5/99/aa/a599aa5352bd44e30c3c9bfed12a8ef2.gif")
        await ctx.send("So, you broke the settings again, lemme get that reset for ya")
        if os.path.exists(f'configs/{ctx.guild.id}_config.ini'):
            print("This should work")
            os.remove(f'configs/{ctx.guild.id}_config.ini')
        else:
            print("Keep debugging, boy")
            #os.remove("C:\Users\then3\Downloads\WerewolfMod-main\WerewolfMod-main\configs\1215796933130588291_config.ini")
            
        await ctx.send("All set, be better next time, okay?")
        await ctx.send("https://gifdb.com/images/high/steve-rogers-captain-america-smile-thumbs-up-l7sytvaa1xgz90mx.gif")
        
            

    @commands.group(help='Chain of commands to view and change settings. \'wolf.settings <group> <entry>\'')
    async def settings(self, ctx):
        config = get_config(ctx)
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return

        if ctx.invoked_subcommand is None:
            channel_mod = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])

            embed = discord.Embed(title='WolfMod Settings Help', color=0xADABE2,
                                  description='Enter "wolf.settings <group> <entry> <value>"')
            embed.add_field(
                name='Groups:',
                value="- names: Set channel and role names\n" +
                      "- messages: Set day/night messages\n" +
                      "- toggles: Set day/night-only or always/never-on\n" +
                      "- show: Displays current settings",
                inline=False
            )
            embed.add_field(
                name='Examples:',
                value='- wolf.settings names alive_role Alive\n' +
                      '- wolf.settings names couple_chat couple-chat\n' +
                      '- wolf.settings messages vb_day "The voting booth is open."\n' +
                      '- wolf.settings toggles townsquare always-on\n' +
                      '- wolf.settings show',
                inline=False
            )
            embed.add_field(name='Full settings:', value='Run "wolf.settings show" for full settings.')
            await channel_mod.send(content=None, embed=embed)

    @settings.command(help='\'wolf.setting show\' Mod command to have all settings posted in mod-chat')
    async def show(self, ctx):
        config = get_config(ctx)
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return

        names_message = ""
        messages_message = ""
        toggles_message = ""
        ids_message = ""

        for key in config['names']:
            names_message += f'{key} = {config["names"][key]}\n'
        for key in config['messages']:
            messages_message += f'{key} = {config["messages"][key]}\n'
        for key in config['toggles']:
            toggles_message += f'{key} = {config["toggles"][key]}\n'
        for key in config['ids']:
            ids_message += f'{key} = {config["ids"][key]}\n'

        embed = discord.Embed(title='WolfMod Settings', color=0xADABE2)
        embed.add_field(name='Names:', value=names_message, inline=False)
        embed.add_field(name='Messages:', value=messages_message, inline=False)
        embed.add_field(name='Toggles:', value=toggles_message, inline=False)
        embed.add_field(name='Ids:', value=ids_message, inline=False)

        channel_mod = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])
        await channel_mod.send(content=None, embed=embed)

    @settings.command()
    async def names(self, ctx, name: str, value: str):
        config = get_config(ctx)
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return

        channel_mod = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])

        if name in config['names']:
            config['names'][name] = value
            save_config(ctx, config)

            logging.info(f'{ctx.guild.name} | Updated name ({name}) to: {value}')
            await channel_mod.send(f'Updated name ({name}) to: {value}')
        else:
            await channel_mod.send(f'**{name}** is not an available option.'
                                   f'Run wolf.settings show to see available options.')

    @settings.command()
    async def messages(self, ctx, name: str, value: str):
        config = get_config(ctx)
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return

        channel_mod = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])

        if name in config['messages'] and name != 'mod_role':
            config['messages'][name] = value
            save_config(ctx, config)

            logging.info(f'{ctx.guild.name} | Updated name ({name}) to: {value}')
            await channel_mod.send(f'Updated name ({name}) to: {value}')
        else:
            await channel_mod.send(f'**{name}** is not an available option.'
                                   f'Run wolf.settings show to see available options.')

    @settings.command()
    async def toggles(self, ctx, name: str, value: str):
        config = get_config(ctx)
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return

        channel_mod = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])

        if name in config['toggles'] and name != 'mod_role':
            config['toggles'][name] = value
            save_config(ctx, config)

            logging.info(f'{ctx.guild.name} | Updated name ({name}) to: {value}')
            await channel_mod.send(f'Updated name ({name}) to: {value}')
        else:
            await channel_mod.send(f'**{name}** is not an available option.'
                                   f'Run wolf.settings show to see available options.')

    @settings.command()
    async def ids(self, ctx, name: str, value: str):
        config = get_config(ctx)
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return

        channel_mod = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])

        if name in config['ids'] and name != 'mod_role':
            config['ids'][name] = value
            save_config(ctx, config)

            logging.info(f'{ctx.guild.name} | Updated name ({name}) to: {value}')
            await channel_mod.send(f'Updated name ({name}) to: {value}')
        else:
            await channel_mod.send(f'**{name}** is not an available option.'
                                   f'Run wolf.settings show to see available options.')

    @commands.command(help='Removes Alive and Dead roles and assigns Spectator')
    async def endgame(self, ctx):
        config = get_config(ctx)
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return

        mod_role = discord.utils.get(ctx.guild.roles, name=config['names']['mod_role'])
        await ctx.send(f'{mod_role.mention}\nAre you sure you want to end the game? Make sure all roles are set '
                       f'in the settings.\n\nIf you are ready, please type \'YES\' to confirm.')

        def check(mes):
            return mes.author == ctx.author and mes.content.upper() == 'YES'

        try:
            resp = await self.bot.wait_for('message', check=check, timeout=15.0)
        except asyncio.TimeoutError:
            logging.error(f'{ctx.guild.name} | Timeout on the endgame command.')
            return

        # Remove Alive/Dead roles and apply Spectator
        await ctx.send(f'Removing Alive and Dead roles.')
        await ctx.send(f'Assigning Spectator roles.')

        try:
            dead_role = discord.utils.get(ctx.guild.roles, name=config['names']['dead_role'])
        except Exception as e:
            await ctx.send(f'I couldn\'t find the dead role. Please check the name and run endgame again.')
            return
        try:
            alive_role = discord.utils.get(ctx.guild.roles, name=config['names']['alive_role'])
        except Exception as e:
            await ctx.send(f'I couldn\'t find the alive role. Please check the name and run endgame again.')
            return
        try:
            spec_role = discord.utils.get(ctx.guild.roles, name=config['names']['spec_role'])
        except Exception as e:
            await ctx.send(f'I couldn\'t find the spectator role. Please check the name and run endgame again.')
            return

        async for x in ctx.guild.fetch_members():
            try:
                if not x.bot:
                    await x.remove_roles(alive_role, dead_role)
                    await x.add_roles(spec_role)
            except discord.HTTPException as e:
                error = f'**ERROR (endgame bravo):** {type(e).__name__} - {e}'
                logging.error(error)
                await ctx.send(f'Failed modifying roles. This might be ugly:\n\n{error}')
            except Exception as e:
                error = f'**ERROR (endgame alpha):** {type(e).__name__} - {e}'
                logging.error(error)
                await ctx.send(f'Ran into an error. This might be ugly:\n\n{error}')
                await ctx.send(f'All done!')

        await ctx.send('All done!')

    @commands.command(help='Mod command to open up signups for a new game')
    async def signups(self, ctx):
        config = get_config(ctx)
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return
        channel_mod = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])

        if ctx.channel == channel_mod:
            await ctx.message.add_reaction('❌')
            await ctx.send('Run this command in the signups channel.')
            return

        signup_message = await ctx.send(config['messages']['signups'])

        config['ids']['signup_message'] = str(signup_message.id)
        config['ids']['signup_channel'] = str(ctx.channel.id)
        save_config(ctx, config)
        save_signups(ctx, [])

        await channel_mod.send('Just opened up signups. Run \'wolf.inlist\' to see who has signed up.')

    @commands.command(help='Mod command to check signups')
    async def inlist(self, ctx):
        config = get_config(ctx)
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return

        mod_chat = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])
        await mod_chat.send(content=None, embed=self.get_signups_embed(ctx))

    @commands.command(help='Convert Signed Up player to Alive')
    async def startgame(self, ctx):
        config = get_config(ctx)
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return

        mod_role = discord.utils.get(ctx.guild.roles, name=config['names']['mod_role'])
        await ctx.send(f'{mod_role.mention}\nAre you sure you want to start the game? Make sure all roles are set '
                       f'in the settings.\n\nIf you are ready, please type \'YES\' to confirm.')

        def check(mes):
            return mes.author == ctx.author and mes.content.upper() == 'YES'

        try:
            resp = await self.bot.wait_for('message', check=check, timeout=15.0)
        except asyncio.TimeoutError:
            logging.error(f'{ctx.guild.name} | Timeout on the startgame command.')
            return

        try:
            logging.info('Starting to flip roles now')
            # Remove Alive/Dead roles and apply Spectator
            signedup_role = discord.utils.get(ctx.guild.roles, name=config['names']['signedup_role'])
            alive_role = discord.utils.get(ctx.guild.roles, name=config['names']['alive_role'])
            spec_role = discord.utils.get(ctx.guild.roles, name=config['names']['spec_role'])
            logging.info(f'Signed up: {signedup_role} / Alive: {alive_role} / Spectator: {spec_role}')
            async for x in ctx.guild.fetch_members():
                logging.info(f'Checking {x.display_name}')
                if not x.bot:
                    if signedup_role in x.roles:
                        logging.info(f'Removing {signedup_role} and {spec_role}')
                        await x.remove_roles(signedup_role, spec_role)
                        logging.info(f'Adding {alive_role}')
                        await x.add_roles(alive_role)
                    else:
                        logging.info(f'{x.display_name} is not signed up.')
            save_signups(ctx, [])
            await ctx.send(f'All done!')
        except Exception as e:
            error = f'**ERROR (startgame alpha):** {type(e).__name__} - {e}'
            logging.error(error)
            await ctx.send(f'Ran into an error. This might be ugly:\n\n{error}')

    @commands.command(name='cheaters', hidden=True)
    @commands.is_owner()
    async def show_cheaters_command(self, ctx):
        cheaters = get_cheaters()
        if len(cheaters) > 0:
            for x in cheaters:
                await ctx.send(f'Name: {x} / Count: {cheaters[x]}')
        else:
            await ctx.send('Clean games so far o7')

    @commands.command(name='ia')
    async def get_inactive_players(self, ctx, *args: str):
        """Displays message count from TS for each alive player since specified time.
        Usage: 'wolf.ia "YYYY-MM-DD HH:mm" (time is 24-hour format with Eastern timezone) """
        config = get_config(ctx)
        if not await self.is_mod(ctx):
            await ctx.message.add_reaction('🖕')
            await ctx.send(f'{config["messages"]["mod_check"]}')
            return

        if len(args) == 0:
            await ctx.send('Usage is wolf.ia "YYYY-MM-DD H:MM". Optionally a second time may be given for cutoff time.')
            return

        # get list of alive users and create dictionary to count messages
        alive = discord.utils.get(ctx.guild.roles, name=config['names']['alive_role']).members
        if len(alive) == 0:
            await ctx.send("Nobody is alive.")
            return
        message_count = {m: 0 for m in alive}
        channel_name = config['names']['townsquare']
        channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)

        local_timezone = pytz.timezone("America/New_York")

        try:
            start_time_naive = datetime.datetime.strptime(args[0], '%Y-%m-%d %H:%M')
        except ValueError:
            await ctx.send(f'Incorrect datetime format, it must be wolf.ia "YYYY-MM-DD H:MM"')
            return
        start_time_local = local_timezone.localize(start_time_naive)
        start_time_utc = start_time_local.astimezone(pytz.utc)

        if len(args) == 1:
            async for message in channel.history(limit=None, after=start_time_utc.replace(tzinfo=None)):
                if message.author in message_count.keys():
                    message_count[message.author] += 1
        elif len(args) == 2:
            try:
                end_time_naive = datetime.datetime.strptime(args[1], '%Y-%m-%d %H:%M')
            except ValueError:
                await ctx.send(f'Incorrect datetime format, it must be wolf.ia "YYYY-MM-DD H:MM" "YYYY-MM-DD H:MM"')
                return

            end_time_local = local_timezone.localize(end_time_naive)
            end_time_utc = end_time_local.astimezone(pytz.utc)

            async for message in channel.history(limit=None, before=end_time_utc.replace(tzinfo=None),
                                                 after=start_time_utc.replace(tzinfo=None)):
                if message.author in message_count.keys():
                    message_count[message.author] += 1
        else:
            await ctx.send(
                'Too many arguments. Usage is wolf.ia "YYYY-MM-DD H:MM". Optionally a second time may be given for '
                'cutoff time.')
            return
        # parse all messages after date, increment dict value for users for each message

        embed = discord.Embed(title='IA Check', color=0xFF0000)
        ordered_list = collections.OrderedDict(sorted(message_count.items(), key=lambda t: t[1]))
        output = ""
        for user in ordered_list:
            output += f'{user.display_name}: {ordered_list[user]}\n'
        embed.add_field(name=f'Message Count',
                        value=output, inline=False)
        mod_chat = discord.utils.get(ctx.guild.text_channels, name=config['names']['mod_chat'])
        await mod_chat.send(content=None, embed=embed)


async def setup(bot):
    await bot.add_cog(Mod(bot))
