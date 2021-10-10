import string
import random

class GrilleBoard:
    __slots__ = ("argument_grid", "character_grid")

    def __init__(self, argument_grid: list, character_grid: list):
        self.argument_grid  = argument_grid
        self.character_grid = character_grid

class GrilleBoardBuilder:
    __slots__ = ("message", )

    def __init__(self, message):
        self.message = message.lower().replace(" ", "")

    def build(self) -> GrilleBoard:
        max_characters_per_line = 2
        argument_grid  = []
        character_grid = []
        alphabet = string.ascii_lowercase
        current_char_index = 0
        width = 5 if len(self.message) < 10 else 7

        done = False

        i = 0
        while not done:
            characters = random.choices(alphabet, k=width)
            character_grid.append([])
            argument_grid.append([])

            amount            = random.randint(0, max_characters_per_line)
            total_indexes     = [x for x in range(width)]
            random.shuffle(total_indexes)
            character_indexes = [total_indexes[x] for x in range(amount)]

            for j in range(width):
                if j in character_indexes and current_char_index < len(self.message):
                    character = self.message[current_char_index]
                    character_grid[i].append(character)
                    argument_grid[i].append(" ")
                    current_char_index += 1
                else:
                    character_grid[i].append(characters[j])
                    argument_grid[i].append("#")

            i += 1
            done = current_char_index > len(self.message)-1

        return GrilleBoard(argument_grid, character_grid)
