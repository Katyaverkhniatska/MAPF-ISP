from core_components.agent_type import AgentType

class Agent:
    def __init__(self, x, y, type : AgentType):
        self.x = x
        self.y = y
        self.type = type

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def move_to(self, x, y):
        self.x = x
        self.y = y