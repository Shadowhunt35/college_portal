import sys

class CustomException(Exception):
    def __init__(self, error_message, error_detail: sys = sys):
        super().__init__(str(error_message))
        self.error_message = self._format(error_message, error_detail)

    @staticmethod
    def _format(message, detail):
        _, _, tb = detail.exc_info()
        if tb:
            file = tb.tb_frame.f_code.co_filename
            line = tb.tb_lineno
            return f'Error in [{file}] at line [{line}]: {message}'
        return str(message)

    def __str__(self):
        return self.error_message