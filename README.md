# ConferenceCentral
Application for Udacity Full Stack Nanodegree - Project 4

## Products
- [App Engine][1]

## Language
- [Python][2]

## APIs
- [Google Cloud Endpoints][3]

## AppEngine ID
[`fsnd-p4-conference-1153`][5]

## ConferenceCentral AppSpot URL
[`https://fsnd-p4-conference-1153.appspot.com`][4]

## EndPoints API Explorer URL for ConferenceCentral
[`https://fsnd-p4-conference-1153.appspot.com/_ah/api/explorer`][5]

## Whats Included?

* ConferenceCentral

  * static
    * Contains static resources like css, js, images, html partials etc.
  * templates
    * Contains index.html page which is rendered as template by python server
  * app.yaml
    * Configuration about application dependencies
  * cron.yaml
    * Configuration for cron jobs
  * index.yaml
    * The indexes information, generated automatically.
  * conference.py
    * All the endpoints for conference central app
  * main.py
    * The methods to handle email confirmations, announcements
  * models.py
    * Definitions of ProRPC Messages, classes for Datastore Entities
  * settings.py
    * Contains Client ID for appspot
  * utils.py
    * Handles utility methods like getting user information etc.

## Setup Instructions
1. Update the value of `application` in `app.yaml` to the app ID you
   have registered in the App Engine admin console and would like to use to host
   your instance of this sample.
1. Update the values at the top of `settings.py` to
   reflect the respective client IDs you have registered in the
   [Developer Console][6].
1. Update the value of CLIENT_ID in `static/js/app.js` to the Web client ID
1. (Optional) Mark the configuration files as unchanged as follows:
   `$ git update-index --assume-unchanged app.yaml settings.py static/js/app.js`
1. Run the app with the devserver using `dev_appserver.py DIR`, and ensure it's running by visiting
   your local server's address (by default [localhost:8080][7].)
1. Generate your client library(ies) with [the endpoints tool][8].
1. Deploy your application.

## Task 1 Explanation
### Entities Defined for Task 1
These entities are added to models.py

* #### Session
Session is defined as a child entity of conference. It has further information about its name, speaker, highlights, start time, duration and date.
It is made child entity of conference because it will be easy to retrieve all the sessions for a conference.

* #### Speaker
Speaker entity is defined with its properties as name, interests, organization. Speaker's websafe key is part of Session attributes.
Speaker is chosen to be as a separate entity to keep further information about speaker and potential future changes to speaker information. It can also help in futrue if the separate speaker profiles are introduced in ConferenceCentral app.

### Methods Defined for Task 1
These methods have been added to conference.py

* #### `getConferenceSessions`
Retrieves all the sessions in a conference based on websafeConferenceKey passed from client and returns as SessionForms object containing resulting sessions. websafeConferenceKey is used as ancestor key to filter the sessions.

* #### `getConferenceSessionsByType`
Retrieves all the sessions in a conference based on websafeConferenceKey and start time passed from client and returns as SessionForms object containing resulting sessions. websafeConferenceKey is used as ancestor key to filter the sessions.

* #### `getSessionsBySpeaker`
Retrieves all the sessions based on speaker information passed from client and returns as SessionForms object containing resulting sessions.

* #### `createSession`
Creates the session using information passed from client which contains name, conference key, speaker key, highlights, start time, duration and date. conference key is used as parent key to add new session.

## Task 2 Explanation
Following methods have been implemented for task 2.
* `addSessionToWishlist`
  * Calls `_updateSessionWishlist` method with `reg=True` parameter which implements functionality of both adding to wishlist and deleting from wishlist, which updates the wishlist property of Profile entity in datastore by adding the session ID in it.

* `deleteSessionInWishlist`
  * Calls `_updateSessionWishlist` method with `reg=False` which implements functionality of both adding to wishlist and deleting from wishlist, which updates the wishlist property of Profile entity in datastore by adding the session ID in it.

* `getSessionsInWishlist`
  * Gets all the sessions in user's wishlist

## Task 3 Explanation
Following endpoints have been added as 2 additional queries which generate two additional indexes.

* ### `getSessionsByStartTimeAndDuration`
Queries the sessions and filters based on the startTime and duration provided by client. Checks for the sessions which start at or after the time provided by client and have requested duration. Returns SessionForms object with resulting sessions.
It generates following index in index.yaml file.
```
   - kind: Session
     properties:
     - name: duration
     - name: startTime
```
* ### `getSessionsByMinStartTimeDurationHighlights`
Queries the sessions and filters based on the startTime, duration and highlights provided by client. Checks for the sessions which start at or after the time provided by client, have requested duration and highlights. Returns SessionForms object with resulting sessions.
It generates following index in index.yaml file
```
   - kind: Session
     properties:
     - name: duration
     - name: highlights
     - name: startTime
```

### Solution for multiple inequality query problem
The problem with querying for sessions which do not have type workshop and start before 7 PM is that it cannot be queried in one go. The reason is that the App Engine does not not allow multiple inequalities in one query. When attempted to do so, it throws an exception.
So in order to handle this scenario, the implemented solution first filters the sessions on type and fetches all the sessions which are not the type of Workshop from datastore, and then the result is iterated to check if each session meets the second inequality condition of starting before 7 PM. Later, the filtered results are returned to client as SessionForms ProtoRPC message containing list of filtered sessions.

## Task 4 Explanation

### `getFeaturedSpeaker`
Gets the memcache entry for featured speaker which is updated when a new session is added and number of sessions of that user are more than one
This has been implemented using task queue. Call to this task queue is made when the session is created.

[1]: https://developers.google.com/appengine
[2]: http://python.org
[3]: https://developers.google.com/appengine/docs/python/endpoints/
[4]: https://fsnd-p4-conference-1153.appspot.com
[5]: https://fsnd-p4-conference-1153.appspot.com/_ah/api/explorer
[6]: https://console.developers.google.com/
[7]: https://localhost:8080/
[8]: https://developers.google.com/appengine/docs/python/endpoints/endpoints_tool
