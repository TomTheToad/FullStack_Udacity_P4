#!/usr/bin/env python
import webapp2
from google.appengine.api import app_identity
from google.appengine.api import mail
from conference import ConferenceApi


class SetAnnouncementHandler(webapp2.RequestHandler):
    def get(self):
        """Set Announcement in Memcache."""
        ConferenceApi._cacheAnnouncement()

class SetFeaturedSpeakerHandler(webapp2.RequestHandler):
    def post(self):
        """Set Featured Speaker in Memcache."""

        # ConferenceApi._setFeaturedSpeaker()

        C_API = ConferenceApi()
        featured_speaker = self.request.get('speaker')

        C_API._setFeaturedSpeaker(featured_speaker)

class SendConfirmationEmailHandler(webapp2.RequestHandler):
    def post(self):
        """Send email confirming Conference creation."""
        mail.send_mail(
            'noreply@%s.appspotmail.com' % (
                app_identity.get_application_id()),     # from
            self.request.get('email'),                  # to
            'You created a new Conference!',            # subj
            'Hi, you have created a following '         # body
            'conference:\r\n\r\n%s' % self.request.get(
                'conferenceInfo')
        )


app = webapp2.WSGIApplication([
    ('/crons/set_announcement', SetAnnouncementHandler),
    ('/tasks/set_featured_speaker', SetFeaturedSpeakerHandler),
    ('/tasks/send_confirmation_email', SendConfirmationEmailHandler),
    ], debug=True)
