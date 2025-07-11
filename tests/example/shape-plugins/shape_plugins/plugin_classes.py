import typing as ty

import base_package

class Quad(base_package.Shape, exclude_from_union=True):
    pass

class Rectangle(Quad):
    type: ty.Literal["Rect"] = "Rect"
    length: float
    width: float

    def area(self) -> float:
        return self.length * self.width

class Square(Quad):
    side: float

    def area(self) -> float:
        return self.side * self.side
