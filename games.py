import pickle

class Party(object):
    def __init__(self, name, playername):
        self.party_name = name
        self.players = set(playername)
        self.game_over = False
        self.currently_playing = playername

    def add_player(self, playername):
        self.players.add(playername)

    def del_player(self, playername):
        self.players.discard(playername)

    def close_game(self):
        self.game_over = True

    def pickle(self):
        return pickle.dumps(self)