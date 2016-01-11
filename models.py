#!/usr/bin/env python
import httplib
import endpoints
from protorpc import messages
from google.appengine.ext import ndb

"""models.py

Udacity conference server-side Python App Engine data & ProtoRPC models

$Id: models.py

Author: Zeeshan Ahmad
Email: ahmad.zeeshaan@gmail.com

"""

__author__ = 'ahmad.zeeshan@gmail.com (Zeeshan Ahmad)'


class Profile(ndb.Model):
    """Profile -- User profile object"""
    displayName = ndb.StringProperty()
    mainEmail = ndb.StringProperty()
    teeShirtSize = ndb.StringProperty(default='NOT_SPECIFIED')
    conferenceKeysToAttend = ndb.StringProperty(repeated=True)
    sessionsWishList = ndb.KeyProperty(kind="Session", repeated=True)

# needed for conference registration


class BooleanMessage(messages.Message):
    """BooleanMessage-- outbound Boolean value message"""
    data = messages.BooleanField(1)


class ConflictException(endpoints.ServiceException):
    """ConflictException -- exception mapped to HTTP 409 response"""
    http_status = httplib.CONFLICT


class ProfileMiniForm(messages.Message):
    """ProfileMiniForm -- update Profile form message"""
    displayName = messages.StringField(1)
    teeShirtSize = messages.EnumField('TeeShirtSize', 2)


class ProfileForm(messages.Message):
    """ProfileForm -- Profile outbound form message"""
    userId = messages.StringField(1)
    displayName = messages.StringField(2)
    mainEmail = messages.StringField(3)
    teeShirtSize = messages.EnumField('TeeShirtSize', 4)
    conferenceKeysToAttend = messages.StringField(5, repeated=True)
    sessionsWishList = messages.StringField(6, repeated=True)


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


class Conference(ndb.Model):
    """Conference -- Conference object"""
    name = ndb.StringProperty(required=True)
    description = ndb.StringProperty()
    organizerUserId = ndb.StringProperty()
    topics = ndb.StringProperty(repeated=True)
    city = ndb.StringProperty()
    startDate = ndb.DateProperty()
    month = ndb.IntegerProperty()
    endDate = ndb.DateProperty()
    maxAttendees = ndb.IntegerProperty()
    seatsAvailable = ndb.IntegerProperty()


class ConferenceForm(messages.Message):
    """ConferenceForm -- Conference outbound form message"""
    name = messages.StringField(1)
    description = messages.StringField(2)
    organizerUserId = messages.StringField(3)
    topics = messages.StringField(4, repeated=True)
    city = messages.StringField(5)
    startDate = messages.StringField(6)
    month = messages.IntegerField(7)
    maxAttendees = messages.IntegerField(8)
    seatsAvailable = messages.IntegerField(9)
    endDate = messages.StringField(10)
    websafeKey = messages.StringField(11)
    organizerDisplayName = messages.StringField(12)


class ConferenceForms(messages.Message):
    """ConferenceForms -- multiple Conference outbound form message"""
    items = messages.MessageField(ConferenceForm, 1, repeated=True)


class ConferenceQueryForm(messages.Message):
    """ConferenceQueryForm -- Conference query inbound form message"""
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)


class ConferenceQueryForms(messages.Message):
    """ConferenceQueryForms -- multiple ConferenceQueryForm
    inbound form message"""
    filters = messages.MessageField(ConferenceQueryForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    data = messages.StringField(1, required=True)


class Session(ndb.Model):
    """Session -- Session object"""
    name = ndb.StringProperty(required=True)
    highlights = ndb.StringProperty(repeated=True)
    websafeSpeakerKey = ndb.StringProperty()
    duration = ndb.IntegerProperty()
    typeOfSession = ndb.StringProperty()
    date = ndb.DateProperty()
    startTime = ndb.IntegerProperty()


class SessionForm(messages.Message):
    """SessionForm -- Session outbound form message"""
    name = messages.StringField(1)
    highlights = messages.StringField(2, repeated=True)
    websafeSpeakerKey = messages.StringField(3)
    duration = messages.IntegerField(4)
    typeOfSession = messages.StringField(5)
    date = messages.StringField(6)
    startTime = messages.IntegerField(7)
    websafeConferenceKey = messages.StringField(8)
    websafeSessionKey = messages.StringField(9)


class SessionForms(messages.Message):
    """SessionForms -- multiple Session outbound form message"""
    sessions = messages.MessageField(SessionForm, 1, repeated=True)


class Speaker(ndb.Model):
    """Speaker -- Speaker object"""
    name = ndb.StringProperty(required=True)
    organization = ndb.StringProperty()
    interests = ndb.StringProperty(repeated=True)


class SpeakerForm(messages.Message):
    """SpeakerForm -- Speaker outbound form message"""
    name = messages.StringField(1)
    organization = messages.StringField(2)
    interests = messages.StringField(3, repeated=True)
    websafeSpeakerKey = messages.StringField(4)


class SpeakerForms(messages.Message):
    """SpeakerForms -- multiple Speaker outbound form message"""
    speakers = messages.MessageField(SpeakerForm, 1, repeated=True)


class QueryForm(messages.Message):
    """QueryForm -- query inbound form message"""
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)


class QueryForms(messages.Message):
    """QueryForms -- multiple QueryForm inbound form message"""
    filters = messages.MessageField(QueryForm, 1, repeated=True)


class ConferenceSessionQueryForm(messages.Message):
    """ConferenceSessionQueryForm -- inbound query form message for
        conference sessions"""
    websafeConferenceKey = messages.StringField(1)


class ConferenceSessionTypeSessionQueryForm(messages.Message):
    """ConferenceSessionTypeSessionQueryForm -- inbound query form message for
        conference sessions based on session type"""
    websafeConferenceKey = messages.StringField(1)
    typeOfSession = messages.StringField(2)


class ConferenceSessionTypeStartTimeQueryForm(messages.Message):
    """ConferenceSessionTypeStartTimeQueryForm -- inbound query form message for
        conference sessions based on session type and start time"""
    typeOfSession = messages.StringField(1)
    startTime = messages.IntegerField(2)


class SpeakerSessionQueryForm(messages.Message):
    """SpeakerSessionQueryForm -- inbound query form message for
        conference sessions based on speaker"""
    websafeSpeakerKey = messages.StringField(1)


class SessionStartTimeQueryForm(messages.Message):
    """SessionStartTimeQueryForm -- inbound query form message for
        conference sessions based on start time"""
    startTime = messages.IntegerField(1)

# For Task 3


class SessionStartTimeDurationQueryForm(messages.Message):
    startTime = messages.IntegerField(1)
    duration = messages.IntegerField(2)


class SessionMinStartTimeDurationHighlightsQueryForm(messages.Message):
    startTime = messages.IntegerField(1)
    duration = messages.IntegerField(2)
    highlights = messages.StringField(3)
