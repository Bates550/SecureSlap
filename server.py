from circuits import Component, Event
from circuits.net.sockets import *
from crypto import *
from user import *
import sys

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
B_CHALNGFAIL	=	b'\x09'

class Newuser(Event):
	''' Newuser event '''

class Userlist(Event):
	''' Userlist event '''

class Server(Component):
	
	def __init__(self, host='localhost', port=4000):
		super(Server, self).__init__()

		self.host = host
		self.port = port

		# clients 	-> {sock: User object}
		# or		-> {sock: symkey} if username has not yet been acquired.
		self.clients = {}
		self.ingame = []
		self.sessions = {}
		self.codes = {
			I_NEWUSER 		:	self._do_code_newuser,
			I_USERLIST		:	self._do_code_userlist,
			I_SYMKEY		:	self._do_code_symkey,
			I_CHALNG		:	self._do_code_chalng,
			I_CHALNGACCEPT	:	self._do_code_chalngreply,
			I_CHALNGDENY	:	self._do_code_chalngreply,
			I_CHALNGFAIL	:	self._do_code_chalngfail
		}

		self.privkey = RSA.generate(2048, Random.new().read)
		self.pubkey = self.privkey.publickey()
		self.pubkeybstr = self.pubkey.exportKey()

		self += TCPServer((self.host, self.port))
		if len(sys.argv) > 1:
			if sys.argv[1] == '-d':
				from circuits import Debugger
				self += Debugger()

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
			ciphertext = encrypt_AES(self.clients[sock].symkey, toChallenge.encode())
			self.fire(write(sock, B_CHALNGFAIL+ciphertext))
	
	def _do_code_chalngreply(self, sock, message):
		plaintext = decrypt_AES(self.clients[sock].symkey, message)
		challenged, challenger = plaintext.split(',')
		self.clients[sock].ingame = True
		self.clients[sock].opponent = challenger
		self.ingame.append(sock)
		for socket in self.clients.keys():
			if self.clients[socket].username == challenger:
				ciphertext = encrypt_AES(self.clients[socket].symkey, challenged)
				self.fire(write(socket, bytes.fromhex('0'+str(code))+ciphertext))
				self.clients[socket].ingame = True
				self.clients[socket].opponent = challenged
				self.ingame.append(socket)
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