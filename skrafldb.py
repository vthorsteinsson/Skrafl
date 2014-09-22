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
        return uuid.uuid1() # Random UUID


class User(ndb.Model):

    """ Models an individual user """

    nickname = ndb.StringProperty()
    inactive = ndb.BooleanProperty()
    timestamp = ndb.DateTimeProperty(auto_now_add = True)

    @classmethod
    def create(cls, user_id, nickname):
        """ Create a new user """
        user = cls(id = user_id)
        user.nickname = nickname # Default to the same nickname
        user.inactive = False # A new user is always active
        return user.put().id()

    @classmethod
    def update(cls, user_id, nickname, inactive):
        user = cls.fetch(user_id)
        user.nickname = nickname
        user.inactive = inactive
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
# 
# 
# class Cover(ndb.Model):
#     """ Models a square being covered in a Move """
# 
#     coord = ndb.StringProperty(required = True)
#     tile = ndb.StringProperty(required = True)
#     letter = ndb.StringProperty(required = True)
# 
# 
# class Move(ndb.Model):
#     """ Models a single move in a Game """
# 
#     kind = ndb.StringProperty(required = True)
#     covers = ndb.LocalStructuredProperty(Cover, repeated = True)
#     score = ndb.IntegerProperty(default = 0)
# 
# 
# class Game(ndb.Model):
#     """ Models a game between two users """
# 
#     match = ndb.KeyProperty(kind = Match)
#     completed = ndb.BooleanProperty()
#     timestamp = ndb.DateTimeProperty(auto_now_add = True)
#     moves = ndb.StructuredProperty(Move, repeated = True)
# 
