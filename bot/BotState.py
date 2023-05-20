from procedures import BotProcedure, EgressProcedure

class BotState:

    def __init__(self) -> None:
        self.procedures = [
            EgressProcedure()
        ]
