"""
GroupMe Bot

Developed by Paul Pfeister
"""
import os
import sys
import requests
import importlib
from flask import Flask, request

#######################################################################################################
######################## Customization ################################################################

'''
The bot will automatically log certain items, and log other items when DEBUG is set.
Some command lines might not show colors well, or they may overlap with your theme.
You can change the appearance of entries by replacing these values with other ANSI codes.
'''
class errcol:
    severe  = '\033[31m[ SEVERE ]\033[00m '  # if something critical is caught
    warn    = '\033[33m[ WARN ]\033[0m '  # not critical, but still bad
    ok      = '\033[32m[ OK ]\033[00m '  # something good happens that might not always happen
    debug = '\033[35m[ BOT-DEBUG ]\033[00m '  # prefix for log entries when debugging
    log = '\033[36m[ BOT-LOG ]\033[00m '  # prefix for all other log entries
    usrmsg  = '\033[36m[ MESSAGE ]\033[00m '  # prefix for captured messages
    botmsg  = '\033[33m[ BOT MSG ]\033[00m '  # prefix for messages by the bot (  i.e. [ MESSAGE ] [ BOT ] Botname: Message  )
    sysmsg  = '\033[00m[ GroupMe ]\033[00m '  # Same as above, but for system messages like topic changes
    tail    = '\033[00m'  # suffix for log entries (normally just clears formatting)

#######################################################################################################
######################## Initialization ###############################################################

# To enable debugging the hard way, type 'True #' after 'Debug = '
DEBUG = (True if os.getenv('BOT_DEBUG') == 'True' else False)
POST_TO = 'https://api.groupme.com/v3/bots/post'
GROUP_RULES = {}
BOT_INFO = {}

if DEBUG:
    print(errcol.debug + "Web concurrency is set to " + os.getenv('WEB_CONCURRENCY') + errcol.tail)
    if os.getenv('WEB_CONCURRENCY') != '1':
        print(errcol.debug + "NOTE: When debugging with concurrency, you may see repetitive log entries." + errcol.tail)

# Parses bot data from the environment into the format { group_id : [bot_id, bot_name] }
for bot in (os.getenv('BOT_INFO')).split('; '):
    info = bot.split(', ')
    BOT_INFO[info[0]] = (info[1], info[2])

# When you create global rules for the bot, they will be imported here.
try:
    GLOBAL_RULES = __import__('global_rules') #TODO Change to importlib.import_module
    print(errcol.ok + "Global rules found and added." + errcol.tail)
except ImportError:
    print(errcol.warn + "Global rules not found. Bot may load, but it won't do anything." + errcol.tail)

# When you create custom rules for a group, they will be imported here.
for group in BOT_INFO:
    try:
        GROUP_RULES[group] = __import__('group_{}'.format(group)) #TODO Change to importlib.import_module
        print(errcol.ok + "Group rules found and added for [G:{}]".format(group) + errcol.tail)
    except ImportError:
        if group in GROUP_RULES: del GROUP_RULES[group]
        if DEBUG: print(errcol.debug + "Group rules not found for [G:{}]".format(group) + errcol.tail)

#######################################################################################################
######################## Helper functions #############################################################

def attach_type(attachments):
    types = {
            'image'    : '[IMG] ',
            'location' : '[LOC] ',
            'poll'     : '',
            'event'    : ''
            }
    typelist = ''
    for attachment in attachments:
        try:
            typelist += types[attachment['type']]
        except KeyError:
            print(errcol.warn + 'Attachment type {} unknown.'.format(attachment['type']) + errcol.tail)
    return typelist

#TODO Make log entries for polls and events appear cleaner (not critical)
def logmsg(data):
    try:
        sender_type = data['sender_type']
    except KeyError as missing_key:
        print(errcol.warn + "Message data does not contain a sender_type." + errcol.tail)
    else:
        if sender_type == 'user':
            print(errcol.usrmsg + "{}: {}{}".format(data['name'], attach_type(data['attachments']), data['text']) + errcol.tail)
        elif sender_type == 'system':
            print(errcol.sysmsg + data['text'] + errcol.tail)
        elif sender_type == 'bot':
            print(errcol.botmsg + "{}: {}{}".format(data['name'], attach_type(data['attachments']) ,data['text']) + errcol.tail)

def send_message(msg, bot_id, img_url):
    if img_url != "":
        data = {
            'bot_id': bot_id,
            'text': msg,
            'attachments': [
                {
                    'type': "image",
                    'url': img_url
                }
            ]
        }
    else:
        data = {
            'bot_id': bot_id,
            'text': msg,
        }
    requests.post(POST_TO, json=data)

#######################################################################################################
######################## The actual bot ###############################################################

app = Flask(__name__)

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    
    logmsg(data)

    # Prevent the bot from acting on its own messages
    if data['name'] == BOT_INFO[data['group_id']][1]:
        return "ok", 200

    if data['group_id'] in GROUP_RULES:
        if GROUP_RULES[data['group_id']].run(data, BOT_INFO[data['group_id']], send_message):
            return "ok", 200

    GLOBAL_RULES.run(data, BOT_INFO[data['group_id']], send_message)

    return "ok", 200
