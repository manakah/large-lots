import zipfile
import shapefile
import sqlalchemy as sa
import geoalchemy as ga2
import csv

def loadShapefileFromZip(path, 
                         extract_path='raw', 
                         connection_string='postgresql://localhost:5432/database',
                         table_name='geom',
                         srid=3435):

    with zipfile.ZipFile(path, 'r') as zf:
        for fname in zf.namelist():
            if fname.endswith('.shp'):
                zf.extract(fname, path=extract_path)
                shp = open('%s/%s' % (extract_path, fname), 'rb')
            if fname.endswith('.dbf'):
                zf.extract(fname, path=extract_path)
                dbf = open('%s/%s' % extract_path, 'rb')
            if fname.endswith('.shx'):
                zf.extract(fname, path=extract_path)
                shx = open('%s/%s' % extract_path, 'rb')
        
    shape_reader = shapefile.Reader(shp=shp, dbf=dbf, shx=shx)

    fields = shape_reader.fields[1:]
    
    GEO_TYPE_MAP = {
        'C': sa.String,
        'N': sa.Integer,
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
    columns.append(sa.Column('geom', ga2.Geometry(geo_type, srid=3435)))

    engine = sa.create_engine(connection_string, 
                           convert_unicode=True, 
                           server_side_cursors=True)

    table = sa.Table(table_name, sa.MetaData(), *columns)
    
    table.drop(engine, checkfirst=True)
    table.create(engine)

    ins = table.insert()
    shp_count = 0
    values = []
    
    records = shape_reader.iterShapeRecords()
    
    with open('%s/%s.csv' % (extract_path, table_name), 'w') as f:
        writer = csv.DictWriter(f, table.columns.keys())
        writer.writeheader()

        for record in records:
            d = {}
            for k,v in zip(table.columns.keys(), record.record):
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

