#import sys
#import threading
import time
#import queue
from msvcrt import getche, kbhit

'''
class StoppableThread(threading.Thread):

	def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
		super(StoppableThread, self).__init__(group, target, name, args, kwargs)
		self._stop = threading.Event()

	def stop(self):
		self._stop.set()

	def stopped(self):
		return self._stop.isSet()

def foobar():
	# Function to be run in separate thread
	def add_input(input_queue):
		while True:
			read = sys.stdin.readline().strip()
			if read == 'exit':
				return	
			input_queue.put(read)

	input_queue = queue.Queue()
	input_thread = threading.Thread(target=add_input, args=(input_queue,))
	input_thread.start()
	while True:
		if not input_queue.empty():
			print(input_queue.get())
		if not input_thread.is_alive():
			return

def input_loop():
	# Function to be run in separate thread
	def add_input(input_queue, stop_queue):
		while True:
			if not stop_queue.empty():
				return	
			read = sys.stdin.readline().strip()
			input_queue.put(read)

	stop_queue = queue.Queue()
	input_queue = queue.Queue()
	input_thread = threading.Thread(target=add_input, args=(input_queue, stop_queue))
	input_thread.start()
	acc = 0
	while True:
		acc += 0.00001
		#print(acc)
		if not input_queue.empty():
			print(input_queue.get())
		if not input_thread.is_alive():
			return
		if acc > 10.0:
			print(input_thread.is_alive())
			stop_queue.put(True)
			return
'''

# Adapted from Paul at http://stackoverflow.com/questions/3471461/raw-input-and-timeout
# NOTE: This is a Windows only solution. 
# TODO: Implement support for backspace (8 == backspace)
def read_input(caption, default, timeout=0.2, partial_input=''):
	last_key_pressed_time = time.time()
	if not partial_input:
		print(caption, end='', flush=True)
		user_input = ''
	else:
		user_input = partial_input
	return_val = user_input
	user_finished = False

	while True:
		if kbhit():
			char = getche()
			last_key_pressed_time = time.time()
			if ord(char) == 13: # enter key
				user_input += char.decode()
				break
			elif ord(char) >= 32: # non system or space character
				user_input += char.decode()
			elif ord(char) == 8: # backspace key
				if user_input:
					user_input = user_input[:-1]
					print(' \b', end='', flush=True)
			else:
				break
		if (time.time() - last_key_pressed_time) > timeout:
			break	

	input_len = len(user_input)
	if input_len > 0 and '\r' in user_input:
		return_val = user_input
		user_finished = True
		print('')
	elif input_len > 0:
		return_val = user_input
	else:
		return_val = default

	return (return_val, user_finished)



# and some examples of usage
'''
(ans, finished) = read_input('>>> ', '') 
print('Command entered: %s' % ans)
print('User finished: %s' % finished)

(ans, finished) = read_input('>>> ', '', partial_input='hello ') 
print('Command entered: %s' % ans)
print('User finished: %s' % finished)
'''
#print('hi', end='')
#print('\b ')