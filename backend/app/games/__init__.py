from app.games.base import Game
from app.games.base import RoundData as RoundData
from app.games.guess_the_song import GuessTheSongGame

GAMES: dict[str, Game] = {g.key: g for g in (GuessTheSongGame(),)}
