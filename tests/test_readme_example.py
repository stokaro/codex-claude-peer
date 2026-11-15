"""Validate the game and message flow shown in the README SVG."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "docs" / "tic-tac-toe.svg"
NS = {"svg": "http://www.w3.org/2000/svg"}
WINNING_LINES = (
    (1, 2, 3), (4, 5, 6), (7, 8, 9),
    (1, 4, 7), (2, 5, 8), (3, 6, 9),
    (1, 5, 9), (3, 5, 7),
)


class ReadmeExampleTests(unittest.TestCase):
    def test_svg_exchanges_eight_moves_and_shows_forced_draw(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("](docs/tic-tac-toe.svg)", readme)

        root = ET.parse(SVG).getroot()
        self.assertIsNotNone(root.find("svg:title", NS))
        self.assertIsNotNone(root.find("svg:desc", NS))

        messages = root.findall(".//svg:g[@class='move']", NS)
        cells = root.findall(".//svg:g[@class='board-cell']", NS)
        self.assertEqual(len(messages), 8)
        self.assertEqual(len(cells), 9)

        turns = []
        for message in messages:
            turn = int(message.attrib["data-turn"])
            agent = message.attrib["data-agent"]
            mark = message.attrib["data-mark"]
            square = int(message.attrib["data-square"])
            self.assertEqual(message.attrib["data-exchanged"], "true")
            self.assertEqual((agent, mark), ("Codex", "X") if turn % 2 else ("Claude", "O"))
            path = message.find("svg:path", NS)
            self.assertEqual(path.attrib["marker-end"], "url(#arrow-x)" if mark == "X" else "url(#arrow-o)")
            label = "".join(message.find("svg:text[@class='chip']", NS).itertext())
            self.assertIn(f"{mark}→ {square}", label)
            turns.append((turn, mark, square))

        self.assertEqual([turn for turn, _, _ in turns], list(range(1, 9)))
        forced = [cell for cell in cells if cell.attrib["data-forced"] == "true"]
        self.assertEqual(len(forced), 1)
        self.assertEqual((forced[0].attrib["data-turn"], forced[0].attrib["data-square"], forced[0].attrib["data-mark"]), ("9", "7", "X"))
        turns.append((9, "X", 7))

        board = [" "] * 9
        for turn, mark, square in turns:
            self.assertEqual(board[square - 1], " ", "a square was played twice")
            board[square - 1] = mark
            for line in WINNING_LINES:
                self.assertFalse(all(board[position - 1] == mark for position in line), f"turn {turn} ended the game before a draw")

        for cell in cells:
            square = int(cell.attrib["data-square"])
            mark = cell.attrib["data-mark"]
            turn = int(cell.attrib["data-turn"])
            self.assertEqual((mark, turn), (board[square - 1], next(t for t, _, s in turns if s == square)))
            self.assertEqual(cell.find("svg:text[@class='board-mark']", NS).text, mark)


if __name__ == "__main__":
    unittest.main()
