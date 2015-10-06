#!/usr/bin/env python

"""models.py

Udacity conference server-side Python App Engine data & ProtoRPC models

$Id: models.py,v 1.1 2014/05/24 22:01:10 wesc Exp $

created/forked from conferences.py by wesc on 2014 may 24

"""

__author__ = 'wesc+api@google.com (Wesley Chun)'

import httplib
import endpoints
from protorpc import messages
from google.appengine.ext import ndb


class ConflictException(endpoints.ServiceException):
    """ConflictException -- exception mapped to HTTP 409 response"""
    http_status = httplib.CONFLICT


class Profile(ndb.Model):
    """Profile -- User profile object"""
    displayName = ndb.StringProperty()
    mainEmail = ndb.StringProperty()
    teeShirtSize = ndb.StringProperty(default='NOT_SPECIFIED')
    conferenceKeysToAttend = ndb.StringProperty(repeated=True)


class ProfileMiniForm(messages.Message):
    """ProfileMiniForm -- update Profile form message"""
    displayName = messages.StringField(1)
    teeShirtSize = messages.EnumField('TeeShirtSize', 2)


class ProfileForm(messages.Message):
    """ProfileForm -- Profile outbound form message"""
    displayName = messages.StringField(1)
    mainEmail = messages.StringField(3)
    teeShirtSize = messages.EnumField('TeeShirtSize', 4)
    conferenceKeysToAttend = messages.StringField(5, repeated=True)


# Child of Profile
class Wishlist(ndb.Model):
    userId = ndb.StringProperty(required=True)
    sessionKeys = ndb.KeyProperty(kind='Session', repeated=True)


class WishlistForm(messages.Message):
    # userId = messages.StringField(1)
    websafeSessionKey = messages.StringField(2)
    # websafeKey = messages.StringField(3)


class WishlistFormName(messages.Message):
    sessionName = messages.StringField(1)
    # websafeKey = messages.StringField(2)


class BooleanMessage(messages.Message):
    """BooleanMessage-- outbound Boolean value message"""
    data = messages.BooleanField(1)


class Conference(ndb.Model):
    """Conference -- Conference object"""
    name            = ndb.StringProperty(required=True)
    description     = ndb.StringProperty()
    organizerUserId = ndb.StringProperty()
    topics          = ndb.StringProperty(repeated=True)
    city            = ndb.StringProperty()
    startDate       = ndb.DateProperty()
    month           = ndb.IntegerProperty()
    endDate         = ndb.DateProperty()
    maxAttendees    = ndb.IntegerProperty()
    seatsAvailable  = ndb.IntegerProperty()


class ConferenceForm(messages.Message):
    """ConferenceForm -- Conference outbound form message"""
    name            = messages.StringField(1)
    description     = messages.StringField(2)
    organizerUserId = messages.StringField(3)
    topics          = messages.StringField(4, repeated=True)
    city            = messages.StringField(5)
    startDate       = messages.StringField(6) #DateTimeField()
    month           = messages.IntegerField(7)
    maxAttendees    = messages.IntegerField(8)
    seatsAvailable  = messages.IntegerField(9)
    endDate         = messages.StringField(10) #DateTimeField()
    websafeKey      = messages.StringField(11)
    organizerDisplayName = messages.StringField(12)


class ConferenceForms(messages.Message):
    """ConferenceForms -- multiple Conference outbound form message"""
    items = messages.MessageField(ConferenceForm, 1, repeated=True)


# Child of Conference
class Session(ndb.Model):
    name                = ndb.StringProperty(required=True)
    highlights          = ndb.StringProperty(repeated=True)
    speakerDisplayName  = ndb.StringProperty(required=True)
    duration            = ndb.IntegerProperty()
    sessionType         = ndb.StringProperty(default='NOT_SPECIFIED', required=True)
    date                = ndb.DateProperty()
    startTime           = ndb.TimeProperty()


class SessionForm(messages.Message):
    name                = messages.StringField(1)
    highlights          = messages.StringField(2, repeated=True)
    speakerDisplayName  = messages.StringField(3)
    duration            = messages.IntegerField(4)
    sessionType         = messages.EnumField('SessionTypeEnum', 5)
    date                = messages.StringField(6)
    startTime           = messages.StringField(7)
    # websafeKey          = messages.StringField(8)


# Child of Session
class Review(ndb.Model):
    conference_name     = ndb.StringProperty()
    session_name        = ndb.StringProperty()
    speaker_name        = ndb.StringProperty()
    review              = ndb.StringProperty()


class ReviewForm(messages.Message):
    conference_name     = messages.StringField(1, required=True)
    session_name        = messages.StringField(2, required=True)
    speaker_name        = messages.StringField(3)
    review              = messages.EnumField('ReviewEnum', 4, required=True)


class ReviewForms(messages.Message):
    """ReviewForms -- multiple Conference outbound form message"""
    items = messages.MessageField(ReviewForm, 1, repeated=True)


class ReviewQueryForm(messages.Message):
    session_name        = messages.StringField(1)


class SessionForms(messages.Message):
    """SessionForms -- multiple Conference outbound form message"""
    items = messages.MessageField(SessionForm, 1, repeated=True)


class TeeShirtSize(messages.Enum):
    """TeeShirtSize -- t-shirt size enumeration value"""
    NOT_SPECIFIED = 1
    XS_M = 2
    XS_W = 3
    S_M = 4
    S_W = 5
    M_M = 6
    M_W = 7
    L_M = 8
    L_W = 9
    XL_M = 10
    XL_W = 11
    XXL_M = 12
    XXL_W = 13
    XXXL_M = 14
    XXXL_W = 15


# Enum for number of stars in review
# Needs a better selections, maybe not satisfied, etc.
class ReviewEnum(messages.Enum):
    """Specify Number of Stars"""
    NO_OPINION = 0
    very_unsatisfied = 1
    unsatisfied = 2
    satisfied = 3
    very_satisfied = 4
    excellent = 5


class SessionTypeEnum(messages.Enum):
    """ Specify Session type """
    NOT_SPECIFIED = 1
    workshop = 2
    lecture = 3
    demonstration = 4
    party = 5


class ConferenceQueryForm(messages.Message):
    """ConferenceQueryForm -- Conference query inbound form message"""
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)


class ConferenceQueryForms(messages.Message):
    """ConferenceQueryForms --
    multiple ConferenceQueryForm inbound form message"""
    filters = messages.MessageField(ConferenceQueryForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    data = messages.StringField(1, required=True)


class SessionQueryForm(messages.Message):
    query = messages.StringField(1)
    # websafeKey = messages.StringField(2)


class SessionQueryKeyForm(messages.Message):
    websafeKey = messages.StringField(1)


class SessionsQueryTypeAndTime(messages.Message):
    # conferenceName = messages.StringField(1)
    sessionType = messages.StringField(2)
    sessionBeforeTime = messages.StringField(3)
    sessionAfterTime = messages.StringField(4)
