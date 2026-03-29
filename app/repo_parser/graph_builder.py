
import networkx as nx


class DependencyGraph:

    def __init__(self):

        self.graph = nx.DiGraph()


    def add_file(self, file_name):

        self.graph.add_node(file_name, type="file")


    def add_imports(self, file_name, imports):

        for imp in imports:

            self.graph.add_edge(file_name, imp)


    def get_graph(self):

        return self.graph


    def print_graph(self):

        for edge in self.graph.edges():
            print(f"{edge[0]} -> {edge[1]}")