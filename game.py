from random import seed, randint, shuffle

MAXGAMES = 100

class Game():
	gameids = []

	def __init__(self, players):
		shuffle(players)
		self._players = players
		self._whose_turn = self._set_first_turn()
		self._gameid = self._set_gameid()
		self._waiting = False
		self._game_ended = False

	def __repr__(self):
		if not self._game_ended:
			return "Gameid: {} (\n Gameids: {}\n Players: {}\n Turn: {}\n)".format(self._gameid, Game.gameids, self._players, self._players[self._whose_turn])
		return "Game {} has ended.".format(self._gameid)

	def _set_first_turn(self):
		seed()
		return randint(0, len(self._players)-1)

	# Returns a unique gameid or -1 if there are already MAXGAMES running. 
	def _set_gameid(self):
		if len(Game.gameids) >= MAXGAMES:
			return -1
		seed()
		r = randint(0, MAXGAMES)
		while r in Game.gameids:
			r = randint(0, MAXGAMES)
		Game.gameids.append(r)
		return r

	def _end_game(self):
		self._game_ended = True
		Game.gameids.remove(self._gameid)

	def gameid(self):
		return self._gameid

	def whose_turn(self):
		return self._whose_turn

	def players(self):
		return self._players

	# Returns True if it is now the next turn, False otherwise. 
	def next_turn(self):
		self._whose_turn = (self._whose_turn + 1)%(len(self._players)-1)	

	# Player can be a User or str containing a username
	# Returns 0 if player has been removed but there is still more than one player in the game.
	# Returns 1 if player has been removed and game has ended since there are one or less players in the game.
	# Returns -1 if player is not in the game. 
	def player_quit(self, player):
		if player in self._players:
			if self._players[self._whose_turn] == player:
				self.next_turn()
			self._players.remove(player)
			self._whose_turn = (self._whose_turn - 1)%len(self._players)
			if len(self._players) <= 1:
				self._end_game()
				return 1
			return 0
		else:
			return -1

if __name__ == '__main__':
	players = ['Tybalt', 'Romeo', 'Juliet']
	print('New game!')
	game = Game(players)
	print(game)
	game.player_quit('Tybalt')
	print('Tybalt quits!')
	print(game)

	print('New game!')
	players2 = ['Mercutio', 'Paris', 'Rosaline']
	game2 = Game(players2)
	print(game2)

	game.player_quit('Romeo')
	print('Romeo quit!')
	print(game)