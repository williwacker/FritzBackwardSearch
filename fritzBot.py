# -*- coding: utf-8 -*-

"""

Provides a Telegram Bot for fritzbox information retrieval
Depends on fritzBackwardSearch

@Werner Kuehn - Use at your own risk
20.12.2017 0.0.1 WK  Initial version
22.06.2018 0.0.2 WK  Add backward search

"""

__version__ = '0.0.2'

import argparse
import configparser
import logging
import os
import re

import certifi
import urllib3
import xmltodict
from fritzconnection import FritzConnection
from telegram import Update
from telegram.ext import (CallbackContext, CommandHandler, Filters,
                          MessageHandler, Updater)

from fritzBackwardSearch import FritzBackwardSearch

logger = logging.getLogger(__name__)


class fritzBot(object):

    def __init__(self):
        self.http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        # Read configuration file
        self.inifile = os.path.join(os.path.dirname(__file__), 'fritzBackwardSearch.ini')
        if os.path.isfile(self.inifile):
            self.cfg = configparser.ConfigParser()
            self.cfg.read(self.inifile)
        else:
            logging.error('{} not found'.format(self.inifile), True)
            exit(1)
        # Enable logging
        self.__init_logging__()

    def __init_logging__(self):
        numeric_level = getattr(logging, self.cfg.get('DEFAULT', 'loglevel').upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)
        logging.basicConfig(
            filename=self.cfg.get('DEFAULT', 'logfile_3'),
            level=numeric_level,
            format=('%(asctime)s %(levelname)s [%(name)s:%(lineno)s] %(message)s'),
            datefmt='%Y-%m-%d %H:%M:%S',
        )

    def check_user(self, update):
        if update.message.chat['username'] in self.cfg.get('DEFAULT', 'telegram_allowedUsers'):
            return True
        else:
            update.message.reply_text('Hallo {}. Ich kenne dich nicht.'.format(update.message.chat['username']))
            logger.warn('Unknown user "%s" identified' % (update.message.chat['username']))
            return False

    def start(self, update: Update, context: CallbackContext) -> None:
        # Your bot will send this message when users first talk to it, or when they use the /start command
        if self.check_user(update):
            update.message.reply_text('Hallo {}. Willkommen auf meinem FritzBot.'.format(
                update.message.chat['first_name']))

    def error(self, update: Update, context: CallbackContext, error):
        logger.warn('Update "%s" caused error "%s"' % (update, error))

    def help(self, update: Update, context: CallbackContext) -> None:
        if self.check_user(update):
            helpText = ['<b>Hier die gültigen Befehle:</b>']
            helpText.append('<i>Anrufe:</i>')
            helpText.append('/getab #')
            helpText.append('/getname # | /whois #')
            update.message.bot.sendMessage(chat_id=update.message.chat_id, text='\n'.join(
                helpText), parse_mode='html')

    def echo(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_text(update.message.text)

    def getab(self, update: Update, context: CallbackContext) -> None:
        # Upload the saved phone message
        if self.check_user(update):
            if update.message.text == 'getab':
                command = update.message.text.split()
            else:
                command = (update.message.text[:5], update.message.text[6:])
            if len(command) > 1:
                messageFile = os.path.join(os.path.dirname(__file__), 'rec.0.{}.wav'.format(command[1]))
                if os.path.isfile(messageFile):
                    update.message.bot.send_audio(chat_id=update.message.chat_id, audio=open(messageFile, 'rb'))
                else:
                    update.message.reply_text('Datei {} nicht gefunden'.format(messageFile))
            else:
                update.message.reply_text('Keine AB Nummer angegeben')

    def getname(self, update: Update, context: CallbackContext) -> None:
        # Do a phone number backward search
        if self.check_user(update):
            command = update.message.text.split()
            if len(command) > 1:
                mySearchEngine = FritzBackwardSearch()
                result = mySearchEngine.runSearch(s=command[1])
                update.message.reply_text(result)
            else:
                update.message.reply_text('Keine Nummer angegeben')

    def startBot(self):
        # Create the EventHandler and pass it your bot's token.
        updater = Updater(self.cfg.get('DEFAULT', 'telegram_token'), use_context=True)
        # Get the dispatcher to register handlers
        dp = updater.dispatcher
        # on different commands - answer in Telegram
        getabCmd = "getab"
        dp.add_handler(CommandHandler(getabCmd, self.getab))
        for x in range(0, 1000):
            getabCmd = "getab%03d" % (x,)
            dp.add_handler(CommandHandler(getabCmd, self.getab))
        dp.add_handler(CommandHandler("getname", self.getname))
        dp.add_handler(CommandHandler("whois", self.getname))
        dp.add_handler(CommandHandler("help", self.help))
        dp.add_handler(CommandHandler("start", self.start))

        # on noncommand i.e message - echo the message on Telegram
        dp.add_handler(MessageHandler(Filters.text, self.echo))

        # log all errors
        dp.add_error_handler(self.error)

        # Start the Bot
        updater.start_polling()

        # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        updater.idle()


if __name__ == '__main__':
    BOT = fritzBot()
    BOT.startBot()
