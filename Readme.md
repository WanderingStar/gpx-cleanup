# GPX Cleanup

This will probably not be useful to anyone but me, but, just in case...

I recently went on a trip to Iceland with my girlfriend. We did a lot of
driving, and I have the GPX tracks from my car GPS for that. We also did some
other activities away from the car (walking, hiking, snowmobiling, etc), I have
tracks from my inReach Explorer for that. The inReach creates two tracks: one
with points every 10 minutes that is uploaded immediately using the satellite
connection, and one with points every 1 minute that is synced later.
Unfortunately, sometimes the 1 minute track doesn't sync properly, so I only
have 10 minute tracks for some parts of the trip.

I wanted to unify the data from all of these partly-overlapping tracks, but keep
the information about when we were driving (without this requirement, GPSBabel's
Merge feature would have done the trick).

This script takes a single GPX file with a number of tracks, figures out what
parts of the tracks overlap, merges the point in the overlapping sections, and
spits out a GPX file with non-overlapping tracks.

```
Input
Car      *-*-*-*-*-*
10 min       *----*----*----*----*----*----*----*
1 min        ***********
Car                            *-*-*-*-*-*-*-*


Output
         *-*-*******
                   *****
                       *----*--*
                               *-*-*-***-*-*-*
                                             *--*
```

The description field of each track in the output tells what all of the source
tracks were.


# Foursquare to GPX

Foursquare offers API access (Free for a limited number of non-commercial
queries): https://developer.foursquare.com

This script logs you in using the API (note that you have to configure a
callback URL in the developer portal). This is slightly annoying for a
command line script because you have to follow the link the script prints
and log in in your browser, then copy the URL from the browser and paste
it at the script's prompt.

Because this annoyed me to figure out: it doesn't really matter what the
callback URL _is_. You don't need to be running a web service that knows
how to handle OAuth2. Preferably, it's some URL you control, so nobody else
can steal your token by looking at their logs (though how would they know
to?). For example, I used the URL of a website I run. The important thing
is that the URL is registered with the Foursquare API for your account.
Otherwise you'll get a cryptic misconfiguration error when you open the
URL the script asks you to open:

> This app has a configuration problem and was unable to connect to your Foursquare account.
>
> Cause of error: Callback uri is not valid for this consumer

The Foursquare API should redirect you to the callback URL with a
`code=` query parameter. Copy the whole thing (or at least the `code=...`)
and paste it at the script's prompt.

The script uses that code to query the Foursquare API for your checkins,
and creates a series of GPX tracks with that data. These are
tracks, not waypoints, because waypoints don't include the time information.

The times in these GPX tracks are in UTC, though they don't have a `Z` or
`+00:00` time zone marker.

Because the Foursquare API limits the number of calls you can make per day, this
processes one month worth of checkins at a time and can be run each day until
you've converted all of your checkins.

To use this, you'll want to create a secrets.py with your Foursquare API keys

```
foursquare_client_id = 'YOUR CLIENT ID'
foursquare_client_secret = 'YOUR CLIENT SECRET'
```

And edit the paths in foursquare-to-gpx.py


# Organize tracks by local day

This uses the Azure timezone API to figure out what the local time was at
the start of each track. It organizes the tracks into one GPX file per
local day.

You'll need to add an Azure key to secrets.py to use this. I considered
a number of APIs that supply data like this, and this was the best one
I could find, so I was willing to go through the hassle of an Azure account.

```
azure_key = 'YOUR KEY'
```


# Point before

I have the start times and site names of a series of scuba dives in a CSV file.
This finds the GPS point where each dive should have started (the latest
point that is before the time the dive started) and prints them as a table
for input into my divelog and as a GPX file of single point tracks.

It would probably be faster to sort all points in all tracks and then search
for the appropriate times, but this isn't too slow as it is.

This one is not very polished (still has hardcoded filenames and time zones).