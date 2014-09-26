# -*- coding: utf-8 -*-

""" Skrafldb - persistent data management for the Netskrafl application

    Author: Vilhjalmur Thorsteinsson, 2014

    This module stores data in the Google App Engine NDB
    (see https://developers.google.com/appengine/docs/python/ndb/).

    The data model is as follows:

    User
       [Properties]
       [1:1] Preferences
            [Properties]
       [2:1] Match
            User
            [1:1] Game
                [Properties]
                [1:N] Move
                    [Properties]
                    [1:N] Cover
                        [Properties]
                    [1:1] Stats
                        [Properties]

"""


import uuid
from google.appengine.ext import ndb


class Unique:
    """ Wrapper for generation of unique id strings for keys """

    @classmethod
    def id(cls):
        """ Generates unique id strings """
        return str(uuid.uuid1()) # Random UUID


class UserModel(ndb.Model):

    """ Models an individual user """

    nickname = ndb.StringProperty()
    inactive = ndb.BooleanProperty()
    prefs = ndb.JsonProperty()
    timestamp = ndb.DateTimeProperty(auto_now_add = True)

    @classmethod
    def create(cls, user_id, nickname):
        """ Create a new user """
        user = cls(id = user_id)
        user.nickname = nickname # Default to the same nickname
        user.inactive = False # A new user is always active
        user.prefs = { } # No preferences
        return user.put().id()

    @classmethod
    def update(cls, user_id, nickname, inactive, prefs):
        user = cls.fetch(user_id)
        user.nickname = nickname
        user.inactive = inactive
        user.prefs = prefs
        user.put()

    @classmethod
    def fetch(cls, user_id):
        return cls.get_by_id(user_id)


# class Match(ndb.Model):
# 
#    """ Models a match that consists of a single Game between two Users """
# 
#     player = ndb.KeyProperty(kind = User)
#     playerid = ndb.IntegerProperty() # Was the player 0 (first move) or 1 (opponent)
#     game = ndb.KeyProperty(kind = Game)
# 
#     @classmethod
#     def create(cls, game_id, player0_id, player1_id):
#         """ Create two Match entities for a Game, one for each User (player) """
#         match = cls(id = Unique.id())
#         match.player = ndb.Key(User, player0_id) # Unique id of user player0
#         match.playerid = 0
#         match.game = ndb.Key(Game, game_id) # Unique id of game
#         match.put()
#         match = cls(id = Unique.id()) # Unique
#         match.player = ndb.Key(User, player1_id)
#         match.playerid = 1
#         match.game = ndb.Key(Game, game_id) # Key of game
#         match.put()
# 
#     @classmethod
#     def fetch_game(cls, game):
#         return User.get_by_id(uuid)


class MoveModel(ndb.Model):
    """ Models a single move in a Game """

    coord = ndb.StringProperty()
    tiles = ndb.StringProperty()
    score = ndb.IntegerProperty(default = 0)


class GameModel(ndb.Model):
    """ Models a game between two users """

    # The players
    player0 = ndb.KeyProperty(kind = UserModel)
    player1 = ndb.KeyProperty(kind = UserModel)

    # The racks
    rack0 = ndb.StringProperty(indexed = False)
    rack1 = ndb.StringProperty(indexed = False)

    # The scores
    score0 = ndb.IntegerProperty()
    score1 = ndb.IntegerProperty()

    # Whose turn is it next, 0 or 1?
    to_move = ndb.IntegerProperty()

    # Is this game over?
    over = ndb.BooleanProperty()

    # When was the game started?
    timestamp = ndb.DateTimeProperty(auto_now_add = True)

    # The moves so far
    moves = ndb.LocalStructuredProperty(MoveModel, repeated = True)

    def set_player(self, ix, user_id):
        """ Set a player key property to point to a given user, or None """
        k = None if user_id is None else ndb.Key(UserModel, user_id)
        if ix == 0:
            self.player0 = k
        elif ix == 1:
            self.player1 = k

    @classmethod
    def fetch(cls, uuid):
        """ Fetch a game model given its uuid """
        return cls.get_by_id(uuid)

    @classmethod
    def find_live_game(cls, user_id):
        """ Query to find a live (ongoing) game for the given user, if it exists """
        assert user_id is not None
        if user_id is None:
            return None
        k = ndb.Key(UserModel, user_id)
        q = cls.query(ndb.OR(GameModel.player0 == k, GameModel.player1 == k)).filter(GameModel.over == False)
        reskey = q.get(keys_only = True)
        return None if reskey is None else reskey.id()
