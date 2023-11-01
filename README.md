# QGIS3 plugin to import survex .3d files 

### Features

* no dependencies (pure python); natively reads binary (v8 format) survex .3d files;
* import stations and legs with full metadata;
* create passage walls, cross-sections, and polygons from LRUD data;
* all features have _z_ dimensions, and (mean) elevations to assist with downstream workflows;
* the co-ordinate reference system (CRS) can be imported from the .3d file (*);
* results can be saved immediately as a GeoPackage file.

(*) with the appropriate `*cs` commands in the .svx source files (see below).

### Installation

The current version (v1.3.1) should be available through the [QGIS Python Plugins
Repository](https://plugins.qgis.org/plugins/): launch QGIS3,
go to 'Plugins &rarr; Manage and Install Plugins...', then (under the
'All' tab) enter 'survex' in the search filter to find the 'Import .3d
file' plugin, select it and click 'Install Plugin'.

When installed, a menu item 'Import .3d file' should appear on the
'Vector' drop-down menu in the main QGIS3 window, and (if enabled) a
.3d icon in a toolbar.

#### Manual installation

Manual installation is possible if the QGIS Python Plugins Repository
route is not available:

* clone or download the present GitHub repository;
* copy `survex_import` to `python/plugins/` in the current active
  profile, the location of which can be found from within QGIS3 by
  going to 'Settings &rarr; User Profiles &rarr; Open Active Profile
  Folder' (\*);
* enable the plugin in QGIS3 by going to 'Plugins &rarr; Manage and
  Install Plugins...'; make sure the box next to 'Import .3d file'
  is checked, in the 'Installed' tab.

(\*) Alternatively if you have `pb_tool` you can run `pb_tool
deploy` from _within_ the `survex_import` directory.

Debian users may be able to install from a packaged version:  
https://packages.debian.org/sid/qgis3-survex-import

### Usage

Selecting 'Import .3d file' (or clicking on the .3d icon) brings up a
window for the user to select a .3d file with a number of options:

* Import legs, with options to include splay, duplicate, and surface legs;
* Import stations, with the option to include surface stations (\*);
* Import passage data computed from LRUDs, with the option to use 
  clino weights (see below):
    - as polygons, with an option to include mean up / down data;
    - as walls;
    - as cross sections;
    - as traverses, showing the centrelines used for above;
* Optionally, set the co-ordinate reference system (CRS)
  from the .3d file or inherit from the QGIS3 project;
* Keep features from previous import(s) (optional);
* Select a GeoPackage (.gpkg) file to save results (optional).
  
(\*) In rare cases a station may be flagged both surface and
underground, in which case it is imported even if the 'surface' option
is left unchecked. 

On clicking OK, vector layers are created to contain the imported
features as desired.  Legs, walls, cross sections, and traverses are
imported as line strings in separate vector layers for convenience.
All created layers are saved to the GeoPackage file if requested (any
existing content is overwritten).

A CRS selector dialog box will appear, if neither of the CRS selector options 
are checked, or if CRS from .3d file is selected but there is no CRS in the .3d 
file.

If 'keep features' is selected, then previously imported features are
not discarded, and the newly-created layers will contain both the
previously imported features plus any new features imported from the
designated .3d file.  This choice allows processed survey data sets to
be combined from multiple sources.  Note that cumulative imports do
not result in features being overwritten, even if they happen to share
the same name, since all features are assigned a unique ID.

#### Therion users

An earlier version of the plugin introduced a mismatch between the CRS
and a proj4 string in the .3d file.  This bug is fixed since v1.2
and import of .3d files generated by Therion should now work.

### Imported attributes

All layers are created with an ELEVATION attribute, for convenience.
For stations this is the just the _z_ dimension.  For all
other features it is the mean elevation.

For station and leg layers, the following additional attribute fields
that are created:

* stations: NAME, and flags SURFACE, UNDERGROUND, ENTRANCE, EXPORTED,
  FIXED, ANON

* legs: NAME, STYLE, DATE1, DATE2, NLEGS (\*), LENGTH (\*), ERROR (\*),
  ERROR_HORIZ (\*), ERROR_VERT (\*), and flags SURFACE, DUPLICATE, SPLAY

(\*) These fields correspond to the error data reported in the .3d
file, which is only generated (by survex) if loop closures are present.

The flags are integer fields set to 0 or 1.

The STYLE field for legs is one of NORMAL, DIVING, CARTESIAN,
CYLPOLAR, or NOSURVEY.

The DATE fields are either the same, or represent a date
range, in the standard QGIS3 format YYYY-MM-DD.

If up / down data for passage polygons is requested, then the polygons have
MEAN_UP and MEAN_DOWN attributes in addition to ELEVATION.  These are
computed from the LRUD data for the two stations at either end of the
leg.  They can be used in 3d work (see end).

#### Passage walls

Passage walls (as line strings), polygons, and cross sections (as
lines) are computed from the left and right measurements in the LRUD
data in the same way that the `aven` viewer in survex displays passage
'tubes' (well, near enough...).  The direction of travel (bearing) is
worked out, and used to compute the positions of points on the left
and right hand passage walls.  These wall points are then assembled
into the desired features (walls, polygons, cross sections).

The direction of travel is inferred from the directions of the two
legs on either side of the given station (with special treatment for
stations at the start and end of a traverse).  In averaging these,
either the legs can be weighted equally (except true plumbs which
break the sequence), or the option is given to weight legs by the
cosine of the inclination (computed from the processed data, not the
actual clino reading).  The former is the default, and the latter
corresponds to checking the 'use clino weights' box in the import
dialog.  This alternative option downplays the significance of the
occasional steeply inclined leg in an otherwise horizontal passage.

One might want to do this for the following reason.  In the 'good old
days' steeply inclined legs were usually avoided as they are difficult
to sight a compass along, and instead good practice was to keep legs
mostly horizontal and add in the occasional plumbed leg when dealing
with inclined passages.  Also pitches were nearly always plumbed.  This
meant that inferring passage direction as a simple average, ignoring
plumbed legs, was most likely correct.  For modern surveying with
digital instruments, this is no longer the case: there is no loss of
accuracy for steeply inclined legs, and shining a laser down a pitch
at an off-vertical angle is no problem.  Therefore, the 'use clino
weights' option has been invented to give such steeply included legs
_less_ weight when inferring the passage direction.  Note that in a
steeply inclined _passage_, all legs are likely roughly equally
inclined, and therefore roughly equally weighted, so using clino
weights shouldn't affect the inferred direction of travel in that
situation.

TL;DR: if in doubt try first with the 'use clino weights' option selected.

Note that passage wall data is _inferred_ and any resemblance to 
reality may be pure coincidence: if in doubt, use splays!

### Co-ordinate reference system (CRS)

To be able to set the CRS from the `.3d` file on import, it's
necessary to add the appropriate `*cs` and `*cs out` commands to the
survex file.  If you can, specify the output CRS using `*cs out` in
the top level `.svx` file with an
[EPSG](https://en.wikipedia.org/wiki/EPSG_Geodetic_Parameter_Dataset)
number.  Some recommended options here are:

* `*cs out EPSG:7405` =
  [OSGB36](https://spatialreference.org/ref/epsg/osgb36-british-national-grid-odn-height/) (British
  National Grid);
* `*cs out EPSG:27700` = basically the same, [OSGB36](https://spatialreference.org/ref/epsg/osgb36-british-national-grid-odn-height/) (see below);
* `*cs out EPSG:25830` = [ETRS89 UTM zone
  30N](https://spatialreference.org/ref/epsg/etrs89-utm-zone-30n/)
  (Europe, −6°W to 0°W, and ETRS89 by country);
* `*cs out EPSG:32630` = [WGS84 UTM zone
  30N](https://spatialreference.org/ref/epsg/wgs-84-utm-zone-30n/)
  (World, N hemisphere, −6°W to 0°W, by country);
* `*cs out UTM30N` = exactly the same [WGS84 UTM zone
  30N](https://spatialreference.org/ref/epsg/wgs-84-utm-zone-30n/),
  but as a convenient mnemonic.

All these can of course be equally used as `*cs` commands for
specifying fixed points such as entrances.

For the first,
[EPSG:7405](https://spatialreference.org/ref/epsg/osgb36-british-national-grid-odn-height/)
officially includes
[ODN](https://en.wikipedia.org/wiki/Ordnance_datum) (Ordnance Datum
Newlyn) heights but in practice it doesn't make any difference to the
output that survex produces.  The [OS online
maps](https://osdatahub.os.uk/docs/wmts/technicalSpecification) though
use [EPSG:27700](https://spatialreference.org/ref/epsg/27700/).

The second and third options are UTM co-ordinate systems that both
cover most of western Europe, with the second
[EPSG:25830](https://spatialreference.org/ref/epsg/25830/) using the
[ETRS89
datum](https://en.wikipedia.org/wiki/European_Terrestrial_Reference_System_1989)
which what is officially recommended, even by the [UK
government](https://www.gov.uk/government/publications/open-standards-for-government/exchange-of-location-point),
and the third
[EPSG:32630](https://spatialreference.org/ref/epsg/32630/) using the
[WGS84 datum](https://en.wikipedia.org/wiki/World_Geodetic_System)
which is what corresponds to
[GPS](https://en.wikipedia.org/wiki/Global_Positioning_System)
co-ordinates in
[UTM](https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system)
format.  The difference between WGS84 and ETRS89 though is minimal:
the current (2023) [datum
shift](https://en.wikipedia.org/wiki/Geodetic_datum) is less than 1m
(≈ 2.5 cm per year since 1989) so for almost all practical purposes
where entrance locations are limited by the accuracy of hand-held GPS
devices, there is not really a distinction between WGS84 UTM
co-ordinates and ETRS89 UTM co-ordinates.  But if you wanted to be
finicky and use GPS entrance co-ordinates but have the output in a
more respectful European-centric CRS, you might have something like
```
*cs EPSG:32630 ; or *cs UTM30N ; GPS entrance co-ordinates are WGS84 UTM zone 30N,
*cs out EPSG:25830 ; when in Europe, output in ETRS89 UTM zone 30N
```
UTM stands for [Universal Transverse
Mercator](https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system)
by the way, and is a way of systematically metricising latitude and
longitude for a given geodetic datum.

For the time being AVOID:

*  `*cs out EPSG:3042` (ostensibly also ETRS89 UTM zone 30N)

since this messes up the grid convergence (see below).

For the UK, survex provides a convenient shorthand for [Ordnance
Survey (OS) grid
letter](https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid)
system.  For example `DowProv.svx` contains the following:
```
*cs OSGB:SD ; co-ordinates are 10-figure grid refs prefaced by SD
*cs out EPSG:7405 ; output is 12-figure OSGB36 + ODN height
```
This specifies that the fixed points (_e.g._ entrances) and the
location for the automatically calculated magnetic declination (see
below) are 10-figure grid references in the OS 100km x 100km SD grid
square, and that the output should be delivered using the all-numeric
12-figure British National Grid.

More details on the `*cs` and `*cs out` commands can be found in the
[survex manual](https://survex.com/docs/manual/datafile.htm).

#### How it works

The CRS defined by `*cs out` gets written as metadata into the `.3d`
file.  For example by using `dump3d` to inspect `DowProv.3d` one finds
the line
```
CS EPSG:7405
```
The QGIS plugin uses this metadata in the `.3d` file to identify the
CRS:

* if it specifies an EPSG number then that determines the CRS;
* otherwise it is assumed to be a
'[proj.4](https://en.wikipedia.org/wiki/PROJ)' string and an attempt
is made to create a CRS accordingly.

If the `.3d` file does not contain CS metadata then the input filter
fall backs onto a CRS selector dialog.

Note that currently some options permissible by survex, such as
specifying the CRS by an ESRI number, are not handled here.  For the
time being, the workaround is to identify what co-ordinate system
these are in QGIS language, then use the CRS selector dialog on
loading to set the layer(s) CRS appropriately, if necessary creating a
custom CRS beforehand, as described next.

In-depth explanations of co-ordinate reference systems in general can
be found in the Ordnance Survey booklet entitled _A Guide to
Coordinate Systems in Great Britain_ which can be found on the
Ordnance Survey website.

#### Custom CRS

In some cases it may be helpful to create beforehand a user-defined
CRS to select in the import dialog.  For example, if the `*cs`
commands are omitted from `DowProv.svx`, the resulting `.3d` file lacks
CS metadata and all co-ordinates are relative to the OS SD grid
square.  This `.3d` file can nevertheless still be imported into QGIS3
by first creating a custom CRS (in QGIS) for the SD grid square, then specifying
this custom CRS in the import dialog (or inheriting from the project
CRS if that is set appropriately).

For the OS SD grid square, the requisite custom CRS can be created
from the following proj.4 string
```
+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 
+x_0=100000 +y_0=-500000 +ellps=airy 
+towgs84=375,-111,431,0,0,0,0 +units=m +vunits=m +no_defs
```
(all on one line).  This is identical to the proj.4 string for the
British National Grid except that the `+x_0` and `+y_0` entries have
been shifted to a new false origin for the SD grid square.

Another example is the Austrian Loser plateau data that accompanies the
survex distribution as sample data.  Many of the cave entrances are 
recorded using a truncated form of the MGI / Gauss-Krüger (GK) Central Austria
CRS (the non-truncated form is
[EPSG:31255](https://spatialreference.org/ref/epsg/mgi-austria-gk-central/)).
This truncated CRS corresponds to a proj.4 string
```
+proj=tmerc +lat_0=0 +lon_0=13d20 +k=1 
+x_0=0 +y_0=-5200000 +ellps=bessel 
+towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +units=m +no_defs
```
(again this should be all on one line).  This is derived from the
proj.4 string for EPSG:31255 by changing the `+y_0` entry.

#### Magnetic declinations

This is potentially a large subject, and one can again refer to the
survex documentation for more details.  The modern approach, which
fits with the recommended use pattern for the `.3d` file importer, is
to use a `*declination auto` command with a position representative of
the cave survey data, and appropriate `*date` commands to reflect the
dates at which the compass bearings were taken.  There are a few
'gotchas' though:

* `*declination auto` should come _after_ the `*cs` and `*cs out`
commands in order that survex knows which input CRS is being used to
define the location used for the magnetic declination calculation, and
which output CRS should be used to calculate the grid convergence
(difference between grid north and true north): if `*declination auto`
comes _before_ `*cs out`, survex doesn't currently complain (it probably
should) but sets the grid convergence to zero;

* likewise avoid having a `*declination <specified>` in the top level
as this will have the side effect of setting the grid convergence _for
the whole survey_ to zero: if you do need to mix `*declination auto`
and `*declination <specified>` commands, limit the scope of the latter
by bracketing them in `*begin` and `*end` statements;

* for certain `*cs out` choices the 'interchange data' order is
(northing, easting) rather than the more usual (easting, northing).
An example is
[EPSG:3042](https://spatialreference.org/ref/epsg/etrs89-etrs-tm30/)
(see above), which is ostensibly the same as
[EPSG:25830](https://spatialreference.org/ref/epsg/25830/) and indeed
you cannot tell the difference either from the proj.4 string or the
so-called '[Well Known
Text](https://en.wikipedia.org/wiki/Well-known_text_representation_of_coordinate_reference_systems)'
either: one has to somehow
[know](https://gis.stackexchange.com/questions/224238/whats-the-difference-between-epsg-3043-and-epsg-25831)
these things, which seem to even be [implementation
dependent](https://gis.stackexchange.com/questions/434038/order-of-latitude-and-longitude-in-epsg4326)!
Currently if you use `*cs out` with one of these co-ordinate systems
in combination with `*declination auto`, it has the unfortunate effect
of throwing the grid convergence calculation out by 90&deg;, thus
completely screwing up the calculations (however, it is pretty obvious
that something extremely weird has happened).  Such CRS choices with
the interchange data order the 'wrong way around' should therefore be
avoided but to my knowledge there is always an equivalent CRS with the
interchange data order the right way around which can be used instead.
For instance, for ETRS89 UTM 30N do NOT use `*cs out EPSG:3042`,
rather use `*cs out EPSG:25830` which is the _exact_ same co-ordinate
system but with the interchange data order the right way around.

Putting this all together, you need something like the following:

```
*cs out <output CRS>
*cs <input CRS>
*declination auto <place> ; specify the location to use, in the input CRS
...
*date <date> ; declination at this date is automatically applied
...
*date <different date> ; declination automatically applied with different date
...
*begin <subsurvey>
*declination <specified> ; if you need to explicitly specify such...
*end <subsurvey>
```
Usually, this would be spread across separate `*include` files and
indeed one would normally split out each individual survey trip into
its own `.svx` file, with its own `*begin` and `*end`.  Discussion of
such 'best practice' for organising cave survey data is probably best
left to another place though!

### What to do next

Once the data is in QGIS3 one can do various things with it.

For example, features (stations, legs, polygons) can be colored
by elevation to mimic the behaviour of the `aven` viewer in survex
(hat tip Julian Todd for figuring some of this out).  The easiest way
to do this is to use the `.qml` style files provided in this
repository.  For example to color legs by depth, open the properties
dialog and under the 'Style' tab, at the bottom select 'Style &rarr;
Load Style', then choose one of the `color_lines_by_elevation*.qml`
style files.  This will apply a color scheme to the ELEVATION field
data with an inverted spectral color ramp.  Use `lines` for legs,
walls, cross sections and traverses; `points` for stations; and
`polygons` for polygons.

Two versions of these style files are provided.

The first version uses a graduated, inverted spectral color ramp to
color ranges of ELEVATION.  A small limitation is that these ranges
are not automatically updated to match the vertical range of the
current data set, but these can be refreshed by clicking on 'Classify'
(then 'Apply' to see the changes).

The second version uses a simple marker (line, or fill) with the
color set by an expression that maps the ELEVATION to a spectral
color ramp.  There are no ranges here, but rather these styles rely
on _zmin_ and _zmax_ variables being set (see 'Variables' tab under
layer &rarr; Properties).  By matching _zmin_ and _zmax_ between layers
with these styles, one can be assured that a common coloring scheme
is being applied.  A handy way to choose values for _zmin_ and _zmax_ is
to open the statistics panel (View &rarr; Panels &rarr; Statistics
Panel) to check out the min and max values in the ELEVATION field.

Color legs by date is possible using an expression like
`day(age("DATE1",'1970-01-01'))` (which gives the number of days
between the recorded DATE1 and the given date).  Color legs by error
is also possible.

Another thing one can do is enable 'map tips', for example to use the
NAME field.  Then, hovering the mouse near a station (or leg) will
show the name as a pop-up label.  For this to work:

* 'View &rarr; Map Tips' should be checked in the main menu;
* the map tip has to be set up to use the NAME field
  ('Properties &rarr; Display') in the relevant layer;
* the layer has to be the currently _selected_ one, though one can set
  the symbology to 'No symbols' to avoid having to display the features.

With a _digital elevation model_ (DEM raster layer) even more
interesting things can be done.  For example one can use raster
interpolation to find the surface elevation at
all the imported stations and save for example to a SURFACE_ELEV
field.  Then, one can use the field calculator to make a
DEPTH field containing the depth below surface, as SURFACE_ELEV minus
ELEVATION.  Stations can be colored by this, or the information can
be added to the 'map tip', etc.

Three dimensional views can be made directly in QGIS3 with 3D Map View
though more conveniently with the Qgis2threejs plugin, usually in
combination with a DEM.  To render features in 3d use the _z_
co-ordinate for points and lines.  Passage 'tubes' like those in aven
can be approximately rendered using LRUD polygons, with the base set to
floor level and the extruded height set to roof level.  To do this
import the MEAN_UP and MEAN_DOWN fields mentioned above and use the
field calculator to make two new floating point (double) fields: FLOOR
equal to ELEVATION minus MEAN_DOWN, and HEIGHT equal to MEAN_DOWN plus
MEAN_UP.  Then render the polygons with the _z_ co-ordinate as the
absolute FLOOR, and extruded height as HEIGHT.

Note that there is currently a bug in the Qgis2threejs plugin for
QGIS3 that causes a python error when features have data defined
properties, such as color by elevation using _zmin_ and _zmax_
variables (second option above).  The error looks like

```
AttributeError:'QgsSimpleLineSymbolLayer' object has no attribute 'dataDefinedProperty'
```
(The problem doesn't arise if features are colored by ranges as in the first
option above.)

A workaround is as follows.  First add _zmin_ and _zmax_ variables
into the layer properties (bring up the Properties window and go to
the Variables tab): use the green '+' button to add two new variables
then click on Apply and OK.  Choose values suited to the data set of
interest (as above), for example for the DowProv case they can be set
to 320 and 400 respectively (elevation in metres ODN).  Second, make
sure in the main QGIS map window the features in the layer of interest
(eg legs) use _only_ a simple style with a fixed colour (this is the
default).  Third, in the Qgis2threejs Exporter window, double click on
the layer of interest (eg legs) to bring up the layer properties, and
in the Style panel select Color &rarr; Expression.  Paste the
following into the Expression box.
```
ramp_color('Spectral',scale_linear("ELEVATION",@zmin,@zmax,1,0))
```
If all is well the lines in the Qgis2threejs Exporter preview window
should change to be colored by elevation.

Note that if you encountered the python error the plugin may not
function correctly any more.  It may have to reloaded (which can be
done if you have installed the 'Plugin Reloader' plugin); or QGIS3
restarted.

### Example

Sample precompiled georeferenced survey data can be found in the `DowProv` directory as
[`DowProv.3d`](example/DowProv.3d).

The corresponding GeoPackage file is in the `example` directory as
[`DowProv.gpkg`](example/DowProv.gpkg).

There is a [QGIS2 version](https://github.com/patrickbwarren/qgis-survex-import)
of this plugin but it is no longer being maintained.

### Changelog

v1.3.1 (current) - fix to handle how survex embeds EPSG numbers in the `.3d` file.  
v1.3 - upload to QGIS3 plugin repository  
v1.2 - fixed CRS import methods  
v1.1 - minor updates, tagged for packaging  
v1.0 - migrated and updated from QGIS 2.18 plugin

### Copying

Code in this repository is licensed under GPL v2:

This program is free software: you can redistribute it and / or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see
<http://www.gnu.org/licenses/>.

### Copyright

Copyright &copy; (2018-2023) Patrick B Warren.

The `.3d` file parser is based on a GPL v2 library to handle Survex 3D
files (`*.3d`), copyright &copy; 2008-2012 Thomas Holder,
http://sf.net/users/speleo3/; see
https://github.com/speleo3/inkscape-speleo.

