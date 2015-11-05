import zipfile
import shapefile
import sqlalchemy as sa
import geoalchemy2 as ga2
import csv
from shapely.geometry import MultiPolygon, asShape
import psycopg2

def openShapefile(zipfile_path, extract_path):
    with zipfile.ZipFile(zipfile_path, 'r') as zf:
        for fname in zf.namelist():
            if fname.endswith('.shp'):
                zf.extract(fname, path=extract_path)
                shp = open('%s/%s' % (extract_path, fname), 'rb')
            if fname.endswith('.dbf'):
                zf.extract(fname, path=extract_path)
                dbf = open('%s/%s' % (extract_path, fname), 'rb')
            if fname.endswith('.shx'):
                zf.extract(fname, path=extract_path)
                shx = open('%s/%s' % (extract_path, fname), 'rb')
        
    return shapefile.Reader(shp=shp, dbf=dbf, shx=shx)

def makeTable(fields, engine, table_name):
    
    GEO_TYPE_MAP = {
        'C': sa.String,
        'N': sa.Float,
        'L': sa.Boolean,
        'D': sa.TIMESTAMP,
        'F': sa.Float
    }

    columns = []
    for field in fields:
        fname, d_type, f_len, d_len = field
        col_type = GEO_TYPE_MAP[d_type]
        kwargs = {}
        
        if d_type == 'C':
            col_type = col_type(f_len)
        if fname == 'objectid':
            kwargs['primary_key'] = True

        columns.append(sa.Column(fname.lower(), col_type, **kwargs))

    geo_type = 'MULTIPOLYGON'
    columns.append(sa.Column('geom', ga2.Geometry(geo_type, srid=srid)))


    table = sa.Table(table_name, sa.MetaData(), *columns)
    
    table.drop(engine, checkfirst=True)
    table.create(engine)
    
    return table

def writeOutCSV(records, 
                fieldnames, 
                extract_path, 
                table_name,
                srid):
    
    with open('%s/%s.csv' % (extract_path, table_name), 'w') as f:
        writer = csv.DictWriter(f, fieldnames)
        writer.writeheader()

        for record in records:
            d = {}
            for k,v in zip(fieldnames, record.record):
                try:
                    d[k] = v.decode('latin-1').replace(' ', '')
                except AttributeError:
                    d[k] = v
            try:
                geom = asShape(record.shape.__geo_interface__)
            except AttributeError as e:
                continue
            geom = MultiPolygon([geom])
            d['geom'] = 'SRID=%s;%s' % (srid, geom.wkt)
            writer.writerow(d)

def bulkLoad(extract_path, 
             table_name,
             engine):
    
    copy_st = ''' 
        COPY %s 
        FROM STDIN 
        WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',')  
    ''' % table_name

    with open('%s/%s.csv' % (extract_path, table_name), 'r') as f:
        conn = engine.raw_connection()

        try:
            cursor = conn.cursor()
            cursor.copy_expert(copy_st, f)
            conn.commit()
        except psycopg2.ProgrammingError as e:
            conn.rollback()
            raise e
        
        conn.close()

    engine.dispose()

if __name__ == "__main__":
    import sys
    
    zipfile_path = sys.argv[1]
    extract_path = 'raw'
    connection_string = 'postgresql://localhost:5432/test_database'
    table_name = 'test_table'
    srid = 3435

    shape_reader = openShapefile(zipfile_path, extract_path)
    
    engine = sa.create_engine(connection_string, 
                              convert_unicode=True, 
                              server_side_cursors=True)

    table = makeTable(shape_reader.fields[1:], engine, table_name)
    
    records = shape_reader.iterShapeRecords()
    
    writeOutCSV(records, table.columns.keys(), extract_path, table_name, srid)

    bulkLoad(extract_path, table_name, engine)
