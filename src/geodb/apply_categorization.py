from collections import defaultdict

import sqlalchemy
from sqlalchemy.orm import sessionmaker

from model import GPSTrack, db_url, Categorization

if __name__ == '__main__':

    engine = sqlalchemy.create_engine(db_url(), echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    namings = defaultdict(lambda: defaultdict(set))

    for track in (
            session.query(GPSTrack)
                    .filter(GPSTrack.source == '4sq')
    ):
        categorization = (
            session.query(Categorization)
                .filter(Categorization.old_name == track.name)
                .one_or_none()
        )

        if categorization:
            if categorization.category != track.description:
                print(f"{categorization.category} <= {track.name}")
            # if we have a matching name, continue even if it's already correct
            continue

        venue = track.raw.get('venue', {})
        primary_categories = [c for c in venue.get('categories', []) if c.get('primary', False)]
        primary_category = primary_categories[0]['name'] if primary_categories else None

        if primary_category:
            categorization = (
                session.query(Categorization)
                    .filter(Categorization.old_category == primary_category)
                    .filter(Categorization.category != track.description)
                    .one_or_none()
            )

            if categorization:
                print(f"{categorization.category} <= {track.name} ({track.description})")