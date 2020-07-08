from discord.ext import commands
import discord
import json
import logging
import sys
import traceback

description = 'Discord Assault PUG Bot'

extensions = ['cogs.admin', 'cogs.info', 'cogs.pug']

discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.CRITICAL)
log = logging.getLogger()
log.setLevel(logging.INFO)
handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
log.addHandler(handler)

help_attrs = dict(hidden=True)
bot = commands.Bot(
        command_prefix=['?','^'],
        description=description,
        pm_help=None,
        help_attrs=help_attrs)

@bot.event
async def on_ready():
    print('Logged in as:')
    print('Username: ' + bot.user.name)
    print('ID: ' + str(bot.user.id))

@bot.event
async def on_resumed():
    print('resumed...')

@bot.event
async def on_command(context):
    message = context.message
    destination = None
    if isinstance(message.channel, discord.abc.PrivateChannel):
        destination = 'Private Message'
    else:
        destination = '#{0.channel.name} ({0.guild.name})'.format(message)

    log.info('{0.created_at}: {0.author.name} in {1}: {0.content}'.format(
        message, destination))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send('This command cannot be used in private messages.')
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send('This command is disabled and cannot be used.')
    elif isinstance(error, commands.CommandInvokeError):
        print('In {0.command.qualified_name}:'.format(ctx), file=sys.stderr)
        traceback.print_tb(error.original.__traceback__)
        print('{0.__class__.__name__}: {0}'.format(error.original), file=sys.stderr)

@bot.event
async def on_message(message):
    if not message.author.bot:
        await bot.process_commands(message)

@bot.event
async def on_message_edit(_, message):
    if not message.author.bot:
        await bot.process_commands(message)

def load_credentials():
    with open('credentials.json') as f:
        return json.load(f)

if __name__ == '__main__':
    if any('debug' in arg.lower() for arg in sys.argv):
        bot.command_prefix = '$'

    credentials = load_credentials()
    for extension in extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print('Failed to load extension {}\n{}: {}'.format(
                extension, type(e).__name__, e))

    bot.run(credentials['token'])
    handlers = log.handlers[:]
    for hdlr in handlers:
        hdlr.close()
        log.removeHandler(hdlr)
