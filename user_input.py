import time
from msvcrt import getch, getche, kbhit

# Adapted from Paul at http://stackoverflow.com/questions/3471461/raw-input-and-timeout
# NOTE: This is a Windows only solution. 
def read_input(caption, default='', timeout=0.2, partial_input=''):
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

def read_game_input(caption, my_turn=False, default='', timeout=0.2):
	last_key_pressed_time = time.time()
	user_input = None
	print(caption, end='', flush=True)
	while True:
		if kbhit():
			char = getch()
			last_key_pressed_time = time.time()
			o = ord(char)
			if o == 32:			# ' '
				print("~*SLAP*~", end='')
				user_input = char.decode()
			elif o == 110 and my_turn:		# 'n'
				print("~*NEXT*~", end='')
				user_input = char.decode() 
			elif o == 113:		# 'q'
				print("Exiting game session...", end='')
				user_input = char.decode()

		if (time.time() - last_key_pressed_time) > timeout:
			break	

	if user_input:
		return user_input
	else:
		return default


if __name__ == "__main__":
	first = True
	char = None
	while not char:
		if first:
			first = False
			char = read_game_input('> ')
		else:
			char = read_game_input('')

	'''(ans, finished) = read_input('>>> ', '') 
	print('Command entered: %s' % ans)
	print('User finished: %s' % finished)

	(ans, finished) = read_input('>>> ', '', partial_input='hello ') 
	print('Command entered: %s' % ans)
	print('User finished: %s' % finished)
	'''