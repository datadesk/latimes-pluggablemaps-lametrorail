# Models
from django.contrib.gis.db import models

# Other helpers
from copy import deepcopy
from django.utils.translation import ugettext_lazy as _
from django.contrib.gis.gdal import OGRGeometry, OGRGeomType


class Line(models.Model):
    """
    A line in the L.A. Metro Rail system.
    """
    # Description
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True, null=True)
    
    # Boundaries
    GEOM_FIELD_LIST = ( # We can use this list later in views to exclude 
                        # bulky geometry fields from database queries
        'linestring_2229',
        'linestring_4269', 'linestring_4326', 'linestring_900913',
        'simple_linestring_4269', 'simple_linestring_4326', 'simple_linestring_900913',
        'simple_linestring_2229',
    )
    linestring_2229 = models.MultiLineStringField(_("Boundary"), srid=2229,
        null=True, blank=True)
    linestring_4269 = models.MultiLineStringField(_("Boundary"), srid=4269,
        null=True, blank=True)
    linestring_4326 = models.MultiLineStringField(srid=4326, null=True, blank=True)
    linestring_900913 = models.MultiLineStringField(srid=900913, null=True,
        blank=True)
    simple_linestring_2229 = models.MultiLineStringField(_("Boundary"), srid=2229,
        null=True, blank=True)
    simple_linestring_4269 = models.MultiLineStringField(srid=4269, null=True,
        blank=True)
    simple_linestring_4326 = models.MultiLineStringField(srid=4326, null=True,
        blank=True)
    simple_linestring_900913 = models.MultiLineStringField(srid=900913, null=True, 
        blank=True)
    
    # Managers
    objects = models.GeoManager()
    
    class Meta:
        ordering = ('name',)
    
    def __unicode__(self):
        return self.name
    
    def get_stop_count(self):
        return self.stop_set.count()
    get_stop_count.short_description = 'Stops'
    
    #
    # Sync linestrings
    #
    
    def get_srid_list(self):
        """
        Returns all of the SRIDs in the polygon set.
        """
        # Pull the meta data for the model
        opts = self.__class__._meta
        
        # Filter the field set down to the polygon fields
        fields = [i.name for i in opts.fields if i.name.startswith('linestring_')]
        
        # Return the SRID number that comes after the underscore.
        return [int(i.split('_')[1]) for i in fields]
    
    def set_linestrings(self, canonical_srid=2229):
        """
        Syncs all linestring fields to the one true field, defined by the 
        `canonical_srid` parameter.
        
        Returns True if successful.
        """
        # Make sure it's a legit srid
        srid_list = self.get_srid_list()
        if canonical_srid not in srid_list:
            raise ValueError("canonical_srid must exist on the model.")
        
        # Grab the canonical data
        canonical_field = 'linestring_%s' % str(canonical_srid)
        canonical_data = getattr(self, canonical_field)
        
        # Update the rest of the fields
        srid_list.remove(canonical_srid)
        for srid in srid_list:
            copy = canonical_data.transform(srid, clone=True)
            this_field = 'linestring_%s' % str(srid)
            setattr(self, this_field, copy)
        return True
    
    def set_simple_linestrings(self, tolerance=500):
        """
        Simplifies the source linestrings so they don't use so many points.
        
        Provide a tolerance score the indicates how sharply the
        the lines should be redrawn.
        
        Returns True if successful.
        """
        # Get the list of SRIDs we need to update
        srid_list = self.get_srid_list()
        
        # Loop through each
        for srid in srid_list:
            
            # Fetch the source polygon
            source_field_name = 'linestring_%s' % str(srid)
            source = getattr(self, source_field_name)
            
            # Fetch the target polygon where the result will be saved
            target_field_name = 'simple_%s' % source_field_name
            
            # If there's nothing to transform, drop out now.
            if not source:
                setattr(self, target_field_name, None)
                continue
            
            if srid != 900913:
                # Transform the source out of lng/lat before the simplification
                copy = source.transform(900913, clone=True)
            else:
                copy = deepcopy(source)
            
            # Simplify the source
            simple = copy.simplify(tolerance, True)
            
            # If the result is a polygon ...
            if simple.geom_type == 'LineString':
                # Create a new Multipolygon shell
                ml = OGRGeometry(OGRGeomType('MultiLineString'))
                # Transform the new poly back to its SRID
                simple.transform(srid)
                # Stuff it in the shell
                ml.add(simple.wkt)
                # Grab the WKT
                target = ml.wkt
            
            # If it's not a polygon...
            else:
                # It should be ready to go, so transform
                simple.transform(srid)
                # And grab the WKT
                target = simple.wkt
            
            # Stuff the WKT into the field
            setattr(self, target_field_name, target)
        return True


class Station(models.Model):
    """
    A portal on the Metro Rail train system where riders can access
    a stop on the system.
    
    A station can host multiple stop,s like 7th Street / Metro Center
    holds separate stops for the Blue and Red lines.
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True, null=True)
    lines = models.ManyToManyField(Line, blank=True, null=True)
    
    class Meta:
        ordering = ('name',)
    
    def __unicode__(self):
        return self.name
    
    def get_line_display(self):
        from django.utils.text import get_text_list
        return get_text_list([i.name for i in self.lines.all()], 'and')
    get_line_display.short_description = 'Lines'
    
    def get_stop_count(self):
        return self.stop_set.count()
    get_stop_count.short_description = 'Stops'


class Stop(models.Model):
    """
    A platform where a train stops in the L.A. Metro Rail system.
    
    A stop can host trains from multiple lines, like Civic Center
    has one stop that runs both Purple and Red line trains.
    
    Each stop belongs to a station.
    """
    # Description
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True, null=True)
    stop_id = models.IntegerField('Stop ID', blank=True, null=True)
    station = models.ForeignKey(Station, blank=True, null=True)
    lines = models.ManyToManyField(Line, blank=True, null=True)
    
    # Boundaries
    GEOM_FIELD_LIST = ( # We can use this list later in views to exclude 
                        # bulky geometry fields from database queries
        'point_4269', 'point_4326', 'point_900913',
    )
    point_4269 = models.PointField(_("Boundary"), srid=4269,
        null=True, blank=True)
    point_4326 = models.PointField(srid=4326, null=True, blank=True)
    point_900913 = models.PointField(srid=900913, null=True,
        blank=True)
    
    # Managers
    objects = models.GeoManager()
    
    class Meta:
        ordering = ('stop_id',)
    
    def __unicode__(self):
        return self.name
    
    def get_line_display(self):
        from django.utils.text import get_text_list
        return get_text_list([i.name for i in self.lines.all()], 'and')
    get_line_display.short_description = 'Lines'
    
    #
    # Sync points
    #
    
    def get_srid_list(self):
        """
        Returns all of the SRIDs in the polygon set.
        """
        # Pull the meta data for the model
        opts = self.__class__._meta
        
        # Filter the field set down to the polygon fields
        fields = [i.name for i in opts.fields if i.name.startswith('point_')]
        
        # Return the SRID number that comes after the underscore.
        return [int(i.split('_')[1]) for i in fields]
    
    def set_point(self, canonical_srid=4269):
        """
        Syncs all point fields to the one true field, defined by the 
        `canonical_srid` parameter.
        
        Returns True if successful.
        """
        # Make sure it's a legit srid
        srid_list = self.get_srid_list()
        if canonical_srid not in srid_list:
            raise ValueError("canonical_srid must exist on the model.")
        
        # Grab the canonical data
        canonical_field = 'point_%s' % str(canonical_srid)
        canonical_data = getattr(self, canonical_field)
        
        # Update the rest of the fields
        srid_list.remove(canonical_srid)
        for srid in srid_list:
            copy = canonical_data.transform(srid, clone=True)
            this_field = 'point_%s' % str(srid)
            setattr(self, this_field, copy)
        return True
    

