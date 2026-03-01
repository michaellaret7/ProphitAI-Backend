from abc import ABC, abstractmethod

import pandas as pd

class Node(ABC):
    @abstractmethod
    def run(self, data: pd.DataFrame) -> pd.DataFrame:
        pass

class Clean(Node):
    def run(self, data: pd.DataFrame) -> pd.DataFrame:
        return data.dropna()

class CreateFeatureGroup(Node):
    def run(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()

        data['feature_group'] = data['name']

        return data

class UpperCase(Node):
    def run(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()

        data['feature_group'] = data['name'].str.upper()

        return data


class Pipeline:
    def __init__(self, nodes: list[Node]):
        self.nodes = nodes

    def run(self, data: pd.DataFrame) -> pd.DataFrame:
        for node in self.nodes:
            data = node.run(data)
        return data


if __name__ == "__main__":
    df = pd.DataFrame({
        'name': ['john', 'jane', 'jim', 'jill'],
        'age': [25, 30, 35, 40],
        'city': ['New York', 'Los Angeles', 'Chicago', 'Houston']
    })

    p = Pipeline(
        [
            Clean(), 
            CreateFeatureGroup(), 
            UpperCase()
        ]
    )
    print(p.run(df))