# Outside dependencies 
import sys, re, msvcrt, threading
from queue import Queue
from circuits import Component, Event
from circuits.net import sockets

# Local dependencies  
from crypto import *
import user
from inputThread import read_input

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
M_CMDLIST		=	"help 	  -- shows this list\nchallenge -- allows you to challenge another user\nusers 	  -- displays a list of users currently connected\nlist 	  -- same as users\nexit 	  -- exits Secure Slap\n"

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
		self.commands = {
			'help'		: 	self._doHelp, 
			'quit'		:	self._doQuit, 
			'exit'		:	self._doQuit, 
			'challenge'	:	self._doChallenge,
			'users'		:	self._doList,
			'list'		:	self._doList,
			''			:	self.Listen
		}
		
		self.waiting = False
		self.threadStop = False
		self.first_cmd = True
		self.user_buffer = ''

		sockets.TCPClient().register(self)
		if len(sys.argv) > 1:
			if sys.argv[1] == '-d':
				from circuits import Debugger
				self += Debugger()

	def read(self, data):
		code = data[0]
		message = data[1:]
		if code == int(S_CHALNG):
			challenger = decrypt_AES(self.symkey, message)
			print("{} is challenging you!\nAccept or deny?".format(challenger))
			response = None
			while not response:
				r = input("> ").lower()
				if r == 'accept' or r == 'a' 	\
					or r == 'yes' or r  == 'y':
					response = 'accept' 
				elif r == 'deny' or r == 'd' 	\
					or r == 'no' or r == 'n':
					response = 'deny'
				else:
					print("Invalid input. Accept or deny?")
			ciphertext = encrypt_AES(self.symkey, (self.username+','+challenger).encode())
			if response == 'accept':
				self.fire(sockets.write(B_CHALNGACCEPT+ciphertext))
				self.fire(GameSession())
			elif response == 'deny':
				self.fire(sockets.write(B_CHALNGDENY+ciphertext))
				#self.fire(Listen())
		elif code == int(S_CHALNGACCEPT):
			challenged = decrypt_AES(self.symkey, message)
			print("{} has accepted your challenge.".format(challenged))
			# fire gamesession
		elif code == int(S_CHALNGDENY):
			challenged = decrypt_AES(self.symkey, message)
			print("{} has denied your challenge.".format(challenged))
			self.fire(Listen())
		elif code == int(S_CHALNGFAIL):
			toChallenge = decrypt_AES(self.symkey, message)
			print("{} is not currently connected.".format(toChallenge))
			self.waiting = False
			self.fire(Listen())
		elif code == int(S_USERLIST):
			message = decrypt_AES(self.symkey, message)
			self.users = message.split(',')
			print("Users:")
			for user in self.users:
				if user != self.username:
					print("   {}".format(user))
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
			self.fire(sockets.write(B_SYMKEY+ciphertext))
		else:
			print("Unrecognized byte code", file=sys.stderr)

	def Listen(self):
		# If prompt not yet printed, print prompt; user_buffer is implicitly empty since this is the first command.
		if self.first_cmd:
			self.first_cmd = False
			user_input, user_finished = read_input('>>> ', '')
		# If prompt already printed and there is partial input in user_buffer, print nothing and add to partial input.
		elif self.user_buffer:
			temp = self.user_buffer
			self.user_buffer = ''
			user_input, user_finished = read_input('', '', partial_input=temp)
		# If prompt already printed and no partial input, print nothing.
		else:
			user_input, user_finished = read_input('', '')	
		# If user has finished entering a command, print prompt on next Listen and evaluate command.	
		if user_finished:
			self.first_cmd = True			
			user_input = user_input.lower().strip()
			if user_input in self.commands.keys():
				self.commands[user_input]()
			else: 
				print("Invalid command. Type 'help' for a list of commands.")
		# If user has not finished entering a command, print nothing and append partial input to user_buffer
		else:
			self.user_buffer += user_input
		if (self.waiting == False):
			self.fire(Listen())

	def _doHelp(self):
		print(M_CMDLIST)

	def _doQuit(self):
		print("Exiting...")
		self.waiting = True
		self.fire(sockets.close())

	def _doList(self):
		self.fire(sockets.write(B_USERLIST))
		self.waiting = True	

	def _doChallenge(self):
		print("Enter name of user to challenge.")
		toChallenge = input("> ")
		if toChallenge == self.username:
			print("You cannot challenge yourself. Try a different command since you're obviously not ready for this.")
		elif toChallenge == 'exit' or toChallenge == 'quit':
			pass
		else:
			print("Challenging {}...".format(toChallenge))
			self.waiting = True
			self.fire(Challenge(toChallenge))

	def close(self):
		self.stop()

	def ready(self, *args):
		self.fire(sockets.connect(self.host, self.port))

	def Challenge(self, toChallenge):
		ciphertext = encrypt_AES(self.symkey, toChallenge.encode())
		self.fire(sockets.write(B_CHALNG+ciphertext))

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
			self.fire(sockets.write(B_NEWUSER+ciphertext))

	
Client().run()

