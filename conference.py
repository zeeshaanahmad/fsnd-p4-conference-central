#!/usr/bin/env python
from datetime import datetime
import json
import os
import time

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import urlfetch
from google.appengine.ext import ndb

from models import Profile
from models import ProfileMiniForm
from models import ProfileForm
from models import TeeShirtSize
from models import Conference
from models import ConferenceForm
from models import Session
from models import Speaker

from settings import WEB_CLIENT_ID

from utils import getUserId

from models import ConferenceForms
from models import ConferenceQueryForm
from models import ConferenceQueryForms

from models import BooleanMessage
from models import ConflictException

from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import StringMessage

from models import SessionForm
from models import SpeakerForm
from models import SpeakerForms
from models import SessionForms
from models import QueryForm
from models import QueryForms
from models import ConferenceSessionQueryForm
from models import ConferenceSessionTypeSessionQueryForm
from models import SpeakerSessionQueryForm
from models import SessionStartTimeQueryForm
from models import ConferenceSessionTypeStartTimeQueryForm
from models import SessionStartTimeDurationQueryForm
from models import SessionMinStartTimeDurationHighlightsQueryForm
"""
conference.py -- Udacity conference server-side Python App Engine API;
    uses Google Cloud Endpoints, Extended the provided code and added new
    methods/Endpoints

$Id: conference.py,v 1 2016/01/03 Zeeshan Ahamd

Author: Zeeshan Ahmad
Email: ahmad.zeeshaan@gmail.com

"""

__author__ = 'ahmad.zeeshan@gmail.com (Zeeshan Ahmad)'

CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)
SESSION_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeSessionKey=messages.StringField(1),
)
SPEAKER_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeSpeakerKey=messages.StringField(1),
)

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID

DEFAULTS = {
    "city": "Default City",
    "maxAttendees": 0,
    "seatsAvailable": 0,
    "topics": ["Default", "Topic"],
}

OPERATORS = {
    'EQ':   '=',
            'GT':   '>',
            'GTEQ': '>=',
            'LT':   '<',
            'LTEQ': '<=',
            'NE':   '!='
}

FIELDS = {
    'CITY': 'city',
            'TOPIC': 'topics',
            'MONTH': 'month',
            'MAX_ATTENDEES': 'maxAttendees',
            'NAME': 'name',
            'INTERESTS': 'interests',
            'ORGANIZATION': 'organization',
}

MEMCACHE_ANNOUNCEMENTS_KEY = 'MEMCACHE_ANNOUNCEMENTS_KEY'
MEMCACHE_FEATURED_SPEAKER_KEY = 'MEMCACHE_FEATURED_SPEAKER_KEY'

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


@endpoints.api(name='conference',
               version='v1',
               allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID],
               scopes=[EMAIL_SCOPE])
class ConferenceApi(remote.Service):
    """Conference API v0.1"""

# - - - Profile objects - - - - - - - - - - - - - - - - - - -

    def _copyProfileToForm(self, prof):
        """Copy relevant fields from Profile to ProfileForm."""
        # copy relevant fields from Profile to ProfileForm
        pf = ProfileForm()
        for field in pf.all_fields():
            if hasattr(prof, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr(pf, field.name, getattr(TeeShirtSize,
                                                    getattr(prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf

    def _getProfileFromUser(self):
        """Return user Profile from datastore, creating new one if
        non-existent."""
        # TODO 2
        # step 1: make sure user is authed
        # uncomment the following lines:
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        p_key = ndb.Key(Profile, getUserId(user))
        profile = None
        # step 2: create a new Profile from logged in user data
        # you can use user.nickname() to get displayName
        # and user.email() to get mainEmail
        profile = p_key.get()
        if not profile:
            profile = Profile(
                key=p_key,
                displayName=user.nickname(),
                mainEmail=user.email(),
                teeShirtSize=str(TeeShirtSize.NOT_SPECIFIED),
            )
            profile.put()

        return profile      # return Profile

    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        prof = self._getProfileFromUser()

        # if saveProfile(), process user-modifyable fields
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
            prof.put()

        # return ProfileForm
        return self._copyProfileToForm(prof)

    @endpoints.method(message_types.VoidMessage, ProfileForm,
                      path='profile', http_method='GET', name='getProfile')
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()

    # TODO 1
    # 1. change request class
    # 2. pass request to _doProfile function
    @endpoints.method(ProfileMiniForm, ProfileForm,
                      path='profile', http_method='POST', name='saveProfile')
    def saveProfile(self, request):
        """Update & return user profile."""
        return self._doProfile(request)

# - - - Conference objects - - - - - - - - - - - - - - - - -

    def _copyConferenceToForm(self, conf, displayName):
        """Copy relevant fields from Conference to ConferenceForm."""
        cf = ConferenceForm()
        for field in cf.all_fields():
            if hasattr(conf, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('Date'):
                    setattr(cf, field.name, str(getattr(conf, field.name)))
                else:
                    setattr(cf, field.name, getattr(conf, field.name))
            elif field.name == "websafeKey":
                setattr(cf, field.name, conf.key.urlsafe())
        if displayName:
            setattr(cf, 'organizerDisplayName', displayName)
        cf.check_initialized()
        return cf

    def _createConferenceObject(self, request):
        """Create or update Conference object,
        returning ConferenceForm/request."""
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        if not request.name:
            raise endpoints.BadRequestException("Conference 'name'\
             field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        del data['websafeKey']
        del data['organizerDisplayName']

        # add default values for those missing (both data model &
        # outbound Message)
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])

        # convert dates from strings to Date objects; set month
        # based on start_date
        if data['startDate']:
            data['startDate'] = datetime.strptime(data['startDate'][:10],
                                                  "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(data['endDate'][:10],
                                                "%Y-%m-%d").date()

        # set seatsAvailable to be same as maxAttendees on creation
        # both for data model & outbound Message
        if data["maxAttendees"] > 0:
            data["seatsAvailable"] = data["maxAttendees"]
            setattr(request, "seatsAvailable", data["maxAttendees"])

        # make Profile Key from user ID
        p_key = ndb.Key(Profile, user_id)
        # allocate new Conference ID with Profile key as parent
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]
        # make Conference key from ID
        c_key = ndb.Key(Conference, c_id, parent=p_key)
        data['key'] = c_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # create Conference & return (modified) ConferenceForm
        Conference(**data).put()
        taskqueue.add(params={'email': user.email(),
                              'conferenceInfo': repr(request)},
                      url='/tasks/send_confirmation_email'
                      )

        return request

    @endpoints.method(ConferenceForm, ConferenceForm, path='conference',
                      http_method='POST', name='createConference')
    def createConference(self, request):
        """Create new conference."""
        return self._createConferenceObject(request)

    @endpoints.method(ConferenceQueryForms, ConferenceForms,
                      path='queryConferences',
                      http_method='POST',
                      name='queryConferences')
    def queryConferences(self, request):
        """Query for conferences."""
        conferences = self._getQuery(request)

        # return individual ConferenceForm object per Conference
        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, "")
                   for conf in conferences]
        )

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='getConferencesCreated',
                      http_method='POST', name='getConferencesCreated')
    def getConferencesCreated(self, request):
        """Return conferences created by user."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # make profile key
        p_key = ndb.Key(Profile, getUserId(user))
        # create ancestor query for this user
        conferences = Conference.query(ancestor=p_key)
        # get the user profile and display name
        prof = p_key.get()
        displayName = getattr(prof, 'displayName')

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, displayName)
                   for conf in conferences]
        )  # registers API

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='filterPlayground',
                      http_method='POST', name='filterPlayground')
    def filterPlayground(self, request):
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        q = Conference.query()
        # simple filter usage:
        # q = q.filter(Conference.city == "Paris")
        q = q.filter(Conference.city == "London")
        q = q.filter(Conference.topics == "Medical Innovations")
        q = q.order(Conference.name)
        q = q.filter(Conference.month == 12)

        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, "") for conf in q]
        )

    def _getQuery(self, request):
        """Return formatted query from the submitted filters."""
        q = Conference.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Conference.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Conference.name)

        for filtr in filters:
            if filtr["field"] in ["month", "maxAttendees"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(
                filtr["field"], filtr["operator"], filtr["value"])
            q = q.filter(formatted_query)
        return q

    def _formatFilters(self, filters):
        """Parse, check validity and format user supplied filters."""
        formatted_filters = []
        inequality_field = None

        for f in filters:
            filtr = {field.name: getattr(f, field.name)
                     for field in f.all_fields()}

            try:
                filtr["field"] = FIELDS[filtr["field"]]
                filtr["operator"] = OPERATORS[filtr["operator"]]
            except KeyError:
                raise endpoints.BadRequestException("Filter contains \
                    invalid field or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                # check if inequality operation has been used in previous
                # filters disallow the filter if inequality was performed
                # on a different field before
                # track the field on which the inequality operation
                # is performed
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException(
                        "Inequality filter is allowed on only one field.")
                else:
                    inequality_field = filtr["field"]

            formatted_filters.append(filtr)
        return (inequality_field, formatted_filters)

    @ndb.transactional(xg=True)
    def _conferenceRegistration(self, request, reg=True):
        """Register or unregister user for selected conference."""
        retval = None
        prof = self._getProfileFromUser()  # get user Profile

        # check if conf exists given websafeConfKey
        # get conference; check that it exists
        wsck = request.websafeConferenceKey
        conf = ndb.Key(urlsafe=wsck).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)

        # register
        if reg:
            # check if user already registered otherwise add
            if wsck in prof.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            # check if seats avail
            if conf.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

            # register user, take away one seat
            prof.conferenceKeysToAttend.append(wsck)
            conf.seatsAvailable -= 1
            retval = True

        # unregister
        else:
            # check if user already registered
            if wsck in prof.conferenceKeysToAttend:

                # unregister user, add back one seat
                prof.conferenceKeysToAttend.remove(wsck)
                conf.seatsAvailable += 1
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()
        conf.put()
        return BooleanMessage(data=retval)

    @endpoints.method(CONF_GET_REQUEST, ConferenceForm,
                      path='conference/{websafeConferenceKey}',
                      http_method='GET', name='getConference')
    def getConference(self, request):
        """Return requested conference (by websafeConferenceKey)."""
        # get Conference object from request; bail if not found
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' %
                request.websafeConferenceKey)
        prof = conf.key.parent().get()
        # return ConferenceForm
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/register/{websafeConferenceKey}',
                      http_method='POST', name='registerForConference')
    def registerForConference(self, request):
        """Register user for selected conference."""
        return self._conferenceRegistration(request)

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/unregister/{websafeConferenceKey}',
                      http_method='POST', name='unregisterFromConference')
    def unregisterFromConference(self, request):
        """Unregister user for selected conference."""
        return self._conferenceRegistration(request, False)

    # endpoint for getting all the conferences for which user has registered
    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='conferences/attending',
                      http_method='GET', name='getConferencesToAttend')
    def getConferencesToAttend(self, request):
        """Get list of conferences that user has registered for."""
        # TODO:

        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # step 1: get user profile
        # make profile key
        prof = self._getProfileFromUser()

        # step 2: get conferenceKeysToAttend from profile.
        conf_keys = [ndb.Key(urlsafe=wsck)
                     for wsck in prof.conferenceKeysToAttend]
        conferences = ndb.get_multi(conf_keys)

        # Do not fetch them one by one!

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(items=[self._copyConferenceToForm(conf, "")
                                      for conf in conferences]
                               )

    # adds the announcement to memcache if the available seats are less than or
    # equal to 5
    @staticmethod
    def _cacheAnnouncement():
        """Create Announcement & assign to memcache; used by
        memcache cron job & putAnnouncement().
        """
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        if confs:
            # If there are almost sold out conferences,
            # format announcement and set it in memcache
            announcement = '%s %s' % (
                'Last chance to attend! The following conferences '
                'are nearly sold out:',
                ', '.join(conf.name for conf in confs))
            memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
            # If there are no sold out conferences,
            # delete the memcache announcements entry
            announcement = ""
            memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

        return announcement

    # Gets announcement from memcache
    @endpoints.method(message_types.VoidMessage, StringMessage,
                      path='conference/announcement/get',
                      http_method='GET', name='getAnnouncement')
    def getAnnouncement(self, request):
        """Return Announcement from memcache."""
        # TODO 1
        # return an existing announcement from Memcache or an empty string.
        announcement = memcache.get(MEMCACHE_ANNOUNCEMENTS_KEY)
        return StringMessage(data=announcement)

# ---------------- Session Objects ----------------------

    def _copySessionToForm(self, session):
        """
        Input:
            session: Session object
        Returns:
            SessionForm
        Description:
            This method takes a session object with values defined from client
            side and returns the SessionFrom after copying the relevant fields in
            it which can be returned to client as ProRPC Message.
        """
        sessionform = SessionForm()
        for field in sessionform.all_fields():
            if hasattr(session, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('date'):
                    setattr(sessionform, field.name,
                            str(getattr(session, field.name)))
                else:
                    setattr(sessionform, field.name,
                            getattr(session, field.name))
            # Checks if the field is websafeSessionKey, then converts it into
            # urlsafe key
            elif field.name == "websafeSessionKey":
                setattr(sessionform, field.name, session.key.urlsafe())

        sessionform.check_initialized()
        return sessionform


    def _createSessionObject(self, request):
        """
        Input:
            request: Takes a request object to parse the data recieved from client
        Returns:
            Returns the SessionForm object
        Description:
            Retrieves information from request object and uses the information to
            add new session. uses the websafeConferenceKey passed from client to
            to add this session as child entity of that conference. After adding
            the session, it adds a message to memcache which states featured speaker
            and his/her session names if the speaker appears in more than one
            sessions
        """
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        if not request.name:
            raise endpoints.BadRequestException("Session 'name' \
                field required")


        #
        # conferences = Conference.query(ancestor=p_key)
        # conferences = conferences.filter()

        conf_key = ndb.Key(urlsafe=request.websafeConferenceKey)
        conf = conf_key.get()

        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' %
                request.websafeConferenceKey)

        # Get logged in user's profile key
        p_key = ndb.Key(Profile, user_id)

        # Get conference's parent profile
        prof = conf.key.parent().get()

        # convert to urlsafe
        usafep1 = prof.key.urlsafe()
        usafep2 = p_key.urlsafe()

        # Check if user is the one who added the conference. Otherwise throw
        # unauthorized exception because only those users who added conferences
        # can add sessions to those conferences
        if usafep1 != usafep2:
            raise endpoints.UnauthorizedException('User is not authorized to '\
            + 'add new session to this conference as he/she is not the '\
            + 'creator of this conference.')

        speaker_key = ndb.Key(urlsafe=request.websafeSpeakerKey)
        speaker = speaker_key.get()
        if not speaker:
            raise endpoints.NotFoundException(
                'No speaker found with key: %s' % request.websafeSpeakerKey)

        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        del data['websafeSessionKey']
        del data['websafeConferenceKey']

        if data['date']:
            data['date'] = datetime.strptime(data['date'][:10],
                                             "%Y-%m-%d").date()

        s_id = Session.allocate_ids(size=1, parent=conf_key)[0]

        s_key = ndb.Key(Session, s_id, parent=conf_key)
        data['key'] = s_key

        # create Conference & return (modified) ConferenceForm
        Session(**data).put()
        taskqueue.add(params={'email': user.email(),
                              'sessionInfo': repr(request)},
                      url='/tasks/send_session_confirmation_email'
                      )

        taskqueue.add(params={'websafeConferenceKey': \
                                request.websafeConferenceKey,
                              'websafeSpeakerKey': request.websafeSpeakerKey,
                              'speaker': speaker.name},
                      url='/tasks/set_featured_speaker'
                      )

        # Return data as SessionForm. Cannot use self._copySessionToForm as
        # that method implementation looks for session object instead data dict
        # and changing the implementation of that method affects the query
        # endpoints
        sessionform = SessionForm()

        for field in sessionform.all_fields():
            if data.has_key(field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('date'):
                    setattr(sessionform, field.name,
                            str(data[field.name]))
                else:
                    setattr(sessionform, field.name,
                            data[field.name])
            # Checks if the field is websafeSessionKey, then converts it into
            # urlsafe key
            elif field.name == "websafeSessionKey":
                setattr(sessionform, field.name, data['key'].urlsafe())

        sessionform.check_initialized()
        return sessionform


    @staticmethod
    def _setFeaturedSpeaker(self, websafeConferenceKey,
        websafeSpeakerKey, speaker):
        """
        Input: websafeConferenceKey, websafeSpeakerKey, speaker
        Returns: Doesn't return anything
        Description: this method checks if the speaker has more than one sessions,
        within the same conference and adds a message in memcache mentioning the
        speaker name as featured speaker and session names he/she is delivering.

        NOTE: This method is being executed using taskqueue from
        SetFeaturedSpeakerHandler() in main.py
        """
        # ---------  add featured speaker to memcache -----------

        conf_key = ndb.Key(urlsafe=websafeConferenceKey)
        # Gets all the sessions for current Conference
        sessions = Session.query(ancestor=conf_key)
        # Filters the returned sessions based on speaker
        sessions = sessions.filter(Session.websafeSpeakerKey ==
                                   websafeSpeakerKey)
        sessions = sessions.fetch()

        # Checks if the more than one sessions were returned for current
        # speaker
        if len(sessions) > 1:
            featuredSpeakerMessage = speaker + " is featured speaker " + \
                "and he will be delivering talk in following sessions. "
            sessionsCSV = ""
            # building a comma separated list of session names where featured
            # speaker is speaking
            for session in sessions:
                sessionsCSV += session.name + ", "

            featuredSpeakerMessage = featuredSpeakerMessage + \
                sessionsCSV[:-2] + "."

            memcache.set(MEMCACHE_FEATURED_SPEAKER_KEY, featuredSpeakerMessage)


    def _getFeaturedSpeaker(self):
        """
        It retrieves the featured speaker and the session names from memcache
        """
        return memcache.get(MEMCACHE_FEATURED_SPEAKER_KEY)


    @endpoints.method(message_types.VoidMessage, StringMessage,
                      path='getfeaturedspeaker',
                      http_method='GET', name='getFeaturedSpeaker')
    def getFeaturedSpeaker(self, request):
        """
        getFeaturedSpeaker endpoint recieves the calls from client to get the
        featured speaker information from memcache

        Input: It doesn't require any input parameters
        Returns: String message about featured speaker and his/her sessions
        """
        featuredSpeaker = memcache.get(MEMCACHE_FEATURED_SPEAKER_KEY)
        return StringMessage(data=featuredSpeaker or "No Featured Speaker")

    def _getConferenceSessions(self, request):
        """
        Description: Retrieves all the sessions in a conference and returns as
        SessionForms object
        """
        conf_key = ndb.Key(urlsafe=request.websafeConferenceKey)
        sessions = Session.query(ancestor=conf_key)
        return SessionForms(
            sessions=[self._copySessionToForm(session)
                      for session in sessions]
        )

    def _getConferenceSessionsByType(self, request):
        """
        Input: request contains
            typeOfSession: parameter for filtering based on type
            websafeConferenceKey: parameter for filitering conference on key
        Retrieves all the sessions in a conference filtered by type and
        Returns as SessionForms object
        """
        conf_key = ndb.Key(urlsafe=request.websafeConferenceKey)
        # First filter the sessions on parent conference based
        # websafeConferenceKey provided by client
        sessions = Session.query(ancestor=conf_key)

        # Filter resulting sessions by typeOfSession
        sessions = sessions.filter(Session.typeOfSession ==
                                   request.typeOfSession)
        return SessionForms(
            sessions=[self._copySessionToForm(session)
                      for session in sessions]
        )


    def _getConferenceSessionsBySpeaker(self, request):
        """
        Input: websafeSpeakerKey is passed as parameter for filtering
        Retrieves all the sessions filtered by speaker
        Returns as SessionForms object
        """
        sessions = Session.query()

        # Filters based on websafeSpeakerKey
        sessions = sessions.filter(Session.websafeSpeakerKey ==
                                   request.websafeSpeakerKey)
        return SessionForms(
            sessions=[self._copySessionToForm(session)
                      for session in sessions]
        )

    @endpoints.method(SessionForm, SessionForm, path='session',
                      http_method='POST', name='createSession')
    def createSession(self, request):
        """
        Creates a new session using conference as parent entity and speaker's
        websafeKey as attribute along with other attributes like name,
        startTime, duration, highilghts etc.
        Input: name, duration, highlights, startTime, date
        Returns: SessionForm object

        NOTE: startTime takes integer value in military hours notation
        e.g. 1705
        """
        return self._createSessionObject(request)


    @endpoints.method(ConferenceSessionQueryForm,
                      SessionForms, path='session/conference',
                      http_method='POST', name='queryConferenceSessions')
    def getConferenceSessions(self, request):
        """
        getConferenceSessions endpoint: calls _getConferenceSessions method,
        websafeConferenceKey is passed from the client as
        ConferenceSessionQueryForm
        """
        return self._getConferenceSessions(request)


    @endpoints.method(ConferenceSessionTypeSessionQueryForm,
                      SessionForms, path='session/conference/sessionType',
                      http_method='POST', name='getConferenceSessionsByType')
    def getConferenceSessionsByType(self, request):
        """
        getConferenceSessionsByType endpoint: Retrieves sessions based on
        type from a conference
        websafeConferenceKey and typeOfSession is passed from the client
        """
        return self._getConferenceSessionsByType(request)


    @endpoints.method(SpeakerSessionQueryForm, SessionForms,
                      path='session/speaker',
                      http_method='POST', name='getSessionsBySpeaker')
    def getSessionsBySpeaker(self, request):
        """
        getSessionsBySpeaker endpoint: Retrieves sessions based on speaker
        websafeSpeakerKey is passed from the client
        """
        return self._getConferenceSessionsBySpeaker(request)

# ---------------- Additional Queries ------------ #

    @endpoints.method(SessionStartTimeDurationQueryForm, SessionForms,
                      path='session/starttime/duration',
                      http_method='POST',
                      name='getSessionsByStartTimeAndDuration')
    def getSessionsByStartTimeAndDuration(self, request):
        """
        getSessionsByStartTimeAndDuration endpoint: Gets the sessions
        filtered by startTime and duration. Checks if the session starts at
        or after the time provided by client and has required duration

        startTime and duration are passed from the client
        returns SessionForms object containing resulting sessions
        """
        return self._getSessionsByStartTimeAndDuration(request)


    def _getSessionsByStartTimeAndDuration(self, request):
        """
        Queries the sessions and filters based on the startTime and duration
        provided by client. Checks for the sessions which start at or after the
        time provided by client and have requested duration.
        Returns SessionForms object with resulting sessions
        """
        sessions = Session.query()
        # Filtering with "greater than or equal to" inequality
        sessions = sessions.filter(Session.startTime >= request.startTime)

        # Filtering further based on matching duration
        sessions = sessions.filter(Session.duration == request.duration)
        return SessionForms(
            sessions=[self._copySessionToForm(session)
                      for session in sessions]
        )

    @endpoints.method(SessionMinStartTimeDurationHighlightsQueryForm,
                      SessionForms,
                      path='session/minstarttime/duration/highlights',
                      http_method='POST',
                      name='getSessionsByMinStartTimeDurationHighlights')
    def getSessionsByMinStartTimeDurationHighlights(self, request):
        """find sessions with min start time, duration and matching
            highlights."""
        return self._getSessionsByMinStartTimeDurationHighlights(request)


    def _getSessionsByMinStartTimeDurationHighlights(self, request):
        """
        Queries the sessions and filters based on the startTime, duration
        and highlights provided by client. Checks for the sessions which start
        at or after the time provided by client, have requested duration and
        highlights.
        Returns SessionForms object with resulting sessions
        """
        sessions = Session.query()
        sessions = sessions.filter(Session.startTime >= request.startTime)
        sessions = sessions.filter(Session.duration == request.duration)
        sessions = sessions.filter(Session.highlights == request.highlights)
        return SessionForms(
            sessions=[self._copySessionToForm(session)
                      for session in sessions]
        )


    @endpoints.method(SessionStartTimeQueryForm, SessionForms,
                      path='session/starttime',
                      http_method='POST', name='getSessionsByStartTime')
    def getSessionsByStartTime(self, request):
        """
        getSessionsByStartTime endpoint: Retrieves sessions based on startTime
        startTime is passed from the client
        """
        return self._getSessionsByStartTime(request)


    def _getSessionsByStartTime(self, request):
        """
        Queries the sessions and filters based on the startTime provided by
        client. Returns SessionForms object with resulting sessions
        """
        sessions = Session.query()
        sessions = sessions.filter(Session.startTime == request.startTime)
        return SessionForms(
            sessions=[self._copySessionToForm(session)
                      for session in sessions]
        )

    @endpoints.method(message_types.VoidMessage, SpeakerForm,
                      path='session/speakerwithmostsessions',
                      http_method='POST',
                      name='getSpeakerWithHighestNumberOfSessions')
    def getSpeakerWithHighestNumberOfSessions(self, request):
        """
        getSpeakerWithHighestNumberOfSessions endpoint: Gets all the
        sessions and their speakers websafe keys.
        """
        return self._getSpeakerWithHighestNumberOfSessions(request)

    def _getSpeakerWithHighestNumberOfSessions(self, request):
        """
        _getSpeakerWithHighestNumberOfSessions: gets all the sessions and their
        speakers websafe keys.
        Uses max() method to determine the highest occuring websafeSpeakerKey in
        resulting speaker keys and gets that speaker's information. Hence, the
        speaker with highest number of sessions
        """
        sessions = Session.query()
        websafeSpeakerKeys = [session.websafeSpeakerKey
                              for session in sessions]
        # Checks for highest count of websafeSpeakerKeys and retrieves that
        # speaker key
        speaker_key = ndb.Key(urlsafe=max(set(websafeSpeakerKeys),
                                          key=websafeSpeakerKeys.count))
        speaker = speaker_key.get()
        return self._copySpeakerToForm(speaker=speaker)

    @endpoints.method(ConferenceSessionTypeStartTimeQueryForm, SessionForms,
                      path='session/bytype/bystarttime',
                      http_method='POST',
                      name='querySessionByTypeAndStartTime')
    def querySessionByTypeAndStartTime(self, request):
        """
        querySessionByTypeAndStartTime solves the multiple inequality problem by
        first retrieving the sessions filtered by typeOfSession requested by
        client and then iterates through the results to check startTime which is
        lesser than the provided startTime
        Returns the resulting sessions in SessionForms
        """
        sessions = Session.query()
        # Filters session on typeOfSession
        sessions = sessions.filter(Session.typeOfSession !=
                                   request.typeOfSession)

        # Checks if each session has startTime lower than the provided
        # startTime
        sessionsBeforeTime = [session for session in sessions
                     if session.startTime < request.startTime]

        # return individual SessionForm object per Session
        return SessionForms(
            sessions=[self._copySessionToForm(session)
                      for session in sessionsBeforeTime]
        )

# ---------------- Speaker Objects ------------ #

    def _createSpeakerObject(self, request):
        """
        Creates a Speaker entity in datastore based on the information provided
        by client.
        Sends a confirmation email after adding the new Speaker
        """
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        if not request.name:
            raise endpoints.BadRequestException("Speaker 'name' \
                field required")

        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        del data['websafeSpeakerKey']

        # create Speaker & return (modified) SpeakerForm
        speaker_key = Speaker(**data).put()
        taskqueue.add(params={'email': user.email(),
                              'speakerInfo': repr(request)},
                      url='/tasks/send_speaker_confirmation_email'
                      )
        # Return data as SpeakerForm
        speakerform = SpeakerForm()

        for field in speakerform.all_fields():
            if data.has_key(field.name):
                setattr(speakerform, field.name,
                            data[field.name])
            # Checks if the field is websafeSpeakerKey, then converts it into
            # urlsafe key
            elif field.name == "websafeSpeakerKey":
                    setattr(speakerform, field.name, speaker_key.urlsafe())

        speakerform.check_initialized()
        return speakerform

    def _copySpeakerToForm(self, speaker):
        """Copy relevant fields from Speaker to SpeakerForm."""
        speakerform = SpeakerForm()
        for field in speakerform.all_fields():
            if hasattr(speaker, field.name):
                setattr(speakerform, field.name, getattr(speaker, field.name))
            elif field.name == "websafeSpeakerKey":
                setattr(speakerform, field.name, speaker.key.urlsafe())
        speakerform.check_initialized()
        return speakerform

    def _getSpeakers(self, request):
        """
        Returns all the speakers if no criteria is provided.
        It can take generic filters
        based on client provided field, operator, value
        format and return results based on that.
        Same as conferences filters
        """
        q = Speaker.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Speaker.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Speaker.name)

        for filtr in filters:
            formatted_query = ndb.query.FilterNode(
                filtr["field"], filtr["operator"], filtr["value"])
            q = q.filter(formatted_query)
        return q

    # endpoint for Creating Speaker
    @endpoints.method(SpeakerForm, SpeakerForm, path='speaker',
                      http_method='POST', name='createSpeaker')
    def createSpeaker(self, request):
        """
        Creates a new speaker
        Input: name, list of interests, organization
        Returns: name, list of interests, organization, websafeSpeakerKey
        """
        return self._createSpeakerObject(request)

    # endpoint for querying speakers
    @endpoints.method(QueryForms, SpeakerForms, path='querySpeakers',
                      http_method='POST', name='querySpeakers')
    def querySpeakers(self, request):
        """
        Queries Speakers, takes generic filters
        Input: Field, Operator, Value
        """
        speakers = self._getSpeakers(request)

        # return individual SpeakerForm object
        return SpeakerForms(
            speakers=[self._copySpeakerToForm(speaker)
                      for speaker in speakers]
        )


    @ndb.transactional(xg=True)
    def _updateSessionWishlist(self, request, reg=True):
        """
        It updates the wishlist attribute of the profile entity of user.
        Stores the session keys
        It adds the session in wishlist if the reg parameter is true, otherwise
        removes the session from wishlist
        This method is transactional so that in case of any failure, the partial
        changes are reverted
        """
        retval = None
        prof = self._getProfileFromUser()  # get user Profile

        # check if session exists given websafeSessionKey
        # get session; check that it exists
        wssk = request.websafeSessionKey
        session_key = ndb.Key(urlsafe=wssk)

        # Assure the websafe key is only for Session and raise exception if
        # key is provided for non Session kind
        if session_key.kind() != "Session":
            raise endpoints.NotFoundException(
                'wrong websafeSessionKey provided')

        session = session_key.get()
        if not session:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wssk)

        # add session to wishlist
        if reg:
            # check if user already has the session in wishlist, otherwise add
            if session_key in prof.sessionsWishList:
                raise ConflictException(
                    "This session is already in the wishlist")

            # register user, take away one seat
            prof.sessionsWishList.append(session_key)
            retval = True

        # remove session from wishlist
        else:
            # check if session is already in wishlist
            if session_key in prof.sessionsWishList:

                # remove session from wishlist
                prof.sessionsWishList.remove(session_key)
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()
        return BooleanMessage(data=retval)

    @endpoints.method(SESSION_GET_REQUEST, BooleanMessage,
                      path='session/addtowishlist/{websafeSessionKey}',
                      http_method='POST', name='addSessionToWishlist')

    def addSessionToWishlist(self, request):
        """
        endpoint for adding session to wishlist
        Input: Takes websafeSessionKey in querystring parameters
        Returns: True/False based on operation completion
        """
        return self._updateSessionWishlist(request)

    @endpoints.method(SESSION_GET_REQUEST, BooleanMessage,
                      path='session/deletefromwishlist/{websafeSessionKey}',
                      http_method='DELETE', name='deleteSessionInWishlist')

    def deleteSessionInWishlist(self, request):
        """
        endpoint for deleting session from wishlist
        Input: Takes websafeSessionKey in querystring parameters
        Returns: True/False based on operation completion
        """
        return self._updateSessionWishlist(request, False)

    @endpoints.method(message_types.VoidMessage, SessionForms,
                      path='session/wishlist',
                      http_method='GET', name='getSessionsInWishlist')
    def getSessionsInWishlist(self, request):
        """
        Get list of sessions that user has added to wishlist
        """

        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get user profile & make profile key
        prof = self._getProfileFromUser()

        # get sessionsWishList from profile.
        sessions = ndb.get_multi(prof.sessionsWishList)

        # return set of SessionForm objects per Session
        return SessionForms(sessions=[self._copySessionToForm(session)
                                      for session in sessions])

api = endpoints.api_server([ConferenceApi])
