# QGIS3 plugin to import survex .3d files

#### _For the older QGIS 2 plugin visit https://github.com/patrickbwarren/qgis-survex-import_

### Features

* no dependencies, natively reads binary v8 format survex .3d files;
* import stations and legs with full metadata;
* create passage walls, cross-sections, and polygons from LRUD data;
* all features have _z_ dimensions, and (mean) elevations to assist coloring;
* the co-ordinate system can be set from a proj4 string embedded in .3d file;
* results can be saved immediately into a GeoPackage shape file.

### Installation

To install the plugin:

* clone or download this repository;
* copy `survex_import` to `python/plugins/` in the current active
  profile, the location of which can be found from within QGIS3 by
  going to 'Settings &rarr; User Profiles &rarr; Open Active Profile
  Folder' (\*);
* enable the plugin in QGIS3 by going to 'Plugins &rarr; Manage and
  Install Plugins...'; make sure the box next to 'Import .3d file'
  is checked, in the 'Installed' tab.

(\*) Alternatively if you have `pb_tool` you can run `pb_tool
deploy` from _within_ the `survex_import` directory.

When installed, a menu item 'Import .3d file' should appear on the
'Vector' drop-down menu in the main QGIS3 window, and (if enabled) a
.3d icon in a toolbar.

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
  from .3d file or inherit from QGIS3 project;
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

#### Imported attributes

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

For the most part importing the CRS from the .3d file should work as
expected if the survey data has been georeferenced using the survex
`*cs` and `*cs out` commands.  If it doesn't work, or this information
isn't present, one can instead inherit the CRS from the current QGIS3
project.  If neither of these options is selected, a CRS dialog box
may appear for each layer, or a default CRS will be chosen
automatically, depending on the system-wide QGIS3 settings.
To maximise the likelihood that CRS import from .3d file works as
expected, use an EPSG code in the `*cs out` survex command rather than
a PROJ.4 string.

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
with rough ground.  Also pitches were nearly always plumbed.  This
meant that inferring passage direction as a simple average, ignoring
plumbed legs, was most likely correct.  For modern surveying with
digital instruments, this is no longer the case: there is no loss of
accuracy for steeply inclined legs, and shining a laser down a pitch
at an off-vertical angle is no problem.  Therefore, the 'use clino
weights' option has been invented to give such steeply included legs
less weight when inferring the passage direction.  Note that in a
steeply inclined _passage_, all legs are likely roughly equally
inclined, and therefore roughly equally weighted, so using clino
weights shouldn't affect the inferred direction of travel in that
situation.

_TL;DR: if in doubt try first with the 'use clino weights' option selected._

Note that passage wall data is _inferred_ and any resemblance to 
reality may be pure coincidence: if in doubt, use splays!

#### Co-ordinate reference systems (CRS)

To be integrated with other sources of geographical information such as 
maps, GPS tracks, and so on, an imported survey should be _georeferenced_, which 
means the _spatial reference system_ (SRS) should be specified; 
in QGIS parlance this is referred to as a _co-ordinate reference system_ (CRS).  

The easiest way to do this is to use survex `*cs` commands in the .svx file to 
set an output CRS in the .3d file, 
then select 'CRS from .3d file' in the import 
dialog.  For example the `DowProv.svx` file in the examples contains

```
*cs OSGB:SD
*cs out EPSG:7405
```
which specifies that the entrance `*fix`'s are in the Ordnance Survey SD grid 
square, and that the output  should use the Ordnance Survey all-numeric 
British National Grid (EPSG:7405).  

If one only has access to the .3d file (for example, it is provided 'as is' 
without source data), one can check for a CRS by using `dump3d`: look for an 
entry near the top which begins 'CS'.  For example `DowProv.3d` contains 

```
CS +init=epsg:7405 +no_defs
```
This is in fact a proj4 string that specifies the CRS.
Note that if an EPSG number is specified in the CS string, the input filter uses that
to fix the CRS.  Otherwise, a CRS is created using the proj4 string directly.

If the .3d file does not 
contain this information, the input filter will fall back onto a CRS selector
dialog.  In such cases, it may be helpful to create a user-defined CRS 
such as for an Ordnance Survey 100km x 100km square.  For example, for the 
SD square, create a custom CRS in QGIS with the following proj4 string

```
+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 
+x_0=100000 +y_0=-500000 +ellps=airy 
+towgs84=375,-111,431,0,0,0,0 +units=m +vunits=m +no_defs
```
(all on one line).  This is identical to the proj4 string for the British
National Grid (EPSG:7405) except that the `+x_0` and `+y_0` entries 
have been shifted to the origin of the SD square.

Another example is Austria for which many of the older cave entrances are 
recorded using a truncated form of the MGI / Austria Gauss-Krüger (GK) Central 
SRS (EPSG:31255),

```
+proj=tmerc +lat_0=0 +lon_0=13d20 +k=1 
+x_0=0 +y_0=-5200000 +ellps=bessel 
+towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +units=m +no_defs
```
(again this should be all on one line).

For more details and examples of survex `*cs` commands see 
[cave_surveying_and_gis.pdf](cave_surveying_and_gis.pdf) in the present 
repository.

In-depth explanations of co-ordinate reference systems can be found in the 
Ordnance Survey booklet entitled _A Guide to Coordinate Systems in 
Great Britain_ which can be found on the Ordnance Survey website.

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

Sample georeferenced survey data can be found in the `example` directory as
[`DowProv.3d`](example/DowProv.3d).

The corresponding GeoPackage file is in the `example` directory as
[`DowProv.gpkg`](example/DowProv.gpkg).

Further notes on cave surveying and GIS are in 
[`cave_surveying_and_GIS.pdf`](cave_surveying_and_GIS.pdf) in `docs`.

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

The .3d file parser is based on a GPL v2 library to handle Survex 3D files (`*.3d`),
copyright &copy; 2008-2012 Thomas Holder, http://sf.net/users/speleo3/; 
see https://github.com/speleo3/inkscape-speleo.

Modifications and extensions copyright &copy; (2018-2020) Patrick B Warren.
