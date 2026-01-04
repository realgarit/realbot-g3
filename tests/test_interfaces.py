
import pytest
from modules.battle.battle_strategies import BattleStrategy
from modules.modes import BotMode
from modules.pokemon.pokemon import Pokemon, Move
from modules.battle.battle_state import BattleState
from modules.modes._interface import BattleAction
from typing import Generator

def test_battle_strategy_is_abstract():
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        class IncompleteStrategy(BattleStrategy):
            pass
        IncompleteStrategy()

def test_battle_strategy_enforcement():
    class CompleteStrategy(BattleStrategy):
        def party_can_battle(self) -> bool: return True
        def pokemon_can_battle(self, pokemon: Pokemon) -> bool: return True
        def which_move_should_be_replaced(self, pokemon: Pokemon, new_move: Move) -> int: return 4
        def should_flee_after_faint(self, battle_state: BattleState) -> bool: return False
        def choose_new_lead_after_battle(self) -> int | None: return None
        def choose_new_lead_after_faint(self, battle_state: BattleState) -> int: return 0
        def decide_turn(self, battle_state: BattleState): return None

    # Should not raise
    CompleteStrategy()

def test_bot_mode_is_abstract():
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        class IncompleteMode(BotMode):
            pass
        IncompleteMode()

def test_bot_mode_enforcement():
    class CompleteMode(BotMode):
        @staticmethod
        def name() -> str: return "Test"
        def run(self) -> Generator: yield
    
    # Should not raise
    CompleteMode()
