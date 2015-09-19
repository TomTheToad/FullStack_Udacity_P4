Author: Victor Asselta
Project: Google App Engine P4
Course: Full Stack Nanodegree

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

    I'll admit to being a little confused by this. I did not see this as a problem, other than datetime conversion for the sake of comparison. That's a bit interesting/ problematic
    I chose to filter a session query in segments, as opposed to using AND/ OR, each layer would be easier to troubleshoot. This seemed proper albeit verbose.


SOME NOTES ABOUT TESTING

Each feature has several requirements to function properly.

For instance, creating a session requires the conference name, name of the session, speaker display name, and the session type (workshop, lecture, demonstration, party).
This last one being an enum with limited values. I tried to include a check for all necessary arguments but I'll admit, that not all argument checking is complete.
I'll included examples in the submission form to help.
