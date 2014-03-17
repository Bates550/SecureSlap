import sys
import re
from circuits import Component, Event
from circuits.net.sockets import *
from crypto import *
import user

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

RANDBYTELEN		=	16

class Newuser(Event):
	''' Fired when a message with code 00 is received from the server. Asks user for username and responds to the server with code 00 and the username. '''

class Listen(Event):
	''' Listen for user input '''

class Userlist(Event):
	''' Receive user list '''

class Challenge(Event):
	''' Challenge another user '''

class GameSession(Event):
	''' GameSession event '''

class Client(Component):

	def __init__(self, host='localhost', port=4000):
		super(Client, self).__init__()

		self.host = host
		self.port = port
		self.users = []
		self.username = ''
		self.reserved = ['quit', 'exit']

		self.closing = False
		self.waiting = False

		TCPClient().register(self)
		if len(sys.argv) > 1:
			if sys.argv[1] == '-d':
				from circuits import Debugger
				self += Debugger()

	def read(self, data):
		code = data[0]
		message = data[1:]
		if code == int(S_CHALNG):
			challenger = decrypt_AES(self.symkey, message)
			print("%s is challenging you!\nAccept or deny?" % challenger)
			response = ''
			while response == '':
				r = input("> ")
				if r == 'accept' or r == 'Accept' 	\
					or r == 'a' or r == 'A' 		\
					or r == 'yes' or r == 'Yes'		\
					or r  == 'y' or r == 'Y':
					response = 'accept' 
				elif r == 'deny' or r == 'Deny'		\
					or r == 'd' or r == 'D'			\
					or r == 'no' or r == 'No'		\
					or r == 'n' or r == 'N':
					response = 'deny'
				else:
					print("Invalid input. Accept or deny?")
			ciphertext = encrypt_AES(self.symkey, (self.username+','+challenger).encode())
			if response == 'accept':
				self.fire(write(B_CHALNGACCEPT+ciphertext))
				self.fire(GameSession())
			elif response == 'deny':
				self.fire(write(B_CHALNGDENY+ciphertext))
		elif code == int(S_CHALNGACCEPT):
			challenged = decrypt_AES(self.symkey, message)
			print("%s has accepted your challenge." % challenged)
		elif code == int(S_CHALNGDENY):
			challenged = decrypt_AES(self.symkey, message)
			print("%s has denied your challenge." % challenged)
			self.fire(Listen())
		elif code == int(S_CHALNGFAIL):
			toChallenge = decrypt_AES(self.symkey, message)
			print("%s is not currently connected." % toChallenge)
			self.waiting = False
			self.fire(Listen())
		elif code == int(S_USERLIST):
			message = decrypt_AES(self.symkey, message)
			self.users = message.split(',')
			print("Users:")
			for user in self.users:
				if user != self.username:
					print("   %s" % user)
			self.waiting = False	
			self.fire(Listen())	
		elif code == int(S_NEWUSER):
			print("Welcome to the Secure Slap server!\nEntire your desired username:")
			self.fire(Newuser())
		elif code == int(S_NAMEACCEPT):
			print("Username accepted! Enjoy your stay.")
			self.fire(Listen())
		elif code == int(S_NAMETAKEN):
			print("Username already taken. Please enter another:")
			self.fire(Newuser())
		elif code == int(S_SERVKEY):
			plainsymkey = Random.get_random_bytes(RANDBYTELEN)
			self.symkey = SHA256.new(str(plainsymkey).encode()).digest()
			pubkey = RSA.importKey(message)
			self.pubkey = PKCS1_OAEP.new(pubkey)
			ciphertext = self.pubkey.encrypt(self.symkey)
			self.fire(write(B_SYMKEY+ciphertext))
		else:
			print("Unrecognized byte code", file=sys.stderr)

	def Listen(self):
		usrin = input(">>> ")
		if usrin == 'help':
			print("help 	 -- shows this list")
			print("challenge -- allows you to challenge another user")
			print("users 	 -- displays a list of users currently connected")
			print("list 	 -- same as users")
			print("exit 	 -- exits Secure Slap")
		elif usrin == 'exit' or usrin == 'quit':
			print("Exiting...")
			self.closing = True
			self.fire(close())
		elif usrin == 'users' or usrin == 'list':
			self.fire(write(B_USERLIST))
			self.waiting = True
		elif usrin == 'challenge':
			print("Enter name of user to challenge.")
			toChallenge = input("> ")
			if toChallenge == self.username:
				print("You cannot challenge yourself. Try a different command since you're obviously not ready for this.")
			elif toChallenge == 'exit' or toChallenge == 'quit':
				pass
			else:
				print("Challenging %s..." % toChallenge)
				self.waiting = True
				self.fire(Challenge(toChallenge))
		else: 
			print("Invalid command. Type 'help' for a list of commands.")
		if (self.closing == False and self.waiting == False):
			self.fire(Listen())

	def close(self):
		self.stop()

	def ready(self, *args):
		self.fire(connect(self.host, self.port))

	def Challenge(self, toChallenge):
		ciphertext = encrypt_AES(self.symkey, toChallenge.encode())
		self.fire(write(B_CHALNG+ciphertext))

	def GameSession(self):
		pass

	def Newuser(self):
		username = input("> ")
		if username in self.reserved or not re.match('^[\w-]+$', username):
			print("Invalid username. Try again.")
			self.fire(Newuser())
		else:
			self.username = username
			ciphertext = encrypt_AES(self.symkey, self.username.encode())
			self.fire(write(B_NEWUSER+ciphertext))


Client().run()

