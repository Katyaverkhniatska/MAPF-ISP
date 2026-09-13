from core_components.agent_type import AgentType
from core_components.grid import Vertex

class Agent:
    def __init__(self, x : int, y : int, type : AgentType):
        self.__x = x
        self.__y = y
        self.__type = type
        self.__target = None

    def move(self, dx, dy):
        self.__x += dx
        self.__y += dy

    def move_to(self, x, y):
        self.__x = x
        self.__y = y

    def set_target(self, target : Vertex):
        self.__target = target

    def get_target(self) -> Vertex | None:
        return self.__target

    def get_position(self) -> Vertex:
        return (self.__x, self.__y)