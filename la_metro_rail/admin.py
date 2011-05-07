# Admin
from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin

# Models
from models import Line, Station, Stop


class LineAdmin(OSMGeoAdmin):
    list_display = ('name', 'get_stop_count',)
    fieldsets = (
        (('Boundaries'),
            {'fields': ('linestring_2229', ),
             'classes': ('wide',),
            }
        ),
        (('Description'),
           {'fields': (
                'name', 'slug',
            ),
            'classes': ('wide',),
           }
        ),
     )
    readonly_fields = (
        'name', 'slug'
        )
    layerswitcher = False
    scrollable = False
    map_width = 400
    map_height = 400
    modifiable = False

admin.site.register(Line, LineAdmin)


class StopAdmin(OSMGeoAdmin):
    list_display = ('stop_id', 'station', 'get_line_display')
    list_filter = ('lines',)
    fieldsets = (
        (('Boundaries'),
            {'fields': ('point_4269', ),
             'classes': ('wide',),
            }
        ),
        (('Description'),
           {'fields': (
                'stop_id', 'slug', 'station', 'lines'
            ),
            'classes': ('wide',),
           }
        ),
     )
    readonly_fields = (
        'stop_id', 'slug', 'station', 'lines'
        )
    layerswitcher = False
    scrollable = False
    map_width = 400
    map_height = 400
    modifiable = False

admin.site.register(Stop, StopAdmin)


class StationAdmin(OSMGeoAdmin):
    list_display = ('name', 'get_stop_count', 'get_line_display')
    list_filter = ('lines',)
    fieldsets = (
        (('Description'),
           {'fields': (
                'name', 'slug',
            ),
            'classes': ('wide',),
           }
        ),
     )
    readonly_fields = (
        'name', 'slug',
        )

admin.site.register(Station, StationAdmin)
