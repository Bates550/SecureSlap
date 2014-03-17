from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Random import random
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Cipher import PKCS1_OAEP

# NOT TESTED; NOT USED
def encrypt_RSA(key, message):
	rsakey = PKCS1_OAEP.new(key)
	encrypted = rsakey.encrypt(message)
	return encrypted.encode()

# NOT TESTED; NOT USED
def sign_data(privkey, data):
	privkey = RSA.importKey(privkey)
	signer = PKCS1_v1_5.new(privkey)
	if type(data) is str:
		data = data.encode()
	digest = SHA256.new(data)
	sign = signer.sign(digest)


''' Adds null bytes to end of msg (str or bytes) until its length is divisible by blocksize and returns a bytes result. '''
def pad(msg, blocksize=16):
	if type(msg) is str:
		msg = msg.encode()
	toAdd = 0 				
	msglen = len(msg) 		
	rem = msglen%blocksize	
	if rem != 0:
		toAdd = blocksize - rem
	while toAdd != 0:
		msg += b'\x00'
		toAdd -= 1
	return msg

''' Removes null bytes from end of msg (str or bytes) and returns the result as a str. '''
def unpad(msg):
	if type(msg) is bytes:
		msg = msg.decode()
	result = ''
	i = 0
	while msg[i] != '\x00':
		result += msg[i]
		i += 1
	return result

''' Pads then encrypts plaintext with AES (CBC mode) and returns the ciphertext prepended by the initialization vector. '''
def encrypt_AES(key, plaintext, blocksize=16):
	plaintext = pad(plaintext)
	iv = Random.new().read(blocksize)
	encryptor = AES.new(key, AES.MODE_CBC, iv)
	ciphertext = encryptor.encrypt(plaintext)
	return iv+ciphertext

''' Parses the initialization vector from beginning of ciphertext and then decrypts remaining ciphertext with AES (CBC mode) and the parsed IV. Then unpads the resulting plaintext and returns the result. '''
def decrypt_AES(key, ciphertext, blocksize=16):
	iv = ciphertext[:blocksize]
	ciphertext = ciphertext[blocksize:]
	decryptor = AES.new(key, AES.MODE_CBC, iv)
	plaintext = decryptor.decrypt(ciphertext)
	return unpad(plaintext)
