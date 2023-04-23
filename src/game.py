import copy
from enum import Enum
import json

from bar import *
from dice import *
from game_board import *
from game_field import *
from player import *

STONES_INIT = [(0, 2, True), (5, 5, False), (7, 3, False), (11, 5, True), (12, 5, False), (16, 3, True), (18, 5, True),
               (23, 2, False)]


class GameState(Enum):
    ROLL_DICE = 0
    MOVE_STONE = 1
    MOVE_STONE_FROM_BAR = 2


class Game:
    """
    Start game
    """

    def __init__(self, win, multiplayer, p1_name, p2_name):
        self.win = win

        self.bar = Bar()

        self.button_pressed = False
        # number of rolls before dice stop
        self.roll = 0
        # Moves which player can do computed from values on dice
        self.dice_move = []
        self.same_number = False
        self.dice = Dice()

        self.game_board = GameBoard(self.win)
        self.text = ''
        self.no_moves = False

        self.game_fields = []
        self.avail_moves = {}
        self.chosen_field = None

        self.game_state = GameState.ROLL_DICE
        self.multiplayer = multiplayer
        self.player1 = ConsolePlayer(has_black_stones=False, name=f'{p1_name}')
        if self.multiplayer:
            self.player2 = AIPlayer(has_black_stones=True, name='AI')
        else:
            self.player2 = ConsolePlayer(has_black_stones=True, name=f'{p2_name}')
        self.player_turn = self.player1

    def init_game(self):
        # number of fields matches white numbering - 1
        for field in STONES_INIT:
            for i in range(field[1]):
                self.game_fields[field[0]].add_stone(GameStone([field[0]], field[2]))

        self.player1.fields = [self.game_fields[5], self.game_fields[7], self.game_fields[12], self.game_fields[23]]
        self.player2.fields = [self.game_fields[0], self.game_fields[11], self.game_fields[16], self.game_fields[18]]

    def init_fields(self):
        for i in range(6):
            self.game_fields.append(GameField(i, 1243.7 - i * 86.5, 167, True))
        for i in range(6, 12):
            self.game_fields.append(GameField(i, 549.5 - (i - 6) * 86.5, 167, True))
        for i in range(12, 18):
            self.game_fields.append(GameField(i, 113 + (i - 12) * 86.5, 480, False))
        for i in range(18, 24):
            self.game_fields.append(GameField(i, 807.2 + (i - 18) * 86.5, 480, False))

    def turn(self):
        if self.game_state == GameState.ROLL_DICE:
            self.roll_dice_state()

        if self.game_state == GameState.MOVE_STONE:
            self.move_stone_state()

        if self.game_state == GameState.MOVE_STONE_FROM_BAR:
            self.move_stone_state()
            self.move_stone_from_bar_state()

    """
    Roll dice
    """

    def roll_dice_state(self):
        if self.no_moves:
            self.text = f"You had no available moves. It's {self.player_turn.name}'s turn."
        else:
            self.text = f"It's {self.player_turn.name}'s turn."

        if self.button_pressed:
            if self.roll:
                self.dice.std_roll(2)
                self.roll -= 1
            else:
                self.stop_rolling()

    def stop_rolling(self):
        self.button_pressed = False

        if self.dice.throw[0] == self.dice.throw[1]:
            self.same_number = True
            self.dice_move = [self.dice.throw[0], 2 * self.dice.throw[0], 3 * self.dice.throw[0],
                              4 * self.dice.throw[0]]
        else:
            self.dice_move = copy.deepcopy(self.dice.throw)
            self.dice_move.append(self.dice_move[0] + self.dice_move[1])

        self.get_avail_moves()

        if self.bar in self.player_turn.fields:
            self.game_state = GameState.MOVE_STONE_FROM_BAR
        else:
            self.game_state = GameState.MOVE_STONE

    def roll_button_clicked(self):
        self.roll = random.randint(4, 8)
        self.dice.used = [False, False]
        self.button_pressed = True

    """
    Move stone
    """

    def move_stone_state(self):
        if self.dice.throw[0] == self.dice.throw[1]:
            self.text = f'{self.player_turn.name} rolled 4x{self.dice.throw[0]} and may move stones {self.dice.throw[0]},' \
                        f' {2 * self.dice.throw[0]}, {3 * self.dice.throw[0]} or {4 * self.dice.throw[0]} spaces.'
        else:
            self.text = f'{self.player_turn.name} rolled {self.dice.throw[0]} and {self.dice.throw[1]} or' \
                        f' {self.dice.throw[0] + self.dice.throw[1]} in total.'

    def move_stone_from_bar_state(self):
        draw_text(self.win, 'Player has stones on bar.', 20, 'Inter-Regular', BLACK, WIDTH / 2 - 295, HEIGHT - 90,
                  center=False)

    def get_avail_moves(self):
        """
        Gets available moves for every field where player has stones.
        """
        if self.chosen_field == self.bar:
            self.bar.number = 24 if self.player_turn.has_black_stones else -1

        self.no_moves = True

        for field in self.player_turn.fields:
            if field == self.bar:
                self.bar.number = 24 if self.player_turn.has_black_stones else -1

            if not self.same_number:
                if len(self.dice_move) == 3:
                    current_avail_moves = self.get_current_avail_moves(field, self.dice_move[:2])
                    if current_avail_moves[0] or current_avail_moves[1]:
                        current_avail_moves += self.get_current_avail_moves(field, self.dice_move[2:])
                    else:
                        current_avail_moves.append(None)
                else:
                    current_avail_moves = self.get_current_avail_moves(field, self.dice_move[:1])

            else:
                current_avail_moves = self.get_current_avail_moves(field, self.dice_move)
                is_none = False
                for i, move in enumerate(current_avail_moves):
                    if not move:
                        is_none = True
                    else:
                        if is_none:
                            current_avail_moves[i] = None

            self.avail_moves[field] = current_avail_moves

        if self.no_moves:
            self.end_turn()

    def get_current_avail_moves(self, field, throw_list):
        """
        Gets available moves for one field.
        """
        current_avail_moves = []

        for throw in throw_list:
            field_num = self.get_valid_field_num(field.number, throw)

            if field_num:
                avail_field = self.game_fields[field_num]
                if avail_field.has_1_or_0_stones() or avail_field in self.player_turn.fields:
                    current_avail_moves.append(avail_field)
                    self.no_moves = False
                else:
                    current_avail_moves.append(None)
            else:
                current_avail_moves.append(None)

        if not current_avail_moves:
            self.no_moves = False

        return current_avail_moves

    def get_valid_field_num(self, start_number, throw):
        if self.player_turn.has_black_stones:
            field_num = start_number - throw
        else:
            field_num = start_number + throw

        if 0 <= field_num < 24:
            return field_num

        return None

    def move_stone(self, end_field, index):
        """
        Moves stone from one field to another.
        """
        stone = self.chosen_field.pop_stone()
        if self.chosen_field.is_empty():
            self.player_turn.fields.remove(self.chosen_field)

        stone.position.append(end_field.number)
        if end_field not in self.player_turn.fields:
            self.player_turn.fields.append(end_field)

            if end_field.has_one_stone():
                opponent_stone = end_field.pop_stone()
                self.bar.add_stone(opponent_stone)

                if self.player_turn == self.player1:
                    self.player2.fields.append(self.bar)
                else:
                    self.player1.fields.append(self.bar)

                opponent_stone.position.append('bar')

        end_field.add_stone(stone)

        self.chosen_field = None

        if not self.same_number:
            if index == 2:
                self.end_turn()
            else:
                self.dice_move.pop(index)
                self.dice.used[index] = True
                if self.dice_move:
                    self.dice_move.pop(-1)
                    self.get_avail_moves()
                else:
                    self.end_turn()
        else:
            if len(self.dice_move) == 0:
                self.end_turn()
            else:
                self.dice_move = self.dice_move[:((len(self.dice_move) - 1) - index)]
                self.get_avail_moves()

    def game_fields_clicked(self, mouse_pos):
        if self.chosen_field:
            for i, field in enumerate(self.avail_moves[self.chosen_field]):
                if field:
                    if field.rect.collidepoint(mouse_pos):
                        self.move_stone(field, i)
                        break

        for field in self.player_turn.fields:
            if field.rect.collidepoint(mouse_pos) and self.chosen_field != self.bar:
                if self.chosen_field == field:
                    self.chosen_field = None
                else:
                    self.chosen_field = field

    def bar_clicked(self):
        self.chosen_field = self.bar
        self.get_avail_moves()
        self.game_state = GameState.MOVE_STONE

    """
    End turn
    """

    def end_turn(self):
        self.game_state = GameState.ROLL_DICE
        self.chosen_field = None
        self.dice.used = [True, True]

        if self.player_turn == self.player1:
            self.player_turn = self.player2
        else:
            self.player_turn = self.player1

    def draw(self):
        self.game_board.draw(self.player1.name, self.player2.name)

        self.dice.draw(0, self.win, 90, 90, WIDTH - 220, HEIGHT - 125)
        self.dice.draw(1, self.win, 90, 90, WIDTH - 110, HEIGHT - 125)

        if self.chosen_field and self.game_state != GameState.ROLL_DICE:
            for field in self.avail_moves[self.chosen_field]:
                if field:
                    field.glow(self.win)

        for field in self.game_fields:
            field.draw_stones(self.win)
        self.bar.draw_stones(self.win)

        draw_text(self.win, self.text, 20, 'Inter-Regular', BLACK, WIDTH / 2 - 295, HEIGHT - 120,
                  center=False)

    def gameloop(self, load = False):
        run = True
        show_menu = False
        self.init_fields()

        if load:
            self.load_game()
        else:
            self.init_game()

        while run:
            pygame.time.Clock().tick(FPS)
            self.win.fill(FAWN)
            mouse_pos = pygame.mouse.get_pos()

            self.draw()
            roll_rect = self.game_board.draw_roll_button()

            self.turn()

            if show_menu:
                pygame.draw.rect(self.win, FAWN, [550, 200, 300, 450], 0)
                save_rect = self.game_board.draw_save_button()
                quit_rect = self.game_board.draw_exit_button()

            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False
                    pygame.quit()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        show_menu = not show_menu

                if event.type == pygame.MOUSEBUTTONDOWN:

                    if roll_rect.collidepoint(mouse_pos) and self.game_state == GameState.ROLL_DICE:
                        self.roll_button_clicked()

                    if self.game_state == GameState.MOVE_STONE:
                        self.game_fields_clicked(mouse_pos)

                    if self.bar.rect.collidepoint(mouse_pos) and self.game_state == GameState.MOVE_STONE_FROM_BAR:
                        self.bar_clicked()

                    if show_menu:
                        if save_rect.collidepoint(mouse_pos):
                            self.save_game()

                        if quit_rect.collidepoint(mouse_pos):
                            run = False
                            pygame.quit()

    def format_for_save(self):
        '''Function to format self.game_fields for saving'''
        #TODO add /n to make the json human-readable.
        data = {}

        data["game_fields"] = []
        for field in self.game_fields:
            stones = []
            for stone in field.stones:
                if stone.is_black:
                    color = "Black"
                else:
                    color = "White"
                stones.append({
                    "position": stone.position,
                    "color": color,
                })
            data["game_fields"].append({
                "number": field.number,
                "stones": stones,
            })

        return data

    def save_game(self):
        '''Function to save game'''
        data = self.format_for_save()
        with open("../save.json", "w") as outfile:
            json.dump(data, outfile)
            # outfile.write(str(data))

    def load_game(self):
        '''Function to load game'''
        with open("../save.json") as json_file:
            data = json.load(json_file)

        for field in data["game_fields"]:
            is_black = False
            for stone in field["stones"]:
                if stone["color"] == "Black":
                    is_black = True
                else:
                    is_black = False
                self.game_fields[field["number"]].add_stone(GameStone(stone["position"], is_black))
            if is_black:
                self.player2.fields.append(self.game_fields[field["number"]])
            else:
                self.player1.fields.append(self.game_fields[field["number"]])