import json
from datetime import datetime
from random import shuffle, randint

from Boardgamebox.Game import Game as BaseGame
from BloodClocktower.Boardgamebox.Player import Player
from BloodClocktower.Boardgamebox.Board import Board
from BloodClocktower.Boardgamebox.State import State
from BloodClocktower.Boardgamebox.Reminder import Reminder
#from Boardgamebox.Board import Board
#from Boardgamebox.State import State

from BloodClocktower.Constants import roles

from typing import Tuple, AnyStr
class Game(BaseGame):
	def __init__(self, cid, initiator, groupName):
		BaseGame.__init__(self, cid, initiator, groupName, None, None)		
		self.using_timer = False
		self.storyteller = None
		self.board_message_id = None
		self.tipo = "blood"
		self.whisper_max = 3
	
	def load_json_data(self, game_data):
		response_msg = ""
		# Agrego roles del ST
		for player in game_data["players"]:
			nombre = player['name']
			rol = player['role']
			if rol == 'drunk':
				rol == ""
			response_msg += self.set_role(nombre, rol)
		# Agrego reminders del ST
		for player in game_data["players"]:
			reminders = player["reminders"]
			nombre = player['name']
			response_msg += self.add_reminders(nombre, reminders)
		return response_msg

	def get_player_reminders(self, name):
		player = self.find_player(name)
		if player != None:
			reminder_text = ""
			if len(player.reminders) > 0:
				reminder_text += f"Notas del jugador {player.name}:\n"
				for reminder in player.reminders:
					reminder_text += f"{reminder.print()}\n"
			else:
				reminder_text = f"El jugador {player.name} no tiene notas."
			return reminder_text
		else:
			return f"No existe ese jugador"

	def add_reminders(self, name, reminders):
		player = self.find_player(name)
		if player != None:
			player.reminders = []
			text_add_reminder = ""
			for reminder in reminders:
				reminder = Reminder(reminder['role'], reminder['name'])
				player.reminders.append(reminder)
				text_add_reminder += f"Se agrego a {player.name} -> {reminder.print()}\n"
			return text_add_reminder
		else:
			return f"No existe ese jugador"

	def start_whisper(self, uid, members_text):		
		members_text_list = members_text.split(",")
		members = []
		requester = self.find_player_by_id(uid)
		members.append(requester)
		not_found = []
		for member in members_text_list:
			player = self.find_player(member.strip())
			if player is None:
				not_found.append(member)
			else:
				members.append(player)

		# Si no encuentro a alguno de los integrantes no hago nada
		if len(not_found) > 0:
			return (False, f"No se encontró: {self.dictate_members_string(not_found)}")
		elif [member for member in members if len(member.whispering) > 0]:
			# Si algun miembro ya esta en whispering...
			members_whispering = [member for member in members if len(member.whispering) > 0]
			txt_members_whispering = ""
			for	member_w in members_whispering:
				txt_members_whispering += f'Jugador {member_w.name} ya esta hablando con {self.dictate_members(member_w.whispering)} que lo finalice con /endwhisper\n'
			return (False, txt_members_whispering)
		else:
			# Creo el whispering
			for member in members:
				member.whispering = members
				member.whispering_count += len(members) -1 #Aumento el count de whispers menos el propio creador que no se tiene que contar
			whisper_message = f"Se ha creado el whisper entre {self.dictate_members(members, True)}"
			self.history.append(whisper_message)			
			return (True, f"{whisper_message}\nPara terminarlo hacer /endwhisper")

	def dictate_members(self, whisper_members, add_whisper_count = False):
		dictado = ""
		for i in range(len(whisper_members)):
			name = f"{whisper_members[i].name} {whisper_members[i].whispering_count}/{self.whisper_max}" if add_whisper_count else whisper_members[i].name 
			if i == len(whisper_members) - 2:
				name_last = f"{whisper_members[i+1].name} {whisper_members[i+1].whispering_count}/{self.whisper_max}" if add_whisper_count else whisper_members[i+1].name 
				dictado += name + " y " + name_last
				break
			else:
				dictado += name + ", "
		return dictado

	def dictate_members_string(self, whisper_members):
		dictado = ""
		for i in range(len(whisper_members)):
			if i == len(whisper_members) - 2:
				dictado += whisper_members[i] + " y " + whisper_members[i+1]
				break
			else:
				dictado += whisper_members[i] + ", "
		if len(whisper_members) == 1:
			dictado = dictado[:-2]

		return dictado

	def end_whisper(self, uid):
		requester = self.find_player_by_id(uid)
		# Si estaba hablando con alguien...
		if requester is not None and len(requester.whispering) > 0:
			whisper_members = requester.whispering.copy()
			# Saco la charla a todos los involucrados
			for member in whisper_members:
				member.whispering = []
			dictado = self.dictate_members(whisper_members, True)
			return f"Se ha terminado el whisper entre {dictado}"
		else:
			return "No estas haciendo actualmente whispering"

	def execute_player(self):
		if self.board.state.chopping_block != None:
			return self.kill_player(self.board.state.chopping_block.name, "ejecutado")
		else:
			return (False, "No hay jugador en el chopping block")
			
	def kill_player(self, player_name, verbo = "matado"):
		player = self.find_player(player_name)
		if player is None:
			return (False, "El jugador no esta en el partido, recuerda poner el nombre que aparece en el board")
		else:
			kill_message = f"Jugador {self.player_call(player)} te han {verbo}, no posees más tu habilidad, pero puedes hablar y votar una última vez"
			player.dead = True
			player.nominated_someone = True # Muertos no pueden nominar
			self.history.append(kill_message)
			return (True, kill_message)

	def tick(self, uid):
		if uid == self.storyteller or (self.get_current_voter() is not None and self.get_current_voter().uid == uid):
			return (True, self.advance_clock(""))
		else:
			return (False, "No puedes hacer /tick porque no eres el storyteller ni el jugador que tiene que votar")

	def get_role_info(self, name):
		return next((x for x in roles if x['id'] == name), None)

	def set_role(self, nombre, rol):
		player = self.find_player(nombre)
		if player != None:
			player.role = rol
			return f"Se ha asignado {rol} a {player.name}"
		else:
			return f"No existe ese jugador"

	def add_traveller(self, uid):
		player = self.find_player_by_id(uid)
		self.player_sequence.insert(randint(0, len(self.player_sequence)), player)

	def get_call_message(self):
		state = self.board.state
		message = "Sin call actual"
		if state.can_nominate and state.accuser is None:
			message = self.get_possible_nominators_message()
		elif state.accuser is not None and state.defense is not None:
			current_voter = self.get_current_voter()
			message = f"{self.player_call(current_voter)} te toca votar"
		return message

	def get_possible_nominators_message(self):
		jugadores_nominadores = "Jugadores que pueden nominar todavia:\n"
	
		for player in self.playerlist.values():
			if not player.nominated_someone:
				jugadores_nominadores += f"{self.player_call(player)}\n"
		return jugadores_nominadores

	def add_note(self, uid, notas):
		player = self.find_player_by_id(uid)
		player.notes.append(notas)

	def find_player(self, name) -> Player:
		for player in self.playerlist.values():
			if player is not None and player.name == name or player.nick == name.replace("@",""):
				return player
		for player in self.player_sequence:
			if player is not None and player.name == name or player.nick == name.replace("@",""):
				return player
		return None

	def find_player_by_id(self, uid) -> Player:
		return self.playerlist[uid]

	def clear_nomination(self):
		state = self.board.state
		state.accuser = None # Jugador que acuso
		state.defender = None # Jugador que fue acusado
		state.accusation = None # Acusacion del acusador
		state.defense = None # Defenss del acusado
		state.votes = {}
		state.clock = -1
	
	def set_night(self):
		state = self.board.state
		state.phase = "Noche"
		state.day += 1
		self.history.append(f"*Noche {state.day}*")
		# Limpio el chopping block
		state.chopping_block_votes = 0
		state.chopping_block = None
		# No se puede nominar a la noche
		state.can_nominate = False
		# refresco el nominar y ser nominado de todos los jugadores, excepto los muertos
		for player in self.player_sequence:
			if not player.dead:
				player.nominated_someone = False # Los muertos no pueden nominar
			player.was_nominated = False # ITodos pueden ser nominados
			player.whispering_count = 0 # reseteo los whispers

	def set_day(self):
		state = self.board.state
		state.phase = "Día"
		self.history.append(f"*Día {state.day}*")

	def get_current_voter(self) -> Player:
		state = self.board.state
		# Si no se esta votando devolver vacio
		# Si el clock no comenzo tampoco hay current voter
		if state.accuser is None or state.clock == -1 or state.clock == len(self.player_sequence):
			return None
		# Obtengo la lista con el defensor al final
		lista = self.board.starting_with(self.player_sequence, state.defender)
		# Valido
		return list(lista)[state.clock]

	def can_modify_vote(self, uid):
		state = self.board.state
		# Si no se esta votando devolver vacio
		# Si el clock no comenzo tampoco hay current voter
		if state.accuser is None or state.clock == -1:
			return False
		# Obtengo la lista con el defensor al final
		lista = self.board.starting_with(self.player_sequence, state.defender)
		
		uid_player_index = next((i for i, item in enumerate(lista) if item.uid == uid), -1)
		# Valido
		return uid_player_index >= state.clock

	def toggle_nominations(self):
		state = self.board.state
		state.can_nominate = not state.can_nominate
	
	def player_call(self, player):
		return "[{0}](tg://user?id={1})".format(player.name, player.uid)

	def advance_clock(self, message) -> str:
		state = self.board.state
		state.clock += 1
		# Si estoy haciendo tick desde el ultimo jugador (que es normalmente el defensor)
		# Aviso al ST que debe decidir que pasa
		if state.clock == len(self.player_sequence):
			storyteller = Player("Storyteller", self.storyteller, "StoryTeller")
			return f"The clock rings the time has ended!\n{self.player_call(storyteller)}: Usa /chopping para mandarlo al chopping block si lo merece, luego Usa /clear para limpiar la nominación"
		else:
			current_voter = self.get_current_voter()
			# Si el jugador actual esta muerto paso al siguiente
			if current_voter.dead and not current_voter.has_last_vote:
				message_voter_without_votes = f"The clock goes forward, skipping {current_voter.name} because is dead and used his last vote!\n"
				message += f"{message_voter_without_votes}"
				return self.advance_clock(message)
			else:
				return f"The clock goes forward {self.player_call(current_voter)} te toca!"
									
	def count_alive(self):
		return sum(not p.dead for p in self.player_sequence)
	
	def count_votes(self):
		return sum(not p.dead or p.has_last_vote for p in self.player_sequence)
	
	def set_playerorder(self, playerorder):
		new_list = []
		for name in playerorder:
			player = self.find_player(name)
			new_list.append(player)
		self.player_sequence = new_list
        
	def startgame(self):
		self.board = Board(len(self.playerlist))

	def get_rules(self):
		return ["""El juego es Blood on the clocktower"""]		
		
	# Creacion de player de juego.	
	def add_player(self, uid, name, nick):
		self.playerlist[uid] = Player(name, uid, nick)

	def create_board(self):
		player_number = len(self.playerlist)
		self.board = Board(player_number, self)
	
	def verify_turn(self, uid):
		if self.board.state.fase_actual == "Proponiendo Pistas":
			return uid not in self.board.state.last_votes
		else:
			return False

	def myturn_message(self, uid):
		try:
			group_link_name = self.groupName
			if self.board.state.fase_actual == "Proponiendo Pistas":
				mensaje_clue_ejemplo = "Ejemplo: Si la palabra fuese (Fiesta)\n/words Cumpleaños, Torta, Decoracion, Musica, Rock, Infantil, Luces, Velas"
				return f"Partida: {group_link_name} debes dar {mensaje_clue_ejemplo}. \nLa palabra es : *{self.board.state.acciones_carta_actual}* propone tus palabras!."
		except Exception as e:
			return str(e)

	def resetPlayerPoints(self):
		for player in self.playerlist.values():
			player.points = 0

	def call(self, context):
		import BloodClocktower.Commands as BloodClocktowerCommands
		if self.board is not None:
				BloodClocktowerCommands.command_call(context.bot, self)
				
	def timer(self, update, context):
		import BloodClocktower.Commands as BloodClocktowerCommands
		if self.board is not None:
			BloodClocktowerCommands.callback_timer(update, context)
