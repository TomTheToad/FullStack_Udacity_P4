#!/usr/bin/env python

"""
conference.py -- Udacity conference server-side Python App Engine API;
    uses Google Cloud Endpoints

$Id: conference.py,v 1.25 2014/05/24 23:42:19 wesc Exp wesc $

created by wesc on 2014 apr 21

"""

from datetime import datetime
import time

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import ConflictException
from models import Profile, ProfileMiniForm, ProfileForm
from models import BooleanMessage
from models import Conference, ConferenceForm, ConferenceForms,\
    ConferenceQueryForms

from models import TeeShirtSize
from models import StringMessage
from models import SessionForm, Session, SessionQueryForm, \
    SessionTypeEnum, SessionForms, SessionsQueryTypeAndTime

from models import Wishlist, WishlistForm, WishlistFormName
from models import Review, ReviewForm, ReviewForms, ReviewQueryForm, ReviewEnum

from utils import getUserId
from settings import WEB_CLIENT_ID

# Author declaration line moved for pep8 compliance
__author__ = 'wesc+api@google.com (Wesley Chun)'

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID
MEMCACHE_ANNOUNCEMENTS_KEY = "RECENT_ANNOUNCEMENTS"


##################
# """ FIELDS """ #
##############################################################################

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
            }

CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

CONF_POST_REQUEST = endpoints.ResourceContainer(
    ConferenceForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_POST_REQUEST = endpoints.ResourceContainer(
    SessionForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_POST_REQUEST_TYPE_TIME = endpoints.ResourceContainer(
    SessionsQueryTypeAndTime,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_POST_QUERY_REQUEST = endpoints.ResourceContainer(
    SessionQueryForm,
    websafeConferenceKey=messages.StringField(1),
)

##########################
# """ CONFERENCE API """ #
##############################################################################


@endpoints.api(name='conference', version='v1',
               allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID],
               scopes=[EMAIL_SCOPE])
class ConferenceApi(remote.Service):
    """Conference API v0.1"""

##############################
# """ CONFERENCE METHODS """ #
##############################################################################

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
            raise endpoints.BadRequestException(
                "Conference 'name' field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        del data['websafeKey']
        del data['organizerDisplayName']

        # add default values for those missing
        # (both data model & outbound Message)
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])

        # convert dates from strings to Date objects;
        # set month based on start_date
        if data['startDate']:
            data['startDate'] = datetime.strptime(
                data['startDate'][:10], "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(
                data['endDate'][:10], "%Y-%m-%d").date()

        # set seatsAvailable to be same as maxAttendees on creation
        if data["maxAttendees"] > 0:
            data["seatsAvailable"] = data["maxAttendees"]
        # generate Profile Key based on user ID and Conference
        # ID based on Profile key get Conference key from ID
        p_key = ndb.Key(Profile, user_id)
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]
        c_key = ndb.Key(Conference, c_id, parent=p_key)
        data['key'] = c_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # create Conference, send email to organizer confirming
        # creation of Conference & return (modified) ConferenceForm
        Conference(**data).put()
        taskqueue.add(params={'email': user.email(),
                              'conferenceInfo': repr(request)},
                      url='/tasks/send_confirmation_email')

        return request

    # Retrieves a single conference query item
    # takes variable websafeConferenceKey
    def _getConferenceByKey(self, websafeConferenceKey):
        conference = ndb.Key(urlsafe=websafeConferenceKey).get()
        return conference

    @ndb.transactional()
    def _updateConferenceObject(self, request):
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}

        # update existing conference
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' %
                request.websafeConferenceKey)

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the conference.')

        # Not getting all the fields, so don't create a new object; just
        # copy relevant fields from ConferenceForm to Conference object
        for field in request.all_fields():
            data = getattr(request, field.name)
            # only copy fields where we get data
            if data not in (None, []):
                # special handling for dates (convert string to Date)
                if field.name in ('startDate', 'endDate'):
                    data = datetime.strptime(data, "%Y-%m-%d").date()
                    if field.name == 'startDate':
                        conf.month = data.month
                # write to Conference object
                setattr(conf, field.name, data)
        conf.put()
        prof = ndb.Key(Profile, user_id).get()
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(ConferenceForm, ConferenceForm, path='conference/create',
                      http_method='POST', name='createConference')
    def createConference(self, request):
        """Create new conference."""
        return self._createConferenceObject(request)

    @endpoints.method(CONF_GET_REQUEST, ConferenceForm,
                      path='conference/get/{websafeConferenceKey}',
                      http_method='GET', name='getConference')
    def getConference(self, request):
        """Return requested conference (by websafeConferenceKey)."""
        # get Conference object from request; bail if not found
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s'
                % request.websafeConferenceKey)
        prof = conf.key.parent().get()
        # return ConferenceForm
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='conference/get/created',
                      http_method='POST', name='getConferencesCreated')
    def getConferencesCreated(self, request):
        """Return conferences created by user."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)
        # create ancestor query for all key matches for this user
        confs = Conference.query(ancestor=ndb.Key(Profile, user_id))
        prof = ndb.Key(Profile, user_id).get()
        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[self._copyConferenceToForm(
                conf, getattr(prof, 'displayName')) for conf in confs]
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
                raise endpoints.BadRequestException(
                    "Filter contains invalid field or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                # check if inequality operation has been used in
                # previous filters
                # disallow the filter if inequality was performed
                # on a different field before
                # track the field on which the inequality
                # operation is performed
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException(
                        "Inequality filter is allowed on only one field.")
                else:
                    inequality_field = filtr["field"]

            formatted_filters.append(filtr)
        return (inequality_field, formatted_filters)

    @endpoints.method(ConferenceQueryForms, ConferenceForms,
                      path='conference/query',
                      http_method='POST',
                      name='queryConferences')
    def queryConferences(self, request):
        """Query for conferences."""
        conferences = self._getQuery(request)

        # need to fetch organiser displayName from profiles
        # get all keys and use get_multi for speed
        organisers = [(ndb.Key(Profile, conf.organizerUserId))
                      for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return individual ConferenceForm object per Conference
        return ConferenceForms(
                items=[self._copyConferenceToForm(
                    conf, names[conf.organizerUserId])
                       for conf in conferences])

#############################
# """ WISH LIST METHODS """ #
##############################################################################

    # Create a wishlist for the current logged in user
    def _makeWishlist(self):
        user = self._getProfileFromUser()
        parent_key = user.key

        new_wish_list = Wishlist(parent=parent_key)
        # set user_id (mainEmail) for ease of query
        new_wish_list.userId = user.mainEmail

        # set wish list as child of current profile
        new_wish_list.put()

    # Return to current user's id
    def _getCurrentUserID(self):
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)
        return user_id

    # Adds a session key to the logged in user's wishlist
    # requires session_key
    def _addSessionToWishlist(self, session_key):
        user_id = self._getCurrentUserID()

        key = ndb.Key(Profile, user_id).get()
        wish_list = Wishlist.query(ancestor=key.key).get()
        if wish_list and wish_list.sessionKeys:
            wish_list.sessionKeys.append(session_key)
        else:
            wish_list.sessionKeys = [session_key]
        wish_list.put()

    # Looks up a model session key given a urlsafe key
    # takes websafeConferenceKey
    def _convertSessionWebsafeKey(self, websafeConferenceKey):
        session = ndb.Key(urlsafe=websafeConferenceKey).get()
        return session.key

    # Finds a session key by session name and calls
    # _addSessionToWishList to add key
    # Requires session name
    def _addSessionToWishListByName(self, session_name):
        session = self._getSessionByName(session_name=session_name)
        self._addSessionToWishlist(session_key=session.key)

    # Retrieves logged in user's wishlist
    # Returns one or more session forms
    def _getSessionsInWishlist(self):
        user_id = self._getCurrentUserID()
        wishlist = Wishlist.query(ancestor=ndb.Key(Profile, user_id)).get()

        forms = SessionForms()

        for key in wishlist.sessionKeys:
            query = Session.query(Session.key == key).get()
            forms.items += [self._copySessionToForm(session=query)]

        return forms

    @endpoints.method(WishlistForm, StringMessage,
                      path='conference/session/wishlist/add',
                      http_method='Post',
                      name='addSessionToWishlist')
    def addSessionToWishlist(self, request):
        """Add a Session to wishlist by session key"""

        session_key = request.websafeSessionKey

        # Convert websafeConferenceKey to datastore id
        session_key = self._convertSessionWebsafeKey(
            session_key)

        self._addSessionToWishlist(session_key=session_key)
        msg = "Session added to your wish list."
        return StringMessage(data=msg)

    @endpoints.method(WishlistFormName, StringMessage,
                      path='conference/session/wishlist/add_by_name',
                      http_method='Post',
                      name='addSessionToWishlistByName')
    def addSessionToWishlistByName(self, request):
        """Add session to wish list by session name"""
        self._addSessionToWishListByName(session_name=request.sessionName)
        msg = "Session added to your wish list."
        return StringMessage(data=msg)

    @endpoints.method(message_types.VoidMessage, SessionForms,
                      path='conference/session/wishlist/get',
                      http_method='GET',
                      name='getSessionsInWishlist')
    def getSessionsInWishlist(self, request):
        """Get Session from current user wishlist"""
        return self._getSessionsInWishlist()

###########################
# """ SESSION METHODS """ #
##############################################################################

    # Convert String to associated SessionType Enum from all possible enums
    #   NOT_SPECIFIED = 1, workshop = 2,
    # lecture = 3, demonstration = 4, party = 5
    def _convertStringToSessionType(self, string_field):

        # todo: Finalize generic field loop
        # enum_list = list(map(str(SessionTypeEnum)))
        # for enum in SessionTypeEnum:
        #     print "ENUM = " + str(enum)
        #
        #     if string_field == str(enum):
        #         output = enum
        #     else:
        #         output = SessionTypeEnum.NOT_SPECIFIED

        if string_field == 'workshop':
            output = SessionTypeEnum.workshop
        elif string_field == 'lecture':
            output = SessionTypeEnum.lecture
        elif string_field == 'demonstration':
            output = SessionTypeEnum.demonstration
        elif string_field == 'party':
            output = SessionTypeEnum.party
        else:
            output = SessionTypeEnum.NOT_SPECIFIED
        return output

    # Copies relevant session information to form for return
    # Takes session query
    # Returns form
    def _copySessionToForm(self, session):
        """Copy relevant fields from Session to SessionForm."""
        session_form = SessionForm()
        for field in session_form.all_fields():
            if field.name == 'sessionType':
                value = self._convertStringToSessionType(
                    string_field=getattr(session, field.name))
                setattr(session_form, field.name, value)
            elif field.name == 'websafeKey':
                setattr(session_form, field.name, session.key.urlsafe())
            elif field.name == 'date' or field.name == 'startTime':
                setattr(session_form, field.name,
                        str(getattr(session, field.name)))
            else:
                setattr(session_form, field.name,
                        getattr(session, field.name))

        return session_form

    # Sends query with possible multiple sessions to _copySessionToForm
    # Returns list of forms
    def _copyMultipleSessionsToForm(self, query):
            session_forms = SessionForms(
                items=[self._copySessionToForm(session=session)
                       for session in query])
            return session_forms

    # Returns single conference query, get by name
    # Takes conference name
    def _getConferenceByName(self, conferenceName):
        try:
            conference = Conference.query(
                Conference.name == conferenceName).get()
            return conference
        except:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % conferenceName)

    # Returns all Sessions by speaker in forms format
    # Takes speaker name
    def _getSessionBySpeaker(self, speaker):
        try:
            query_sessions = Session.query(
                Session.speakerDisplayName == speaker
            )
            return self._copyMultipleSessionsToForm(query=query_sessions)
        except:
            raise endpoints.NotFoundException(
                'No sessions found with speaker: %s' % speaker)

    # Returns number of sessions by speaker
    # Takes speaker name
    def _getNumberOfConferenceSessionBySpeaker(
            self, speaker, websafeConferenceKey):
        try:
            query_session = Session.query(
                ancestor=ndb.Key(urlsafe=websafeConferenceKey))
            query_session.filter(Session.speakerDisplayName == speaker)
            return query_session.count
        except:
            raise endpoints.NotFoundException(
                'No sessions found with speaker: %s' % speaker)

    # Returns all sessions by type
    # Takes type of session and websafeConferenceKey
    # Modified to require websafeConferenceKey
    def _getConferenceSessionByType(
            self, websafeConferenceKey, type_of_session):
        try:
            conference = self._getConferenceByKey(websafeConferenceKey)
            sessions = Session.query(ancestor=conference.key)
            results = sessions.filter(Session.sessionType == type_of_session)
            return self._copyMultipleSessionsToForm(query=results)

        except:
            raise endpoints.NotFoundException(
                'No sessions found of type: %s' % type_of_session)

    # Returns all session associated with a conference
    # Takes conference name or websafeConferenceKey
    def _getConferenceSessionsByName(self, conferenceName):
        try:
            conference = self._getConferenceByName(conferenceName)
            query_sessions = Session.query(
                Session.conferenceName == conference.name)
            return self._copyMultipleSessionsToForm(query=query_sessions)
        except:
            raise endpoints.NotFoundException(
                'No sessions found')

    # Returns all session associated with a conference
    # Takes conference name or websafeConferenceKey
    def _getConferenceSessionsByKey(self, websafeConferenceKey):
        try:
            query_sessions = Session.query(
                ancestor=ndb.Key(urlsafe=websafeConferenceKey))
            return self._copyMultipleSessionsToForm(query=query_sessions)
        except:
            raise endpoints.NotFoundException(
                'No sessions found')

    # Returns a session key
    # Requires name of session (session_name)
    # Returns associated key
    def _getSessionByName(self, session_name):
        query_session = Session.query(Session.name == session_name)
        result = query_session.fetch(limit=1)
        return result[0]

    # Verifies speaker is registered. Speakers have a profile and
    # are identified by Google display name
    def _checkSpeakerProfile(self, displayName):
        try:
            speaker = Profile.query(Profile.displayName == displayName).get()
            return True
        except:
            print "No one with displayName: {} has been registered".format(
                displayName)
            raise endpoints.NotFoundException(
                'No Profile found with key: %s' % displayName)

    # Check if current user is logged in
    def _checkLoggedIn(self):
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        return user

    # Check to see if the current user is entity owner
    def _checkOwner(self, owner):

        user = self._checkLoggedIn()
        user_email = user.email()

        if user_email != owner:
            raise endpoints.ForbiddenException(
                'Only the conference owner can add sessions.')

    # Convert the date key in a data field to datetime
    # Takes data
    # Returns the data field with altered key
    def _convertDateKey(self, data):
        if data['date']:
            data['date'] = datetime.strptime(
                data['date'][:10], "%Y-%m-%d").date()

        return data

    # todo: bug: date still showing in dbase
    # Converts string time in key 'startTime to datetime.time()
    # Takes data
    # Returns data with altered key
    def _convertTime(self, data):
        if data['startTime']:
            data['startTime'] = datetime.strptime(
                data['startTime'], '%H:%M').time()

        return data

    # Delete websafe key in data fields
    # Returns data field without websafekey
    def _dropWebsafeKey(self, data):
        # del data['websafeKey']
        if data['websafeConferenceKey']:
            del data['websafeConferenceKey']
        return data

    # Convert enum session type to enum in data
    # Returns data
    def _convertSessionType(self, data):
        if data['sessionType']:
            data['sessionType'] = str(data['sessionType'])
        return data

    # Convert enum in data field review to string
    # Returns data
    def _convertReview(self, data):
        if data['review']:
            data['review'] = str(data['review'])
        return data

    # Automates formatting of data fields with above methods
    # Returns altered data
    def _cleanData(self, data):
        convertDate = self._convertDateKey(data=data)
        dropWebsafeKey = self._dropWebsafeKey(data=convertDate)
        convertSessionType = self._convertSessionType(data=dropWebsafeKey)
        convertTime = self._convertTime(data=convertSessionType)

        return convertTime

    # requires conference id, speaker id, conferenceName, and sessionType
    # speaker id = profile id
    # An attendee can also be a speaker
    def _createSessionObject(self, request):

        # Check to see if user is logged in
        self._checkLoggedIn()

        # Check to see if minimum, necessary information
        # has been supplied in request
        if not request.name:
            raise endpoints.BadRequestException(
                "Conference session 'name' field required")
        if not request.speakerDisplayName:
            raise endpoints.BadRequestException(
                "Conference session 'speakerDisplayName' field required")
        if not request.sessionType:
            raise endpoints.BadRequestException(
                "Conference session 'sessionType' field required")

        # Check to make sure speaker has a profile: using displayName
        self._checkSpeakerProfile(displayName=request.speakerDisplayName)

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}

        # Retrieve Conference by websafeConferenceKey
        conference = self._getConferenceByKey(request.websafeConferenceKey)

        # clean up and translate date fields
        clean_data = self._cleanData(data=data)

        # Check for legal owner
        self._checkOwner(owner=conference.organizerUserId)

        # Get Parent Key
        parent_key = conference.key

        # Set session as child of user supplied conference
        # Associate data and put session object
        session = Session(parent=parent_key, **clean_data)
        session.put()

        # Update featured speaker key in memcache
        # Get the current speaker
        speaker = session.speakerDisplayName

        # Get the number of session hosted by current speaker
        number_sessions = self._getNumberOfConferenceSessionBySpeaker(
            speaker, request.websafeConferenceKey)

        # If number of sessions greater than one set featured speaker
        if number_sessions > 1:
            taskqueue.add(
                params={'speaker': speaker,
                        'websafeConferenceKey': request.websafeConferenceKey},
                url='/tasks/set_featured_speaker')

        return self._copySessionToForm(session=session)

    @endpoints.method(CONF_POST_REQUEST, ConferenceForm,
                      path='conference/update/{websafeConferenceKey}',
                      http_method='POST', name='updateConference')
    def updateConference(self, request):
        """Update conference w/provided fields & return w/updated info."""
        return self._updateConferenceObject(request)

    @endpoints.method(SESSION_POST_REQUEST, SessionForm,
                      path=('conference/session/create/'
                            '{websafeConferenceKey}'),
                      http_method='POST',
                      name='createSession')
    def createSession(self, request):
        """Create new session."""
        return self._createSessionObject(request=request)

    @endpoints.method(SESSION_GET_REQUEST, SessionForms,
                      path='conference/session/query/by_conference'
                           '/{websafeConferenceKey}',
                      http_method='GET',
                      name='getConferenceSessions')
    def getConferenceSessions(self, request):
        """Get sessions by conference web safe key."""
        return self._getConferenceSessionsByKey(
            websafeConferenceKey=request.websafeConferenceKey)

    @endpoints.method(SESSION_POST_QUERY_REQUEST, SessionForms,
                      path='conference/session/query/'
                           'by_type/{websafeConferenceKey}',
                      http_method='POST',
                      name='getConferenceSessionByType')
    def getConferenceSessionByType(self, request):
        """Get all session by type(lecture, workshop, demonstration, party."""
        return self._getConferenceSessionByType(
            type_of_session=request.query,
            websafeConferenceKey=request.websafeConferenceKey)

    @endpoints.method(SessionQueryForm, SessionForms,
                      path='conference/session/query/by_speaker',
                      http_method='POST',
                      name='getSessionsBySpeaker')
    def getSessionsBySpeaker(self, request):
        """Get all session by speaker display name."""
        return self._getSessionBySpeaker(speaker=request.query)

#############################
# """ TASK QUESTION 3.5 """ #
##############################################################################

    # Implementation from Task3, query related problem
    # This method assumes the user is looking for a session for a
    # particular conference
    # Takes arguments from request:
    # websafeConferenceKey, notThisSessionType,
    # sessionBeforeTime, sessionAfterTime
    def _getConferenceSessionsByTypeAndTimeA(
            self, request):

        not_this_session_type = request.notThisSessionType

        before_time = datetime.strptime(
            request.sessionBeforeTime, '%H:%M').time()
        after_time = datetime.strptime(
            request.sessionAfterTime, '%H:%M').time()

        sessions = Session.query(
            ancestor=ndb.Key(urlsafe=request.websafeConferenceKey))\
            .filter(Session.sessionType != not_this_session_type)

        sessions_filtered_by_times = []

        if iter(sessions):
            for session in sessions:
                if before_time > session.startTime > after_time:
                    sessions_filtered_by_times.append(session)
        else:
            if before_time > sessions.startTime > after_time:
                sessions_filtered_by_times = [sessions]

        return self._copyMultipleSessionsToForm(sessions_filtered_by_times)

    def _getConferenceSessionsByTypeAndTimeB(
            self, request):

        # Fields
        avoid_session_type = request.notThisSessionType
        before_time = datetime.strptime(
            request.sessionBeforeTime, '%H:%M').time()
        after_time = (datetime.strptime(
            request.sessionAfterTime, '%H:%M').time())
        acceptable_session_types = []

        # Get current enum types and convert to dictionary
        enum_types = SessionTypeEnum(1).to_dict()
        # Alt idea: del key from enum_types dict using protected method

        # Populate acceptable_session_type list with enum values
        # not equal to avoided type
        for item in enum_types:
            if item != avoid_session_type:
                acceptable_session_types.append(item)

        # Query Sessions by web safe conference key
        filter1 = Session.query(ancestor=ndb.Key(
            urlsafe=request.websafeConferenceKey))

        # filter by approved session types
        filter2 = filter1.filter(
            Session.sessionType.IN(acceptable_session_types))

        # filter sessions prior to before_time
        filter3 = filter2.filter(Session.startTime < before_time)

        # filter sessions after to after_time
        filter4 = filter3.filter(Session.startTime > after_time)

        return self._copyMultipleSessionsToForm(query=filter4)

    @endpoints.method(SESSION_POST_REQUEST_TYPE_TIME, SessionForms,
                      path='conference/session/query/'
                           'type_time_A/{websafeConferenceKey}',
                      http_method='POST',
                      name='getSessionByTypeAndTimeA')
    def getConferenceSessionsByTypeAndTimeA(self, request):
        """Task 3 solution A"""
        return self._getConferenceSessionsByTypeAndTimeA(request)

    @endpoints.method(SESSION_POST_REQUEST_TYPE_TIME, SessionForms,
                      path='conference/session/query/'
                           'type_time_B/{websafeConferenceKey}',
                      http_method='POST',
                      name='getSessionByTypeAndTimeB')
    def getConferenceSessionsByTypeAndTimeB(self, request):
        """Task 3 solution B"""
        return self._getConferenceSessionsByTypeAndTimeB(request)

###########################
# """ PROFILE METHODS """ #
##############################################################################

    def _copyProfileToForm(self, prof):
        """Copy relevant fields from Profile to ProfileForm."""
        # copy relevant fields from Profile to ProfileForm
        pf = ProfileForm()
        for field in pf.all_fields():
            if hasattr(prof, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr(pf, field.name, getattr(
                        TeeShirtSize, getattr(prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf

    def _getProfileFromUser(self):
        """Return user Profile from datastore,
        creating new one if non-existent."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get Profile from datastore
        user_id = getUserId(user)
        p_key = ndb.Key(Profile, user_id)
        profile = p_key.get()
        # create new Profile if not there
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
                      path='profile/get', http_method='GET', name='getProfile')
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()

    @endpoints.method(ProfileMiniForm, ProfileForm,
                      path='profile/save',
                      http_method='POST',
                      name='saveProfile')
    def saveProfile(self, request):
        """Update & return user profile."""
        self._makeWishlist()
        return self._doProfile(request)

########################
# """ REGISTRATION """ #
##############################################################################

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

    # todo: This supplied method is not working properly
    # error only when deployed to app spot, not local
    # appears to be an api change?
    # id_token verification failed
    # nonetype object has no attribute organizerUserId
    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='conference/attending/get',
                      http_method='GET', name='getConferencesToAttend')
    def getConferencesToAttend(self, request):
        """Get list of conferences that user has registered for."""
        prof = self._getProfileFromUser()  # get user Profile
        conf_keys = [ndb.Key(urlsafe=wsck) for wsck in
                     prof.conferenceKeysToAttend]
        conferences = ndb.get_multi(conf_keys)

        # get organizers
        organisers = [ndb.Key(Profile, conf.organizerUserId) for conf in
                      conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[self._copyConferenceToForm(
                conf, names[conf.organizerUserId]) for conf in conferences])

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/register/{websafeConferenceKey}',
                      http_method='POST', name='registerForConference')
    def registerForConference(self, request):
        """Register user for selected conference."""
        return self._conferenceRegistration(request)

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/unregister/{websafeConferenceKey}',
                      http_method='DELETE', name='unregisterFromConference')
    def unregisterFromConference(self, request):
        """Unregister user for selected conference."""
        return self._conferenceRegistration(request, reg=False)

#########################
# """ ANNOUNCEMENTS """ #
##############################################################################

    @staticmethod
    def _cacheAnnouncement():
        """Create Announcement & assign to memcache; used by
        memcache cron job & putAnnouncement().
        """
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        # Set MEMCACHE key to RECENT ANNOUNCEMENTS
        memcache_announcements_key = 'RECENT ANNOUNCEMENTS'

        if confs:
            # If there are almost sold out conferences,
            # format announcement and set it in memcache
            announcement = '%s %s' % (
                'Last chance to attend! The following conferences '
                'are nearly sold out:',
                ', '.join(conf.name for conf in confs))
            memcache.set(memcache_announcements_key, announcement)
        else:
            # If there are no sold out conferences,
            # delete the memcache announcements entry
            announcement = ""
            memcache.delete(memcache_announcements_key)

        return announcement

    @endpoints.method(message_types.VoidMessage, StringMessage,
                      path='conference/announcement/get',
                      http_method='GET', name='getAnnouncement')
    def getAnnouncement(self, request):
        """Return Announcement from memcache."""
        # return an existing announcement from Memcache or an empty string.
        memcache_announcement = memcache.get('RECENT ANNOUNCEMENTS')

        if memcache_announcement is not None:
            return StringMessage(data=memcache_announcement)
        else:
            announcement = ""
            return StringMessage(data=announcement)

##########################
# """ REVIEW METHODS """ #
##############################################################################

    # Takes a string_field for posted review
    # Returns associated enum
    def _convertToReviewType(self, string_field):

        if string_field == 'very_unsatisfied':
            enum = ReviewEnum.very_unsatisfied
        elif string_field == 'unsatisfied':
            enum = ReviewEnum.unsatisfied
        elif string_field == 'satisfied':
            enum = ReviewEnum.satisfied
        elif string_field == 'very_satisfied':
            enum = ReviewEnum.very_satisfied
        elif string_field == 'excellent':
            enum = ReviewEnum.excellent
        else:
            enum = ReviewEnum.NO_OPINION
        return enum

    # Takes a review and copies field to review form
    # Returns review form
    def _copyReviewToReviewForm(self, review):
        """Copy relevant fields from Review to ReviewForm."""
        review_form = ReviewForm()
        for field in review_form.all_fields():
            if field.name == 'review':
                value = self._convertToReviewType(
                    string_field=getattr(review, field.name))
                setattr(review_form, field.name, value)
            else:
                setattr(review_form, field.name, getattr(review, field.name))
        return review_form

    # Allows for copying multiple reviews to review form
    # Returns list of review forms
    def _copyMutipleReivewsToReviewForm(self, query):
        review_forms = ReviewForms(
            items=[self._copyReviewToReviewForm(
                review=review)for review in query])
        return review_forms

    @endpoints.method(ReviewForm, StringMessage,
                      path='session/review/post',
                      http_method='POST',
                      name='postReview')
    def postReview(self, request):
        """Post a review for a session"""
        self._checkLoggedIn()

        if not request.conference_name:
            raise endpoints.BadRequestException(
                "Conference session 'conference_name' field required")
        if not request.session_name:
            raise endpoints.BadRequestException(
                "Conference session 'name' field required")
        if not request.review:
            raise endpoints.BadRequestException(
                "Conference session 'review' review required")

        # Check to make sure conference exists and get for parent key
        parent = self._getSessionByName(session_name=request.session_name)

        # Get Parent key
        parent_key = parent.key

        # Check to make sure speaker has a profile: using displayName
        if request.speaker_name:
            self._checkSpeakerProfile(displayName=request.speaker_name)

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}

        # convert review to string for database put
        data = self._convertReview(data)

        # Set session as child of user supplied conference
        # Associate data and put session object
        review = Review(parent=parent_key, **data)
        review.put()

        msg = "Thank you for your feedback"

        return StringMessage(data=msg)

    @endpoints.method(ReviewQueryForm, ReviewForms,
                      path='session/review/query',
                      http_method='POST',
                      name='getReview')
    def getReview(self, request):
        """Get review for a session"""
        self._checkLoggedIn()

        reviews = Review.query(Review.session_name == request.session_name)

        return self._copyMutipleReivewsToReviewForm(query=reviews)

############################
# """ FEATURED SPEAKER """ #
##############################################################################

    # Sets a memcache key to speaker
    def _setFeaturedSpeaker(self, featured_speaker, websafeConferenceKey):

        # Set MEMCACHE key to FEATURED SPEAKER
        memcache_speaker_key = 'FEATURED SPEAKER'

        # Get Session Names associated with featured speaker
        sessions = Session.query(
            ancestor=(ndb.Key(urlsafe=websafeConferenceKey)))
        sessions.filter(Session.speakerDisplayName == featured_speaker)

        # Create message
        memcache_msg = "Our Featured speaker is " + str(featured_speaker) + \
                       ". sessions: "

        for session in sessions:
            memcache_msg += str(session.name) + ", "

        # Set memcache key
        memcache.set(memcache_speaker_key, memcache_msg)

    @endpoints.method(message_types.VoidMessage, StringMessage,
                      path='conference/featured_speaker/get',
                      http_method='GET',
                      name='getFeaturedSpeaker')
    def getFeaturedSpeaker(self, request):
        """Get featured speaker"""
        memcache_speaker = memcache.get('FEATURED SPEAKER')

        if memcache_speaker is not None:
            return StringMessage(data=memcache_speaker)
        else:
            msg = "Check back for our upcoming featured speaker!"
            return StringMessage(data=msg)

#############################
# """ Test ONLY methods """ #
##############################################################################

    # Method is for testing purposes only
    # Easy way to get generated url safe key for testing methods
    # Takes conference name
    # Returns generated websafe key
    @endpoints.method(SessionQueryForm, StringMessage,
                      path='query/get/WebsafeConferenceKey',
                      http_method='GET',
                      name='get_conference_key')
    def get_conference_key(self, request):
        """Retrieve websafe conference key for method testing purposes"""
        try:
            conference = Conference.query(
                Conference.name == request.query).get()
            msg = str(conference.key.urlsafe())
            return StringMessage(data=msg)
        except:
            raise endpoints.BadRequestException(
                "No conference with the name: {} has been found").format(
                request.query)

    # Method is for testing purposes only
    # Easy way to get generated url safe key for testing methods
    # Takes session name
    # Returns generated websafe key
    @endpoints.method(SessionQueryForm, StringMessage,
                      path='query/get/WebsafeSessionKey',
                      http_method='GET',
                      name='get_session_key')
    def get_session_key(self, request):
        """Retrieve websafe session key for method testing purposes"""
        try:
            session = Session.query(Session.name == request.query).get()
            msg = str(session.key.urlsafe())
            return StringMessage(data=msg)
        except:
            raise endpoints.BadRequestException(
                "No session with the name: {} has been found").format(
                request.query)

########################
# """ Register API """ #
##############################################################################

api = endpoints.api_server([ConferenceApi])  # register API
