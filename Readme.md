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

Foursquare lets you download your checkins:
https://foursquare.com/settings/privacy "Export My Data"

They also offer API access (Free for a limited number of non-commercial
queries): https://developer.foursquare.com

This script takes the output of that export and queries the Foursquare API to
make a series of GPX tracks with that data. These are tracks, not waypoints,
because waypoints don't include the time information.

Because the Foursquare API limits the number of calls you can make per day, this
processes one month worth of checkins at a time and can be run each day until
you've converted all of your checkins.

To use this, you'll want to create a secrets.py with your Foursquare API keys

```
foursquare_client_id = 'YOUR CLIENT ID'
foursquare_client_secret = 'YOUR CLIENT SECRET'
```

And edit the paths in foursquare-to-gpx.py