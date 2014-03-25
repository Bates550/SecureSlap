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
			'help'		: 	self._do_cmd_help, 
			'quit'		:	self._do_cmd_quit, 
			'exit'		:	self._do_cmd_quit, 
			'challenge'	:	self._do_cmd_challenge,
			'users'		:	self._do_cmd_list,
			'list'		:	self._do_cmd_list,
			''			:	self.Listen
		}
		self.codes = {
			I_NEWUSER 		:	self._do_code_newuser,
			I_USERLIST		:	self._do_code_userlist,
			I_NAMETAKEN		:	self._do_code_nametaken,
			I_NAMEACCEPT	:	self._do_code_nameaccept,
			I_SERVKEY 		:	self._do_code_servkey,
			I_CHALNG		:	self._do_code_chalng,
			I_CHALNGACCEPT	:	self._do_code_chalngaccept,
			I_CHALNGDENY	:	self._do_code_chalngdeny,
			I_CHALNGFAIL	:	self._do_code_chalngfail
		}
		
		self.waiting = False
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
		if code in self.codes.keys():
			self.codes[code](message)
		else:
			print("Unrecognized byte code", file=sys.stderr)

	# NOTE: Doesn't actually use passed message.
	def _do_code_newuser(self, message):
		print("Welcome to the Secure Slap server!\nEntire your desired username:")
		self.fire(Newuser())

	def _do_code_userlist(self, message):
		message = decrypt_AES(self.symkey, message)
		self.users = message.split(',')
		print("Users:")
		for user in self.users:
			if user != self.username:
				print("   {}".format(user))
		self.waiting = False	
		self.fire(Listen())

	# NOTE: Doesn't actually use passed message.
	def _do_code_nametaken(self, message):
		print("Username already taken. Please enter another:")
		self.fire(Newuser())

	# NOTE: Doesn't actually use passed message.
	def _do_code_nameaccept(self, message):
		print("Username accepted! Enjoy your stay.")
		self.fire(Listen())

	def _do_code_servkey(self, message):
		plainsymkey = Random.get_random_bytes(RANDBYTELEN)
		self.symkey = SHA256.new(str(plainsymkey).encode()).digest()
		pubkey = RSA.importKey(message)
		self.pubkey = PKCS1_OAEP.new(pubkey)
		ciphertext = self.pubkey.encrypt(self.symkey)
		self.fire(sockets.write(B_SYMKEY+ciphertext))

	def _do_code_chalng(self, message):
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
			self.first_cmd = True
			self.waiting = False
			self.fire(Listen())

	def _do_code_chalngaccept(self, message):
		challenged = decrypt_AES(self.symkey, message)
		print("{} has accepted your challenge.".format(challenged))
		# fire gamesession

	def _do_code_chalngdeny(self, message):
		challenged = decrypt_AES(self.symkey, message)
		print("{} has denied your challenge.".format(challenged))
		self.waiting = False
		self.fire(Listen())

	def _do_code_chalngfail(self, message):
		toChallenge = decrypt_AES(self.symkey, message)
		print("{} is not currently connected.".format(toChallenge))
		self.waiting = False
		self._doChallenge()

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

	def _do_cmd_help(self):
		print(M_CMDLIST)

	def _do_cmd_quit(self):
		print("Exiting...")
		self.waiting = True
		self.fire(sockets.close())

	def _do_cmd_list(self):
		self.fire(sockets.write(B_USERLIST))
		self.waiting = True	

	def _do_cmd_challenge(self):
		print("Enter name of user to challenge.")
		toChallenge = input("> ")
		if toChallenge == self.username:
			print("You cannot challenge yourself. Try a different command since you're obviously not ready for this.")
		elif toChallenge == 'exit' or toChallenge == 'quit':
			self.fire(Listen())
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

