from framebuf import FrameBuffer

class Display(FrameBuffer):
    def __init__(self, buffer: Any, width: int, height: int, format: int, stride: int = 0) -> None:
        super().__init__(buffer, width, height, format, stride)
        self.width = width
        self.height = height

    def ready(self) -> None:
        raise NotImplementedError("function not implemented.")

    def show(self, buf1=bytearray(1)) -> None:
        raise NotImplementedError("function not implemented.")

    def clear(self) -> None:
        self.fill(0)
