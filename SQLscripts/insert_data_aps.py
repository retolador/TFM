import pandas as pd
#import arules as ar
from pandas import DataFrame


try:
    connection = psycopg2.connect(user = "postgres",
                                  password = "pass@#29",
                                  host = "127.0.0.1",
                                  port = "5432",
                                  database = "postgres_db")

    cursor = connection.cursor()

    print("PostgreSQL connection is open")

    dataframe = pd.read_csv()

    for index_fila,fila in dataframe.iterrows():
        query = """INSERT into tfmpausalasapinformacioAP(apmac, name, latitud, longitud, zonaname) values('%s','%s',%s,%s,'%s');
                """% ( str(fila['mac']), str(fila['name']), str(fila['lat']), str(fila['lng']), str(fila['zona_name']))

        try:
            cursor.execute(query)
            connection.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            print("Error: %s" % error)
            conn.rollback()
            cursor.close()
            return 1

except (Exception, psycopg2.DatabaseError) as error :
    print ("Error while connecting PostgreSQL table", error)




finally:
#closing database connection.
    if(connection):
        cursor.close()
        connection.close()
        print("PostgreSQL connection is closed")
