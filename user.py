class User:
	def __init__(self, symkey, username):
		self.symkey = symkey
		self.username = username
		self._in_game = False
		self._gameid = None
		self._opponents = None

	def __repr__(self):
		return "{}".format(self.username)

	def __eq__(self, right):
		if type(right) is str:
			return self.username == right
		return NotImplemented

	def set_game(self, gameid):
		self._gameid = gameid
		if self._gameid:
			self._in_game = True
		else:
			self._in_game = False

	def exit_game(self):
		self._in_game = False
		self._gameid = None
		self._opponents = None




