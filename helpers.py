import datetime
import logging

import os
import pickle
from configparser import ConfigParser

date = f'{datetime.datetime.now().year}-{datetime.datetime.now().month}-{datetime.datetime.now().day}'
logging.basicConfig(
    filename=f'logs/{date}.log',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def get_config(ctx):
    config = ConfigParser()
    if os.path.exists(f'configs/{ctx.guild.id}_config.ini'):
        config.read(f'configs/{ctx.guild.id}_config.ini')
    else:
        logging.info(f'{ctx.guild.name} | Creating default config file.')
        config.add_section('names')
        config['names']['alive_role'] = 'Alive'
        config['names']['dead_role'] = 'Dead'
        config['names']['mod_role'] = 'Mod'
        config['names']['spec_role'] = 'Spectator'
        config['names']['signedup_role'] = 'Signed Up'
        config['names']['voting_booth'] = 'voting-booth'
        config['names']['townsquare'] = 'townsquare'
        config['names']['couple_chat'] = 'couple-chat'
        config['names']['mod_chat'] = 'mod-chat'

        config.add_section('messages')
        config['messages']['vb_day'] = 'The voting booth is open.'
        config['messages']['vb_night'] = 'The voting booth is closed.'
        config['messages']['ts_day'] = 'Good morning, villagers.'
        config['messages']['ts_night'] = 'Go the heck to sleep. We will reconvene in the morning.'
        config['messages']['cc_day'] = 'Time to head to townsquare.'
        config['messages']['cc_night'] = 'The couple has arrived home.'
        config['messages']['mod_check'] = 'Fuck outta here, bruh. Mods only'
        config['messages']['signups'] = 'Type wolf.in to sign up for the game!'

        # Options: 'day-only', 'night-only', 'always-on', 'always-off'
        config.add_section('toggles')
        config['toggles']['voting_booth'] = 'day-only'
        config['toggles']['townsquare'] = 'always-on'
        config['toggles']['couple_chat'] = 'night-only'

        # Ids
        config.add_section('ids')
        config['ids']['vote_message'] = '000'
        config['ids']['signup_message'] = '000'
        config['ids']['signup_channel'] = '000'

        with open(f'configs/{ctx.guild.id}_config.ini', 'w') as configfile:
            config.write(configfile)

    return config


def save_config(ctx, config):
    with open(f'configs/{ctx.guild.id}_config.ini', 'w') as configfile:
        config.write(configfile)


def save_votes(ctx, votes):
    pickle.dump(votes, open(f'configs/{ctx.guild.id}_votes.pkl', 'wb'))


def get_votes(ctx):
    votes = {}
    if os.path.exists(f'configs/{ctx.guild.id}_votes.pkl'):
        votes = pickle.load(open(f'configs/{ctx.guild.id}_votes.pkl', 'rb'))
    else:
        logging.info(f'{ctx.guild.name} | Creating initial votes file')
        pickle.dump(votes, open(f'configs/{ctx.guild.id}_votes.pkl', 'wb'))

    return votes


def save_signups(ctx, ins):
    pickle.dump(ins, open(f'configs/{ctx.guild.id}_ins.pkl', 'wb'))


def get_signups(ctx):
    ins = []
    if os.path.exists(f'configs/{ctx.guild.id}_ins.pkl'):
        ins = pickle.load(open(f'configs/{ctx.guild.id}_ins.pkl', 'rb'))
    else:
        logging.info(f'{ctx.guild.name} | Creating initial ins file')
        pickle.dump(ins, open(f'configs/{ctx.guild.id}_ins.pkl', 'wb'))

    return ins


def get_cheaters():
    cheaters = {}
    if os.path.exists(f'configs/cheaters.pkl'):
        cheaters = pickle.load(open(f'configs/cheaters.pkl', 'rb'))
    else:
        logging.info(f'Creating initial cheaters file')
        pickle.dump(cheaters, open(f'configs/cheaters.pkl', 'wb'))

    return cheaters


def save_cheaters(cheaters):
    pickle.dump(cheaters, open(f'configs/cheaters.pkl', 'wb'))


