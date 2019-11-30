# Yahoo! Fantasy Bot

_A bot that can act as a manager in a Yahoo! fantasy league_

## Build status

[![Build Status](https://travis-ci.com/spilchen/yahoo_fantasy_bot.svg?branch=master)](https://travis-ci.com/spilchen/yahoo_fantasy_bot)

## Installation

One time setup:
```
git clone https://github.com/spilchen/yahoo_fantasy_bot.git
cd yahoo_fantasy_bot
virtualenv --python=python3.7 env
source env/bin/activate
pip install -r requirements.txt
# You can get your key/secret from https://developer.yahoo.com/apps/create/.  You must request read/write access.
python examples/init_oauth_env.py -k <yahoo_consumer_key> -s <yahoo_secret_key> oauth2.json
```

You need to setup a config file to tune the program for your specific league.  Use sample_config.ini as a guide.

## Restrictions
This program will only optimize lineups for teams in a Yahoo! Head-to-Head league.

## Execution
Once installed and the config file created, you can run the program via this command:
```
python ybot.py <cfg_file>
```

The default is to run in automated mode.  This will optimize the lineup for the next scoring period.  You can do this in a dry-run meaning no changes are made with Yahoo by specifying the --dry-run option.  There is also an interactive mode where you get a menu system and you can run the various lineup optimization commands with the --interactive option.

To get a full help text use the `--help` option.

### Example
Here is a sample run through.  In this run it will optimize the lineup, print out the lineup then list the roster changes.  It will manage two players on the IR and replace one player in the lineup from the free agent pool.
```
$> python ybot.py hockey.cfg
Evaluating trades
Adjusting lineup for player status
Optimizing open lineup spots using available free agents
100%|################################################################################################################|
Optimizing lineup using players available from bench
100%|################################################################################################################|
Optimized lineup
B   :                        WK_G G/A/PPP/SOG/PIM
C   : Aleksander Barkov         3 38.0/63.0/32.0/241.0/10.0
C   : Brayden Point             3 38.0/55.0/38.0/223.0/26.0
LW  : Andrei Svechnikov         3 30.0/25.0/12.0/261.0/72.0
LW  : Evander Kane              4 31.0/26.0/12.0/279.0/132.0
RW  : David Pastrnak            3 44.0/53.0/39.0/281.0/40.0
RW  : Alexander Radulov         3 28.0/45.0/24.0/212.0/64.0
D   : Tyson Barrie              3 13.0/44.0/24.0/191.0/30.0
D   : Thomas Chabot             3 15.0/43.0/15.0/197.0/36.0
D   : P.K. Subban               4 12.0/40.0/16.0/174.0/70.0
D   : Aaron Ekblad              3 14.0/25.0/11.0/186.0/55.0

G   :                        WK_G W/SV%
G   : Ben Bishop                3 31.0/0.922
G   : Connor Hellebuyck         3 36.0/0.916

Bench
Jeff Skinner
Patrice Bergeron

Injury Reserve
Sidney Crosby
Mitchell Marner

Computing roster moves to apply
Move Sidney Crosby to IR
Move Mitchell Marner to IR
Add Brayden Point and drop Anthony Mantha
Move David Pastrnak to RW
Move Aleksander Barkov to C
Move Ben Bishop to G
Move Connor Hellebuyck to G
Move Brayden Point to C
Move Andrei Svechnikov to LW
Move Evander Kane to LW
Move Alexander Radulov to RW
Move Tyson Barrie to D
Move Thomas Chabot to D
Move P.K. Subban to D
Move Aaron Ekblad to D
Move Jeff Skinner to BN
Move Patrice Bergeron to BN
```
