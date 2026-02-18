import random
import string
import tempfile
import os
import time

try:
	import sounddevice as sd
	from scipy.io.wavfile import write as wav_write
except Exception:
	sd = None

try:
	import speech_recognition as sr
except Exception:
	sr = None

try:
	from googletrans import Translator
except Exception:
	Translator = None


LEVELS = {
	'easy': [
		('gato', 'cat'),
		('perro', 'dog'),
		('casa', 'house'),
		('manzana', 'apple'),
		('libro', 'book'),
	],
	'medium': [
		('cielo', 'sky'),
		('fuego', 'fire'),
		('agua', 'water'),
		('puerta', 'door'),
		('ventana', 'window'),
		('mesa', 'table'),
		('silla', 'chair'),
	],
	'hard': [
		('comida', 'food'),
		('amistad', 'friendship'),
		('conocimiento', 'knowledge'),
		('desarrollo', 'development'),
		('pensamiento', 'thinking'),
	],
}

SENTENCES = {
	'easy': [
		('¿Dónde está el gato?', 'Where is the cat?'),
		('Tengo un libro.', 'I have a book.'),
		('La casa es grande.', 'The house is big.'),
	],
	'medium': [
		('El cielo está muy azul hoy.', 'The sky is very blue today.'),
		('Ella abrió la puerta lentamente.', 'She opened the door slowly.'),
		('Nos gusta leer en la biblioteca.', 'We like to read in the library.'),
	],
	'hard': [
		('El conocimiento se obtiene con el tiempo y la práctica.', 'Knowledge is gained with time and practice.'),
		('El desarrollo sostenible requiere colaboración internacional.', 'Sustainable development requires international collaboration.'),
		('El pensamiento crítico mejora la toma de decisiones.', 'Critical thinking improves decision making.'),
	],
}


def normalize(text: str) -> str:
	if not text:
		return ''
	text = text.lower()
	text = text.strip()
	text = ''.join(ch for ch in text if ch not in string.punctuation)
	return text


def record_temp_wav(duration=3, fs=16000) -> str:
	if sd is None:
		raise RuntimeError('sounddevice not available; install sounddevice and scipy')
	print(f'Recording for {duration} seconds... Speak now.')
	sd.default.samplerate = fs
	sd.default.channels = 1
	recording = sd.rec(int(duration * fs))
	sd.wait()
	# convert float32 to int16
	import numpy as np
	audio_int16 = (recording[:, 0] * 32767).astype(np.int16)
	tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
	wav_write(tmp.name, fs, audio_int16)
	tmp.close()
	return tmp.name


def recognize_wav_file(path: str, language='en-US') -> str:
	if sr is None:
		raise RuntimeError('speech_recognition not available; install SpeechRecognition')
	r = sr.Recognizer()
	with sr.AudioFile(path) as source:
		audio = r.record(source)
	try:
		text = r.recognize_google(audio, language=language)
		return text
	except sr.UnknownValueError:
		return ''
	except sr.RequestError as e:
		raise RuntimeError(f'Could not request results from Google Speech Recognition service; {e}')


def translate_text(text: str, dest='es') -> str:
	if Translator is None:
		return ''
	try:
		translator = Translator()
		res = translator.translate(text, dest=dest)
		return res.text
	except Exception:
		return ''


def is_correct(recognized: str, expected: str) -> bool:
	r = normalize(recognized)
	e = normalize(expected)
	if not r:
		return False
	if r == e:
		return True
	# allow cases where recognized contains expected word(s)
	r_words = set(r.split())
	e_words = set(e.split())
	return e_words.issubset(r_words)


def play_written_round(spanish_sentence: str, expected_en: str):
	print('\nTranslate to English (write your translation):')
	print(f'  >>> {spanish_sentence}')
	answer = input('Your translation: ').strip()
	print('You wrote:', answer or '(nothing)')
	# Compare typed answer with expected
	correct = is_correct(answer, expected_en)
	if correct:
		print('Correct!')
	else:
		print(f'Incorrect. Expected (one possible): "{expected_en}"')
	return correct, answer


def play_round(spanish_word: str, expected_en: str, duration=3):
	print('\nTranslate to English and pronounce:')
	print(f'  >>> {spanish_word}')
	input(f'Press Enter to start recording (will record {duration} seconds)...')
	wav_path = None
	try:
		wav_path = record_temp_wav(duration=duration)
	except Exception as ex:
		print('Recording failed:', ex)
		return False, ''

	try:
		recognized = recognize_wav_file(wav_path)
	except Exception as ex:
		print('Recognition error:', ex)
		recognized = ''
	finally:
		try:
			os.remove(wav_path)
		except Exception:
			pass

	print('Recognized (raw):', recognized or '(nothing)')
	translated_back = translate_text(recognized, dest='es') if recognized else ''
	if translated_back:
		print('Interpreted meaning (translated to Spanish):', translated_back)

	correct = is_correct(recognized, expected_en)
	if correct:
		print('Correct!')
	else:
		print(f'Incorrect. Expected: "{expected_en}"')
	return correct, recognized


def main():
	print('Voice translation game — Spanish -> English')
	if sd is None or sr is None:
		print('\nMissing dependencies detected. Make sure you installed:')
		print('  pip install sounddevice scipy SpeechRecognition googletrans==4.0.0-rc1 numpy')
		print('Then re-run this script.')
		return

	# Selección de nivel
	level_keys = list(LEVELS.keys())
	print('\nSelect difficulty level:')
	for i, k in enumerate(level_keys, 1):
		print(f'  {i}. {k}')
	choice = ''
	while True:
		choice = input('Enter 1/2/3 or easy/medium/hard: ').strip().lower()
		if choice in ('1', '2', '3'):
			choice = level_keys[int(choice) - 1]
		if choice in LEVELS:
			level = choice
			break
		print('Invalid choice, try again.')

	score = 0
	errors = 0
	max_errors = 3
	round_num = 0
	print(f"\nStarting game on '{level}' — you can make {max_errors} errors before the game ends.")
	# Seleccionar modo de ejercicio
	print('\nChoose exercise mode:')
	print('  1. Voice (pronounce single words)')
	print('  2. Written sentences (type translations)')
	mode = ''
	while True:
		mode = input('Enter 1 or 2: ').strip()
		if mode in ('1', '2'):
			break
		print('Invalid choice, try again.')

	try:
		while errors < max_errors:
			round_num += 1
			if mode == '1':
				spanish, english = random.choice(LEVELS[level])
				correct, recognized = play_round(spanish, english, duration=3)
			else:
				spanish, english = random.choice(SENTENCES[level])
				correct, recognized = play_written_round(spanish, english)

			if correct:
				score += 1
			else:
				errors += 1
			print(f'Score: {score} | Errors: {errors}/{max_errors} | Rounds played: {round_num}')
	except KeyboardInterrupt:
		print('\nGame interrupted by user.')

	print('\nGame over.')
	print(f'Final score: {score} | Total rounds: {round_num} | Errors: {errors}')


if __name__ == '__main__':
	main()

