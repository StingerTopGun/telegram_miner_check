#!/usr/bin/env python
# -*- coding: utf-8 -*-
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import ChatAction, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from functools import wraps
import logging
import socket
import os
import time
import sys
import json
import datetime
import config

# --------------------------------------------------------------------
# Telegram Bot for checking mining operations
# created by StingerTopGun
# using https://github.com/python-telegram-bot/python-telegram-bot.git
# --------------------------------------------------------------------

# Dictionary which holds miners in error state, dont touch this!
merr = {}
temp_err = {}
last_msg = None

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

def ifnull(var, val):
  if var is None:
    return val
  return var

def ifzero(var, val):
  if var == 0:
    return val
  return var

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    update.message.reply_text("*Miner Check*\n"
                              "This bot checks mining operations every " + str(config.run_interval) + "sec\n\n"
                              "Commands:\n"
                              "- /status | check all miners\n" 
                              "- /status <miner> | check specific miner\n"
                              "- /pause all | stop monitoring all miners\n"
                              "- /pause <miner> | stop monitoring specific miner\n"
                              "- /unpause all | start monitoring all miners again\n"
                              "- /unpause <miner> | start monitoring specific miner again", parse_mode=ParseMode.MARKDOWN, quote=False)


def status(bot, update, args):

  bot.send_chat_action(update.message.chat_id, ChatAction.TYPING)
  message = ""

  # Do we have a parameter ?
  try: 

    # is it a miner ?
    if args[0] in config.mlist:
    
      # Make that shit readable dude
      logger.info('got /status WITH parameter: <' + args[0] + "> in chat: <" + str(update.message.chat_id) + ">")
      message = args[0] + ": " + check_miner(args[0], config.mlist[args[0]])

    # Got a parameter but its not a valid miner
    else:

      logger.info("Got wrong parameter: " + args[0] + "> in chat: <" + str(update.message.chat_id) + ">")
      message = "Wrong parameter, please use a miner as parameter, for example:\n" \
                "\"/status miner1\""

    # Now send the actual message
    message = ( "*Status:*\n" + message )
    update.message.reply_text(str(message).replace("OK", '✅'), parse_mode=ParseMode.MARKDOWN, quote=False)


  except (IndexError):

    logger.info('got /status WITHOUT parameter' + "> in chat: <" + str(update.message.chat_id) + ">")
    # Call periodic miner check with the third parameter -update-, if this one is not None, it will send the outcome to that chat where it has been called
    check_miners_periodic(bot, None, update)



def check_miners_periodic(bot, job, update = None):
  if config.pause_start <= datetime.datetime.now().time() <= config.pause_end and (update is None):

    logger.info("------------------------------")
    logger.info("Inside pause time, do not check because " + 'Timestamp: {:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()) + " is between " + '{:%H:%M:%S}'.format(config.pause_start) + " and " + '{:%H:%M:%S}'.format(config.pause_end))
    logger.info("------------------------------")

  else:

    logger.info("------------------------------")
    logger.info("Start checking miners periodic")
    
    message = ""
    chat_message = ""
    global last_msg
    global temp_err

    for key, value in sorted(config.mlist.iteritems()):
      
      check = check_miner(key, value)

      chat_message += key + ": " + check + "\n"

      
      if check != "OK":
        
        if merr.get(key, None) != True:

          logger.info(key + " is not OK: " + check)

          # Finally add miner to error dict and save text for editing it later 
          merr[key] = False

        else:
    
          logger.info(key + " already confirmed or on pause")

      elif key in merr:
 
        # If the miner is OK again, delete entry
        del merr[key]

        bot.send_message(chat_id=config.chat_id,
                         text="*" + key + "* is back to work ✅",
                         parse_mode=ParseMode.MARKDOWN)

        logger.info(key + " seems to be OK again, reset")

    if update is not None:
      # update is not none if this function has been called manually, for example from a /status
      update.message.reply_text(str("*Status:*\n" + chat_message).replace("OK", '✅'), parse_mode=ParseMode.MARKDOWN, quote=False)

    if False in merr.values():

      message = ( "⚠ *Mining ALERT* ‼\n\n" + chat_message).replace("OK", '✅')

      keyboard = [[InlineKeyboardButton("Confirm", callback_data="hi")]]

      reply_markup = InlineKeyboardMarkup(keyboard)

      # First delete the old message, if nofthing changed and there even is any saved
      if last_msg is not None:
        logger.info("deleting last_msg: " + str(last_msg))
        bot.delete_message(chat_id = config.chat_id, message_id = last_msg)

      last_msg = bot.send_message(chat_id=config.chat_id,
                                  text=message,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=reply_markup).message_id

      # Make a temporary copy of merr to know what miners have been in error state when confirming
      temp_err = merr.copy()


    if not merr and temp_err:
      # dict is empty, so everything is ok again, send one ok message
      last_msg = None
      temp_err = {}
      bot.send_message(chat_id=config.chat_id, text=str("*Everything OK again*\n" + chat_message).replace("OK", '✅'), parse_mode=ParseMode.MARKDOWN, quote=False)


    logger.info("Finished checking miners periodic")


def confirm(bot, update):
    query = update.callback_query

    logger.info(str(query.from_user.first_name) + " confirmed")

    bot.edit_message_text(text=query.message.text_markdown + "\n\n*CONFIRMED* by " + str(query.from_user.first_name),
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id,
                          parse_mode=ParseMode.MARKDOWN)

    # Set miners to confirmed (true)
    for key, value in temp_err.iteritems():
      if value == False:
        merr[key] = True

    # Delete last_msg so the confirmed message will not be deleted
    last_msg = None

def check_miner(miner, coin):
  logger.info("checking " + miner + " on coin " + coin)
  client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  client.settimeout(10)

  if coin == "ETH":
    sendstr = '{"id":0,"jsonrpc":"2.0","method":"miner_getstat1"}'
    port = config.eth_port
  elif coin in {"ZEC", "DSTM"}:
    sendstr = '{"id":1, "method":"getstat"}\n'
    port = config.zec_port
  else:
    return "invalid_coin"

  logger.debug("Everything set, try to connect")

  try:
    client.connect((miner, port))
  except socket.error, exc:
    print "Caught exception socket.error : %s" % exc
    return str(exc)

  logger.debug("Connection etablished, now send string")

  client.send(sendstr)

  logger.debug("String has been sent, try to get a response")

  response = ""

  try:
    while True:
      logger.debug("inside receiving loop")
      data = client.recv(4096)
      if not data: break
      response += data
  except socket.error, exc:
    print "Caught exception socket.error : %s" % exc
    return str(exc)

  logger.debug("got response, now parse it")

  answ_json = json.loads(response)

  logger.debug("converted to json, now start checking on different coins")

  # ---------
  # Check ETH
  if coin == "ETH":

    hashes = map(float, str(answ_json['result'][2]).split(';'))
    single_hash = map(float, str(answ_json['result'][3]).split(';'))
    gpus = map(float, str(answ_json['result'][6]).split(';'))

    # Check overall hashrate and invalid shares percent
    if ( hashes[0] / 1000 ) < ( config.eth_min_hash * len(single_hash) ):
      logger.info("low overall hashrate")
      return "low overall hashrate"
    elif ( hashes[2] / ( hashes[1] / 100 )) > config.eth_max_inv_shares:
      logger.info("invalid shares")
      return "invalid shares"

    # Check single hashrate
    for h in single_hash:
      if ( h / 1000 ) < config.eth_min_hash:
        logger.info("low single hashrate")
        return "low single hashrate"

    # Check temperature
    for t in gpus[::2]:
      if t > config.eth_max_temp:
        logger.info("high temperature")
        return "high temperature"

    # Check fan speed
    for f in gpus[1::2]:
      if f > config.eth_max_fan:
        logger.info("high fan speed")
        return "high fan speed"

    # If we are still here, everything is good, return OK
    logger.info("Everthing OK")
    return "OK"

  # ---------
  # Check ZEC
  elif coin == "ZEC":

    # Loop over all GPUs
    for g in answ_json['result']:

      # Check hashrates
      if float(g['speed_sps']) < config.zec_min_hash:
        logger.info("low single hashrate")
        return "low single hashrate"
      # Check invalid shares
      if ( float(g['rejected_shares']) / ( float(ifzero(g['accepted_shares'], 1)) / 100 )) > config.zec_max_inv_shares:
        logger.info("invalid shares")
        return "invalid shares"
      # Check temperatures
      if float(g['temperature']) > config.zec_max_temp:
        logger.info("high temperature")
        return "high temperature"

     # If we are still here, everything is good, return OK
    logger.info("Everything OK")
    return "OK"

  # ---------
  # Check DSTM
  elif coin == "DSTM":

    # Loop over all GPUs
    for g in answ_json['result']:

      # Check hashrates
      if float(g['sol_ps']) < config.zec_min_hash:
        logger.info("low single hashrate")
        return "low single hashrate"
      # Check invalid shares
      if ( float(g['rejected_shares']) / ( float(ifzero(g['accepted_shares'], 1)) / 100 )) > config.zec_max_inv_shares:
        logger.info("invalid shares")
        return "invalid shares"
      # Check temperatures
      if float(g['temperature']) > config.zec_max_temp:
        logger.info("high temperature")
        return "high temperature"

     # If we are still here, everything is good, return OK
    logger.info("Everything OK")
    return "OK"

  # Something is wrong with the call of this script
  else:

    return "invalid coin"


def pause(bot, update, args):
    
    if not args:
      logger.info("No arguments given in pause command")

      update.message.reply_text("No arguments given, usage:\n/pause all\n/pause <miner>", quote=False)

    elif args[0] == "all":
      logger.info("Pause all miners")
      
      for key, value in sorted(config.mlist.iteritems()):
        merr[key] = False

      update.message.reply_text("pause active, no miners will be monitored", quote=False)

    elif args[0] in config.mlist:
      logger.info("Pause " + args[0])

      merr[args[0]] = False
      update.message.reply_text(args[0] + " on pause", quote=False)

    else:

      logger.info("Invalid argument in pause command")
      update.message.reply_text("Invalid argument, usage:\n/pause all\n/pause <miner>", quote=False)



def unpause(bot, update, args):

    if not args:
      logger.info("No arguments given in unpause command")
      
      update.message.reply_text("No arguments given, usage:\n/unpause all\n/unpause <miner>", quote=False)

    elif args[0] == "all":
      logger.info("Unpause all miners")
      
      for key, value in sorted(config.mlist.iteritems()):
        merr.pop(key, None)

      update.message.reply_text("all miners will be monitored again", quote=False)

    elif args[0] in merr:
      logger.info("Unpause " + args[0])
      
      del merr[args[0]]
      update.message.reply_text(args[0] + " will be monitored again", quote=False)

    else:

      logger.info("Invalid argument in unpause command or monitor already active")
      update.message.reply_text("Invalid argument or monitor already active, usage:\n/unpause all\n/unpause <miner>", quote=False)


def restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in config.LIST_OF_ADMINS:
            print("Unauthorized access denied for {}.".format(user_id))
            bot.send_message(update.message.chat_id, "Unauthorized !")
            return
        return func(bot, update, *args, **kwargs)
    return wrapped


@restricted
def setlog(bot, update, args):

    if not args:
      logger.info("No arguments given in setlog command")
      update.message.reply_text("No arguments given, usage:\n/setlog <log-lvl>\n\nlog-levels:\nCRITICAL\n ERROR\n WARNING\n INFO\n DEBUG", quote=False)
      return

    new_lvl = str(args[0]).upper()

    if new_lvl not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
      update.message.reply_text("Wrong parameter! usage:\n/setlog <log-lvl>\n\nlog-levels:\nCRITICAL\n ERROR\n WARNING\n INFO\n DEBUG", quote=False)
      logger.warning("Wrong use of setlog function with parameter: " + new_lvl)
      return

    logger.setLevel(new_lvl)
    update.message.reply_text("Log Level is now set to " + new_lvl, quote=False)
    logger.info("Log is now set to: " + new_lvl)


@restricted
def restart(bot, update):
    bot.send_message(update.message.chat_id, "Bot is restarting...")
    time.sleep(0.2)
    os.execl(sys.executable, sys.executable, *sys.argv)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(config.api_key)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    j = updater.job_queue

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("status", status, pass_args=True))
    dp.add_handler(CallbackQueryHandler(confirm))
    dp.add_handler(CommandHandler("restart", restart))
    dp.add_handler(CommandHandler("pause", pause, pass_args=True))
    dp.add_handler(CommandHandler("unpause", unpause, pass_args=True))
    dp.add_handler(CommandHandler("setlog", setlog, pass_args=True))

    p_check = j.run_repeating(check_miners_periodic, interval=config.run_interval, first=0)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
