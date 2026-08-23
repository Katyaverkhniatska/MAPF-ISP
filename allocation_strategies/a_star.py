from visualization.grid import Grid
import heapq

class AStar:
    def __init__(self, start : tuple, goal : tuple, grid : Grid):
        self.grid = grid
        if not self.grid.is_passable(start) or not self.grid.is_passable(goal):
            raise ValueError("Start or goal position is invalid or out of bounds.")
        self.start = start
        self.goal = goal

        # The open set is a priority queue that will store the nodes to be evaluated
        self.open_set = []
        # The closed set is a matrix where cell (i, j) has value True if 
        # the node (i, j) has been evaluated, False otherwise
        self.closed_set = [[False for _ in range(grid.width)] for _ in range(grid.height)]
        heapq.heappush(self.open_set, (self.heuristic(start, goal), start))

        # Cost from start to each node
        self.g_score = {
            start: 0
        }

    def heuristic(self, a, b):
        # Using Manhattan distance as heuristic
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    def find_path(self):
        if self.start == self.goal:
            return [self.start]  # Start and goal are the same
        
        # Used to reconstruct the final path
        came_from = {self.start: None}

        while len(self.open_set) > 0:
            # Get the cell with the smallest f value from the open list
            _, least_f_node = heapq.heappop(self.open_set)

            if least_f_node == self.goal:
                return self.reconstruct_path(came_from, least_f_node)

            # Mark this cell as evaluated
            self.closed_set[least_f_node[0]][least_f_node[1]] = True

            neighbors = self.grid.get_neighbors(least_f_node)

            for neighbor in neighbors:
                if self.closed_set[neighbor[0]][neighbor[1]]:
                    continue

                if not self.grid.is_passable(neighbor):
                    continue

                tentative_g = self.g_score[least_f_node] + 1

                # If this path to neighbor is better than any previous one, record it
                if tentative_g < self.g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = least_f_node
                    self.g_score[neighbor] = tentative_g

                    f_score = tentative_g + self.heuristic(neighbor, self.goal)
                    # Update the priority queue with the new f_score
                    heapq.heappush(self.open_set, (f_score, neighbor))
        
        return None  # No path found

    def reconstruct_path(self, came_from, tail):
        path = [tail]
        while tail in came_from and came_from[tail] is not None:
            tail = came_from[tail]
            path.append(tail)
        return list(reversed(path))