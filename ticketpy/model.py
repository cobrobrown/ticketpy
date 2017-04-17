"""Models for API objects"""
from collections import namedtuple
from datetime import datetime
import re
import ticketpy


Status = namedtuple('Status', ['code'])
Embedded = namedtuple('Embedded', ['events', 'venues', 'attractions'])
Promoter = namedtuple('Promoter', ['id', 'name', 'description'])
Price = namedtuple('Price', ['type', 'currency', 'min', 'max'])
Place = namedtuple('Place', ['area', 'address', 'city', 'state',
                             'country', 'postal_code', 'location',
                             'name'])

Area = namedtuple('Area', ['name'])
Address = namedtuple('Address', ['line_1', 'line_2', 'line_3'])
City = namedtuple('City', ['name'])
State = namedtuple('State', ['state_code', 'name'])
Country = namedtuple('Country', ['country_code', 'name'])
DMA = namedtuple('DMA', ['id'])
Location = namedtuple('Location', ['latitude', 'longitude'])
Market = namedtuple('Market', ['id'])
BoxOfficeInfo = namedtuple('BoxOfficeInfo', ['phone_number_detail',
                                             'open_hours_detail',
                                             'accepted_payment_detail',
                                             'will_call_detail'])
GeneralInfo = namedtuple('GeneralInfo', ['general_rule', 'child_rule'])
Image = namedtuple('Image', ['url', 'ratio', 'width', 'height', 'fallback',
                             'attribution'])
Start = namedtuple('Start', ['local_date', 'local_time', 'date_time',
                                     'date_tbd', 'date_tba', 'time_tba',
                                     'no_specific_time'])
End = namedtuple('End', ['local_time', 'date_time', 'approximate'])
Access = namedtuple('Access', ['start_date_time', 'start_approximate',
                               'end_date_time', 'end_approximate'])
Sales = namedtuple('Sales', ['public', 'presales'])
PublicSale = namedtuple('PublicSales', ['start_date_time', 'end_date_time',
                                         'start_tbd'])
Presale = namedtuple('Presale', ['name', 'description', 'url',
                                 'start_date_time', 'end_date_time'])


attr_map = {
    'localDate': 'local_date',
    'localTime': 'local_time',
    'dateTime': 'date_time',
    'dateTBD': 'date_tbd',
    'startTBD': 'start_tbd',
    'dateTBA': 'date_tba',
    'timeTBA': 'time_tba',
    'noSpecificTime': 'no_specific_time',
    'startDateTime': 'start_date_time',
    'startApproximate': 'start_approximate',
    'endDateTime': 'end_date_time',
    'endApproximate': 'end_approximate',
    'postalCode': 'postal_code',
    'stateCode': 'state_code',
    'countryCode': 'country_code',
    'line1': 'line_1',
    'line2': 'line_2',
    'line3': 'line_3',
    'additionalInfo': 'additional_info',
    'pleaseNote': 'please_note',
    'priceRanges': 'price_ranges',
    'parkingDetail': 'parking_detail',
    'accessibleSeatingDetail': 'accessible_seating_detail',
    'boxOfficeInfo': 'box_office_info',
    'generalInfo': 'general_info',
    'subType': 'subtype',
    'phoneNumberDetail': 'phone_number_detail',
    'openHoursDetail': 'open_hours_detail',
    'acceptedPaymentDetail': 'accepted_payment_detail',
    'willCallDetail': 'will_call_detail',
    'generalRule': 'general_rule',
    'childRule': 'child_rule'
}


class Page(list):
    """API response page"""
    def __init__(self, number=None, size=None, total_elements=None,
                 total_pages=None):
        super().__init__([])
        self.number = number
        self.size = size
        self.total_elements = total_elements
        self.total_pages = total_pages

    @staticmethod
    def from_json(json_obj):
        """Instantiate and return a Page(list)"""
        pg = Page()
        _Util.assign_links(pg, json_obj, ticketpy.ApiClient.root_url)
        pg.number = json_obj['page']['number']
        pg.size = json_obj['page']['size']
        pg.total_pages = json_obj['page']['totalPages']
        pg.total_elements = json_obj['page']['totalElements']

        embedded = json_obj.get('_embedded')
        if not embedded:
            return pg

        object_models = {
            'events': Event,
            'venues': Venue,
            'attractions': Attraction,
            'classifications': Classification
        }
        for k, v in embedded.items():
            if k in object_models:
                obj_type = object_models[k]
                pg += [obj_type.from_json(obj) for obj in v]

        return pg

    def __str__(self):
        return ("Page {number}/{total_pages}, Size: {size}, "
                "Total elements: {total_elements}").format(**self.__dict__)

    def __repr__(self):
        return str(self)


class Dates:
    def __init__(self, start=None, end=None, access=None, timezone=None,
                 status=None):
        self.start = start
        self.end = end
        self.access = access
        self.timezone = timezone
        self.status = status

    @staticmethod
    def __start(start):
        kwargs = Dates.__namedtuple_kwargs(start, Start)
        dt = kwargs.get('date_time')
        if dt:
            kwargs['date_time'] = Dates.__format_utc_timestamp(dt)
        return Start(**kwargs)

    @staticmethod
    def __access(access):
        kwargs = Dates.__namedtuple_kwargs(access, Access)
        start_dt = kwargs.get('start_date_time')
        if start_dt:
            kwargs['start_date_time'] = Dates.__format_utc_timestamp(start_dt)

        end_dt = kwargs.get('end_date_time')
        if end_dt:
            kwargs['end_date_time'] = Dates.__format_utc_timestamp(end_dt)
        return Access(**kwargs)

    @staticmethod
    def from_json(json_obj):
        dates = Dates()
        dates.timezone = json_obj.get('timezone')
        dates.start = _Util.namedtuple(Start, json_obj.get('start'))
        dates.end = _Util.namedtuple(End, json_obj.get('end'))
        dates.access = _Util.namedtuple(Access, json_obj.get('access'))
        dates.status = _Util.namedtuple(Status, json_obj.get('status'))
        return dates


class _Util:
    def __init__(self):
        pass

    @staticmethod
    def assign_links(obj, json_obj, base_url=None):
        """Assigns ``links`` attribute to an object from JSON"""
        # Normal link strucutre is {link_name: {'href': url}},
        # but some responses also have lists of other models.
        # API occasionally returns bad URLs (with {&sort} and similar)
        json_links = json_obj.get('_links')
        if not json_links:
            obj.links = {}
        else:
            obj_links = {}
            for k, v in json_links.items():
                if 'href' in v:
                    href = re.sub("({.+})", "", v['href'])
                    if base_url:
                        href = "{}{}".format(base_url, href)
                    obj_links[k] = href
                else:
                    obj_links[k] = v
            obj.links = obj_links

    @staticmethod
    def namedtuple(namedtuple_model, json_obj=None):
        kwargs = {k: None for k in namedtuple_model._fields}
        if not json_obj:
            return None
        _Util.update_kwargs(json_obj)
        kwargs.update(json_obj)
        return namedtuple_model(**kwargs)

    @staticmethod
    def update_kwargs(kwargs):
        kws = {}
        for k, v in dict(kwargs).items():
            if k in attr_map:
                kws[attr_map[k]] = v
                del kwargs[k]

        dt_updates = {}
        for k, v in kws.items():
            if 'date_time' in k or 'dateTime' in k:
                dt_updates[k] = _Util.format_utc_timestamp(v)

        kwargs.update(kws)
        kwargs.update(dt_updates)

    @staticmethod
    def sales(json_obj):
        pub_sales = _Util.namedtuple(PublicSale, json_obj.get('public'))
        presales = [_Util.namedtuple(Presale, ps) for ps in
                    json_obj.get('presales', [])]
        return Sales(pub_sales, presales)

    @staticmethod
    def format_utc_timestamp(timestamp):
        return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def place(json_obj):
        kws = {k: None for k in Place._fields}
        kws.update({
            'name': json_obj.get('name'),
            'postal_code': json_obj.get('postalCode'),
            'area': _Util.namedtuple(Area, json_obj.get('area')),
            'address': _Util.address(json_obj.get('address')),
            'city': _Util.namedtuple(City, json_obj.get('city')),
            'state': _Util.state(json_obj.get('state')),
            'country': _Util.state(json_obj.get('country')),
            'location': _Util.namedtuple(json_obj.get('location'))
        })
        return Place(**kws)

    @staticmethod
    def state(json_obj):
        return _Util.namedtuple(State, json_obj)

    @staticmethod
    def address(json_obj):
        return _Util.namedtuple(Address, json_obj)


class Event:
    """Ticketmaster event

    The JSON returned from the Discovery API (at least, as far as 
    what's being used here) looks like:

    .. code-block:: json

        {
            "name": "Event name",
            "dates": {
                "start": {
                    "localDate": "2019-04-01",
                    "localTime": "2019-04-01T23:00:00Z"
                },
                "status": {
                    "code": "onsale"
                }
            },
            "classifications": [
                {
                    "genre": {
                        "name": "Rock"
                    }
                },
                {
                    "genre": {
                        "name": "Funk"
                    }
                }
            ],
            "priceRanges": [
                {
                    "min": 10,
                    "max": 25
                }
            ],
            "_embedded": {
                "venues": [
                    {
                        "name": "The Tabernacle"
                    }
                ]
            }
        }
    """
    def __init__(self, event_id=None, name=None, start_date=None,
                 start_time=None, status=None, price_ranges=None,
                 venues=None, utc_datetime=None, classifications=None,
                 links=None, distance=None, units=None, locale=None,
                 description=None, additional_info=None, url=None,
                 images=None, sales=None, info=None, please_note=None,
                 place=None, test=None, promoter=None):
        self.id = event_id
        self.name = name
        self.classifications = classifications
        self.price_ranges = price_ranges
        self.venues = venues
        self.links = links

        self.distance = distance
        self.units = units
        self.locale = locale
        self.description = description
        self.additional_info = additional_info
        self.url = url
        self.images = images
        self.sales = sales
        self.info = info
        self.please_note = please_note
        self.place = place
        self.test = test
        self.promoter = promoter

    @staticmethod
    def from_json(json_event):
        """Creates an ``Event`` from API's JSON response"""
        args = ['name', 'distance', 'units', 'locale', 'description',
                'url', 'test', 'info']
        kwargs = {k: json_event.get(k) for k in args}
        kwargs.update({
            'event_id': json_event.get('id'),
            'promoter': _Util.namedtuple(Promoter, json_event.get('promoter')),
            'sales': _Util.sales(json_event.get('sales')),
            'dates': Dates.from_json(json_event.get('dates'))
        })
        kwargs['event_id'] = json_event.get('id')
        ev = Event(**kwargs)

        images = json_event.get('images')
        if images:
            ev.images = [_Util.namedtuple(Image, i) for i in images]

        price_ranges = json_event.get('priceRanges')
        if price_ranges:
            ev.price_ranges = [_Util.namedtuple(Price, p) for p in price_ranges]

        classifications = json_event.get('classifications')
        if classifications:
            ev.classifications = [EventClassification.from_json(cl)
                                  for cl in classifications]

        venues = json_event.get('_embedded', {}).get('venues')
        if venues:
            ev.venues = [Venue.from_json(v) for v in venues]

        _Util.assign_links(ev, json_event)
        return ev

    def __str__(self):
        tmpl = ("Event:            {name}\n"
                "Venues:           {venues}\n"
                "Start date:       {local_start_date}\n"
                "Start time:       {local_start_time}\n"
                "Price ranges:     {price_ranges}\n"
                "Status:           {status}\n"
                "Classifications:  {classifications!s}\n")
        return tmpl.format(**self.__dict__)

    def __repr__(self):
        return str(self)


class Venue:
    """A Ticketmaster venue
    
    The JSON returned from the Discovery API looks something like this 
    (*edited for brevity*):
    
    .. code-block:: json
    
        {
            "id": "KovZpaFEZe",
            "name": "The Tabernacle",
            "url": "http://www.ticketmaster.com/venue/115031",
            "timezone": "America/New_York",
            "address": {
                "line1": "152 Luckie Street"
            },
            "city": {
                "name": "Atlanta"
            },
            "postalCode": "30303",
            "state": {
                "stateCode": "GA",
                "name": "Georgia"
            },
            "country": {
                "name": "United States Of America",
                "countryCode": "US"
            },
            "location": {
                "latitude": "33.758688",
                "longitude": "-84.391449"
            },
            "social": {
                "twitter": {
                    "handle": "@TabernacleATL"
                }
            },
            "markets": [
                {
                    "id": "10"
                }
            ]
        }

    
    """
    def __init__(self, name=None, address=None, city=None, state=None,
                 postal_code=None,
                 markets=None, url=None, box_office_info=None,
                 dmas=None, general_info=None, venue_id=None,
                 social=None, timezone=None, images=None,
                 parking_detail=None, accessible_seating_detail=None,
                 links=None, type=None, distance=None, units=None,
                 locale=None, description=None, additional_info=None,
                 country=None, currency=None, test=None, location=None):
        self.name = name
        self.id = venue_id
        self.address = address
        self.postal_code = postal_code
        self.city = city
        #: State code (ex: 'GA' not 'Georgia')
        self.state = state
        self.timezone = timezone
        self.url = url
        self.box_office_info = box_office_info
        self.dmas = dmas
        self.markets = markets
        self.general_info = general_info
        self.social = social
        self.images = images
        self.parking_detail = parking_detail
        self.accessible_seating_detail = accessible_seating_detail
        self.links = links

        self.type = type
        self.distance = distance
        self.units = units
        self.locale = locale
        self.description = description
        self.additional_info = additional_info
        self.country = country
        self.currency = currency
        self.test = test
        self.location = location

    @staticmethod
    def from_json(json_venue):
        """Returns a ``Venue`` object from JSON"""
        args = ['name', 'url', 'type', 'distance', 'units', 'locale',
                'description', 'additionalInfo', 'postalCode', 'timezone',
                'currency', 'parkingDetail', 'test', 'social']
        kwargs = {k: json_venue.get(k) for k in args}
        kwargs.update({
            'venue_id': json_venue.get('id'),
            'city': _Util.namedtuple(City, json_venue.get('city')),
            'state': _Util.namedtuple(State, json_venue.get('state')),
            'country': _Util.namedtuple(Country, json_venue.get('country')),
            'address': _Util.namedtuple(Address, json_venue.get('address')),
            'location': _Util.namedtuple(Location, json_venue.get('location')),
            'generalInfo': _Util.namedtuple(GeneralInfo,
                                            json_venue.get('generalInfo')),
            'boxOfficeInfo': _Util.namedtuple(BoxOfficeInfo,
                                              json_venue.get('boxOfficeInfo')),
            'accessibleSeatingDetail':
                json_venue.get('accessibleSeatingDetail')
        })
        _Util.update_kwargs(kwargs)
        v = Venue(**kwargs)

        images = json_venue.get('images')
        if images:
            v.images = [_Util.namedtuple(Image, i) for i in images]

        markets = json_venue.get('markets')
        if markets:
            v.markets = [_Util.namedtuple(Market, m) for m in markets]

        dmas = json_venue.get('dmas')
        if dmas:
            v.dmas = [_Util.namedtuple(DMA, d) for d in dmas]

        _Util.assign_links(v, json_venue)
        return v

    def __str__(self):
        return ("{name} at {address} in "
                "{city} {state}").format(**self.__dict__)

    def __repr__(self):
        return str(self)


class Attraction:
    """Attraction"""
    def __init__(self, attraction_id=None, attraction_name=None, url=None,
                 classifications=None, images=None, test=None, links=None):
        self.id = attraction_id
        self.name = attraction_name
        self.url = url
        self.classifications = classifications
        self.images = images
        self.test = test
        self.links = links

    @staticmethod
    def from_json(json_obj):
        """Convert JSON object to ``Attraction`` object"""
        att = Attraction()
        att.id = json_obj.get('id')
        att.name = json_obj.get('name')
        att.url = json_obj.get('url')
        att.test = json_obj.get('test')

        images = json_obj.get('images')
        if images:
            att.images = [_Util.namedtuple(Image, i) for i in images]

        classifications = json_obj.get('classifications')
        att.classifications = [Classification.from_json(cl)
                               for cl in classifications]

        _Util.assign_links(att, json_obj)
        return att

    def __str__(self):
        return self.name if self.name is not None else 'Unknown'

    def __repr__(self):
        return str(self)


class Classification:
    """Classification object (segment/genre/sub-genre)
    
    For the structure returned by ``EventSearch``, see ``EventClassification``
    """
    def __init__(self, segment=None, classification_type=None, subtype=None,
                 primary=None, links=None):
        self.segment = segment
        self.type = classification_type
        self.subtype = subtype
        self.primary = primary
        self.links = links

    @staticmethod
    def from_json(json_obj):
        """Create/return ``Classification`` object from JSON"""
        cl = Classification()
        cl.primary = json_obj.get('primary')

        segment = json_obj.get('segment')
        if segment:
            cl.segment = Segment.from_json(segment)

        cl_t = json_obj.get('type')
        if cl_t:
            cl.type = ClassificationType(cl_t['id'], cl_t['name'])

        subtype = json_obj.get('subType')
        if subtype:
            cl.subtype = ClassificationSubType(subtype['id'], subtype['name'])

        _Util.assign_links(cl, json_obj)
        return cl


class EventClassification:
    """Classification as it's represented in event search results
    See ``Classification()`` for results from classification searches
    """
    def __init__(self, genre=None, subgenre=None, segment=None,
                 classification_type=None, classification_subtype=None,
                 primary=None, links=None):
        self.genre = genre
        self.subgenre = subgenre
        self.segment = segment
        self.type = classification_type
        self.subtype = classification_subtype
        self.primary = primary
        self.links = links

    @staticmethod
    def from_json(json_obj):
        """Create/return ``EventClassification`` object from JSON"""
        ec = EventClassification()
        ec.primary = json_obj.get('primary')

        segment = json_obj.get('segment')
        if segment:
            ec.segment = Segment.from_json(segment)

        genre = json_obj.get('genre')
        if genre:
            ec.genre = Genre.from_json(genre)

        subgenre = json_obj.get('subGenre')
        if subgenre:
            ec.subgenre = SubGenre.from_json(subgenre)

        cl_t = json_obj.get('type')
        if cl_t:
            ec.type = ClassificationType(cl_t['id'], cl_t['name'])

        cl_st = json_obj.get('subType')
        if cl_st:
            ec.subtype = ClassificationSubType(cl_st['id'], cl_st['name'])

        _Util.assign_links(ec, json_obj)
        return ec

    def __str__(self):
        return ("Segment: {segment} / Genre: {genre} / Subgenre: {subgenre} / "
                "Type: {type} / Subtype: {subtype}").format(**self.__dict__)

    def __repr__(self):
        return str(self)


class ClassificationType:
    def __init__(self, type_id=None, type_name=None, subtypes=None):
        self.id = type_id
        self.name = type_name
        self.subtypes = subtypes

    def __str__(self):
        return self.name if self.name is not None else 'Unknown'

    def __repr__(self):
        return str(self)


class ClassificationSubType:
    def __init__(self, type_id=None, type_name=None):
        self.id = type_id
        self.name = type_name

    def __str__(self):
        return self.name if self.name is not None else 'Unknown'

    def __repr__(self):
        return str(self)


class Segment:
    def __init__(self, segment_id=None, segment_name=None, genres=None,
                 links=None):
        self.id = segment_id
        self.name = segment_name
        self.genres = genres
        self.links = links

    @staticmethod
    def from_json(json_obj):
        """Create and return a ``Segment`` from JSON"""
        seg = Segment()
        seg.id = json_obj['id']
        seg.name = json_obj['name']

        if '_embedded' in json_obj:
            genres = json_obj['_embedded']['genres']
            seg.genres = [Genre.from_json(g) for g in genres]

        _Util.assign_links(seg, json_obj)
        return seg

    def __str__(self):
        return self.name if self.name is not None else 'Unknown'

    def __repr__(self):
        return str(self)


class Genre:
    def __init__(self, genre_id=None, genre_name=None, subgenres=None,
                 links=None):
        self.id = genre_id
        self.name = genre_name
        self.subgenres = subgenres
        self.links = links

    @staticmethod
    def from_json(json_obj):
        g = Genre()
        g.id = json_obj.get('id')
        g.name = json_obj.get('name')
        if '_embedded' in json_obj:
            embedded = json_obj['_embedded']
            subgenres = embedded['subgenres']
            g.subgenres = [SubGenre.from_json(sg) for sg in subgenres]

        _Util.assign_links(g, json_obj)
        return g

    def __str__(self):
        return self.name if self.name is not None else 'Unknown'

    def __repr__(self):
        return str(self)


class SubGenre:
    def __init__(self, subgenre_id=None, subgenre_name=None, links=None):
        self.id = subgenre_id
        self.name = subgenre_name
        self.links = links

    @staticmethod
    def from_json(json_obj):
        sg = SubGenre()
        sg.id = json_obj['id']
        sg.name = json_obj['name']
        _Util.assign_links(sg, json_obj)
        return sg

    def __str__(self):
        return self.name if self.name is not None else 'Unknown'

    def __repr__(self):
        return str(self)


