#!/usr/bin/env python
import webapp2
from google.appengine.api import app_identity
from google.appengine.api import mail
from conference import ConferenceApi

from google.appengine.api import app_identity
from google.appengine.api import mail

# Sends confirmation email for Conference addition


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

# Sends confirmation email for new Session


class SendSessionConfirmationEmailHandler(webapp2.RequestHandler):

    def post(self):
        """Send email confirming Conference creation."""
        mail.send_mail(
            'noreply@%s.appspotmail.com' % (
                app_identity.get_application_id()),     # from
            self.request.get('email'),                  # to
            'You created a new Session!',            # subj
            'Hi, you have created a following '         # body
            'session:\r\n\r\n%s' % self.request.get(
                'sessionInfo')
        )

# Sends confirmation email for new speaker


class SendSpeakerConfirmationEmailHandler(webapp2.RequestHandler):

    def post(self):
        """Send email confirming Conference creation."""
        mail.send_mail(
            'noreply@%s.appspotmail.com' % (
                app_identity.get_application_id()),     # from
            self.request.get('email'),                  # to
            'You added a new Speaker!',            # subj
            'Hi, you have add the following '         # body
            'speaker:\r\n\r\n%s' % self.request.get(
                'speakerInfo')
        )

# Sets memcache entry for announcement


class SetAnnouncementHandler(webapp2.RequestHandler):

    def get(self):
        """Set Announcement in Memcache."""
        # TODO 1
        # use _cacheAnnouncement() to set announcement in Memcache
        ConferenceApi._cacheAnnouncement()

app = webapp2.WSGIApplication([
    ('/crons/set_announcement', SetAnnouncementHandler),
    ('/tasks/send_confirmation_email', SendConfirmationEmailHandler),
    ('/tasks/send_session_confirmation_email',
        SendSessionConfirmationEmailHandler),
    ('/tasks/send_speaker_confirmation_email',
        SendSpeakerConfirmationEmailHandler),
], debug=True)
