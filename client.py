# Outside dependencies 
import sys, re, time
from queue import Queue
from circuits import Component, Event
from circuits.net import sockets

# Local dependencies  
from crypto import *
from user_input import read_input, read_game_input

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

RANDBYTELEN		=	16
MAXNAMELEN 		= 	12

class NewUser(Event):
	''' Fired when a message with code 00 is received from the server. Asks user for username and responds to the server with code 00 and the username. '''

class Listen(Event):
	''' Listen for user input '''

class Userlist(Event):
	''' Receive user list '''

class Challenge(Event):
	''' Challenge another user '''

class GameSessionInit(Event):
	''' GameSessionInit event '''

class GameSessionEnd(Event):
	''' GameSessionEnd event '''

class GameSession(Event):
	''' GameSession event '''

class Client(Component):

	def __init__(self, host='localhost', port=8000):
		super(Client, self).__init__()

		self.host = host
		self.port = port
		self.username = ''
		self.gameid = None
		self.challenged = None
		self.challenger = None
		self.reserved = ['quit', 'exit', 'list']
		self.command_list = "help 	  -- shows this list\nchallenge -- allows you to challenge another user\nusers 	  -- displays a list of users currently connected\nlist 	  -- same as users\nexit 	  -- exits Secure Slap\n"
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
			I_CHALNGFAIL	:	self._do_code_chalngfail,
			I_GAMEID		:	self._do_code_gameid,
		}
		self.chalng_replies = {
			'accept'	:	['accept', 'a', 'yes', 'y'],
			'deny'		: 	['deny', 'd', 'no', 'n']
		}
		
		# waiting should be set to True just before the user should not enter input and to False just before Listen event is fired.
		self.waiting 				= False
		self.first_listen_input		= True
		self.is_challenger 			= False
		self.my_turn 				= False
		self.in_game				= False
		self.first_game_input		= True
		self.user_buffer			= ''

		sockets.TCPClient().register(self)
		if len(sys.argv) > 1:
			if sys.argv[1] == '-d':
				from circuits import Debugger
				self += Debugger()		

	def close(self):
		self.stop()

	def read(self, data):
		code = data[0]
		message = data[1:]
		if code in self.codes.keys():
			self.codes[code](message)
		else:
			print("Unrecognized byte code", file=sys.stderr)

	def ready(self, *args):
		self.fire(sockets.connect(self.host, self.port))

	def Listen(self):
		if self.waiting:
			return
		# If prompt not yet printed, print prompt; user_buffer is implicitly empty since this is the first command.
		if self.first_listen_input:
			self.first_listen_input = False
			user_input, user_finished = read_input('>>> ')
		# If prompt already printed and there is partial input in user_buffer, print nothing and add to partial input.
		elif self.user_buffer:
			temp = self.user_buffer
			self.user_buffer = ''
			user_input, user_finished = read_input('', partial_input=temp)
		# If prompt already printed and no partial input, print nothing.
		else:
			user_input, user_finished = read_input('')	
		# If user has finished entering a command, print prompt on next Listen and evaluate command.	
		if user_finished:
			self.first_listen_input = True			
			user_input = user_input.lower().strip()
			if user_input in self.commands.keys():
				self.commands[user_input]()
			else: 
				print("Invalid command. Type 'help' for a list of commands.")
		# If user has not finished entering a command, print nothing and append partial input to user_buffer
		else:
			self.user_buffer += user_input
		if not self.waiting:
			self.fire(Listen())

	def Challenge(self, to_challenge):
		self.challenged = to_challenge
		print("Challenging {}...".format(to_challenge))
		ciphertext = encrypt_AES(self.symkey, to_challenge.encode())
		self.fire(sockets.write(B_CHALNG+ciphertext))

	def GameSessionInit(self, opponent, gameid):
		self.in_game = True
		print("Now in game with {}. Press 'q' to quit.".format(opponent))
		print("idk whose turn it is.")
		self.fire(GameSession(opponent))

	def GameSession(self, opponent):
		user_input = None
		while not user_input:
			if self.first_game_input:
				self.first_game_input = False
				user_input = read_game_input('['+self.username+']: ', self.my_turn)
			else:
				user_input = read_game_input('', self.my_turn)
		if self.my_turn:
			self.my_turn = False
		time_input_received = str(round(time.time(), 3)).encode()
		time_len = str(len(time_input_received)).encode()
		if user_input == ' ':
			message = B_GAMESLAP+encrypt_AES(self.symkey, time_input_received)
		elif user_input == 'n':
			message = B_GAMENEXT+encrypt_AES(self.symkey, time_input_received)
		elif user_input == 'q':
			message = B_GAMEQUIT+encrypt_AES(self.symkey, str(self.gameid).encode())
			self.fire(GameSessionEnd())
		else:
			print("Invalid user input for game session: '{}'".format(user_input), file=sys.stderr)
		self.fire(sockets.write(message))

	def GameSessionEnd(self):
		self.challenged = None
		self.gameid = None
		self.in_game = False
		self.is_challenger = False
		self.waiting = False
		print('')
		self.fire(Listen())

	def NewUser(self):
		while True:
			username = input("> ")
			if username in self.reserved:
				print("Username contains a reserved word. Try again.")
			elif not re.match('^[\w-]+$', username):
				print("Username may only contain alphanumeric characters. Try again.")
			elif len(username) > MAXNAMELEN:
				print("Name too long. Try again.")
			else:
				self.username = username
				ciphertext = encrypt_AES(self.symkey, self.username.encode())
				self.fire(sockets.write(B_NEWUSER+ciphertext))
				break

	# NOTE: Doesn't actually use passed message.
	def _do_code_newuser(self, message):
		print("Welcome to the Secure Slap server!\nEnter your desired username:")
		self.fire(NewUser())

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
		self.fire(NewUser())

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
		self.waiting = True
		self.challenger = decrypt_AES(self.symkey, message)
		print("{} is challenging you!\nAccept or deny?".format(self.challenger))
		response = None
		while not response:
			r = input("> ").lower()
			if r in self.chalng_replies['accept']:
				response = 'accept' 
			elif r in self.chalng_replies['deny']:
				response = 'deny'
			else:
				print("Invalid input. Accept or deny?")
		ciphertext = encrypt_AES(self.symkey, (self.username+','+self.challenger).encode())
		self.first_listen_input = True
		if response == 'accept':
			self.fire(sockets.write(B_CHALNGACCEPT+ciphertext))
			#self.fire(GameSessionInit(challenger))
		elif response == 'deny':
			self.fire(sockets.write(B_CHALNGDENY+ciphertext))
			self.challenger = None
			self.waiting = False
			self.fire(Listen())

	def _do_code_chalngaccept(self, message):
		print("{} has accepted your challenge.".format(self.challenged))
		self.gameid = decrypt_AES(self.symkey, message)
		#self.is_challenger = True
		self.waiting = False
		self.fire(GameSessionInit(self.challenger, self.gameid))		

	# NOTE: Doesn't actually use passed message. 
	def _do_code_chalngdeny(self, message):
		print("{} has denied your challenge.".format(self.challenged))
		self.challenged = None
		self.waiting = False
		self.fire(Listen())

	def _do_code_chalngfail(self, message):
		print("{} is not currently connected. Try another user or type 'exit' to return to the main menu.".format(self.challenged))
		self.challenged = None
		self.waiting = False
		self._do_cmd_challenge(False)

	def _do_code_gameid(self, message):
		self.gameid = decrypt_AES(self.symkey, message)
		#self.is_challenger = True
		self.waiting = False
		self.fire(GameSessionInit(self.challenger, self.gameid))

	def _do_cmd_help(self):
		print(self.command_list)

	def _do_cmd_quit(self):
		print("Exiting...")
		self.waiting = True
		self.fire(sockets.close())

	def _do_cmd_list(self):
		self.fire(sockets.write(B_USERLIST))
		self.waiting = True	

	def _do_cmd_challenge(self, first_call=True):
		if first_call:
			print("Enter name of user to challenge.")
		while True:
			to_challenge = input("> ")
			if to_challenge == self.username:
				print("You cannot challenge yourself.")
			elif to_challenge == 'exit' or to_challenge == 'quit':
				print("Returning to main menu.")
				self.fire(Listen())
				break
			elif to_challenge == '':
				pass
			else:
				self.waiting = True
				self.fire(Challenge(to_challenge))
				break
	
Client().run()