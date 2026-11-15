"""Keep the documented tic-tac-toe exchange legal and its board accurate."""

from pathlib import Path
import re
import unittest


README = Path(__file__).resolve().parents[1] / "README.md"
MOVE = re.compile(r"^\| ([1-9]) \| (Codex|Claude) \| ([XO]) \| ([1-9]) \|$")
WINNING_LINES = (
    (1, 2, 3), (4, 5, 6), (7, 8, 9),
    (1, 4, 7), (2, 5, 8), (3, 6, 9),
    (1, 5, 9), (3, 5, 7),
)


class ReadmeExampleTests(unittest.TestCase):
    def test_documented_game_is_a_draw_and_matches_board(self):
        readme = README.read_text(encoding="utf-8")
        example = readme.split("## Example: a game of tic-tac-toe\n", 1)[1].split("\n## ", 1)[0]
        moves = [MOVE.fullmatch(line).groups() for line in example.splitlines() if MOVE.fullmatch(line)]
        self.assertEqual(len(moves), 9)

        board = [" "] * 9
        for turn, (number, agent, mark, square) in enumerate(moves, 1):
            self.assertEqual(int(number), turn)
            self.assertEqual((agent, mark), ("Codex", "X") if turn % 2 else ("Claude", "O"))
            index = int(square) - 1
            self.assertEqual(board[index], " ", "a square was played twice")
            board[index] = mark
            for line in WINNING_LINES:
                self.assertFalse(all(board[position - 1] == mark for position in line), "the game ended before a draw")

        rendered = "\n---+---+---\n".join(" {} | {} | {}".format(*board[i:i + 3]) for i in (0, 3, 6))
        self.assertIn("```text\n" + rendered + "\n```", example)


if __name__ == "__main__":
    unittest.main()
