import abc

from src.games.game.base import BaseUi


class UI(BaseUi):
    cards_hidden_unicode = "┌─────┐\n│░░░░░│\n│░░░░░│\n│░░░░░│\n└─────┘"

    @abc.abstractmethod
    def hit_or_stand(self, player):
        pass

    def card_unicode(self, card):
        if card.hidden:
            return self.cards_hidden_unicode.replace("┌", "╭").replace("┐", "╮").replace("┘", "╯").replace("└", "╰")
        else:
            spaces = " " if len(card.rank) == 1 else ""
            lines = []
            lines.append("┌─────┐")
            lines.append(f"│{card.rank}{spaces}   │")
            lines.append(f"│{card.symbol}   {card.symbol}│")
            lines.append(f"│   {spaces}{card.rank}│")
            lines.append("└─────┘")
            unicode = "\n".join(lines)
            return unicode.replace("┌", "╭").replace("┐", "╮").replace("┘", "╯").replace("└", "╰")

    def display_cards(self, player, hidden):
        pass

    def display_board(self, game):
        pass
