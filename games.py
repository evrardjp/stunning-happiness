import pickle
from uuid import uuid4 as uuidgen
from collections import namedtuple

# Everything should be in bytes, please decode to utf8
class Party(object):
    def __init__(self, name):
        self.party_name = name
        self.players = set()
        self.game_over = False
        self.currently_playing = ""
        self.uuid = uuidgen()

    def add_player(self, playername):
        if len(self.currently_playing) == 0:
            self.currently_playing = playername
        self.players.add(playername)

    def del_player(self, playername):
        self.players.discard(playername)
        if len(self.players) == 0:
            self.close_game()

    def close_game(self):
        self.game_over = True

    def serialize(self):
        return pickle.dumps(self)
    
    @staticmethod
    def deserialize(obj):
        return pickle.loads(obj)

SimpleParty = namedtuple('SimpleParty', ['party_name', 'party_size', 'players'])

class InGamePlayer(object):
    pass