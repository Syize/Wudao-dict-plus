class WudaoErrorBase(Exception):
    pass


class OnlineDictError(WudaoErrorBase):
    pass


__all__ = ["OnlineDictError", "WudaoErrorBase"]
