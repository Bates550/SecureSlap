from circuits import Component, Event
from circuits.net.sockets import *
from crypto import *
from user import *
import sys

''' Message Code Str '''
S_NEWUSER 		= 	'00'
S_USERLIST		=	'01'
S_NAMETAKEN		=	'02'
S_NAMEACCEPT	=	'03'
S_SERVKEY 		=	'04'
S_SYMKEY		= 	'05'
S_CHALNG		=	'06'
S_CHALNGACCEPT	=	'07'
S_CHALNGDENY	=	'08'
S_CHALNGFAIL	=	'09'

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

		self.privkey = RSA.generate(2048, Random.new().read)
		self.pubkey = self.privkey.publickey()
		self.pubkeybstr = self.pubkey.exportKey()

		self += TCPServer((self.host, self.port))
		if len(sys.argv) > 1:
			if sys.argv[1] == '-d':
				pass
				from circuits import Debugger
				self += Debugger()

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

	def close(self, sock):
		print("close")

	# Does not get fired when a client closes. According to the developer, James Mills, this should not happen, but Circuits is not developed or debugged with Windows and is thus not guaranteed to work on Windows. I have not had the opportunity to test Secure Slap on a Unix system to confirm that this problem does not occur. 
	def disconnected(self):
		pass
		# Moved this functionality to disconnect event, which seems to work.

	def read(self, sock, data):
		code = data[0]
		message = data[1:]
		if code == int(S_CHALNG):
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
		elif code == int(S_CHALNGACCEPT) or code == int(S_CHALNGDENY):
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
		elif code == int(S_CHALNGFAIL):
			pass
		elif code == int(S_NEWUSER):
			message = decrypt_AES(self.clients[sock], message)
			self.fire(Newuser(sock, message))
		elif code == int(S_USERLIST):
			self.fire(Userlist(sock))
		elif code == int(S_SYMKEY):
			rsakey = PKCS1_OAEP.new(self.privkey)
			# Store symkey in clients[sock] until username is acquired and User object can be created.
			self.clients[sock] = rsakey.decrypt(message)
			self.fire(write(sock, B_NEWUSER))

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

Server().run()