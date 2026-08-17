from enum import Enum


class ContentTypeAPI(str, Enum):
    SHOW = "show"
    MOVIE = "movie"


class UserStatusAPI(str, Enum):
    WATCHING = "watching"
    WATCHLIST = "watchlist"
    WATCHED = "watched"
    DROPPED = "dropped"
    PAUSED = "paused"
    NOT_INTERESTED = "not_interested"
