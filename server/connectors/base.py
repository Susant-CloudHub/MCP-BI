from typing import Dict, Any, Generator

class BaseConnector:
    name: str
    version: str

    def capabilities(self) -> Dict[str, Any]:
        raise NotImplementedError

    def discover(self) -> Dict[str, Any]:
        raise NotImplementedError

    def execute(self, query: str, dialect: str, stream: bool = True) -> Generator:
        raise NotImplementedError
