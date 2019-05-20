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
        venue = track.raw.get('venue', {})
        primary_categories = [c for c in venue.get('categories', []) if c.get('primary', False)]
        primary_category = primary_categories[0]['name'] if primary_categories else None

        namings[primary_category][track.description].add(f"{track.name}")

    for p_c, names in namings.items():
        for name, items in names.items():
            if name == p_c:
                continue
            if len(names) == 1:
                print(f"Always map {name} <= {p_c}: {', '.join(items)}")
                c = Categorization(category=name, old_category=p_c)
                session.add(c)
            else:
                print(f"Map {name} <= {', '.join(items)}")
                for old_name in items:
                    c = Categorization(category=name, old_name=old_name)
                    session.add(c)

    session.commit()

    # pprint(namings, width=200)
    # pprint(sorted(names))