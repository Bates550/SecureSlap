class User:
	def __init__(self, symkey, username):
		self.symkey = symkey
		self.username = username
		self.ingame = False
		self.opponent = None