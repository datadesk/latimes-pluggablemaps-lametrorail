"""
Utilities for loading data into our Geodjango database.
"""
import gc
import os
import urllib
import zipfile
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.utils import LayerMapping

# The location of this directory
this_dir = os.path.dirname(__file__)
# The location of our source files.
lines_dir = os.path.join(this_dir, 'data', 'MetroRailLines1210')
lines_file = os.path.join(lines_dir, 'RailLines1109.shp')
stations_dir = os.path.join(this_dir, 'data', 'MetroRailStations1210')
stations_file = os.path.join(stations_dir, 'RailStations1109.shp')
crosswalk_file = os.path.join(stations_dir, 'crosswalk.csv')


def all():
    """
    Wrap it all together and load everything
    
    Example usage:
        
        >> from la_metro_rail import load; load.all()

    """
    from models import Line, Station, Stop
    [i.delete() for i in Station.objects.all()]
    [i.delete() for i in Stop.objects.all()]
    [i.delete() for i in Line.objects.all()]
    lines()
    fix_line_dupes()
    line_extras()
    stops()
    stations()


def lines():
    """
    Load the ESRI shapefile of Metro lines.
    
    Example usage:
    
        >> from us_counties import load; load.shp();
    
    """
    # Import the database model where we want to store the data
    from models import Line
    
    # A crosswalk between the fields in our database and the fields in our
    # source shapefile
    shp2db = {
        'linestring_2229': 'LineString',
        'name': 'Name',
    }
    # Load our model, shape, and the map between them into GeoDjango's magic
    # shape loading function.
    lm = LayerMapping(Line, lines_file, shp2db, source_srs=2229)
    # Fire away!
    lm.save(verbose=False)


def stops():
    """
    Load the ESRI shapefile of Metro stops.
    
    Example usage:
    
        >> from la_metro_rail import load; load.stops();
    
    """
    # Import the database model where we want to store the data
    from models import Stop, Station, Line
    
    # A crosswalk between the fields in our database and the fields in our
    # source shapefile
    shp2db = {
        'point_4269': 'Point',
        'name': 'STOP_NAME',
        'stop_id': 'STOP_ID',
    }
    # Load our model, shape, and the map between them into GeoDjango's magic
    # shape loading function.
    lm = LayerMapping(Stop, stations_file, shp2db, source_srs=4269)
    # Fire away!
    lm.save(verbose=False)


def stations():
    """
    Roll up the stops in the Metro Rail file into stations and links the lines.
    """
    import csv
    from models import Stop, Station, Line
    from django.template.defaultfilters import slugify
    crosswalk = csv.DictReader(open(crosswalk_file))
    stop_lookup = dict((i['stop_id'], i) for i in crosswalk)
    for stop in Stop.objects.all():
        this_crosswalk = stop_lookup[str(stop.stop_id)]
        stop.name = this_crosswalk.get("clean_station_name")
        stop.slug = slugify(stop.name) + "-" + str(stop.stop_id)
        if this_crosswalk.get("Line1", None):
            stop.lines.add(Line.objects.get(name=this_crosswalk.get("Line1")))
        if this_crosswalk.get("Line2", None):
            stop.lines.add(Line.objects.get(name=this_crosswalk.get("Line2")))
        station, created = Station.objects.get_or_create(
            name=this_crosswalk.get("clean_station_name"),
            slug=slugify(this_crosswalk.get("clean_station_name")),
        )
        stop.station = station
        stop.save()
        for line in stop.lines.all():
            station.lines.add(line)
        station.save()


def fix_line_dupes():
    """
    LA Metro breaks some lines into more than one shape.
    This is a pain in the butt.
    
    To fix it, this function will consolidate duplicates into a single
    "multilinestring."
    
    Example usage: 
    
        >> from mapping.la_metro_rail import load; load.fix_dupes();

    """
    from django.db.models import Count
    from la_metro_rail.models import Line
    
    # Group and count the county names that appear more than once
    dupe_list = Line.objects.values('name').annotate(
        count=Count('name')).filter(count__gt=1)

    # Loop through each of the dupes
    for dupe in dupe_list:
        # Select all the records with that name
        this_list = Line.objects.filter(name=dupe['name'])
        # Print out what you're up to
        #print "Consolidating %s shapes for %s line" % (
        #    this_list.count(),
        #    dupe['name'],
        #    )
        # Use GeoDjango magic to consolidate all of their shapes into
        # one big multipolygon
        this_multilinestring = this_list.unionagg()
        # Create a new Line record with the unified shape and the rest of
        # the data found in each of the dupes.
        this_obj = Line.objects.create(
            name = this_list[0].name,
            linestring_2229 = this_multilinestring,
        )
        # Delete all of the duplicates
        [i.delete() for i in 
            Line.objects.filter(name=dupe['name']).exclude(id=this_obj.id)]


def line_extras():
    """
    Load some of the extra data we want for our model that's not included
    in the source shapefile. 
        
        * Slugify the name field
        * Simplified versions of our polygons that contain few points
        
    Example usage:
    
        >> from la_metro_rail import load; load.extras();
        
    """
    from django.template.defaultfilters import slugify
    from models import Line
    # Loop through everybody...
    for obj in Line.objects.all():
        #print "Adding extras for %s line" % obj.name
        # ...slug...
        obj.slug = slugify(obj.name)
        # .. the full set of polygons...
        obj.set_linestrings()
        obj.set_simple_linestrings()
        obj.save()


def specs():
    """
    Examine our source shapefile and print out some basic data about it.
    
    We can use this to draft the model where we store it in our system.
    
    Done according to documentation here: http://geodjango.org/docs/layermapping.html
    
    Example usage:
    
        >> from us_counties import load; load.specs();
    
    What we get in this case:
    
        Fields: ['STOP_ID', 'STOP_NAME', 'STOP_LAT', 'STOP_LON']
        Number of features: 73
        Geometry Type: Point
        SRS: GEOGCS["GCS_North_American_1983",
            DATUM["North_American_Datum_1983",
                SPHEROID["GRS_1980",6378137.0,298.257222101]],
            PRIMEM["Greenwich",0.0],
            UNIT["Degree",0.0174532925199433]]
        
        Fields: ['PATH_ID', 'Miles', 'Line', 'Name']
        Number of features: 183
        Geometry Type: LineString
        SRS: PROJCS["NAD_1983_StatePlane_California_V_FIPS_0405_Feet",
            GEOGCS["GCS_North_American_1983",
                DATUM["North_American_Datum_1983",
                    SPHEROID["GRS_1980",6378137.0,298.257222101]],
                PRIMEM["Greenwich",0.0],
                UNIT["Degree",0.0174532925199433]],
            PROJECTION["Lambert_Conformal_Conic_2SP"],
            PARAMETER["False_Easting",6561666.666666666],
            PARAMETER["False_Northing",1640416.666666667],
            PARAMETER["Central_Meridian",-118.0],
            PARAMETER["Standard_Parallel_1",34.03333333333333],
            PARAMETER["Standard_Parallel_2",35.46666666666667],
            PARAMETER["Latitude_Of_Origin",33.5],
            UNIT["Foot_US",0.3048006096012192]]
    """
    # Crack open the shapefile
    ds = DataSource(stations_file)
    # Access the data layer
    layer = ds[0]
    # Print out all kinds of goodies
    print "Fields: %s" % layer.fields
    print "Number of features: %s" % len(layer)
    print "Geometry Type: %s" % layer.geom_type
    print "SRS: %s" % layer.srs


