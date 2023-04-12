from sqlalchemy import Column, String, Float


class FavouriteBook:
    name = Column(String(255))
    author = Column(String(255))
    rating = Column(Float())
