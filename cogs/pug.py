import time
from datetime import datetime
import functools
import itertools
import random
import re
import requests # should replace with aiohttp. See https://discordpy.readthedocs.io/en/latest/faq.html#what-does-blocking-mean
import json
from discord.ext import commands, tasks
import discord

# Commands and maps from the IRC bot:
#
#<UTAPugbot> !pughelp !reset !setmaps !setplayers !listmaps !pug !letter !status !server !captainmode !launchprotect !version
#<UTAPugbot> during pug setup: !player !randplayer !map !randmap !showteams !showmaps !captain
#
#Maplist:
#Server map list is: 1.AS-AsthenosphereSE 2.AS-AutoRip 3.AS-Ballistic 4.AS-Bridge 5.AS-Desertstorm 6.AS-Desolate][ 7.AS-Frigate
#8.AS-GolgothaAL 9.AS-Golgotha][AL 10.AS-Mazon 11.AS-RiverbedSE 12.AS-Riverbed]l[AL 13.AS-Rook 14.AS-Siege][
#15.AS-Submarinebase][ 16.AS-SaqqaraPE_preview3 17.AS-SnowDunes][AL_beta 18.AS-LostTempleBetaV2 19.AS-TheDungeon]l[AL
#20.AS-DustbowlALRev04 21.AS-NavaroneAL 22.AS-TheScarabSE 23.AS-Vampire 24.AS-ColderSteelSE_beta3 25.AS-HiSpeed
#26.AS-NaliColony_preview5 27.AS-LavaFort][PV 28.AS-BioassaultSE_preview2 29.AS-Razon_preview3 30.AS-Resurrection
#31.AS-WorseThings_preview 32.AS-GekokujouAL][

DEFAULT_PLAYERS = 12
DEFAULT_MAPS = 7
DEFAULT_PICKMODETEAMS = 2
DEFAULT_PICKMODEMAPS = 2

DEFAULT_GAME_SERVER_IP = '0.0.0.0'
DEFAULT_GAME_SERVER_PORT = '7777'
DEFAUlT_GAME_SERVER_NAME = 'Unknown Server'
DEFAULT_POST_SERVER = 'https://www.utassault.net'
DEFAULT_POST_TOKEN = 'NoToken'
DEFAULT_SERVER_FILE = 'servers/default_server.json'

RED_PASSWORD_PREFIX = 'RP'
BLUE_PASSWORD_PREFIX = 'BP'
DEFAULT_SPECTATOR_PASSWORD = 'pug'
DEFAULT_NUM_SPECTATORS = 4
DEFAULT_RED_PASSWORD = RED_PASSWORD_PREFIX + '000'
DEFAULT_BLUE_PASSWORD = BLUE_PASSWORD_PREFIX + '000'

# TODO: Add option to read maplist from file. Bot will need a command too.
MAP_LIST = [
    'AS-AsthenosphereSE',
    'AS-AutoRip',
    'AS-Ballistic',
    'AS-Bridge',
    'AS-Desertstorm',
    'AS-Desolate][',
    'AS-Frigate',
    'AS-GolgothaAL',
    'AS-Golgotha][AL',
    'AS-Mazon',
    'AS-RiverbedSE',
    'AS-Riverbed]l[AL',
    'AS-Rook',
    'AS-Siege][',
    'AS-Submarinebase][',
    'AS-SaqqaraPE_preview3',
    'AS-SnowDunes][AL_beta',
    'AS-LostTempleBetaV2',
    'AS-TheDungeon]l[AL',
    'AS-DustbowlALRev04',
    'AS-NavaroneAL',
    'AS-TheScarabSE',
    'AS-Vampire',
    'AS-ColderSteelSE_beta3',
    'AS-HiSpeed',
    'AS-NaliColony_preview5',
    'AS-LavaFort][PV',
    'AS-BioassaultSE_preview2',
    'AS-Razon_preview3',
    'AS-Resurrection',
    'AS-WorseThings_preview',
    'AS-GekokujouAL]['
]
MAX_MAPS_LIMIT = len(MAP_LIST)

PICKMODES = [
        [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        [0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0],
        [0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        [0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0]]
MAX_PLAYERS_LIMIT = len(PICKMODES[0]) + 2

PLASEP = '\N{SMALL ORANGE DIAMOND}'
MODSEP = '\N{SMALL BLUE DIAMOND}'
OKMSG = '\N{OK HAND SIGN}'

DISCORD_MD_CHARS = '*~_`'
DISCORD_MD_ESCAPE_RE = re.compile('[{}]'.format(DISCORD_MD_CHARS))
DISCORD_MD_ESCAPE_DICT = {c: '\\' + c for c in DISCORD_MD_CHARS}

#########################################################################################
# Utilities
#########################################################################################

def discord_md_escape(value):
    return DISCORD_MD_ESCAPE_RE.sub(lambda match: DISCORD_MD_ESCAPE_DICT[match.group(0)], value)

def display_name(member):
    return discord_md_escape(member.display_name)

def getDuration(then, now = datetime.now(), interval = "default"):
    # Adapted from https://stackoverflow.com/a/47207182
    duration = now - then
    duration_in_s = duration.total_seconds()

    def years():                    return divmod(duration_in_s, 31536000) # Seconds in a year=31536000.
    def days(seconds = None):       return divmod(seconds if seconds != None else duration_in_s, 86400) # Seconds in a day = 86400
    def hours(seconds = None):      return divmod(seconds if seconds != None else duration_in_s, 3600) # Seconds in an hour = 3600
    def minutes(seconds = None):    return divmod(seconds if seconds != None else duration_in_s, 60) # Seconds in a minute = 60
    def seconds(seconds = None):    return divmod(seconds, 1) if seconds != None else duration_in_s
    def totalDuration():
        y = years()
        d = days(y[1]) # Use remainder to calculate next variable
        h = hours(d[1])
        m = minutes(h[1])
        s = seconds(m[1])
        msg = []
        if y: msg.append('{} years'.format(int(y[0])))
        if d: msg.append('{} days'.format(int(d[0])))
        if h: msg.append('{} hours'.format(int(h[0])))
        if m: msg.append('{} minutes'.format(int(m[0])))
        if s: msg.append('{} seconds'.format(int(s[0])))
        return ', '.join(msg)
    return {'years': int(years()[0]),'days': int(days()[0]),'hours': int(hours()[0]),'minutes': int(minutes()[0]),'seconds': int(seconds()),'default': totalDuration()}[interval]

class Players:
    """Maintains the state of a set of players"""
    def __init__(self, maxPlayers):
        self.maxPlayers = maxPlayers
        self.players = []

    def __contains__(self, player):
        return player in self.players

    def __iter__(self):
        return iter(self.players)

    def __len__(self):
        return len(self.players)

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['players']
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        self.players = []

    #########################################################################################
    # Properties
    #########################################################################################
    @property
    def playersBrief(self):
        return '[{}/{}]'.format(len(self), self.maxPlayers)

    @property
    def playersFull(self):
        return len(self) == self.maxPlayers

    @property
    def playersNeeded(self):
        return self.maxPlayers - len(self)

    #########################################################################################
    # Functions
    #########################################################################################
    def addPlayer(self, player):
        if player not in self and not self.playersFull:
            self.players.append(player)
            return True
        return False

    def removePlayer(self, player):
        if player in self:
            self.players.remove(player)
            return True
        return False

    def resetPlayers(self):
        self.players = []

    def setMaxPlayers(self, numPlayers):
        if numPlayers < MAX_PLAYERS_LIMIT:
            self.maxPlayers = numPlayers
        else:
            self.maxPlayers = MAX_PLAYERS_LIMIT
        # If we have more players, then prune off the end.
        while(len(self) > self.maxPlayers):
            self.players.pop()


class PugMaps:
    """Maintains the state of a set of maps for a pug"""
    def __init__(self, maxMaps, pickMode):
        self.maxMaps = maxMaps
        self.pickMode = pickMode
        self.completeMaplist = MAP_LIST
        self.maps = []

    def __contains__(self, map):
        return map in self.maps

    def __iter__(self):
        return iter(self.maps)

    def __len__(self):
        return len(self.maps)

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['maps']
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        self.maps = []

    #########################################################################################
    # Properties
    #########################################################################################
    @property
    def mapsFull(self):
        return len(self) == self.maxMaps

    @property
    def currentTeamToPickMap(self):
        return PICKMODES[self.pickMode][len(self.maps)]

    #########################################################################################
    # Formatted strings
    #########################################################################################
    def format_maplist(self, maps):
        indexedMaps = self.indexMaps(maps)
        fmt = '**{0})** {1}'
        return PLASEP.join(fmt.format(*x) for x in indexedMaps)

    @property
    def format_complete_maplist(self):
        return self.format_maplist(self.completeMaplist)

    @property
    def format_current_maplist(self):
        return self.format_maplist(self.maps)

    #########################################################################################
    # Functions
    #########################################################################################
    def indexMaps(self, maps):
        indexedMaplist = ((i, m) for i, m in enumerate(maps, 1) if m)
        return indexedMaplist

    def addMap(self, map):
        if map not in self and not self.mapsFull:
            self.maps.append(map)
            return True
        return False

    def removeMap(self, map):
        if map in self:
            self.maps.remove(map)
            return True
        return False

    def resetMaps(self):
        self.maps = []

    def setMaxMaps(self, numMaps):
        if numMaps <= MAX_MAPS_LIMIT:
            self.maxMaps = numMaps
        else:
            self.maxMaps = MAX_MAPS_LIMIT


class Team(list):
    """Represents a team of players with a captain"""
    def __init__(self):
        super().__init__()

    #########################################################################################
    # Properties
    #########################################################################################
    @property
    def captain(self):
        if len(self):
            return self[0]
        return None


class PugTeams(Players):
    """Represents players who can be divided into 2 teams who captains pick."""
    def __init__(self, maxPlayers, pickMode):
        super().__init__(maxPlayers)
        self.teams = (Team(), Team())
        self.pickMode = pickMode
        self.here = [True, True] # Not used, could add later.
        self.task = None # Not used, might need later.

    def __contains__(self, player):
        return player in (self.players + self.red + self.blue)

    def __getstate__(self):
        state = super().__getstate__()
        del state['teams']
        del state['task']
        del state['here']
        return state

    def __setstate__(self, state):
        super().__setstate__(state)
        self.teams = (Team(), Team())
        self.task = None
        self.here = [True, True]

    #########################################################################################
    # Properties
    #########################################################################################
    @property
    def numCaptains(self):
        return sum([self.red.captain != None, self.blue.captain != None])

    @property
    def captainsFull(self):
        return self.red and self.blue

    @property
    def currentTeamToPickPlayer(self):
        return PICKMODES[self.pickMode][len(self.red) + len(self.blue) - 2] if len(self.red) + len(self.blue) > 1 else 0

    @property
    def currentCaptainToPickPlayer(self):
        if self.captainsFull:
            return self.teams[self.currentTeamToPickPlayer].captain
        else:
            return None

    @property
    def teamsFull(self):
        return len(self.red) + len(self.blue) == self.maxPlayers

    @property
    def team(self):
        return PICKMODES[self.pickMode][len(self.red) + len(self.blue) - 2]

    @property
    def red(self):
        return self.teams[0]

    @property
    def blue(self):
        return self.teams[1]

    #########################################################################################
    # Functions:
    #########################################################################################
    def removePugTeamPlayer(self, player):
        if player in self:
            if self.red:
                self.softPugTeamReset()
            if self.task:
                self.task.cancel()
            self.removePlayer(player)
            return True
        return False

    def softPugTeamReset(self):
        if self.red:
            self.players += self.red + self.blue
            self.players = list(filter(None, self.players))
            self.red.clear()
            self.blue.clear()
            self.here = [True, True]
            if self.task:
                self.task.cancel()
            return True
        return False

    def fullPugTeamReset(self):
        self.players = []
        self.red.clear()
        self.blue.clear()
        self.here = [True, True]
        if self.task:
            self.task.cancel()

    def setCaptain(self, player):
        if player in self.players and self.playersFull:
            index = self.players.index(player)
            if not self.red:
                self.red.append(player)
            elif not self.blue:
                self.blue.append(player)
            else:
                return False
            self.players[index] = None
            return True
        return False

    def pickPlayer(self, captain, index: int):
        if captain == self.currentCaptainToPickPlayer:

            if index < 0 or index >= len(self) or not self.players[index]:
                return False

            player = self.players[index]
            self.teams[self.team].append(player)
            self.players[index] = None

            # check to see if next team has any choice and move them
            index = len(self.red) + len(self.blue) - 2
            remaining = PICKMODES[self.pickMode][index:self.maxPlayers - 2]
            if len(set(remaining)) == 1:
                self.teams[remaining[0]].extend(p for p in self.players if p)
            return True


class GameServer:
    def __init__(self, setupfile):
        # POST server and game server info:
        self.postServer = DEFAULT_POST_SERVER
        self.authtoken = DEFAULT_POST_TOKEN
        self.gameServerIP = DEFAULT_GAME_SERVER_IP
        self.gameServerPort = DEFAULT_GAME_SERVER_PORT
        self.gameServerName = DEFAUlT_GAME_SERVER_NAME
        self.redPassword = DEFAULT_RED_PASSWORD
        self.bluePassword = DEFAULT_BLUE_PASSWORD
        self.spectatorPassword = DEFAULT_SPECTATOR_PASSWORD
        self.numSpectators = DEFAULT_NUM_SPECTATORS

        # We keep a track of the server's match status and also if we have used "endMatch" since the last server setup, which
        # can be used to override the updating matchInProgress when a match has been ended since the last server setup.
        # This avoids  avoids the need to wait for the last map to complete before the server shows as match finished.
        self.matchInProgress = False
        self.endMatchPerformed = False

        # Store the responses from the setup server.
        self.lastSetupResult = ''
        self.lastCheckJSON = {}
        self.lastSetupJSON = {}
        self.lastEndGameJSON = {}

        self.lastUpdateTime = datetime.now()

        self.loadPostServerInfo(setupfile)
        self.updateServerStatus()

    def loadPostServerInfo(self, setupfile):
        with open(setupfile) as f:
            info = json.load(f)
            self.postServer = info['postserver']
            self.authtoken = info['authtoken']

    #########################################################################################
    # Formatted JSON
    #########################################################################################
    @property
    def format_post_header_auth(self):
        fmt = {
                "Content-Type": "application/json; charset=UTF-8",
                "PugAuth": '{}'.format(self.authtoken)
        }
        return fmt

    @property
    def format_post_header_check(self):
        fmt = self.format_post_header_auth
        fmt.update({"Mode": "check"})
        return fmt

    @property
    def format_post_header_setup(self):
        fmt = self.format_post_header_auth
        fmt.update({"Mode": "setup"})
        return fmt

    @property
    def format_post_header_endgame(self):
        fmt = self.format_post_header_auth
        fmt.update({"Mode": "endgame"})
        return fmt

    def format_post_body_setup(self, players, maps):
        fmt = {
            "authEnabled": True,
            "tiwEnabled": True,
            "matchLength": len(maps),
            "maxPlayers": len(players),
            "specLimit": self.numSpectators,
            "redPass": self.redPassword,
            "bluePass": self.bluePassword,
            "specPass": self.spectatorPassword,
            "maplist": maps,
            "gameType": "LeagueAS140.LeagueAssault",
            "mutators": None,
            "friendlyFireScale": 0,
            "initialWait": 180
        }
        return fmt

    #########################################################################################
    # Formatted strings
    #########################################################################################
    @property
    def format_gameServerURL(self):
        return 'unreal://{0}:{1}'.format(self.gameServerIP, self.gameServerPort)

    @property
    def format_gameServerURL_red(self):
        return '{0}{1}{2}'.format(self.format_gameServerURL, '?password=', self.redPassword)

    @property
    def format_gameServerURL_blue(self):
        return '{0}{1}{2}'.format(self.format_gameServerURL, '?password=', self.bluePassword)

    @property
    def format_gameServerURL_spectator(self):
        return '{0}{1}{2}'.format(self.format_gameServerURL, '?password=', self.spectatorPassword)

    @property
    def format_server_info(self):
        fmt = '{0} | {1}'.format(self.gameServerName, self.format_gameServerURL)
        return fmt

    @property
    def format_red_password(self):
        fmt = 'Red team password: **{}**'.format(self.redPassword)
        return fmt

    @property
    def format_blue_password(self):
        fmt = 'Blue team password: **{}**'.format(self.bluePassword)
        return fmt

    @property
    def format_spectator_password(self):
        fmt = 'Spectator password: **{}**'.format(self.spectatorPassword)
        return fmt

    @property
    def format_game_server(self):
        fmt = 'Pug Server: **{}**'.format(self.format_gameServerURL)
        return fmt
    
    @property
    def format_game_server_status(self):
        info = self.getServerStatus(restrict=True, delay=5)
        if not info:
            info = self.lastCheckJSON
        msg = ['```']
        msg.append('Server: ' + info['serverName'])
        msg.append(self.format_gameServerURL)
        msg.append('Summary: ' + info['serverStatus']['Summary'])
        msg.append('Map: ' + info['serverStatus']['Map'])  
        msg.append('Players: ' + info['serverStatus']['Players'])
        msg.append('Remaining Time: ' + info['serverStatus']['RemainingTime'])
        msg.append('TournamentMode: ' + info['serverStatus']['TournamentMode'])
        msg.append('Status: ' + info['setupResult'])
        msg.append('```')
        return '\n'.join(msg)

    #########################################################################################
    # Functions:
    #########################################################################################
    def generatePasswords(self):
        """Generates random passwords for red and blue teams."""
        # Spectator password is not changed, think keeping it fixed is fine.
        self.redPassword = RED_PASSWORD_PREFIX + str(random.randint(0, 999))
        self.bluePassword = BLUE_PASSWORD_PREFIX + str(random.randint(0, 999))

    def getServerStatus(self, restrict: bool = False, delay: int = 0):
        if restrict and (datetime.now() - self.lastUpdateTime).total_seconds() < delay:
            # 5 second delay between requests when restricted.
            return None
        
        r = requests.post(self.postServer, headers=self.format_post_header_check)
        self.lastUpdateTime = datetime.now()
        if(r):
            return r.json()
        else:
            return None

    def updateServerStatus(self):
        info = self.getServerStatus()
        if info:
            self.gameServerName = info["serverName"]
            self.gameServerIP = info["serverAddr"]
            self.gameServerPort = info["serverPort"]
            if not self.endMatchPerformed:
                self.matchInProgress = info["matchStarted"]
            self.lastSetupResult = info["setupResult"]
            self.lastCheckJSON = info
            return True
        self.lastSetupResult = 'Failed'
        return False

    def setupMatch(self, players, maps):
        if not self.updateServerStatus() or self.matchInProgress:
            return False

        self.generatePasswords()
        headers = self.format_post_header_setup
        body = self.format_post_body_setup(players, maps)
        r = requests.post(self.postServer, headers=headers, json=body)
        if(r):
            info = r.json()
            self.lastSetupResult = info['setupResult']
            self.matchInProgress = info['matchStarted']
            self.lastSetupJSON = info
            self.endMatchPerformed = False

            # Get passwords from the server (doesn't currently seem to accept them)
            self.redPassword = info['setupConfig']['redPass']
            self.bluePassword = info['setupConfig']['bluePass']
            self.spectatorPassword = info['setupConfig']['specPass']

            return self.lastSetupResult == 'Completed'

        self.matchInProgress = False
        self.lastSetupResult = 'Failed'
        return False

    def endMatch(self):
        # returns server back to public
        if not self.updateServerStatus():
            return False

        r = requests.post(self.postServer, headers=self.format_post_header_endgame)
        if(r):
            info = r.json()
            self.lastSetupResult = info['setupResult']
            self.lastEndGameJSON = info
            if self.lastSetupResult == 'Completed':
                self.matchInProgress = False
                self.endMatchPerformed = True
                return True

            return False
        self.lastSetupResult = 'Failed'
        return False

    def processMatchFinished(self):
        if self.lastSetupResult == 'Failed' or not self.updateServerStatus():
            return False

        if not self.matchInProgress and self.lastSetupResult == 'Match Finished':
            return self.endMatch()

class AssaultPug(PugTeams):
    """Represents a Pug of 2 teams (to be selected), a set of maps to be played and a server to play on."""
    def __init__(self, numPlayers, numMaps, pickModeTeams, pickModeMaps):
        super().__init__(numPlayers, pickModeTeams)
        self.name = 'ASPug'
        self.desc = 'Assault PUG'
        self.maps = PugMaps(numMaps, pickModeMaps)
        self.servers = [GameServer(DEFAULT_SERVER_FILE)]
        self.serverIndex = 0
        self.lastPugTeams = 'No previous pug.'
        self.lastPugMaps = None
        self.lastPugTimeStarted = None
        self.pugLocked = False

    #########################################################################################
    # Properties:
    #########################################################################################
    @property
    def currentCaptainToPickMap(self):
        if self.captainsFull and not self.maps.mapsFull:
            return self.teams[self.maps.currentTeamToPickMap].captain
        else:
            return None

    @property
    def playersReady(self):
        if self.playersFull:
            return True
        return False

    @property
    def captainsReady(self):
        if self.captainsFull:
            return True
        return False

    @property
    def teamsReady(self):
        if self.captainsFull and self.teamsFull:
            return True
        return False

    @property
    def mapsReady(self):
        if self.maps.mapsFull:
            return True
        return False

    @property
    def matchReady(self):
        if self.teamsFull and self.maps.mapsFull:
            return True
        return False

    @property
    def gameServer(self):
        if len(self.servers):
            return self.servers[self.serverIndex]
        else:
            return None

    #########################################################################################
    # Formatted strings:
    #########################################################################################
    def format_players(self, players, number=False, mention=False):
        def name(p):
            return p.mention if mention else display_name(p)
        numberedPlayers = ((i, name(p)) for i, p in enumerate(players, 1) if p)
        fmt = '**{0})** {1}' if number else '{1}'
        return PLASEP.join(fmt.format(*x) for x in numberedPlayers)

    def format_all_players(self, number=False, mention=False):
        return self.format_players(self, number=number, mention=mention)

    def format_remaining_players(self, number=False, mention=False):
        return self.format_players(self.players, number=number, mention=mention)

    def format_red_players(self, number=False, mention=False):
        return self.format_players(self.red, number=number, mention=mention)

    def format_blue_players(self, number=False, mention=False):
        return self.format_players(self.blue, number=number, mention=mention)

    def format_teams(self, number=False, mention=False):
        teamsStr = '**Red Team:** {}\n**Blue Team:** {}'
        red = self.format_red_players(number=number, mention=mention)
        blue = self.format_blue_players(number=number, mention=mention)
        return teamsStr.format(red, blue)

    @property
    def format_pug_short(self):
        fmt = '**__{0.desc} [{1}/{0.maxPlayers}]__**'
        return fmt.format(self, len(self))

    def format_pug(self, number=True, mention=False):
        fmt = '**__{0.desc} [{1}/{0.maxPlayers}]:__**\n{2}'
        return fmt.format(self, len(self), self.format_all_players(number=number, mention=mention))

    @property
    def format_match_is_ready(self):
        fmt = ['Match is ready:']
        fmt.append(self.format_teams(mention=True))
        fmt.append('Maps:\n{}'.format(self.maps.format_current_maplist))
        fmt.append(self.gameServer.format_game_server)
        fmt.append(self.gameServer.format_spectator_password)
        return '\n'.join(fmt)

    @property
    def format_match_in_progress(self):
        fmt = ['Match in progress ({} ago):'.format(getDuration(self.lastPugTimeStarted))]
        fmt.append(self.format_teams(mention=False))
        fmt.append('Maps:\n{}'.format(self.maps.format_current_maplist))
        fmt.append(self.gameServer.format_game_server)
        fmt.append(self.gameServer.format_spectate_password)
        return '\n'.join(fmt)

    @property
    def format_last_pug(self):
        fmt = []
        if self.lastPugTimeStarted:
            fmt.append('Last **{}** ({} ago)'.format(self.desc, getDuration(self.lastPugTimeStarted)))
            fmt.append(self.lastPugTeams)
            fmt.append('Maps:\n{}'.format(self.lastPugMaps))
        else:
            fmt.append(self.lastPugTeams)
        return '\n'.join(fmt)

    @property
    def format_list_servers(self):
        indexedServers = ((i,s) for i,s in enumerate(self.servers, 1) if s)
        fmt = []
        for x in indexedServers:
            fmt.append('**{0})** {1}'.format(str(x[0]), x[1].format_server_info))

        return '\n'.join(fmt)

    #########################################################################################
    # Functions:
    #########################################################################################
    def addServer(self, serverfile: str):
        try:
            self.servers.add(GameServer(serverfile))
            return True
        except:
            return False

    def removeServer(self, index):
        if index >= 0 and index < len(self.servers):
            self.servers.pop(index)
            if self.serverIndex == index and len(self.servers) > 0:
                self.serverIndex = 0

    def removePlayerFromPug(self, player):
        if self.removePugTeamPlayer(player):
            # Reset the maps too if maps have already been picked,
            # removing a player will mean teams and maps must be re-picked.
            self.maps.resetMaps()
            return True
        else:
            return False

    def pickMap(self, captain, index: int):
        if captain == self.currentCaptainToPickMap:

            if index < 0 or index >= len(self):
                return False

            if index >= 0 or index < len(MAP_LIST):
                map = self.maps.completeMaplist[index]
                return self.maps.addMap(map)
        return False

    def setupPug(self):
        if not self.pugLocked and self.matchReady:
            # Try to set up 5 times with a 5s delay between attempts.
            result = False
            for x in range(0, 5):
                result = self.gameServer.setupMatch(self, self.maps)

                if not result:
                    time.sleep(5)
                else:
                    self.pugLocked = True
                    self.lastPugTimeStarted = datetime.now()
                    self.storeLastPug()
                    return True
        return False

    def storeLastPug(self):
        if self.matchReady:
            self.lastPugTeams = self.format_teams()
            self.lastPugMaps = self.maps.format_current_maplist
            self.lastPugTimeStarted = datetime.now()
            return True
        return False

    def resetPug(self):
        self.maps.resetMaps()
        self.fullPugTeamReset()
        if self.pugLocked or (self.gameServer and self.gameServer.matchInProgress):
        # Is this a good idea? Might get abused.
            self.gameServer.endMatch()
        self.pugLocked = False
        return True

#########################################################################################
# Static methods for cogs.
#########################################################################################
def isActiveChannel_Check(ctx): return ctx.bot.get_cog('PUG').isActiveChannel(ctx)

def isPugInProgress_Warn(ctx): return ctx.bot.get_cog('PUG').isPugInProgress(ctx, warn=True)

def isPugInProgress_Ignore(ctx): return ctx.bot.get_cog('PUG').isPugInProgress(ctx, warn=False)

#########################################################################################
# Main pug cog class.
#########################################################################################
class PUG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.activeChannel = None
        self.pugInfo = AssaultPug(DEFAULT_PLAYERS, DEFAULT_MAPS, DEFAULT_PICKMODETEAMS, DEFAULT_PICKMODEMAPS)

        # Start the looped task which checks the server when a pug is in progress (to detect match finished)
        self.updateGameServer.start()

    def cog_unload(self):
        self.updateGameServer.cancel()

    @tasks.loop(seconds=60.0)
    async def updateGameServer(self):
        if self.pugInfo.pugLocked:
            print('Updating game server...\n')
            if not self.pugInfo.gameServer.updateServerStatus():
                print('Cannot contact game server.\n')
            if self.pugInfo.gameServer.processMatchFinished():
                await self.bot.send(self.activeChannel, 'Match finished. Resetting pug...')
                if self.pugInfo.resetPug():
                    await self.bot.send(self.activeChannel, self.pugInfo.format_pug)
                    print('Match over.')
                    return
                await self.bot.send(self.activeChannel, 'Reset failed.')
                print('Reset failed')
            print('Could not contact game server.\n')
            

    @updateGameServer.before_loop
    async def before_updateGameServer(self):
        print('Waiting for updating game server...\n')
        await self.bot.wait_until_ready()

    #########################################################################################
    # Formatted strings:
    #########################################################################################

    def format_pick_next_player(self, mention=False):
        player = self.pugInfo.currentCaptainToPickPlayer
        return '{} to pick next player (**.pick <number>**)'.format(player if mention else display_name(player))

    def format_pick_next_map(self, mention=False):
        player = self.pugInfo.currentCaptainToPickMap
        return '{} to pick next map (use **.map <number>** to pick and **.listmaps** to view available maps)'.format(player.mention if mention else display_name(player))

    #########################################################################################
    # Functions:
    #########################################################################################
    def isActiveChannel(self, ctx):
        return self.activeChannel is not None and self.activeChannel == ctx.message.channel

    async def processPugStatus(self, ctx):
        # Big function to test which stage of setup we're at:
        if not self.pugInfo.playersFull:
            # Not filled, nothing to do.
            return

        # Work backwards from match ready.
        if self.pugInfo.matchReady:
            # Implies self.pugInfo.mapsReady.
            if self.pugInfo.setupPug():
                await self.sendPasswordsToTeams()
                await ctx.send(self.format_match_is_ready(self.pugInfo))                
            else:
                msg = ['**PUG Setup Failed**. Try again or contact an admin.']
                msg.append('Resetting...')
                await ctx.send('\n'.join(msg))
                self.pugInfo.resetPug()

        if self.pugInfo.teamsReady:
            # Need to pick maps.
            await ctx.send(self.format_pick_next_map(mention=True))
        
        if self.pugInfo.captainsReady:
            # Need to pick players.
            msg = '\n'.join([
                self.pugInfo.format_all_players(number=True),
                self.pugInfo.format_teams(),
                self.format_pick_next_player(mention=True)])
            await ctx.send(msg)
        
        if self.pugInfo.numCaptains == 1:
            # Need second captain (blue is always second)
            await ctx.send('Waiting for **Blue Team** captain. Type **.captain** to become Blue captain.')

        if self.playersReady:
            # Need captains.
            msg = ['**{}** has filled.'.format(self.pugInfo.name)]
            if self.playersFull and len(self) == 2:
                # Special case, 1v1: assign captains instantly, so jump straight to map picks.
                self.setCaptain(self.players[0])
                self.setCaptain(self.players[1])
                await ctx.send('Teams have been automatically filled.\n{}'.format(self.pugInfo.format_teams(mention=True)))
                self.processPugStatus(ctx)

            # Standard case, moving to captain selection.
            msg.append(self.pugInfo.format_pug(mention=True))
            # Need first captain (red is always first)
            msg.append('Type **.captain** to become Red captain.')
            await ctx.send('\n'.join(msg))

    async def sendPasswordsToTeams(self):
        if self.pugInfo.matchReady:
            msg_redPassword = self.pugInfo.gameServer.format_red_password
            msg_redServer = self.pugInfo.gameServer.format_gameServerURL_red
            msg_bluePassword = self.pugInfo.gameServer.format_blue_password
            msg_blueServer = self.pugInfo.gameServer.format_gameServerURL_blue
            for player in self.pugInfo.red:
                await player.send('{0}\nJoin the server @ **{1}**'.format(msg_redPassword, msg_redServer))
            for player in self.pugInfo.blue:
                await player.send('{0}\nJoin the server @ **{1}**'.format(msg_bluePassword, msg_blueServer))
        if self.activeChannel:
            await self.activeChannel.send('Check private messages for server passwords.')
        return True

    async def isPugInProgress(self, ctx, warn: bool=False):
        if not self.isActiveChannel(ctx):
            return False
        if warn and self.pugInfo.pugLocked:
            msg = ['Match is currently in progress.']
            if ctx.message.author in self.pugInfo:
                msg.append('{},  please, join the match or find a sub.'.format(ctx.author.mention))
                msg.append('If the match has just ended, please, wait at least 60 seconds for the pug to reset.')
            else:
                msg.append('Pug will reset when it is finished.')
            await ctx.send('\n'.join(msg))
        return not self.pugInfo.pugLocked

    #########################################################################################
    # Bot commands.
    #########################################################################################
    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def enable(self, ctx):
        """Enables PUG commands in the channel. Note only one channel can be active at a time."""
        self.activeChannel = ctx.message.channel
        await ctx.send('PUG commands are enabled in ' + self.activeChannel.mention)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def disable(self, ctx):
        """Disables PUG commands in the channel. Note only one channel can be active at a time."""
        await ctx.send('PUG commands are disabled in ' + self.activeChannel.mention)
        self.activeChannel = None

    @commands.command(aliases = ['pug'])
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    async def list(self, ctx):
        """Displays pug status"""
        if self.pugInfo.pugLocked:
            await ctx.send(self.pugInfo.format_match_in_progress)
        else:
            await ctx.send(self.pugInfo.format_pug())

    @commands.command()
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    async def server(self, ctx):
        """Displays Pug server info"""
        await ctx.send(self.pugInfo.gameServer.format_game_server)

    @commands.command()
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    async def serverstatus(self, ctx):
        """Displays Pug server info"""
        await ctx.send(self.pugInfo.gameServer.format_game_server_status)

    @commands.command()
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    @commands.check(isPugInProgress_Warn)
    async def setplayers(self, ctx, limit: int):
        """Sets number of players"""
        if self.pugInfo.captainsReady:
            await ctx.send('Pug already in picking mode. Reset if you wish to change player limit.')
        elif (limit > 1 and limit % 2 == 0 and limit <= MAX_PLAYERS_LIMIT):
            self.pugInfo.setMaxPlayers(limit)
            await ctx.send('Player limit set to ' + str(self.pugInfo.maxPlayers))
            await self.processPugStatus(ctx)
        else:
            await ctx.send('Player limit unchanged. Players must be a multiple of 2 + between 2 and ' + str(MAX_PLAYERS_LIMIT))

    @commands.command()
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    @commands.check(isPugInProgress_Warn)
    async def setmaps(self, ctx, limit: int):
        """Sets number of maps"""
        if (limit > 0 and limit <= MAX_MAPS_LIMIT):
            self.pugInfo.maps.setMaxMaps(limit)
            await ctx.send('Map limit set to ' + str(self.pugInfo.maps.maxMaps))
            await self.processPugStatus(ctx)
        else:
            await ctx.send('Map limit unchanged. Map limit is ' + str(MAX_MAPS_LIMIT))

    @commands.command()
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    async def reset(self, ctx):
        """Resets the pug. Players will need to rejoin. This will reset the server, even if a match is running. Use with care."""
        await ctx.send('Removing all signed players: {}'.format(self.pugInfo.format_all_players(number=False, mention=True)))
        if self.pugInfo.resetPug():
            await ctx.send('Pug Reset. {}'.format(self.pugInfo.format_pug_short))
        else:
            await ctx.send('Reset failed. Please, try again or inform an admin.')

    @commands.command()
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    @commands.check(isPugInProgress_Warn)
    async def resetcaptains(self, ctx):
        """Resets back to captain mode. Any players or maps picked will be reset."""
        if self.pugInfo.numCaptains < 1:
            return

        self.pugInfo.maps.resetMaps()
        self.pugInfo.softPugTeamReset()
        await ctx.send('Captains have been reset.')
        await self.processPugStatus(ctx)

    @commands.command(aliases=['j'])
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    @commands.check(isPugInProgress_Warn)
    async def join(self, ctx):
        """Joins the pug"""
        player = ctx.message.author
        if not self.pugInfo.addPlayer(player):
            if self.pugInfo.playersReady:
                await ctx.send('Pug is already full.')
                return
            else:
                await ctx.send('Already added.')
                return

        await ctx.send(display_name(player) + ' added. ' + self.pugInfo.format_pug())
        await self.processPugStatus(ctx)

    @commands.command(aliases=['l'])
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    @commands.check(isPugInProgress_Warn)
    async def leave(self, ctx):
        """Leaves the pug"""
        player = ctx.message.author
        if self.pugInfo.removePlayerFromPug(player):
            await ctx.send(display_name(player) + ' left. ' + self.pugInfo.format_pug())

    @commands.command()
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    @commands.check(isPugInProgress_Ignore)
    async def captain(self, ctx):
        """Volunteer to be a captain in the pug"""
        if self.pugInfo.gameServer.matchInProgress: # Not strictly needed here, would be caught by setCaptain.
            return

        player = ctx.message.author

        if self.pugInfo.setCaptain(player):
            if self.pugInfo.captainsFull:
                await ctx.send(player.mention + ' is captain for the **Blue Team**')
                await self.processPugStatus(ctx)
            else:
                await ctx.send(player.mention + ' is captain for the **Red Team**')
                await self.processPugStatus(ctx)

    @commands.command(aliases=['p'])
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    async def pick(self, ctx, *players: int):
        """Picks a player for a team in the pug"""
        captain = ctx.message.author
        if not self.pugInfo.captainsFull or captain == self.pugInfo.currentCaptainToPickPlayer or self.pugInfo.gameServer.matchInProgress:
            return

        picks = list(itertools.takewhile(functools.partial(self.pugInfo.pickPlayer, captain), (x - 1 for x in players)))

        if picks:
            if self.pugInfo.teamsFull:
                await ctx.send('Teams have been selected:\n{}'.format(self.pugInfo.format_teams(mention=True)))
            await self.processPugStatus(ctx)

    @commands.command()
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    async def listmaps(self, ctx):
        """Returns the list of maps to pick from"""
        msg = ['Server map list is: ']
        msg.append(self.pugInfo.maps.format_complete_maplist)
        await ctx.send('\n'.join(msg))

    @commands.command(aliases=['m'])
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    async def map(self, ctx, idx: int):
        """Picks a map in the pug"""

        captain = ctx.message.author
        if (self.pugInfo.matchReady or not self.pugInfo.teamsReady or captain != self.pugInfo.currentCaptainToPickMap):
            # Skip if not in captain mode with full teams or if the author is not the next map captain.
            return

        mapIndex = idx - 1 # offset as users see them 1-based index.
        if mapIndex < 0 or mapIndex >= len(self.pugInfo.maps.completeMaplist):
            await ctx.send('Pick a valid map. Use .map <map_number>. Use .listmaps to see the list of available maps.')
            return

        if not self.pugInfo.pickMap(captain, mapIndex):
            await ctx.send('Map already picked. Please, pick a different map.')
            return
        
        msg = ['Maps chosen:']
        msg.append(self.pugInfo.maps.format_current_maplist)
        await ctx.send(msg)
        await self.processPugStatus(ctx)

    @commands.command()
    @commands.guild_only()
    @commands.check(isActiveChannel_Check)
    async def last(self, ctx):
        """Shows the last pug info"""
        if self.pugInfo.gameServer.matchInProgress:
            msg = ['Last match not complete...\n' + self.format_match_in_progress(self.pugInfo)]
            await ctx.send(msg)
        else:
            await ctx.send(self.pugInfo.format_last_pug)

def setup(bot):
    bot.add_cog(PUG(bot))