Author: Victor Asselta
Project: Google App Engine P4
Course: Full Stack Nanodegree

App Engine application for the Udacity training course.

## Products
- [App Engine][1]

## Language
- [Python][2]

## APIs
- [Google Cloud Endpoints][3]

## Setup Instructions
1. Update the value of `application` in `app.yaml` to the app ID you
   have registered in the App Engine admin console and would like to use to host
   your instance of this sample.
1. Update the values at the top of `settings.py` to
   reflect the respective client IDs you have registered in the
   [Developer Console][4].
1. Update the value of CLIENT_ID in `static/js/app.js` to the Web client ID
1. (Optional) Mark the configuration files as unchanged as follows:
   `$ git update-index --assume-unchanged app.yaml settings.py static/js/app.js`
1. Run the app with the devserver using `dev_appserver.py DIR`, and ensure it's running by visiting your local server's address (by default [localhost:8080][5].)
1. (Optional) Generate your client library(ies) with [the endpoints tool][6].
1. Deploy your application.


[1]: https://developers.google.com/appengine
[2]: http://python.org
[3]: https://developers.google.com/appengine/docs/python/endpoints/
[4]: https://console.developers.google.com/
[5]: https://localhost:8080/
[6]: https://developers.google.com/appengine/docs/python/endpoints/endpoints_tool


The following files have been added to, adapted, and wholly changed in order to satisfy the course requirements.

The included files are designed to run with Google's app engine and will not work properly on their own.

The working version of these files can be on found at the following url:
https://ttt-conference.appspot.com

I have included many extra methods to help with testing this applications.
Please see my submission as I do not wish to make them public knowledge.


To the reviewer:

PEP8:
I too use, and love, pyCharm with pep8 formatting. This file was given to us in it's current state with camel case functions and variable names.
I was not sure if I was permitted to reformat the file. Given this feedback I reformatted the file as much as seemed polite with pep8online.com and pyCharm warnings.
I have not changed the function or variable names as I don't think the original file creator would appreciate this.

addSessionToWishlist:
Task 2 showed the variable with 'SessionKey' as opposed to websafeConferenceKey in task 1. I took this to mean the requirement was for the model key.
Given your response I have added a convert method to change a urlsafe key to a model key for use in testing this method.

featured speaker criteria:
The function _setFeaturedSpeaker does indeed check for more than 2 sessions prior to setting the memcache key.
I understand the confusion given the function name so I renamed it to _checkThenSetFeaturedSpeaker().

I finished the memcache task per instructed. I did indeed forget to fully implement this task.

paths:
I removed the testing toggle which ultimately altered the path variable for the sake of simplicity.
I've attempted to set the paths as you suggested.

resource containers:
I have changed a number of string message uses to resource containers per instructions.


TASK 1 Explain Design Choices:

I decided that it would be best to implement each session, as a child of a particular conference.
( A conference has sessions )

I also decided that speakers would also be conference attendees. I made this decision based on the fact that I attend many conferences and this always seems to be the case.
Many times I have noticed that the past speaker was sitting in attendance in other sessions.
At the time of writing this though, I would think it would be best to also implement a speaker class. A speaker class would HAVE a profile, so that would work.
My only hesitation in doing this now as I have been unable to retrieve family, or full names from google's associated api. This may be due to limitations set within my own accounts.
I chose to use the user's display name as this seems to always be available. A speaker must have a profile. This is checked for in the code.
I figured that a speaker would be registered for a conference as well.

I took some liberties with the required function arguments as the previous review suggested that these names were not set in stone.
I prefer to contain everything within a request argument and to use the 'POST' http method due to the number of arguments for each session. The urls get very messy otherwise.
I did go with the http get methods when it made sense. Such as fetching the current users wish list which requires no arguments.

I also attempted to break down many of the longer methods, or functions, in to smaller, more purpose related methods.
I have recently been reading "Clean Code" by Robert C Martin and I have been trying to implement some of the suggestions in this book.

The specific types as as follows for the class Session and ndb.Model instance:
A string type for the name as this is a presentation name as opposed to and id.
    name                = ndb.StringProperty(required=True)
Also a string type for similar reasons.
    highlights          = ndb.StringProperty(repeated=True)
Although not a proper name, still a name.
    speakerDisplayName  = ndb.StringProperty(required=True)
Again a string type because the name of a conference is presented as such, not an id.
    conferenceName      = ndb.StringProperty(required=True)
This is not really a currently useful field but duration is typically represented an integer. Let's say number of minutes.
This would make it easier to perform operations as well.
    duration            = ndb.IntegerProperty()
This is an enum, as a conference is likely to only have a finite number of session types.
    sessionType         = ndb.StringProperty(default='NOT_SPECIFIED', required=True)
A datetime property because this is a calendar date.
    date                = ndb.DateProperty()
This is essentially a datetime property as time is a child of datetime. Although the point is that we are only interested in the time in this instance.
    startTime           = ndb.TimeProperty()


TASK 3 Additional queries:

I think you'll notice that the current code has many additional queries for added functionality and utility.

I'll outline a couple here:

postReview and getReview
    These do more or less what they indicate. Conferences frequently, if not always, pester you for reviews for every aspect of said conference.
    I chose to utilize an enum for setting values.

    I'd also like to point out the functions created for testing purposes. Please see the submission note for these methods as I do not wish to share them publicly.

TASK 3 Query related problem:

    update: After reviewing the problem and some helpful hints from my reviewer:

    The following query would necessitate the use of inequality filters. That is any of the following filters:

    not equal: !=
    less than: <
    greater than: >
    less than or equal to: <=
    greater than or equal to: >=

    Inequality because they represent alternate cases to being equal to as in the equality filter ' = '

    In this case, I'm guessing here, one 'problem' would be the need for composite indexes. Due to the nature of datastore, queries need an index to work properly.
    Fortunately when you run a query on your local dev server, these indexes are created for you.
    If you were to not run these queries locally then they WILL NOT WORK on app spot.

    Another perceived problem might be a particular nature of datastore queries involving inequality filters.

    I'm guessing that this is the real problem we're talking about here.

    An inequality filter can only be applied to a single property.
    This creates a problem with composite indexes. So in this case you must construct a query which utilizes more than a single composite index or, stated differently, more than a single query.

    I, being me and slightly confused, did not see this as a 'problem' but as just another step to building the application. A design necessity as it is.

    This query, which necessitates at least three inequality filters, dictates the need for multiple queries to apply the inequality filters. No > && < allowed here.

    In the past I have been attempting to apply these filters by altering the returned query. This hasn't worked.

    This time around:

    1) Query all available sessions using the websafeConferenceKey and being not equal to the given session type. Note no get() method here.
            sessions = Session.query(ancestor=ndb.Key(urlsafe=request.websafeConferenceKey)).filter(Session.sessionType != not_this_session_type)

    2) Create an empty collection for the returned sessions.
            sessions_filtered_by_times = []

    3) Filter sessions by specified before and after times. This logic determines if the query returned is iterable or not.
        if iter(sessions):
            for session in sessions:
                if before_time > session.startTime > after_time:
                    sessions_filtered_by_times.append(session)
        else:
            if before_time > sessions.startTime > after_time:
                sessions_filtered_by_times = [sessions]

    4) Return the results
        return self._copyMultipleSessionsToForm(sessions_filtered_by_times)

    So here was the previous answer. I was trying to figure out a way of allowing the database to do the work.
    In this case, as an applied solution, I decided to simply apply each filter one by one.

    SO I figured the following would be the simplest solution:

        1) Query all available sessions:
            sessions = Session.query()

        2) Filter by the specific conference by name with an equality filter:
            filter1 = sessions.filter(Session.conferenceName == conference.name)

        3) Filter by session type (workshop, lecture, etc. ) with another equality filter.
            filter2 = filter1.filter(Session.sessionType == session_type)

        4) Filter the query down to the sessions before a specific time with an inequality filter ( less than )
            filter3 = filter2.filter(Session.startTime < before_time)

        5) And finally filter the query down to the sessions that are scheduled after a specific time using the another inequality filter ( greater than )
            filter4 = filter3.filter(Session.startTime > after_time)

        We could combine some these filters and have much less code but, the steps appear clearer this way. At least I think so.
        As stated above though, you can not combine inequality filters. All though these results are not sorted, it is worth mentioning, that any sorting need be applied prior to other filters.
        More specifically prior to the inequality filters. I'm guessing again that the query data is altered by applying filters and these alterations would interfere with ordering each record.


    old answer:
        I'll admit to being a little confused by this. I did not see this as a problem, other than datetime conversion for the sake of comparison. That's a bit interesting/ problematic
        I chose to filter a session query in segments, as opposed to using AND/ OR, each layer would be easier to troubleshoot. This seemed proper albeit verbose.


SOME NOTES ABOUT TESTING

Each feature has several requirements to function properly.

For instance, creating a session requires the conference name, name of the session, speaker display name, and the session type (workshop, lecture, demonstration, party).
This last one being an enum with limited values. I tried to include a check for all necessary arguments but I'll admit, that not all argument checking is complete.
I'll included examples in the submission form to help.
