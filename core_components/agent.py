from core_components.agent_type import AgentType
from core_components.grid import Vertex

class Agent:
    def __init__(self, x : int, y : int, type : AgentType):
        self.x = x
        self.y = y
        self.type = type
        self.target = None

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def move_to(self, x, y):
        self.x = x
        self.y = y

    def set_target(self, target : Vertex):
        self.target = target