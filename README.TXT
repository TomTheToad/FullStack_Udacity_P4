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
I prefer to contain everything within a request argument and to use the 'POST' http method due to the number of arguments for each session.
(see "Code Formatting and Arrangement" section)

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

    Ultimately I chose to provide two solutions to this problem. One that solely uses datastore to do the work and the other a "half and half" approach that I think previous reviewer was referring to.


    The "Problem":

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


    Solution A:

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

    Solution B: (my favorite and thanks to Jeff Donovan for the hint which ultimately helped me solve my issue)

    This solution allows datastore to do most all of the work and would, as I understand it, be far more efficient.

    1) Get the list of supplied session types from the enumeration model and convert to a dictionary.
        enum_types = SessionTypeEnum(1).to_dict()

    2) Populate a new dict of acceptable session types. This could also be accomplished by deleting the given session type from the previous dict.
    I thought this way would make for easier reading and not throw an exception if the user entered something that wasn't contained in the enum.

    for item in enum_types:
        if item != avoid_session_type:
            acceptable_session_types.append(item)

    3) Filter the query by the given conference key.
        filter1 = Session.query(ancestor=ndb.Key(urlsafe=request.websafeConferenceKey))

    4) Filter the query by approved session types.
        filter2 = filter1.filter(Session.sessionType.IN(acceptable_session_types))

    5) Filter the query for sessions that start prior to the given before_time
        filter3 = filter2.filter(Session.startTime < before_time)

    6) Filter the query for sessions that start after the given after_time
        filter4 = filter3.filter(Session.startTime > after_time)

    7) Pass the query object to a forms method to return the results.
        return self._copyMultipleSessionsToForm(query=filter4)



SOME NOTES ABOUT TESTING

Each feature has several requirements to function properly.

For instance, creating a session requires the conference websafeConferenceKey, name of the session, speaker display name, and the session type (workshop, lecture, demonstration, party).
This last one being an enum with limited values.


Code Formatting and Arrangement

This has been a point of contention with this project so I'm taking the time to further explain my reasons behind the appearance of the project code.

I've added something major to each project I've done for Udacity thus far. This could be a question I'd like to answer, something I wish to learn and apply, or something that I thought would be valuable in the future.

The first project uses a challenging API that was not well documented. This gave me insight into issues and design Challenges with creating and documenting an API.

The second project I decided to explore decorators and build a basic style ORM from them. The next project called for the use of sqlalchemy which mean't that we'd be abstracting the database layer soon so I gave it a shot.
Ultimately my database helper file was ultra simplified as to avoid confusing the reviewer and moving the focus from the main project.

The third project I decided I'd explore some front end problems as well as some more complex, inter-related database table calls. I also wanted to use some of my cartooning skills for the fun of it.

This, the fourth project, I decided to apply some of what I have been reading and studying lately with regards to code formatting.
It's an interesting problem. We, in the coding community, have our very own kind of prophets. Those that preach "clean code", "flat code", and coders as being similar to authors.

I took notes from books such as "Clean Code" by "Uncle Bob" Robert C Martin, articles such as "Flat Code" from Code magazine by Mike Yeager, and courses such as "Clean Code: Writing for Humans" by Cory House or commentary and courses from Simon Alardice.

I wondered how one might apply all these various principles to actual work. I started with Test Driven Development but, since I was kind of dinged for that in the previous project, decided not to move forward with it.
I regret this decision now. I was fascinated by the application of mocks and would have liked to apply more of that to this project in particular. Someone like me, who finds themselves typing out stream of consciousness type code, can benefit greatly from the short, strong code TDD produces.
I was fortunate enough to attend a meetup with Bitly's local senior developer talking about TDD. We got to speak one on one about mocks and clean code in general. I'm looking forward to applying some TDD in the near future.

I tried to apply ideas such as DRY (Do not Repeat Yourself), breaking larger code into the smallest possible functions, and creating functions that did not necessarily require comments.

What you see in the conference file is my attempts at applying all these principles. I'm not saying everything went to plan, or even well for that matter.

I met a great deal of resistance, from one reviewer in particular, but ultimately have learned much by this approach. You can do allot in a single line of code but there remains a strong argument for breaking code apart and showing the individuals pieces.

Do I string a set of function calls together (.this.that.something_else) or separate them out like paragraphs in an article? Do I explicitly show each step, and necessary call or do I produce slick, one line code for the sake of less lines?

I can't really say yet. I can't really say if it ultimately makes any difference to the compiler either. I can say that I'm learning allot by peoples reactions.
I am fortunate to have good friends who are engineers in aerospace, major ratings companies, and fortunate 100 tech companies. I've heard hours long arguments on poison code, code readability and more.

I can't say I have many answers yet but the results so far have been eye opening.