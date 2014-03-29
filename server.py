# Outside dependencies
import sys
from circuits import Component, Event, Debugger
from circuits.net.sockets import *
from crypto import *

# Local dependencies
from user import User
from game import Game

''' Message Code Ints '''
I_NEWUSER 		= 	0
I_USERLIST		=	1
I_NAMETAKEN		=	2
I_NAMEACCEPT	=	3
I_SERVKEY 		=	4
I_SYMKEY		= 	5
I_CHALNG		=	6
I_CHALNGACCEPT	=	7
I_CHALNGDENY	=	8
I_CHALNGFAIL	=	9
I_GAMEQUIT		= 	10
I_GAMESLAP		= 	11
I_GAMENEXT		= 	12
I_GAMEID		= 	13

''' Message Code Bytes '''
B_NEWUSER		= 	b'\x00'
B_USERLIST		=	b'\x01'
B_NAMETAKEN		=	b'\x02'
B_NAMEACCEPT	= 	b'\x03'
B_SERVKEY		=	b'\x04'
B_SYMKEY		= 	b'\x05'
B_CHALNG		=	b'\x06'
B_CHALNGACCEPT	=	b'\x07'
B_CHALNGDENY	=	b'\x08'
B_CHALNGFAIL	=	b'\x09' # b'\t'
B_GAMEQUIT		= 	b'\x0A' # b'\n'
B_GAMESLAP		= 	b'\x0B'
B_GAMENEXT		= 	b'\x0C'
B_GAMEID		= 	b'\x0D' # b'\r'

class Newuser(Event):
	''' Newuser event '''

class Userlist(Event):
	''' Userlist event '''

class Server(Component):
	
	def __init__(self, host='localhost', port=8000):
		super(Server, self).__init__()

		self.host = host
		self.port = port

		self.clients = {} 	# clients 	-> {sock: User object} or {sock: symkey} if username has not yet been acquired.
		self.ingame = []
		self.games = {}		# games 	-> {gameid : game}
		self.codes = {
			I_NEWUSER 		:	self._do_code_newuser,
			I_USERLIST		:	self._do_code_userlist,
			I_SYMKEY		:	self._do_code_symkey,
			I_CHALNG		:	self._do_code_chalng,
			I_CHALNGACCEPT	:	self._do_code_chalngaccept,
			I_CHALNGDENY	:	self._do_code_chalngdeny,
			I_CHALNGFAIL	:	self._do_code_chalngfail,
			I_GAMEQUIT		:	self._do_code_gamequit,
			I_GAMESLAP		:	self._do_code_gameslap,
			I_GAMENEXT		:	self._do_code_gamenext
		}

		self.privkey = RSA.generate(2048, Random.new().read)
		self.pubkey = self.privkey.publickey()
		self.pubkeybstr = self.pubkey.exportKey()

		self += TCPServer((self.host, self.port))
		self += Debugger()
		'''if len(sys.argv) > 1:
			if sys.argv[1] == '-d':
				from circuits import Debugger
				self += Debugger()
				'''
				
	def read(self, sock, data):
		code = data[0]
		message = data[1:]
		if code in self.codes.keys():
			self.codes[code](sock, message)
		else:
			print("Unrecognized byte code", file=sys.stderr)

	def started(self, *args):
		print("Server started.")

	def ready(self, *args):
		print("Server ready.")

	def connect(self, sock, host, port):
		# Send RSA public key to client.
		self.fire(write(sock, B_SERVKEY+self.pubkeybstr))

	def disconnect(self, sock):
		noclients = True
		deleted = self.clients[sock].username
		del self.clients[sock]
		print("Deleted %s." % deleted)
		print("Clients:")
		for user in self.clients.values():
			if type(user) is User:
				print("   %s" % user.username)
				noclients = False
		if noclients:
			print("   There are no clients connected.")

	def Newuser(self, sock, username):
		nametaken = False
		for client in self.clients.values():
			if type(client) is User:
				if client.username == username:
					self.fire(write(sock, B_NAMETAKEN))
					nametaken = True 
					break
		if not nametaken:
			symkey = self.clients[sock]
			self.clients[sock] = User(symkey, username)
			self.fire(write(sock, B_NAMEACCEPT))	

	def Userlist(self, sock):
		userlist = []
		for client in self.clients.values():
			if type(client) is User:
				userlist.append(client.username)
		ciphertext = encrypt_AES(self.clients[sock].symkey, ','.join(userlist).encode())
		self.fire(write(sock, B_USERLIST+ciphertext))

	def _do_code_gamequit(self, sock, message):
		gameid = decrypt_AES(self.clients[sock].symkey, message)
		player = self.clients[sock]
		retval = self.games[gameid].player_quit(player)
		if retval == 1:
			self.games.remove(gameid)
		elif retval == -1:
			print('Tried to remove nonexistent player from game {}'.format(gameid), file=sys.stderr)

	def _do_code_gameslap(self, sock, message):
		time_slapped = float(decrypt_AES(self.clients[sock].symkey, message))
		user = self.clients[sock]

	def _do_code_gamenext(self, sock, message):
		pass

	def _do_code_chalng(self, sock, message):
		challenger = self.clients[sock].username
		toChallenge = decrypt_AES(self.clients[sock].symkey, message)
		toChallengeExists = False
		for socket, client in self.clients.items():
			if type(client) is User:
				if toChallenge == client.username:
					toChallengeExists = True
					ciphertext = encrypt_AES(self.clients[socket].symkey, challenger.encode())
					self.fire(write(socket, B_CHALNG+ciphertext))
					break
		if not toChallengeExists:
			self.fire(write(sock, B_CHALNGFAIL))
	
	# NOTE: this can be combined with _do_code_chalngden(); the only difference is which byte code is sent, but I will have to change the way arguments are passed in the read event if this is to work such that the code can be passed. I feel like if I just pass the code to all of the _do_code functions, why even have them in the codes dict? Maybe use *args for variable arg length?
	def _do_code_chalngaccept(self, sock, message):
		plaintext = decrypt_AES(self.clients[sock].symkey, message)
		challenged, challenger = plaintext.split(',')
		players = [self.clients[sock]]

		for user in self.clients.values():
			if user == challenger:
				players.append(user)
		
		# Init new Game and put it in games dict with gameid as key
		new_game = Game(players)
		gameid = new_game.gameid()
		self.games[gameid] = new_game		

		# Set gameid for challenged in clients dict and send gameid
		self.clients[sock].set_game(gameid)
		ciphertext = encrypt_AES(self.clients[sock].symkey, str(gameid).encode())
		self.fire(write(sock, B_GAMEID+ciphertext))

		# Set gameid for challenger in clients dict and send gameid
		for socket, user in self.clients.items():
			if user == challenger:
				print("Sent B_CHALNGACCEPT to {}".format(user))
				ciphertext = encrypt_AES(user.symkey, str(gameid).encode())
				self.fire(write(socket, B_CHALNGACCEPT+ciphertext))

	def _do_code_chalngdeny(self, sock, message):
		plaintext = decrypt_AES(self.clients[sock].symkey, message)
		challenged, challenger = plaintext.split(',')
		for socket in self.clients.keys():
			if self.clients[socket].username == challenger:
				self.fire(write(socket, B_CHALNGDENY))
				break

	def _do_code_chalngfail(self, sock, message):
		pass

	def _do_code_newuser(self, sock, message):
		message = decrypt_AES(self.clients[sock], message)
		self.fire(Newuser(sock, message))

	def _do_code_userlist(self, sock, message):
		self.fire(Userlist(sock))

	def _do_code_symkey(self, sock, message):
		rsakey = PKCS1_OAEP.new(self.privkey)
		# Store symkey in clients[sock] until username is acquired and User object can be created.
		self.clients[sock] = rsakey.decrypt(message)
		self.fire(write(sock, B_NEWUSER))

Server().run()