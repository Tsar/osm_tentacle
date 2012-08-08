#!/bin/sh
DBNAME="spb_elagin_ostrov"

createdb $DBNAME
psql -d $DBNAME -c "CREATE EXTENSION hstore;"
psql -d $DBNAME -f /usr/share/postgresql/9.1/contrib/postgis-1.5/postgis.sql
psql -d $DBNAME -f /usr/share/postgresql/9.1/contrib/postgis-1.5/spatial_ref_sys.sql
psql -d $DBNAME -f /home/volkov/work/osmosis/package/script/pgsnapshot_schema_0.6.sql

/home/volkov/work/osmosis/package/bin/osmosis --read-xml /home/volkov/work/data/osms/${DBNAME}.osm --write-pgsql user=volkov database=${DBNAME} password=********
