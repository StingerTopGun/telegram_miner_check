# telegram_miner_check

This python written telegram bot checks GPU miners in a configurable time period.

Currently Supported mining-software:

 - [Claymore ETH](https://bitcointalk.org/index.php?topic=1433925.0) 
 - [EWBF Equihash](https://bitcointalk.org/index.php?topic=1707546.0)
 - [DSTM Equihash](https://bitcointalk.org/index.php?topic=2021765.0)

It uses the integrated API of those miners to check on configurable thresholdes for temperature, hashrate, invalid shares and fanspeed. It also messages you if there is no connection to the miner.

# Features

 - Check multiple miners
 - Configurable time between checks
 - Repeat alert until "Confirmed"
 - Pause check on single miner or all miners (while working on miner for example)
 - Can be used in Telegram groups or on single persons
 - Can be run on a miner or on a dedicated server
 - Configurable pause time (for example while scheduled reboot of rigs)

# Screenshots

![start](https://i.imgur.com/4mxMWRl.jpg)
![status](https://i.imgur.com/54vDB5E.jpg)
![alert](https://i.imgur.com/n8yy56m.jpg)
![confirmed](https://i.imgur.com/UjB9Qjg.jpg)


# Requirements

 - [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot.git) needs to be installed first

Tested on Ubuntu 16.04 with python 2.7.12.


# Installation

Checkout from GIT:

    git clone https://github.com/StingerTopGun/telegram_miner_check.git

Copy config example to real config:

    cd telegram_miner_check
    cp config.py.example config.py

Edit config with your preferred editor, see comments inside config for more information.

For testing run bot like this:

    python telegram_miner_check.py

If everything works you can install it as a systemd service using the given systemd script:

    sudo cp telegram_miner_check.service /lib/systemd/system/
    systemctl daemon-reload
    systemctl start telegram_miner_check.service

To enable autostart at startup run:

    systemctl enable telegram_miner_check.service
